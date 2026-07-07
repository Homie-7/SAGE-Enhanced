"""Lightweight timeline profiling for benchmark comparison.

Distinct from app.xmlengine.parser (the strict V1 ingest parser): this
profiler must read *any* xmeml timeline — before/after, v4/v5, multi-track,
multi-source — without judging it, because reference finals routinely use
structures V1 does not rebuild. It extracts, per clipitem, the span of
SOURCE MEDIA used, keyed by media file (not by volatile file ids, which
differ between exports of the same project).
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from lxml import etree
from pydantic import BaseModel, Field


class ClipSpan(BaseModel):
    media_key: str            # normalized media file name
    mediatype: str            # "video" | "audio"
    track: int                # 1-based within its mediatype
    timeline_start_s: float
    timeline_end_s: float
    source_in_s: float        # file-relative
    source_out_s: float
    clip_name: str | None = None


class TimelineProfile(BaseModel):
    path: str
    sequence_name: str | None
    xmeml_version: str | None
    frame_rate: float
    ntsc: bool
    duration_s: float
    video_tracks: int
    audio_tracks: int
    clip_count: int
    media_keys: list[str]
    spans: list[ClipSpan]
    warnings: list[str] = Field(default_factory=list)

    def spans_for(self, mediatype: str, media_keys: set[str] | None = None
                  ) -> list[ClipSpan]:
        out = [s for s in self.spans if s.mediatype == mediatype]
        if media_keys is not None:
            out = [s for s in out if s.media_key in media_keys]
        return sorted(out, key=lambda s: (s.timeline_start_s, s.track))


def media_key_from(name: str | None, pathurl: str | None) -> str | None:
    """Stable per-media key: the decoded basename of pathurl, else the file
    name element. Lowercased; extension kept (proxies vs originals differ)."""
    raw = None
    if pathurl:
        raw = unquote(pathurl).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    elif name:
        raw = name
    if not raw:
        return None
    return re.sub(r"\s+", " ", raw.strip().lower())


def profile_timeline(xml_path: str | Path) -> TimelineProfile:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    seq = tree.find(".//sequence")
    if seq is None:
        raise ValueError(f"{xml_path}: no <sequence> element found.")

    tb_text = seq.findtext("./rate/timebase")
    ntsc = (seq.findtext("./rate/ntsc") or "FALSE").upper() == "TRUE"
    timebase = float(tb_text) if tb_text else 25.0
    rate = timebase * (1000 / 1001) if ntsc else timebase

    warnings: list[str] = []
    # First pass: file id -> media key (full definitions carry the facts).
    file_key: dict[str, str | None] = {}
    for f in seq.iter("file"):
        fid = f.get("id")
        if fid is None:
            continue
        key = media_key_from(f.findtext("name"), f.findtext("pathurl"))
        if fid not in file_key or file_key[fid] is None:
            file_key[fid] = key

    spans: list[ClipSpan] = []
    clip_count = 0
    v_tracks = a_tracks = 0
    for mediatype in ("video", "audio"):
        tracks = seq.findall(f"./media/{mediatype}/track")
        if mediatype == "video":
            v_tracks = len(tracks)
        else:
            a_tracks = len(tracks)
        for t_index, track in enumerate(tracks, start=1):
            for clip in track.findall("./clipitem"):
                clip_count += 1
                fid_el = clip.find("file")
                fid = fid_el.get("id") if fid_el is not None else None
                key = file_key.get(fid) if fid else None
                if key is None:
                    warnings.append(
                        f"clipitem '{clip.findtext('name')}' on {mediatype} "
                        f"track {t_index} has no resolvable media file; skipped.")
                    continue
                vals = {}
                ok = True
                for field in ("start", "end", "in", "out"):
                    txt = clip.findtext(field)
                    try:
                        vals[field] = int(txt)
                    except (TypeError, ValueError):
                        ok = False
                if not ok or vals["start"] < 0 or vals["end"] < 0:
                    warnings.append(
                        f"clipitem '{clip.findtext('name')}' has non-numeric or "
                        f"negative timing; skipped.")
                    continue
                spans.append(ClipSpan(
                    media_key=key, mediatype=mediatype, track=t_index,
                    timeline_start_s=vals["start"] / rate,
                    timeline_end_s=vals["end"] / rate,
                    source_in_s=vals["in"] / rate,
                    source_out_s=vals["out"] / rate,
                    clip_name=clip.findtext("name"),
                ))

    dur_text = seq.findtext("duration")
    duration_s = (float(dur_text) / rate) if dur_text else (
        max((s.timeline_end_s for s in spans), default=0.0))

    return TimelineProfile(
        path=str(xml_path),
        sequence_name=seq.findtext("name"),
        xmeml_version=root.get("version"),
        frame_rate=round(rate, 3),
        ntsc=ntsc,
        duration_s=round(duration_s, 3),
        video_tracks=v_tracks,
        audio_tracks=a_tracks,
        clip_count=clip_count,
        media_keys=sorted({s.media_key for s in spans}),
        spans=spans,
        warnings=warnings,
    )
