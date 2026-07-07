# Benchmark cases

Real editorial projects used to evaluate SAGE against human-made finals.
Cases are general-purpose: any suitable video project from any user or
content stream can become a case. `content_stream` is a descriptive tag
only — nothing in SAGE or this framework branches on it.

## Structure

    cases/<case_id>/
      case.json        manifest (sources, reference final, caveats)
      inputs/          before XML(s), raw transcript JSON(s), reference final
      derived/         generated: profile.json, SAGE-ingest transcripts
      runs/            comparison reports per run (label = provider+date)

## Operator workflow

1. **Ingest** a new case (any number of sources; after/transcripts optional):

       python scripts/ingest_case.py --id my_case --title "My Case" \
           --source main:/path/before.xml:/path/transcript.json \
           --after /path/final.xml

   Ingest profiles everything immediately and records caveats (e.g.
   transcript/timeline misalignment) in the manifest permanently.

2. **Profile** — feasibility per source (V1 scope, provider context fit)
   plus the human-edit baseline (what the human kept; recall = SAGE's
   material ceiling from that source):

       python scripts/benchmark_case.py profile my_case

3. **Prepare** a live run — writes the SAGE-ingest transcript and prints
   the exact pre-flight + live-loop commands (human approval gate intact):

       python scripts/benchmark_case.py prepare my_case --source main

4. **Compare** any candidate XML (a SAGE output from mock/claude/val — same
   case, same comparator, so providers are directly comparable) against the
   reference final; the report is stored under runs/<label>/ for regression
   tracking:

       python scripts/benchmark_case.py compare my_case out.xml \
           --source main --run-label claude-2026-07-07

## What comparison can and cannot prove

It measures WHICH source material an edit kept (recall/precision/Jaccard on
merged source spans, per media file matched by name), the order it plays in,
runtime, and shot statistics; and it lists the largest divergences with
transcript excerpts for human review. It does NOT measure trim finesse, mix,
grade, b-roll placement, music, or multi-track craft, and its numbers never
grade an edit — they locate the differences a human should look at.

## Privacy note

Cases contain real interview transcripts and media file names. Treat this
directory according to the material's consent/policy status before pushing
to any shared repository.
