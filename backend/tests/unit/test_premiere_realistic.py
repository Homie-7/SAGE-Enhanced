"""Reality-check: parser and rebuilder against the structural shape real
Premiere Pro FCP7-XML exports actually have (project wrapper, pproTicks,
masterclipid, id-only file refs, sourcetrack, stereo pairs on two mono
tracks, transitionitem, generatoritem, markers, filters, labels)."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from app.schemas.state import BeatMapping, RebuildPlan
from app.xmlengine.parser import parse_source_xml
from app.xmlengine.rebuilder import rebuild_sequence

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "xml" / "premiere_realistic.xml"


def test_parse_premiere_realistic_structure():
    facts = parse_source_xml(FIXTURE)
    assert facts.frame_rate == 25.0 and facts.ntsc is False
    assert facts.video_tracks == 2  # V2 holds only a generatoritem
    assert facts.audio_tracks == 2  # stereo exploded onto two mono tracks
    # generatoritem is not a clipitem; 2 video + 4 audio clipitems
    assert len(facts.clipitems) == 6
    assert facts.file_ids == ["file-1"]
    assert facts.multicam_detected is False
    assert facts.external_audio_detected is False
    # Dropped-intent elements are reported precisely, never silently ignored.
    joined = " ".join(facts.warnings)
    assert "transitionitem" in joined and "generatoritem" in joined
    # id-only later file refs still resolve to the same file id.
    c2 = next(c for c in facts.clipitems if c.clipitem_id == "clipitem-2")
    assert c2.file_id == "file-1"
    assert len(c2.links) == 3  # video + two audio channels


def test_rebuild_from_premiere_realistic_source(tmp_path):
    plan = RebuildPlan(
        style="B",
        mappings=[
            # source-timeline seconds; second clip region exercises the
            # timeline→file-frame translation through a non-zero <in>.
            BeatMapping(bid="B1", source_file_id="file-1", in_seconds=31.0, out_seconds=34.0),
            BeatMapping(bid="B2", source_file_id="file-1", in_seconds=2.0, out_seconds=5.0),
        ],
    )
    out = tmp_path / "edited.xml"
    rebuild_sequence(FIXTURE, plan, out)

    tree = etree.parse(str(out))
    video = tree.findall(".//media/video/track/clipitem")
    audio = tree.findall(".//media/audio/track/clipitem")
    assert len(video) == 2
    assert len(audio) == 4  # both stereo channels preserved per beat

    # B1 falls at timeline 775..850 → clipitem-2 whose file in==750:
    v1 = video[0]
    assert v1.findtext("start") == "0" and v1.findtext("end") == "75"
    assert v1.findtext("in") == "775" and v1.findtext("out") == "850"
    # B2 falls in clipitem-1 (file in == 0):
    v2 = video[1]
    assert v2.findtext("start") == "75" and v2.findtext("end") == "150"
    assert v2.findtext("in") == "50" and v2.findtext("out") == "125"

    # Exactly one full file definition; every other ref is id-only.
    files = tree.findall(".//file")
    full = [f for f in files if len(f)]
    assert len(full) == 1 and all(f.get("id") == "file-1" for f in files)
    # No transitions or generators leak into the rebuilt output.
    assert not tree.findall(".//transitionitem")
    assert not tree.findall(".//generatoritem")
    # Link groups resolve within the output.
    ids = {c.get("id") for c in video + audio}
    for ref in tree.findall(".//link/linkclipref"):
        assert ref.text in ids


def test_beat_spanning_two_source_clips_is_refused(tmp_path):
    import pytest
    from app.xmlengine.rebuilder import RebuildError

    plan = RebuildPlan(
        style="B",
        mappings=[BeatMapping(bid="B1", source_file_id="file-1",
                              in_seconds=28.0, out_seconds=33.0)],  # crosses frame 750
    )
    with pytest.raises(RebuildError, match="crosses a clipitem boundary"):
        rebuild_sequence(FIXTURE, plan, tmp_path / "out.xml")
