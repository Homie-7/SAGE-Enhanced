"""Regenerate the teacher_success_story mock task fixtures.

Spans are computed from the transcript so they are exact by construction.
Run from backend/: python tests/fixtures/benchmarks/generate_teacher_fixtures.py
Fixtures must validate against app.schemas.tasks output models (enforced here).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.schemas.tasks import (  # noqa: E402
    ClassificationOutput, GroupingOutput, PaperEditOutput,
    RebuildPlanOutput, RosterOutput, SourceAuditOutput, StructureOutput,
)

ROOT = Path(__file__).parent / "teacher_success_story"
TRANSCRIPT = (ROOT / "inputs" / "transcript.txt").read_text()
OUT = ROOT / "expected" / "mock_tasks"
OUT.mkdir(parents=True, exist_ok=True)

TC = re.compile(r"\[(\d{2}):(\d{2}):(\d{2})\]")

# Split into blocks; compute char spans + timeline seconds per block.
blocks = []
pos = 0
for raw in TRANSCRIPT.split("\n\n"):
    start = TRANSCRIPT.index(raw, pos)
    end = start + len(raw)
    pos = end
    m = TC.search(raw)
    h, mi, s = (int(g) for g in m.groups())
    blocks.append({"span": (start, end), "t": h * 3600 + mi * 60 + s, "text": raw})

SOURCE_END_SECONDS = 348.0  # 8700 frames @ 25fps in source.xml
for i, b in enumerate(blocks):
    b["t_end"] = blocks[i + 1]["t"] if i + 1 < len(blocks) else SOURCE_END_SECONDS

# (index, seg_id, label, cid, function-group)
SEGS = [
    (0,  "S1",  "contamination", "C2", "exclude"),     # interviewer prompt
    (1,  "S2",  "false_start",   "C1", "exclude"),
    (2,  "S3",  "keeper",        "C1", "hook"),        # value-first opening
    (3,  "S4",  "setup",         "C1", "context"),
    (4,  "S5",  "contamination", "C2", "exclude"),
    (5,  "S6",  "setup",         "C1", "problem"),
    (6,  "S7",  "process",       "C1", "process"),
    (7,  "S8",  "example",       "C1", "example"),
    (8,  "S9",  "contamination", "C2", "exclude"),
    (9,  "S10", "evidence",      "C1", "evidence"),
    (10, "S11", "filler",        "C1", "exclude"),     # beanbag tangent
    (11, "S12", "reflection",    "C1", "reflection"),
    (12, "S13", "close",         "C1", "closing"),     # strongest resolved close
    (13, "S14", "contamination", "C2", "exclude"),
]

seg_by_id = {}
segments = []
for idx, seg_id, label, cid, func in SEGS:
    b = blocks[idx]
    seg = {
        "seg_id": seg_id, "source": "SRC1",
        "transcript_span": list(b["span"]),
        "time_span": [float(b["t"]), float(b["t_end"])],
        "label": label, "cid": cid, "confidence": "high",
    }
    seg_by_id[seg_id] = {**seg, "func": func}
    segments.append(seg)


def stub(text: str, head=5, tail=5) -> str:
    body = TC.sub("", text)
    body = re.sub(r"^[A-Z][A-Za-z .'-]*:\s*", "", body).strip()
    words = body.split()
    return " ".join(words[:head]) + " … " + " ".join(words[-tail:])


fixtures = {
    "source_audit": SourceAuditOutput.model_validate({
        "tech_risks": [
            "Interviewer voice is off-mic and must not reach the cut",
            "One false start and one mid-take tangent require clean trim boundaries",
        ],
        "material_type_guess": "interview",
        "notes": "Single-contributor testimonial; warm tone; clear value-first "
                 "opening and a strong resolved close are both present.",
    }),
    "contributor_roster": RosterOutput.model_validate({"contributors": [
        {"cid": "C1", "label": "Sarah Chen", "role": "Teacher, Year 5, Westbrook Primary",
         "source": "SRC1", "confidence": "high", "status": "keep",
         "value_note": "Sole on-camera voice; carries the whole story"},
        {"cid": "C2", "label": "Interviewer", "role": "Off-mic interviewer",
         "source": "SRC1", "confidence": "high", "status": "exclude",
         "value_note": "Prompts only; never in the cut"},
    ]}),
    "material_classification": ClassificationOutput.model_validate({"segments": segments}),
    "function_grouping": GroupingOutput.model_validate({"groups": [
        {"func": "hook", "seg_ids": ["S3"], "note": "Value-first opening moment"},
        {"func": "context", "seg_ids": ["S4"]},
        {"func": "problem", "seg_ids": ["S6"]},
        {"func": "process", "seg_ids": ["S7"]},
        {"func": "example", "seg_ids": ["S8"]},
        {"func": "evidence", "seg_ids": ["S10"]},
        {"func": "reflection", "seg_ids": ["S12"]},
        {"func": "closing", "seg_ids": ["S13"], "note": "Strongest resolved line"},
        {"func": "exclude", "seg_ids": ["S1", "S2", "S5", "S9", "S11", "S14"],
         "note": "Interviewer prompts, false start, tangent"},
    ]}),
    "mode_and_structure": StructureOutput.model_validate({
        "mode": "narrative",
        "rationale": "Single-contributor testimonial with a clear arc: hook, "
                     "context, problem, process, example, evidence, close. "
                     "Preset 1 territory: warm tone, value-first opening, end "
                     "on the strongest resolved line.",
        "proposed_order": ["hook", "context", "problem", "process", "example",
                            "evidence", "reflection", "closing"],
        "exclusions": ["interviewer prompts", "false start", "beanbag tangent"],
    }),
}

BEATS = [
    ("B1", "S3",  "hook",       "Value-first opening: the moment of change"),
    ("B2", "S4",  "context",    "Who Sarah is and where; grounds the story"),
    ("B3", "S6",  "problem",    "The students who had given up"),
    ("B4", "S7",  "process",    "The flip: their own stories become the books"),
    ("B5", "S8",  "example",    "M's story — concrete, emotional proof"),
    ("B6", "S10", "evidence",   "Fourteen months average gain; attendance turnaround"),
    ("B7", "S12", "reflection", "The barrier was belief, not ability"),
    ("B8", "S13", "closing",    "Strongest resolved close: the book club"),
]
beats = []
for bid, seg_id, func, reason in BEATS:
    s = seg_by_id[seg_id]
    beats.append({
        "bid": bid, "src": "SRC1", "cid": "C1", "role": "Teacher", "func": func,
        "quote_stub": stub(blocks[[x[1] for x in SEGS].index(seg_id)]["text"]),
        "est_duration": round(s["time_span"][1] - s["time_span"][0], 1),
        "boundary_status": "clean", "confidence": "high",
        "include_reason": reason, "uncertainty_labels": [],
        "status": "candidate", "seg_ids": [seg_id],
    })
beats[3]["uncertainty_labels"] = ["SENTENCE_SEAM_RISK"]
beats[3]["boundary_status"] = "tight-out"

fixtures["paper_edit"] = PaperEditOutput.model_validate({
    "beats": beats,
    "representation_summary": "Single contributor (C1) carries 100% of the cut; "
                              "interviewer fully excluded per roster.",
    "clarity_summary": "Arc is self-explanatory; no graphics required.",
    "main_risks": ["Tight out-point on B4 (process) — seam risk flagged"],
})

fixtures["rebuild_plan"] = RebuildPlanOutput.model_validate({
    "plan": {
        "style": "B",
        "mappings": [
            {"bid": b["bid"], "source_file_id": "SOURCE_XML",
             "clipitem_refs": ["clipitem-1"],
             "in_seconds": seg_by_id[b["seg_ids"][0]]["time_span"][0],
             "out_seconds": seg_by_id[b["seg_ids"][0]]["time_span"][1],
             "track_handling": "V1 only", "audio_handling": "linked sync audio, "
             "independently manageable", "boundary_note": b["boundary_status"],
             "uncertainty_labels": b["uncertainty_labels"]}
            for b in beats
        ],
        "provenance_notes": [
            f"{b['bid']}: SRC1 @{seg_by_id[b['seg_ids'][0]]['time_span'][0]:.0f}s, "
            f"boundary {b['boundary_status']}" for b in beats
        ],
    },
    "seam_risks": ["B4 out-point trims mid-breath; check seam on import"],
})

# Deterministic legal revision fixture: tighten B7's stub (editable beat).
fixtures["targeted_revision"] = {
    "changed_beats": [{**beats[6],
                       "quote_stub": stub(blocks[11]["text"], head=4, tail=4),
                       "include_reason": "Tightened reflection per revision request",
                       "est_duration": 30.0}],
    "reason": "Tightened B7 (reflection) as requested; no other beats touched.",
    "runtime_effect": "-5s approx",
    "contributor_effect": "none",
    "risk_effect": "none",
}

for name, model in fixtures.items():
    payload = model if isinstance(model, dict) else model.model_dump(mode="json")
    (OUT / f"{name}.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {name}.json")

# Golden approved paper edit (all beats locked) for benchmark comparison.
golden = {"version": 1, "beats": [{**b, "status": "locked"} for b in beats]}
(ROOT / "expected" / "paper_edit.json").write_text(json.dumps(golden, indent=2) + "\n")

(ROOT / "expected" / "output_checks.json").write_text(json.dumps({
    "expected_clip_count_video": len(beats),
    "expected_beat_order": [b["bid"] for b in beats],
    "frame_rate": 25,
    "max_total_duration_seconds": 300,
}, indent=2) + "\n")
print("wrote golden paper_edit.json + output_checks.json")
