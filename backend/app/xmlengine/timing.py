"""Timing maths: frames, samples, seconds, pproTicks.

Canonical rules (file 04):
  - use source XML frame/sample logic for timing
  - use the Premiere tick scale only for pproTicks
  - do not guess missing technical structure

PPRO_TICKS_PER_SECOND is the fixed Premiere tick scale.
"""

from __future__ import annotations

PPRO_TICKS_PER_SECOND = 254_016_000_000


def seconds_to_frames(seconds: float, frame_rate: float, ntsc: bool = False) -> int:
    rate = frame_rate * (1000 / 1001) if ntsc else frame_rate
    return round(seconds * rate)


def frames_to_seconds(frames: int, frame_rate: float, ntsc: bool = False) -> float:
    rate = frame_rate * (1000 / 1001) if ntsc else frame_rate
    return frames / rate


def seconds_to_ppro_ticks(seconds: float) -> int:
    return round(seconds * PPRO_TICKS_PER_SECOND)
