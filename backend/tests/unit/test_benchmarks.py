"""Benchmark framework tests: interval math correctness, transcript
normalization, feasibility verdicts, and a smoke pass over the two real
ingested cases (tss, lnd_showcase)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.benchmarks.compare import (
    compare_timelines, intersect, kendall_tau_normalized, merge, subtract, total)
from app.benchmarks.feasibility import assess_source
from app.benchmarks.manifest import CaseManifest, cases_root, list_cases
from app.benchmarks.timeline import media_key_from, profile_timeline
from app.benchmarks.transcript import (
    alignment_verdict, load_word_timed_json, words_on_source_clock)

CASES = cases_root()


# --- interval math -----------------------------------------------------------

def test_merge_intersect_subtract():
    assert merge([(5, 7), (1, 3), (2, 4)]) == [(1, 4), (5, 7)]
    assert intersect([(0, 10)], [(3, 5), (8, 12)]) == [(3, 5), (8, 10)]
    assert subtract([(0, 10)], [(3, 5), (8, 12)]) == [(0, 3), (5, 8)]
    assert total([(0, 3), (5, 8)]) == 6
    assert merge([(1, 1), (2, 1)]) == []  # degenerate spans dropped


def test_kendall_tau():
    assert kendall_tau_normalized([0, 1, 2, 3]) == 1.0
    assert kendall_tau_normalized([3, 2, 1, 0]) == 0.0
    assert kendall_tau_normalized([1]) == 1.0


def test_media_key_normalization():
    assert media_key_from(None, "file://localhost/V/My%20Clip.MOV") == "my clip.mov"
    assert media_key_from("Clip A", None) == "clip a"
    assert media_key_from(None, None) is None


# --- transcript --------------------------------------------------------------

def _tiny_transcript(tmp_path: Path) -> Path:
    data = {
        "language": "en",
        "speakers": [{"id": "s1", "name": "Ada"}, {"id": "s2", "name": "Speaker 2"}],
        "segments": [
            {"start": 0, "duration": 2.0, "speaker": "s1", "words": [
                {"type": "word", "text": "Hello", "start": 0.2, "duration": 0.3},
                {"type": "word", "text": "world", "start": 0.6, "duration": 0.3},
            ]},
            {"start": 5, "duration": 1.0, "speaker": "s2", "words": [
                {"type": "word", "text": "Reply", "start": 5.1, "duration": 0.4},
            ]},
        ],
    }
    p = tmp_path / "t.json"
    p.write_text(json.dumps(data))
    return p


def test_normalizer_produces_sage_format(tmp_path):
    t = load_word_timed_json(_tiny_transcript(tmp_path))
    assert "[00:00:00] ADA: Hello world" in t.sage_text
    assert "[00:00:05] SPEAKER 2: Reply" in t.sage_text
    assert t.named_speaker_count == 1 and t.speaker_count == 2
    ok, _ = alignment_verdict(t, timeline_duration_s=10)
    assert ok
    ok, msg = alignment_verdict(t, timeline_duration_s=2.0)
    assert not ok and "different/longer sequence" in msg


def test_unknown_dialect_fails_precisely(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"utterances": []}))
    with pytest.raises(ValueError, match="not a recognised transcript dialect"):
        load_word_timed_json(p)


# --- real ingested cases (smoke) ----------------------------------------------

pytestmark_real = pytest.mark.skipif(
    not (CASES / "tss" / "case.json").is_file(),
    reason="real benchmark cases not ingested")


@pytestmark_real
def test_real_cases_load_and_profile():
    ids = {m.case_id for m in list_cases()}
    assert {"tss", "lnd_showcase"} <= ids

    tss = CaseManifest.load(CASES / "tss")
    assert tss.caveats, "TSS transcript misalignment must be recorded as a caveat"

    before = profile_timeline(CASES / "tss" / tss.sources[0].before_xml)
    after = profile_timeline(CASES / "tss" / tss.reference_after_xml)
    assert before.frame_rate == 25.0 and before.clip_count == 147
    assert after.clip_count == 79

    rep = compare_timelines(after, before)
    # Every span comparison invariant: overlap can exceed neither side.
    assert rep.overlap_s <= min(rep.reference_kept_s, rep.candidate_kept_s) + 0.01
    assert 0 <= rep.jaccard <= 1
    assert rep.limits  # limits are always stated


@pytestmark_real
def test_lnd_aligned_transcript_annotates_divergences():
    lnd = CaseManifest.load(CASES / "lnd_showcase")
    src = lnd.sources[0]
    before = profile_timeline(CASES / "lnd_showcase" / src.before_xml)
    after = profile_timeline(CASES / "lnd_showcase" / lnd.reference_after_xml)
    t = load_word_timed_json(CASES / "lnd_showcase" / src.transcript_json)
    aligned, _ = alignment_verdict(t, before.duration_s)
    assert aligned
    words = words_on_source_clock(before, t)
    assert words, "aligned transcript must map onto source clocks"
    rep = compare_timelines(after, before, source_words=words)
    assert any(d.transcript_excerpt for d in rep.divergences)


@pytestmark_real
def test_feasibility_reports_val_context_limit_honestly():
    lnd = CaseManifest.load(CASES / "lnd_showcase")
    src = next(s for s in lnd.sources if s.source_id == "interior_design")
    before = profile_timeline(CASES / "lnd_showcase" / src.before_xml)
    t = load_word_timed_json(CASES / "lnd_showcase" / src.transcript_json)
    configs = Path(__file__).resolve().parents[3] / "prompts" / "configs"
    feas = assess_source(src.source_id, before, t, configs)
    assert "DOES NOT FIT" in feas.provider_fit["val"]
    assert "fits single-pass" in feas.provider_fit["claude"]
