#!/usr/bin/env python3
"""Audit a real Premiere Pro FCP7-XML export for SAGE compatibility.

Usage:
    python scripts/audit_real_export.py path/to/export.xml [--rebuild-probe]

Prints a precise readiness report:
  - deterministic facts the parser extracted,
  - every warning (dropped-intent elements, unknowns),
  - hard blockers, if any,
  - with --rebuild-probe: performs a tiny 2-beat rebuild across the first
    video clipitem and runs the full XML integrity suite on the result, so
    structural rebuild problems surface before any LLM is involved.

Nothing here can prove Premiere import success — that check happens in
Premiere itself (canonical file 05 treats import safety as a warning, never
a certainty).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.state import BeatMapping, RebuildPlan  # noqa: E402
from app.schemas.state import RebuildStyle  # noqa: E402
from app.validation.report import ReportBuilder  # noqa: E402
from app.validation.xml_integrity import check_output_xml  # noqa: E402
from app.xmlengine.parser import XMLParseError, parse_source_xml  # noqa: E402
from app.xmlengine.rebuilder import RebuildError, rebuild_sequence  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("xml", type=Path)
    ap.add_argument("--rebuild-probe", action="store_true",
                    help="attempt a minimal deterministic rebuild + integrity check")
    args = ap.parse_args()

    print(f"== SAGE real-export audit: {args.xml} ==\n")
    try:
        facts = parse_source_xml(args.xml)
    except XMLParseError as exc:
        print(f"BLOCKER — parse failed: {exc}")
        return 2

    print(f"frame rate      : {facts.frame_rate} (ntsc={facts.ntsc})")
    print(f"video tracks    : {facts.video_tracks}")
    print(f"audio tracks    : {facts.audio_tracks}")
    print(f"clipitems       : {len(facts.clipitems)}")
    print(f"file ids        : {', '.join(facts.file_ids) or '(none)'}")
    print(f"multicam        : {facts.multicam_detected}")
    print(f"external audio  : {facts.external_audio_detected}")

    print("\n-- clipitems --")
    for c in facts.clipitems:
        print(f"  {c.track:>3}  {c.clipitem_id:<22} file={c.file_id or '?':<10} "
              f"start={c.start} end={c.end} in={c.in_point} out={c.out_point} "
              f"links={len(c.links)}")

    if facts.warnings:
        print("\n-- warnings (review, not blockers) --")
        for w in facts.warnings:
            print(f"  ⚠ {w}")

    blockers: list[str] = []
    if facts.frame_rate is None:
        blockers.append("No readable sequence frame rate.")
    if not facts.clipitems:
        blockers.append("No clipitems in sequence.")
    if not any(c.track and c.track.startswith("V") for c in facts.clipitems):
        blockers.append("No video clipitems found.")
    if facts.multicam_detected:
        blockers.append("Multicam/nested sequence detected — flatten before SAGE V1.")

    if blockers:
        print("\n-- BLOCKERS --")
        for b in blockers:
            print(f"  ✗ {b}")
        return 2

    if args.rebuild_probe:
        print("\n-- rebuild probe --")
        v = next(c for c in facts.clipitems if c.track and c.track.startswith("V")
                 and c.start is not None and c.end is not None)
        rate = facts.frame_rate or 25.0
        s0 = v.start / rate
        span = min(3.0, max(1.0, (v.end - v.start) / rate / 4))
        plan = RebuildPlan(style="B", mappings=[
            BeatMapping(bid="PROBE1", source_file_id=v.file_id or facts.file_ids[0],
                        in_seconds=s0 + span, out_seconds=s0 + 2 * span),
            BeatMapping(bid="PROBE2", source_file_id=v.file_id or facts.file_ids[0],
                        in_seconds=s0, out_seconds=s0 + span),
        ])
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "probe.xml"
            try:
                rebuild_sequence(args.xml, plan, out)
            except RebuildError as exc:
                print(f"  ✗ rebuild failed: {exc}")
                return 2
            rb = ReportBuilder()
            check_output_xml(out, RebuildStyle.B_EDITORIAL_USABILITY_FIRST, rb)
            report = rb.build()
            for chk in report.checks:
                mark = {"pass": "✓", "warn": "⚠", "fail": "✗"}[chk.outcome.value]
                print(f"  {mark} {chk.name}: {chk.detail or chk.outcome.value}")
            if report.blockers:
                for b in report.blockers:
                    print(f"  ✗ {b.check}: {b.why_it_blocks} → {b.what_is_needed}")
                return 2
        print("  rebuild probe OK (import check still happens in Premiere)")

    print("\nReadiness: OK for the SAGE core loop. Final proof is a Premiere import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
