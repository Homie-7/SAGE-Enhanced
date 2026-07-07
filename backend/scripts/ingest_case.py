#!/usr/bin/env python3
"""Ingest a real editorial project as a SAGE benchmark case.

Usage (repeat --source for multi-source cases):
  python scripts/ingest_case.py --id my_case --title "My Case" \\
      --source main:/path/before.xml:/path/transcript.json \\
      --after /path/final.xml [--stream ANY_TAG] [--notes notes.md]

Source syntax:  <source_id>:<before_xml_path>[:<transcript_json_path>]

Copies files into backend/benchmarks/cases/<id>/, writes case.json, and runs
an immediate profile so ingest problems surface at ingest time.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.benchmarks.manifest import CaseManifest, CaseSource, cases_root  # noqa: E402
from app.benchmarks.timeline import profile_timeline  # noqa: E402
from app.benchmarks.transcript import (  # noqa: E402
    alignment_verdict, load_word_timed_json)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--stream", default=None,
                    help="free content-stream tag; never changes behaviour")
    ap.add_argument("--source", action="append", required=True,
                    metavar="ID:BEFORE_XML[:TRANSCRIPT_JSON]")
    ap.add_argument("--after", type=Path, default=None)
    ap.add_argument("--notes", type=Path, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    case_dir = cases_root() / args.id
    if case_dir.exists() and not args.force:
        print(f"BLOCKER: {case_dir} exists (use --force to replace)."); return 2
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "inputs").mkdir(parents=True)
    (case_dir / "derived").mkdir()
    (case_dir / "runs").mkdir()

    caveats: list[str] = []
    sources: list[CaseSource] = []
    for raw in args.source:
        parts = raw.split(":", 2)
        if len(parts) < 2:
            print(f"BLOCKER: bad --source '{raw}'."); return 2
        sid, before = parts[0], Path(parts[1])
        transcript = Path(parts[2]) if len(parts) > 2 and parts[2] else None
        if not before.is_file():
            print(f"BLOCKER: {before} not found."); return 2
        before_rel = f"inputs/{sid}_before{before.suffix}"
        shutil.copy2(before, case_dir / before_rel)
        transcript_rel = None
        if transcript is not None:
            if not transcript.is_file():
                print(f"BLOCKER: {transcript} not found."); return 2
            transcript_rel = f"inputs/{sid}_transcript{transcript.suffix}"
            shutil.copy2(transcript, case_dir / transcript_rel)
        sources.append(CaseSource(source_id=sid, before_xml=before_rel,
                                  transcript_json=transcript_rel, label=sid))

        # profile at ingest — problems surface now, and caveats are recorded
        profile = profile_timeline(case_dir / before_rel)
        print(f"source '{sid}': {profile.frame_rate}fps, "
              f"{profile.clip_count} clips, {len(profile.media_keys)} media, "
              f"{profile.duration_s:.0f}s")
        if transcript_rel:
            t = load_word_timed_json(case_dir / transcript_rel)
            ok, msg = alignment_verdict(t, profile.duration_s)
            print(("  ✓ " if ok else "  ⚠ ") + msg)
            if not ok:
                caveats.append(f"source '{sid}': {msg}")

    after_rel = None
    if args.after is not None:
        if not args.after.is_file():
            print(f"BLOCKER: {args.after} not found."); return 2
        after_rel = f"inputs/reference_after{args.after.suffix}"
        shutil.copy2(args.after, case_dir / after_rel)
        p = profile_timeline(case_dir / after_rel)
        print(f"reference after: {p.frame_rate}fps, {p.clip_count} clips, "
              f"{p.duration_s:.0f}s")

    notes = args.notes.read_text() if args.notes else None
    manifest = CaseManifest(
        case_id=args.id, title=args.title, content_stream=args.stream,
        sources=sources, reference_after_xml=after_rel,
        notes=notes, caveats=caveats)
    manifest.save(case_dir)
    print(f"\ncase '{args.id}' ingested at {case_dir}")
    if caveats:
        print("recorded caveats:")
        for c in caveats:
            print(f"  ⚠ {c}")
    print(f"next: python scripts/benchmark_case.py profile {args.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
