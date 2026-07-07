"""Rebuild feasibility for a benchmark case source, against V1 scope and the
configured providers' limits. Every verdict is a fact with a reason —
nothing here is stream-specific.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.benchmarks.timeline import TimelineProfile
from app.benchmarks.transcript import NormalizedTranscript, alignment_verdict


class FeasibilityItem(BaseModel):
    name: str
    ok: bool
    detail: str


class FeasibilityReport(BaseModel):
    source_id: str
    items: list[FeasibilityItem]
    provider_fit: dict[str, str] = Field(default_factory=dict)
    overall_ok: bool

    def blockers(self) -> list[FeasibilityItem]:
        return [i for i in self.items if not i.ok]


def _estimate_tokens(text: str) -> int:
    return len(text) // 4  # rough, stated as such in output


def assess_source(
    source_id: str,
    profile: TimelineProfile,
    transcript: NormalizedTranscript | None,
    prompts_configs_dir: str | Path | None = None,
) -> FeasibilityReport:
    items: list[FeasibilityItem] = []

    items.append(FeasibilityItem(
        name="frame_rate", ok=profile.frame_rate > 0,
        detail=f"{profile.frame_rate} fps (ntsc={profile.ntsc}), "
               f"xmeml v{profile.xmeml_version}"))

    n_media = len(profile.media_keys)
    items.append(FeasibilityItem(
        name="single_source_scope", ok=n_media <= 1 or profile.video_tracks <= 1,
        detail=(f"{n_media} media file(s) across "
                f"V{profile.video_tracks}/A{profile.audio_tracks}. "
                + ("Within V1 single-source rebuild scope."
                   if n_media <= 1 else
                   "V1 rebuilds from ONE source timeline; multiple media "
                   "files mean the LLM's plan and the deterministic rebuild "
                   "must stay within spans this timeline actually contains — "
                   "verified per beat at rebuild time, but cross-media "
                   "storytelling like the human final is out of V1 scope."))))

    items.append(FeasibilityItem(
        name="clip_timing", ok=not profile.warnings,
        detail=("All clipitems carry numeric timing."
                if not profile.warnings else
                f"{len(profile.warnings)} clipitem issue(s): "
                + "; ".join(profile.warnings[:3]))))

    if transcript is None:
        items.append(FeasibilityItem(
            name="transcript", ok=False,
            detail="No transcript ingested for this source."))
    else:
        aligned, msg = alignment_verdict(transcript, profile.duration_s)
        items.append(FeasibilityItem(
            name="transcript_alignment", ok=aligned, detail=msg))
        items.append(FeasibilityItem(
            name="speaker_identification",
            ok=True,  # never a blocker — roster task handles uncertainty
            detail=(f"{transcript.named_speaker_count}/{transcript.speaker_count} "
                    "speakers carry real names; the rest will surface as "
                    "IDENTITY_UNCERTAIN in the roster (canonical behaviour).")))

    provider_fit: dict[str, str] = {}
    if transcript is not None and prompts_configs_dir:
        est = _estimate_tokens(transcript.sage_text)
        for cfg_path in sorted(Path(prompts_configs_dir).glob("*.json")):
            cfg = json.loads(cfg_path.read_text())
            limit = int(cfg.get("max_context_tokens", 0))
            name = cfg.get("provider", cfg_path.stem)
            headroom = limit - est - 3000  # prompt scaffolding allowance
            provider_fit[name] = (
                f"~{est} transcript tokens (chars/4 estimate) vs "
                f"{limit} context: "
                + ("fits single-pass." if headroom > 0 else
                   f"DOES NOT FIT single-pass (short by ~{-headroom}); "
                   "V1 has no chunking — run fails explicitly."))

    overall = all(i.ok for i in items)
    return FeasibilityReport(source_id=source_id, items=items,
                             provider_fit=provider_fit, overall_ok=overall)
