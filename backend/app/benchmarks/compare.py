"""Candidate-vs-reference timeline comparison.

Compares which SOURCE MATERIAL two edits kept, on media both timelines can
see. Practical and deliberately partial — see LIMITS below.

Core idea: every clipitem is a span of source media (media_key, in, out).
Merge those spans per media file for each timeline, then measure:

  - runtime difference,
  - kept-content recall/precision/Jaccard (seconds of source material),
  - order similarity of shared material (normalized Kendall tau),
  - shot statistics (count, average shot length),
  - divergences worth human review: the largest spans one edit kept and the
    other did not, annotated with transcript excerpts where word timing on
    the relevant source is available.

LIMITS (stated wherever a report is produced):
  - Media matching is by file name; renamed/re-exported media will not match
    and is reported as unshared, not silently guessed.
  - Overlap measures WHAT material was kept, not how it was trimmed, mixed,
    coloured, or layered. B-roll placement, music, titles, and multi-track
    craft are out of scope by design.
  - A high overlap does not mean an equally good edit; a low overlap is not
    proof of a bad one. The numbers locate the differences for a HUMAN to
    review — they never grade the edit.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.benchmarks.timeline import TimelineProfile
from app.benchmarks.transcript import Word, excerpt

Interval = tuple[float, float]


# --- interval math -----------------------------------------------------------

def merge(intervals: list[Interval]) -> list[Interval]:
    out: list[Interval] = []
    for a, b in sorted((i for i in intervals if i[1] > i[0])):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def total(intervals: list[Interval]) -> float:
    return sum(b - a for a, b in intervals)


def intersect(xs: list[Interval], ys: list[Interval]) -> list[Interval]:
    out: list[Interval] = []
    i = j = 0
    while i < len(xs) and j < len(ys):
        a = max(xs[i][0], ys[j][0])
        b = min(xs[i][1], ys[j][1])
        if b > a:
            out.append((a, b))
        if xs[i][1] < ys[j][1]:
            i += 1
        else:
            j += 1
    return out


def subtract(xs: list[Interval], ys: list[Interval]) -> list[Interval]:
    out: list[Interval] = []
    for a, b in xs:
        cur = a
        for c, d in ys:
            if d <= cur or c >= b:
                continue
            if c > cur:
                out.append((cur, c))
            cur = max(cur, d)
            if cur >= b:
                break
        if cur < b:
            out.append((cur, b))
    return out


def kendall_tau_normalized(order: list[int]) -> float:
    """1.0 = same order, 0.0 = fully reversed. `order` is the candidate's
    rank sequence of items taken in reference order."""
    n = len(order)
    if n < 2:
        return 1.0
    swaps = sum(1 for i in range(n) for j in range(i + 1, n)
                if order[i] > order[j])
    return 1.0 - swaps / (n * (n - 1) / 2)


# --- report models -----------------------------------------------------------

class Divergence(BaseModel):
    media_key: str
    source_in_s: float
    source_out_s: float
    duration_s: float
    kept_by: str                    # "reference_only" | "candidate_only"
    transcript_excerpt: str | None = None


class ComparisonReport(BaseModel):
    reference: str
    candidate: str
    mediatype: str                  # which clip lane the comparison used
    shared_media: list[str]
    reference_only_media: list[str]
    candidate_only_media: list[str]
    reference_runtime_s: float
    candidate_runtime_s: float
    reference_kept_s: float         # merged source seconds on shared media
    candidate_kept_s: float
    overlap_s: float
    recall: float                   # overlap / reference_kept
    precision: float                # overlap / candidate_kept
    jaccard: float
    order_similarity: float | None  # None when < 2 shared segments
    reference_shots: int
    candidate_shots: int
    reference_avg_shot_s: float
    candidate_avg_shot_s: float
    divergences: list[Divergence]
    limits: list[str] = Field(default_factory=list)


_LIMITS = [
    "Media matched by file name; renamed/re-exported media reports as unshared.",
    "Measures which source material was kept, not trims, mix, grade, b-roll "
    "placement, music, or multi-track craft.",
    "Numbers locate differences for human review; they do not grade the edit.",
]


def _kept_by_media(profile: TimelineProfile, mediatype: str,
                   media: set[str]) -> dict[str, list[Interval]]:
    kept: dict[str, list[Interval]] = {}
    for s in profile.spans_for(mediatype, media):
        kept.setdefault(s.media_key, []).append((s.source_in_s, s.source_out_s))
    return {k: merge(v) for k, v in kept.items()}


def compare_timelines(
    reference: TimelineProfile,
    candidate: TimelineProfile,
    source_words: dict[str, list[Word]] | None = None,
    mediatype: str = "audio",
    top_divergences: int = 10,
) -> ComparisonReport:
    """`source_words` maps media_key -> words on that media's own SOURCE
    clock (build with transcript.words_on_source_clock; pass only
    verified-aligned transcripts). Defaults to the audio lane: in interview-led edits the audio spine is
    what SAGE selects; video overlays would inflate differences that are
    b-roll craft, not content selection."""
    ref_media = set(reference.media_keys)
    cand_media = set(candidate.media_keys)
    shared = ref_media & cand_media

    ref_kept = _kept_by_media(reference, mediatype, shared)
    cand_kept = _kept_by_media(candidate, mediatype, shared)
    # Fall back to video if the requested lane is empty on either side
    # (some timelines carry the narrative on V only).
    if mediatype == "audio" and (not ref_kept or not cand_kept):
        mediatype = "video"
        ref_kept = _kept_by_media(reference, mediatype, shared)
        cand_kept = _kept_by_media(candidate, mediatype, shared)

    ref_total = sum(total(v) for v in ref_kept.values())
    cand_total = sum(total(v) for v in cand_kept.values())
    overlap = 0.0
    for key in shared:
        overlap += total(intersect(ref_kept.get(key, []), cand_kept.get(key, [])))
    union = ref_total + cand_total - overlap

    # Order similarity: reference-kept merged segments in reference timeline
    # order vs the order the candidate plays their midpoints.
    def order_positions(profile: TimelineProfile) -> list[tuple[str, float, float]]:
        pos = []
        for s in profile.spans_for(mediatype, shared):
            pos.append((s.media_key, s.source_in_s, s.source_out_s,
                        s.timeline_start_s))
        return pos

    def timeline_time_of(profile_pos, key: str, mid: float) -> float | None:
        for k, a, b, t in profile_pos:
            if k == key and a <= mid < b:
                return t + (mid - a)
        return None

    ref_pos = order_positions(reference)
    cand_pos = order_positions(candidate)
    shared_segments: list[tuple[float, float]] = []  # (ref_time, cand_time)
    for key in sorted(shared):
        for a, b in intersect(ref_kept.get(key, []), cand_kept.get(key, [])):
            mid = (a + b) / 2
            rt = timeline_time_of(ref_pos, key, mid)
            ct = timeline_time_of(cand_pos, key, mid)
            if rt is not None and ct is not None:
                shared_segments.append((rt, ct))
    order_sim = None
    if len(shared_segments) >= 2:
        by_ref = sorted(shared_segments)
        cand_rank = {ct: i for i, (_, ct) in
                     enumerate(sorted(by_ref, key=lambda x: x[1]))}
        order_sim = round(kendall_tau_normalized(
            [cand_rank[ct] for _, ct in by_ref]), 3)

    # Divergences with transcript annotation where possible.
    divergences: list[Divergence] = []
    for key in sorted(shared):
        r, c = ref_kept.get(key, []), cand_kept.get(key, [])
        for kept_by, spans in (("reference_only", subtract(r, c)),
                               ("candidate_only", subtract(c, r))):
            for a, b in spans:
                text = None
                if source_words and key in source_words:
                    text = excerpt(source_words[key], a, b)
                divergences.append(Divergence(
                    media_key=key, source_in_s=round(a, 2),
                    source_out_s=round(b, 2), duration_s=round(b - a, 2),
                    kept_by=kept_by, transcript_excerpt=text))
    divergences.sort(key=lambda d: -d.duration_s)

    ref_shots = len(reference.spans_for(mediatype, shared))
    cand_shots = len(candidate.spans_for(mediatype, shared))
    return ComparisonReport(
        reference=reference.path, candidate=candidate.path,
        mediatype=mediatype,
        shared_media=sorted(shared),
        reference_only_media=sorted(ref_media - cand_media),
        candidate_only_media=sorted(cand_media - ref_media),
        reference_runtime_s=reference.duration_s,
        candidate_runtime_s=candidate.duration_s,
        reference_kept_s=round(ref_total, 2),
        candidate_kept_s=round(cand_total, 2),
        overlap_s=round(overlap, 2),
        recall=round(overlap / ref_total, 3) if ref_total else 0.0,
        precision=round(overlap / cand_total, 3) if cand_total else 0.0,
        jaccard=round(overlap / union, 3) if union else 0.0,
        order_similarity=order_sim,
        reference_shots=ref_shots, candidate_shots=cand_shots,
        reference_avg_shot_s=round(ref_total / ref_shots, 2) if ref_shots else 0.0,
        candidate_avg_shot_s=round(cand_total / cand_shots, 2) if cand_shots else 0.0,
        divergences=divergences[:top_divergences],
        limits=list(_LIMITS),
    )
