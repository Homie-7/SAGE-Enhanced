"""Transcript ingestion for benchmark cases.

Accepts the word-timed JSON dialect used by the first real cases
({language, segments:[{start,duration,speaker,words:[{start,duration,text,eos}]}],
speakers:[{id,name}]}) and produces:

  - SAGE ingest text: "[HH:MM:SS] SPEAKER: sentence…" blocks, the exact
    format the app already accepts;
  - a word index (time → text) used to annotate comparison divergences;
  - an alignment verdict against a timeline duration, because a transcript
    whose clock does not match the XML given to SAGE breaks span mapping —
    that must be a recorded caveat, never a silent assumption.

Other transcript dialects get added here when real cases bring them.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Word(BaseModel):
    start_s: float
    end_s: float
    text: str


class NormalizedTranscript(BaseModel):
    speakers: dict[str, str]          # speaker id -> display name
    words: list[Word]
    sage_text: str
    total_speech_s: float
    max_end_s: float
    named_speaker_count: int
    speaker_count: int


def _tc(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def load_word_timed_json(path: str | Path) -> NormalizedTranscript:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or "segments" not in data:
        raise ValueError(
            f"{path}: not a recognised transcript dialect (expected top-level "
            "'segments'). Add a loader to app/benchmarks/transcript.py.")
    return normalize_word_timed(data)


def normalize_word_timed(data: dict) -> NormalizedTranscript:
    """Core normalizer for the word-timed dialect; raises KeyError/TypeError
    on malformed segments — callers turn that into a precise message."""

    speakers = {s["id"]: (s.get("name") or "Unknown")
                for s in data.get("speakers", [])}
    named = sum(1 for n in speakers.values()
                if n and not n.lower().startswith(("speaker", "unknown")))

    words: list[Word] = []
    blocks: list[str] = []
    total = 0.0
    for seg in data["segments"]:
        total += float(seg.get("duration") or 0)
        seg_words = [w for w in seg.get("words", [])
                     if w.get("type") == "word" and (w.get("text") or "").strip()]
        if not seg_words:
            continue
        for w in seg_words:
            start = float(w["start"])
            words.append(Word(start_s=start,
                              end_s=start + float(w.get("duration") or 0),
                              text=w["text"].strip()))
        speaker = speakers.get(seg.get("speaker"), "Unknown")
        text = " ".join(w["text"].strip() for w in seg_words)
        blocks.append(f"[{_tc(float(seg_words[0]['start']))}] "
                      f"{speaker.upper()}: {text}")

    max_end = max((w.end_s for w in words), default=0.0)
    return NormalizedTranscript(
        speakers=speakers,
        words=words,
        sage_text="\n\n".join(blocks) + "\n",
        total_speech_s=round(total, 1),
        max_end_s=round(max_end, 1),
        named_speaker_count=named,
        speaker_count=len(speakers),
    )


def alignment_verdict(transcript: NormalizedTranscript,
                      timeline_duration_s: float) -> tuple[bool, str]:
    """Aligned = every word timestamp fits the timeline (small tolerance).
    Misalignment means the transcript belongs to a different (usually longer,
    earlier) sequence than the XML — SAGE quote resolution still works on
    text, but time-span mapping to this XML would be wrong."""
    tol = max(2.0, timeline_duration_s * 0.02)
    if transcript.max_end_s <= timeline_duration_s + tol:
        return True, (f"Transcript fits the timeline "
                      f"({transcript.max_end_s:.0f}s ≤ {timeline_duration_s:.0f}s).")
    return False, (
        f"Transcript extends to {transcript.max_end_s:.0f}s but the timeline "
        f"is {timeline_duration_s:.0f}s — the transcript belongs to a "
        "different/longer sequence. Time-based span mapping against this XML "
        "is unreliable; obtain the matching sequence export or a re-synced "
        "transcript before a live SAGE run on this source.")


def excerpt(words: list[Word], start_s: float, end_s: float,
            max_words: int = 24) -> str:
    hits = [w.text for w in words if w.start_s < end_s and w.end_s > start_s]
    if not hits:
        return "(no transcript speech in this range)"
    if len(hits) > max_words:
        head = " ".join(hits[:max_words // 2])
        tail = " ".join(hits[-max_words // 2:])
        return f"{head} … {tail}"
    return " ".join(hits)


def words_on_source_clock(profile, transcript: "NormalizedTranscript"
                          ) -> dict[str, list[Word]]:
    """Translate word times from the before-SEQUENCE clock onto each media
    file's SOURCE clock, via the before timeline's clip spans (source time =
    clip.in + (word_time - clip.start)). Only valid for transcripts verified
    aligned to that timeline; words falling in timeline gaps are dropped
    rather than guessed. `profile` is the before TimelineProfile."""
    out: dict[str, list[Word]] = {}
    spans = sorted(
        (s for s in profile.spans if s.mediatype == "audio") or profile.spans,
        key=lambda s: s.timeline_start_s)
    for w in transcript.words:
        mid = (w.start_s + w.end_s) / 2
        for s in spans:
            if s.timeline_start_s <= mid < s.timeline_end_s:
                offset = s.source_in_s - s.timeline_start_s
                out.setdefault(s.media_key, []).append(Word(
                    start_s=w.start_s + offset,
                    end_s=w.end_s + offset,
                    text=w.text))
                break
    for words in out.values():
        words.sort(key=lambda w: w.start_s)
    return out
