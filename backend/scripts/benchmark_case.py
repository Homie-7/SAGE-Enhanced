#!/usr/bin/env python3
"""Operate on benchmark cases.

  list                          all ingested cases
  profile <case>                timelines, feasibility, human-edit baseline
  prepare <case> [--source ID]  write SAGE-ingest transcript + print the
                                exact live-loop command
  compare <case> <candidate_xml> [--source ID] [--run-label NAME]
                                compare any candidate XML (e.g. SAGE output)
                                against the case's reference final

Reports are printed and written to <case>/derived/ (profile) or
<case>/runs/<label>/ (comparisons) as JSON for regression tracking and
provider comparison (mock vs claude vs val: same case, different runs,
same comparator).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.benchmarks.compare import compare_timelines  # noqa: E402
from app.benchmarks.feasibility import assess_source  # noqa: E402
from app.benchmarks.manifest import CaseManifest, cases_root, list_cases  # noqa: E402
from app.benchmarks.timeline import profile_timeline  # noqa: E402
from app.benchmarks.transcript import (  # noqa: E402
    load_word_timed_json, words_on_source_clock)

CONFIGS = Path(__file__).resolve().parents[2] / "prompts" / "configs"


def _load(case_id: str) -> tuple[CaseManifest, Path]:
    case_dir = cases_root() / case_id
    if not (case_dir / "case.json").is_file():
        print(f"BLOCKER: no case '{case_id}' at {case_dir}"); raise SystemExit(2)
    return CaseManifest.load(case_dir), case_dir


def _print_comparison(rep) -> None:
    print(f"  media shared/ref-only/cand-only: {len(rep.shared_media)}/"
          f"{len(rep.reference_only_media)}/{len(rep.candidate_only_media)} "
          f"(lane: {rep.mediatype})")
    print(f"  runtime: reference {rep.reference_runtime_s:.0f}s vs "
          f"candidate {rep.candidate_runtime_s:.0f}s")
    print(f"  kept source material: reference {rep.reference_kept_s:.0f}s, "
          f"candidate {rep.candidate_kept_s:.0f}s, overlap {rep.overlap_s:.0f}s")
    print(f"  recall {rep.recall:.0%} · precision {rep.precision:.0%} · "
          f"jaccard {rep.jaccard:.0%} · order similarity "
          f"{rep.order_similarity if rep.order_similarity is not None else 'n/a'}")
    print(f"  shots: {rep.reference_shots} vs {rep.candidate_shots} "
          f"(avg {rep.reference_avg_shot_s:.1f}s vs {rep.candidate_avg_shot_s:.1f}s)")
    if rep.divergences:
        print("  top divergences for human review:")
        for d in rep.divergences[:6]:
            print(f"    [{d.kept_by:<15}] {d.media_key} "
                  f"{d.source_in_s:.0f}–{d.source_out_s:.0f}s ({d.duration_s:.0f}s)")
            if d.transcript_excerpt:
                print(f"        “{d.transcript_excerpt}”")
    print("  limits: " + " ".join(rep.limits))


def cmd_list() -> int:
    for m in list_cases():
        print(f"{m.case_id:<16} {m.title} "
              f"[stream={m.content_stream or '-'}] sources={len(m.sources)} "
              f"after={'yes' if m.reference_after_xml else 'no'} "
              f"caveats={len(m.caveats)}")
    return 0


def cmd_profile(case_id: str) -> int:
    manifest, case_dir = _load(case_id)
    print(f"== case {case_id}: {manifest.title} ==")
    for c in manifest.caveats:
        print(f"⚠ caveat: {c}")

    derived = case_dir / "derived"
    derived.mkdir(exist_ok=True)
    out: dict = {"case_id": case_id, "sources": {}, "human_baseline": None}

    after_profile = None
    if manifest.reference_after_xml:
        after_profile = profile_timeline(case_dir / manifest.reference_after_xml)
        print(f"\nreference final: '{after_profile.sequence_name}' "
              f"{after_profile.duration_s:.0f}s, {after_profile.clip_count} clips, "
              f"V{after_profile.video_tracks}/A{after_profile.audio_tracks}, "
              f"{len(after_profile.media_keys)} media")

    for src in manifest.sources:
        print(f"\n-- source '{src.source_id}' --")
        profile = profile_timeline(case_dir / src.before_xml)
        print(f"before: '{profile.sequence_name}' {profile.duration_s:.0f}s, "
              f"{profile.clip_count} clips, "
              f"V{profile.video_tracks}/A{profile.audio_tracks}, "
              f"{len(profile.media_keys)} media")
        transcript = None
        if src.transcript_json:
            transcript = load_word_timed_json(case_dir / src.transcript_json)
            print(f"transcript: {transcript.total_speech_s:.0f}s speech, "
                  f"{len(transcript.words)} words, "
                  f"{transcript.named_speaker_count}/{transcript.speaker_count} "
                  "named speakers")
        feas = assess_source(src.source_id, profile, transcript, CONFIGS)
        for item in feas.items:
            print(("  ✓ " if item.ok else "  ✗ ") + f"{item.name}: {item.detail}")
        for provider, verdict in feas.provider_fit.items():
            print(f"  · provider {provider}: {verdict}")
        entry = {"feasibility": feas.model_dump()}

        if after_profile is not None:
            # Human-edit baseline: what did the human keep from THIS source?
            words = None
            if transcript is not None and all(
                    i.ok for i in feas.items
                    if i.name == "transcript_alignment"):
                words = words_on_source_clock(profile, transcript)
            rep = compare_timelines(after_profile, profile,
                                    source_words=words)
            print("\n  human-edit baseline (reference final vs this before):")
            print("  (recall here = share of the final's kept material that "
                  "exists in this before timeline — SAGE's ceiling from this "
                  "source)")
            _print_comparison(rep)
            entry["human_baseline"] = rep.model_dump()

        out["sources"][src.source_id] = entry

    (derived / "profile.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwritten: {derived / 'profile.json'}")
    return 0


def cmd_prepare(case_id: str, source_id: str | None) -> int:
    manifest, case_dir = _load(case_id)
    src = (next((s for s in manifest.sources if s.source_id == source_id), None)
           if source_id else manifest.sources[0])
    if src is None:
        print(f"BLOCKER: no source '{source_id}' in case."); return 2
    if not src.transcript_json:
        print(f"BLOCKER: source '{src.source_id}' has no transcript."); return 2

    transcript = load_word_timed_json(case_dir / src.transcript_json)
    sage_txt = case_dir / "derived" / f"{src.source_id}_transcript_sage.txt"
    sage_txt.parent.mkdir(exist_ok=True)
    sage_txt.write_text(transcript.sage_text)
    xml = case_dir / src.before_xml
    print(f"SAGE transcript written: {sage_txt}")
    for c in manifest.caveats:
        if src.source_id in c:
            print(f"⚠ {c}")
    print("\npre-flight:")
    print(f"  python scripts/audit_real_export.py '{xml}' --rebuild-probe")
    print("live run (human approval gate included):")
    print(f"  python scripts/run_live_loop.py --xml '{xml}' "
          f"--transcript '{sage_txt}' --provider <mock|claude|val> "
          f"--name '{manifest.title} [{src.source_id}]'")
    print("then compare the output:")
    print(f"  python scripts/benchmark_case.py compare {case_id} "
          f"<output.xml> --source {src.source_id} --run-label <provider-date>")
    return 0


def cmd_compare(case_id: str, candidate_xml: Path,
                source_id: str | None, run_label: str | None) -> int:
    manifest, case_dir = _load(case_id)
    if not manifest.reference_after_xml:
        print("BLOCKER: case has no reference final to compare against."); return 2
    if not candidate_xml.is_file():
        print(f"BLOCKER: {candidate_xml} not found."); return 2

    reference = profile_timeline(case_dir / manifest.reference_after_xml)
    candidate = profile_timeline(candidate_xml)

    source_words: dict = {}
    for src in manifest.sources:
        if source_id and src.source_id != source_id:
            continue
        if src.transcript_json:
            t = load_word_timed_json(case_dir / src.transcript_json)
            p = profile_timeline(case_dir / src.before_xml)
            from app.benchmarks.transcript import alignment_verdict
            aligned, _ = alignment_verdict(t, p.duration_s)
            if aligned:
                for key, ws in words_on_source_clock(p, t).items():
                    source_words.setdefault(key, ws)

    rep = compare_timelines(reference, candidate,
                            source_words=source_words or None)
    print(f"== compare: candidate {candidate_xml.name} vs reference final ==")
    _print_comparison(rep)

    label = run_label or datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")
    run_dir = case_dir / "runs" / label
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "comparison.json").write_text(rep.model_dump_json(indent=2) + "\n")
    print(f"\nwritten: {run_dir / 'comparison.json'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("profile"); p.add_argument("case_id")
    p = sub.add_parser("prepare"); p.add_argument("case_id")
    p.add_argument("--source", default=None)
    p = sub.add_parser("compare"); p.add_argument("case_id")
    p.add_argument("candidate_xml", type=Path)
    p.add_argument("--source", default=None)
    p.add_argument("--run-label", default=None)
    a = ap.parse_args()
    if a.cmd == "list":
        return cmd_list()
    if a.cmd == "profile":
        return cmd_profile(a.case_id)
    if a.cmd == "prepare":
        return cmd_prepare(a.case_id, a.source)
    return cmd_compare(a.case_id, a.candidate_xml, a.source, a.run_label)


if __name__ == "__main__":
    raise SystemExit(main())
