# Benchmark fixtures

Each benchmark is one real (or realistic) SAGE job used to test the full loop
deterministically and to compare provider behaviour without changing the
canonical workflow.

## Structure per benchmark

```
<benchmark_name>/
├── benchmark.json        # metadata + setup answers + success criteria
├── inputs/
│   ├── source.xml        # synced source XML (Premiere/FCP7 export)
│   ├── transcript.txt    # matching transcript
│   └── notes.md          # optional brief/notes
└── expected/
    ├── mock_tasks/       # fixture responses per LLM task (drives MockProvider)
    │   ├── source_audit.json
    │   ├── contributor_roster.json
    │   ├── material_classification.json
    │   ├── function_grouping.json
    │   ├── mode_and_structure.json
    │   ├── paper_edit.json
    │   └── rebuild_plan.json
    ├── paper_edit.json   # golden approved paper edit
    └── output_checks.json# assertions the rebuilt XML must satisfy
```

## Benchmarks

1. **teacher_success_story** — single-contributor testimonial/impact piece.
   Exercises: warm tone inference, value-first opening, strongest resolved
   close, Preset 1/2 territory.
2. **lnd_specialist_showcase** — role/concept showcase where clarity matters.
   Exercises: clarity requirement, definition/explainer beat, representation
   summary, Preset 3/5 territory.
3. **benchmark_03_placeholder** — reserved third benchmark (suggested: a
   tutorial/walkthrough or a cleanup-first assembly, to cover a different
   mode). Populate when source material is chosen.

## Rules

- Fixtures contain no confidential material unless the repo remains internal.
- `expected/mock_tasks/` must validate against the task output schemas
  (backend/app/schemas/tasks.py) — CI should enforce this.
- Real source XML should come from actual Premiere exports; do not hand-craft
  structure the parser will never see in the wild.
