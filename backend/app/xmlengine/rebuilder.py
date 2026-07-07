"""Deterministic XML rebuild engine.

'LLM plans, code builds XML.' The LLM produces a RebuildPlan (beat -> source
clip in/out mappings); this engine performs the actual clone/trim/reorder
from the source XML.

Canonical rules enforced here (file 04):
  - clone, trim, reorder from source only; never invent unmappable structure
  - preserve required track structure, sync, and source relationships
  - recalc timing correctly (timing.py)
  - keep the mapping between approved beats and real segments (provenance)
  - rebuild styles A/B/C; V1 implements Style B (editorial usability first)

Mapping semantics: in_seconds/out_seconds are positions on the SOURCE
SEQUENCE TIMELINE (the synced source), matching transcript timecodes. The
engine translates timeline positions into source-file in/out via the
referenced clipitem — never by guessing.
"""

from __future__ import annotations

import copy
from pathlib import Path

from lxml import etree

from app.schemas.state import BeatMapping, RebuildPlan, RebuildStyle
from app.xmlengine.timing import seconds_to_frames, seconds_to_ppro_ticks


class RebuildError(Exception):
    """Raised with an exact blocker when a safe rebuild cannot be generated.
    Never emit guessed XML instead."""


def _txt(el: etree._Element, tag: str) -> str | None:
    return el.findtext(tag)


def _set_int(el: etree._Element, tag: str, value: int) -> None:
    child = el.find(tag)
    if child is None:
        child = etree.SubElement(el, tag)
    child.text = str(value)


def _remove(el: etree._Element, tag: str) -> None:
    for child in el.findall(tag):
        el.remove(child)


class _SourceIndex:
    def __init__(self, tree: etree._ElementTree):
        self.tree = tree
        self.seq = tree.getroot().find(".//sequence")
        if self.seq is None:
            raise RebuildError("Source XML has no <sequence>; cannot rebuild.")
        tb = self.seq.findtext("rate/timebase")
        if not tb:
            raise RebuildError("Source sequence has no rate/timebase; timing cannot be preserved.")
        self.timebase = float(tb)
        self.ntsc = (self.seq.findtext("rate/ntsc") or "FALSE").strip().upper() == "TRUE"
        self.video_clips: dict[str, etree._Element] = {}
        self.audio_clips: dict[str, etree._Element] = {}
        for media_type, store in (("video", self.video_clips), ("audio", self.audio_clips)):
            media_el = self.seq.find(f"media/{media_type}")
            if media_el is None:
                continue
            for ci in media_el.iterfind("track/clipitem"):
                cid = ci.get("id")
                if cid:
                    store[cid] = ci

    def clip(self, clipitem_id: str) -> tuple[etree._Element, str]:
        if clipitem_id in self.video_clips:
            return self.video_clips[clipitem_id], "video"
        if clipitem_id in self.audio_clips:
            return self.audio_clips[clipitem_id], "audio"
        raise RebuildError(
            f"Rebuild plan references clipitem '{clipitem_id}' which does not "
            "exist in the source XML. The plan must map beats to real source clips."
        )


def _timeline_to_file_frames(
    src_clip: etree._Element, in_frames: int, out_frames: int, bid: str
) -> tuple[int, int]:
    """Translate sequence-timeline frames into source-file in/out frames using
    the source clipitem's own start/in relationship."""
    start = _txt(src_clip, "start")
    end = _txt(src_clip, "end")
    file_in = _txt(src_clip, "in")
    if start is None or end is None or file_in is None:
        raise RebuildError(
            f"Beat {bid}: source clipitem '{src_clip.get('id')}' lacks "
            "start/end/in timing; cannot trim without guessing."
        )
    start_i, end_i, file_in_i = int(start), int(end), int(file_in)
    if in_frames < start_i or out_frames > end_i:
        raise RebuildError(
            f"Beat {bid}: requested span [{in_frames}, {out_frames}] frames is "
            f"outside source clipitem '{src_clip.get('id')}' timeline span "
            f"[{start_i}, {end_i}]. The plan must stay within real source material."
        )
    offset = in_frames - start_i
    duration = out_frames - in_frames
    return file_in_i + offset, file_in_i + offset + duration


def rebuild_sequence(
    source_xml_path: str | Path,
    plan: RebuildPlan,
    output_path: str | Path,
) -> Path:
    """Build the output XML from the source XML and the approved plan.
    Returns the output path. Raises RebuildError with an exact blocker on
    failure — never writes partial or guessed XML."""
    if plan.style != RebuildStyle.B_EDITORIAL_USABILITY_FIRST:
        raise RebuildError(
            f"Rebuild style '{plan.style.value}' is not implemented in V1. "
            "Style B (editorial usability first) is the V1 default; choose it "
            "or wait for styles A/C post-V1."
        )
    if not plan.mappings:
        raise RebuildError("Rebuild plan contains no beat mappings; nothing to build.")

    try:
        tree = etree.parse(str(source_xml_path))
    except etree.XMLSyntaxError as exc:
        raise RebuildError(f"Source XML is not well-formed: {exc}") from exc

    src = _SourceIndex(tree)
    rate = src.timebase

    # --- output skeleton cloned from source (never invented) ---------------
    out_root = etree.Element("xmeml", version=tree.getroot().get("version", "4"))
    out_seq = etree.SubElement(out_root, "sequence", id="sequence-sage-rebuild")
    name_el = etree.SubElement(out_seq, "name")
    name_el.text = f"{src.seq.findtext('name') or 'Sequence'} — SAGE Rebuild"
    out_seq.append(copy.deepcopy(src.seq.find("rate")))
    media_el = etree.SubElement(out_seq, "media")
    video_el = etree.SubElement(media_el, "video")
    src_vformat = src.seq.find("media/video/format")
    if src_vformat is not None:
        video_el.append(copy.deepcopy(src_vformat))
    vtrack = etree.SubElement(video_el, "track")
    audio_el = etree.SubElement(media_el, "audio")
    src_aformat = src.seq.find("media/audio/format")
    if src_aformat is not None:
        audio_el.append(copy.deepcopy(src_aformat))
    atracks: list[etree._Element] = []

    def audio_track(idx: int) -> etree._Element:
        while len(atracks) < idx:
            atracks.append(etree.SubElement(audio_el, "track"))
        return atracks[idx - 1]

    cursor = 0  # timeline frames in the rebuilt sequence
    counter = 0
    defined_file_ids: set[str] = set()

    def clone_clip(
        src_clip: etree._Element,
        new_id: str,
        file_in: int,
        file_out: int,
        start: int,
        end: int,
    ) -> etree._Element:
        clone = copy.deepcopy(src_clip)
        clone.set("id", new_id)
        _set_int(clone, "start", start)
        _set_int(clone, "end", end)
        _set_int(clone, "in", file_in)
        _set_int(clone, "out", file_out)
        _set_int(clone, "duration", file_out - file_in)
        # Premiere tick values, recalculated — never carried over stale.
        for tag, frames in (("pproTicksIn", file_in), ("pproTicksOut", file_out)):
            if clone.find(tag) is not None:
                _set_int(clone, tag, seconds_to_ppro_ticks(frames / rate))
        _remove(clone, "link")  # links are rebuilt for the new clone group
        # First reference defines the file; later references are id-only.
        file_el = clone.find("file")
        if file_el is not None:
            fid = file_el.get("id")
            if fid:
                if fid in defined_file_ids:
                    for child in list(file_el):
                        file_el.remove(child)
                else:
                    # Ensure the definition is full: copy from the first source
                    # definition if this occurrence is a bare reference.
                    if len(file_el) == 0:
                        full = None
                        for cand in tree.getroot().iterfind(f".//file[@id='{fid}']"):
                            if len(cand):
                                full = cand
                                break
                        if full is not None:
                            clone.remove(file_el)
                            file_el = copy.deepcopy(full)
                            # insert after out element for tidy ordering
                            clone.append(file_el)
                    defined_file_ids.add(fid)
        return clone

    for mapping in plan.mappings:
        counter += 1
        in_frames = seconds_to_frames(mapping.in_seconds, rate, src.ntsc)
        out_frames = seconds_to_frames(mapping.out_seconds, rate, src.ntsc)
        if out_frames <= in_frames:
            raise RebuildError(
                f"Beat {mapping.bid}: out ({mapping.out_seconds}s) is not after "
                f"in ({mapping.in_seconds}s)."
            )

        # Primary video clipitem for the beat. Explicit refs are a hint;
        # the timeline span is authoritative and resolves deterministically.
        video_ref = None
        for ref in mapping.clipitem_refs:
            if ref in src.video_clips:
                candidate = src.video_clips[ref]
                c_start = _txt(candidate, "start")
                c_end = _txt(candidate, "end")
                if (c_start is not None and c_end is not None
                        and int(c_start) <= in_frames < int(c_end)):
                    video_ref = ref
                break
        if video_ref is None:
            for cid, clip in src.video_clips.items():
                c_start, c_end = _txt(clip, "start"), _txt(clip, "end")
                if (c_start is not None and c_end is not None
                        and int(c_start) <= in_frames < int(c_end)):
                    video_ref = cid
                    break
        if video_ref is None:
            raise RebuildError(
                f"Beat {mapping.bid}: no video clipitem on the source timeline "
                f"covers {mapping.in_seconds}s (frame {in_frames}). "
                f"Refs given: {mapping.clipitem_refs or '(none)'}."
            )
        src_v = src.video_clips[video_ref]
        v_end = _txt(src_v, "end")
        if v_end is not None and out_frames > int(v_end):
            raise RebuildError(
                f"Beat {mapping.bid}: span {mapping.in_seconds}s–{mapping.out_seconds}s "
                f"crosses a clipitem boundary at frame {v_end} "
                f"(clip {video_ref} ends there). A beat cannot span two source "
                "clips; split the beat or correct the span."
            )
        file_in, file_out = _timeline_to_file_frames(src_v, in_frames, out_frames, mapping.bid)
        duration = file_out - file_in
        start, end = cursor, cursor + duration

        v_id = f"sage-b{counter}-v"
        v_clone = clone_clip(src_v, v_id, file_in, file_out, start, end)
        vtrack.append(v_clone)

        # Linked audio: follow the source clip's links (Style B: preserve sync,
        # keep audio independently manageable — no over-linking).
        group: list[tuple[etree._Element, str, int]] = [(v_clone, "video", 1)]
        a_index = 0
        for link_ref in [
            lr.text.strip() for lr in src_v.findall("link/linkclipref")
            if lr.text and lr.text.strip() and lr.text.strip() != video_ref
        ]:
            src_a = src.audio_clips.get(link_ref)
            if src_a is None:
                continue
            a_index += 1
            a_id = f"sage-b{counter}-a{a_index}"
            a_clone = clone_clip(src_a, a_id, file_in, file_out, start, end)
            audio_track(a_index).append(a_clone)
            group.append((a_clone, "audio", a_index))

        # Rebuild links within the clone group.
        if len(group) > 1:
            for el, _, _ in group:
                for idx, (other, mtype, tindex) in enumerate(group, start=1):
                    link = etree.SubElement(el, "link")
                    etree.SubElement(link, "linkclipref").text = other.get("id")
                    etree.SubElement(link, "mediatype").text = mtype
                    etree.SubElement(link, "trackindex").text = str(tindex)
                    etree.SubElement(link, "clipindex").text = str(counter)

        cursor = end

    _set_int(out_seq, "duration", cursor)
    # keep <duration> near the top for convention
    out_seq.insert(1, out_seq.find("duration"))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    etree.ElementTree(out_root).write(
        str(output_path),
        xml_declaration=True,
        encoding="UTF-8",
        doctype="<!DOCTYPE xmeml>",
        pretty_print=True,
    )
    return output_path
