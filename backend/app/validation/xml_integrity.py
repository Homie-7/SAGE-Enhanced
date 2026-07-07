"""XML integrity checks (deterministic, canonical file 04 checklist):
  - well formed (parser round-trip)
  - timing coherent (start/end vs in/out durations)
  - file definitions valid, references resolvable
  - links reference existing clipitems
  - required tracks present
  - likely import-safe (reported as likelihood, never certainty)
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from app.schemas.state import RebuildStyle
from app.validation.report import ReportBuilder


def check_output_xml(output_path: str | Path, style: RebuildStyle, rb: ReportBuilder) -> None:
    output_path = Path(output_path)
    try:
        tree = etree.parse(str(output_path))
    except (etree.XMLSyntaxError, OSError) as exc:
        rb.failed(
            "xml_well_formed",
            why_it_blocks=f"Output XML failed to parse: {exc}.",
            what_is_needed="Regenerate the rebuild; the output must be well-formed xmeml.",
        )
        return
    rb.passed("xml_well_formed", "Output XML parses (round-trip).")

    seq = tree.getroot().find(".//sequence")
    if seq is None:
        rb.failed("xml_structure", "Output has no <sequence>.", "Regenerate the rebuild.")
        return

    clipitems = seq.findall(".//clipitem")
    clip_ids = {c.get("id") for c in clipitems}

    timing_problems, ref_problems, link_problems = [], [], []
    defined_files = set()
    for c in clipitems:
        cid = c.get("id", "?")
        try:
            start, end = int(c.findtext("start")), int(c.findtext("end"))
            in_p, out_p = int(c.findtext("in")), int(c.findtext("out"))
        except (TypeError, ValueError):
            timing_problems.append(f"{cid}: missing/non-numeric timing")
            continue
        if not (start < end and in_p < out_p and (end - start) == (out_p - in_p)):
            timing_problems.append(
                f"{cid}: start/end [{start},{end}] inconsistent with in/out [{in_p},{out_p}]"
            )
        f = c.find("file")
        if f is None or not f.get("id"):
            ref_problems.append(f"{cid}: no file reference")
        elif len(f):
            defined_files.add(f.get("id"))
        for lr in c.findall("link/linkclipref"):
            if lr.text and lr.text.strip() not in clip_ids:
                link_problems.append(f"{cid} -> {lr.text.strip()}")

    referenced_files = {
        f.get("id") for f in seq.findall(".//clipitem/file") if f.get("id")
    }
    undefined = referenced_files - defined_files
    if undefined:
        ref_problems.append(f"file ids referenced but never defined: {sorted(undefined)}")

    if timing_problems:
        rb.failed("xml_timing", why_it_blocks="; ".join(timing_problems),
                  what_is_needed="Regenerate the rebuild; timing must be coherent.")
    else:
        rb.passed("xml_timing", "Clipitem timing is coherent (start/end matches in/out).")

    if ref_problems:
        rb.failed("xml_file_refs", why_it_blocks="; ".join(ref_problems),
                  what_is_needed="Every clipitem must reference a defined file.")
    else:
        rb.passed("xml_file_refs", "All file references resolve to definitions.")

    if link_problems:
        rb.failed("xml_links", why_it_blocks=f"Dangling links: {link_problems}.",
                  what_is_needed="Links must reference clipitems present in the output.")
    else:
        rb.passed("xml_links", "All links reference existing clipitems.")

    video_tracks = len(seq.findall("media/video/track"))
    if video_tracks < 1:
        rb.failed("xml_tracks", "No video track in output.", "Regenerate the rebuild.")
    else:
        rb.passed("xml_tracks", f"{video_tracks} video track(s) present (Style {style.value}).")

    rb.warned(
        "import_safety",
        "Output is likely import-safe, never guaranteed: run the post-import "
        "checklist in Premiere (canonical file 05).",
    )
