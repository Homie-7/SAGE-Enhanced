"""FCP7/Premiere XML parsing — deterministic source-audit facts.

The parser extracts structural facts (frame rate, tracks, links, clipitems,
file definitions) so the LLM never guesses XML structure (canonical rule).
LLM tasks receive these facts as structured context, not raw XML.

Rule: unknowns stay None and are reported in warnings — never guessed.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pydantic import BaseModel, Field


class ClipItemFact(BaseModel):
    clipitem_id: str
    name: str | None = None
    track: str | None = None  # e.g. "V1", "A1"
    file_id: str | None = None
    start: int | None = None   # frames, sequence timeline
    end: int | None = None
    in_point: int | None = None   # frames, source file
    out_point: int | None = None
    links: list[str] = Field(default_factory=list)


class SequenceFacts(BaseModel):
    frame_rate: float | None = None
    ntsc: bool | None = None
    video_tracks: int = 0
    audio_tracks: int = 0
    clipitems: list[ClipItemFact] = Field(default_factory=list)
    file_ids: list[str] = Field(default_factory=list)
    multicam_detected: bool = False
    external_audio_detected: bool = False
    warnings: list[str] = Field(default_factory=list)


class XMLParseError(Exception):
    """Raised with an exact blocker when the source XML cannot be read."""


def _int_or_none(el: etree._Element | None) -> int | None:
    if el is None or el.text is None:
        return None
    try:
        return int(el.text.strip())
    except ValueError:
        return None


def _parse_clipitem(ci: etree._Element, track_label: str, facts: SequenceFacts) -> ClipItemFact:
    file_el = ci.find("file")
    fact = ClipItemFact(
        clipitem_id=ci.get("id", ""),
        name=(ci.findtext("name") or None),
        track=track_label,
        file_id=file_el.get("id") if file_el is not None else None,
        start=_int_or_none(ci.find("start")),
        end=_int_or_none(ci.find("end")),
        in_point=_int_or_none(ci.find("in")),
        out_point=_int_or_none(ci.find("out")),
        links=[
            lr.text.strip()
            for lr in ci.findall("link/linkclipref")
            if lr.text and lr.text.strip()
        ],
    )
    if not fact.clipitem_id:
        facts.warnings.append(f"Clipitem on {track_label} has no id attribute.")
    if ci.find("multiclip") is not None or ci.find("sequence") is not None:
        facts.multicam_detected = True
    return fact


def parse_source_xml(path: str | Path) -> SequenceFacts:
    """Parse a synced source XML into deterministic facts."""
    path = Path(path)
    if not path.exists():
        raise XMLParseError(f"Source XML not found at {path}.")
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as exc:
        raise XMLParseError(f"Source XML is not well-formed: {exc}") from exc

    root = tree.getroot()
    if root.tag != "xmeml":
        raise XMLParseError(
            f"Expected an FCP7 <xmeml> document, found <{root.tag}>. "
            "Export a synced sequence as Final Cut Pro XML from Premiere."
        )

    seq = root.find(".//sequence")
    if seq is None:
        raise XMLParseError("No <sequence> found in source XML.")

    facts = SequenceFacts()

    timebase = seq.findtext("rate/timebase")
    ntsc_text = (seq.findtext("rate/ntsc") or "").strip().upper()
    if timebase:
        try:
            facts.frame_rate = float(timebase)
        except ValueError:
            facts.warnings.append(f"Unreadable sequence timebase '{timebase}'.")
    else:
        facts.warnings.append("Sequence has no rate/timebase; timing facts unavailable.")
    facts.ntsc = True if ntsc_text == "TRUE" else False if ntsc_text == "FALSE" else None

    video_file_ids: set[str] = set()
    audio_file_ids: set[str] = set()
    seen_file_ids: list[str] = []

    for media_type, bucket in (("video", video_file_ids), ("audio", audio_file_ids)):
        media_el = seq.find(f"media/{media_type}")
        if media_el is None:
            continue
        tracks = media_el.findall("track")
        if media_type == "video":
            facts.video_tracks = len(tracks)
        else:
            facts.audio_tracks = len(tracks)
        prefix = "V" if media_type == "video" else "A"
        for idx, track in enumerate(tracks, start=1):
            for ci in track.findall("clipitem"):
                fact = _parse_clipitem(ci, f"{prefix}{idx}", facts)
                facts.clipitems.append(fact)
                if fact.file_id:
                    bucket.add(fact.file_id)
                    if fact.file_id not in seen_file_ids:
                        seen_file_ids.append(fact.file_id)

    facts.file_ids = seen_file_ids
    facts.external_audio_detected = bool(audio_file_ids - video_file_ids)
    n_transitions = len(seq.findall(".//transitionitem"))
    if n_transitions:
        facts.warnings.append(
            f"Source contains {n_transitions} transitionitem(s). Style B rebuilds "
            "straight cuts only; source transitions are not carried into the output."
        )
    n_generators = len(seq.findall(".//generatoritem"))
    if n_generators:
        facts.warnings.append(
            f"Source contains {n_generators} generatoritem(s) (titles/graphics). "
            "These are not part of the interview rebuild and are not carried over."
        )
    if not facts.clipitems:
        facts.warnings.append("Sequence contains no clipitems.")
    return facts
