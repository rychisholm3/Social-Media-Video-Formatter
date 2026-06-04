"""
OpenShot effect helpers — text overlays and audio normalization.

OpenShot represents all animated properties as Keyframe objects so that
values can change over time. Even a static value (e.g. a title that never
moves) is expressed as a single-point Keyframe. This module wraps that
pattern into ergonomic builder functions.
"""

import openshot


def build_title_overlay(
    text: str,
    timeline_width: int,
    timeline_height: int,
    start_frame: int,
    end_frame: int,
    position: str = "bottom",
    font_size: int = 60,
) -> openshot.FrameMapper | None:
    """
    Create an OpenShot TitleClip-style text overlay using the built-in
    QtImageReader (SVG-rendered text).  Returns the configured Clip ready
    to be added to a Timeline, or None if text is empty.

    Position options: 'top', 'center', 'bottom'
    """
    if not text:
        return None

    # OpenShot renders text via its QtImageReader with an SVG payload.
    svg = _build_text_svg(text, timeline_width, timeline_height, position, font_size)

    reader = openshot.QtImageReader(svg)
    reader.Open()

    clip = openshot.Clip(reader)
    clip.Position(start_frame / 30.0)
    clip.Start(0)
    clip.End((end_frame - start_frame) / 30.0)
    clip.Layer(2)

    # Fade in/out over 0.5 s (15 frames at 30 fps)
    alpha = openshot.Keyframe()
    alpha.AddPoint(1, 0.0)
    alpha.AddPoint(15, 1.0)
    alpha.AddPoint(end_frame - start_frame - 15, 1.0)
    alpha.AddPoint(end_frame - start_frame, 0.0)
    clip.alpha = alpha

    return clip


def _build_text_svg(
    text: str,
    width: int,
    height: int,
    position: str,
    font_size: int,
) -> str:
    """Return an SVG string that OpenShot's QtImageReader can render."""
    y_map = {"top": int(height * 0.12), "center": height // 2, "bottom": int(height * 0.88)}
    y = y_map.get(position, y_map["bottom"])

    # Semi-transparent black pill behind the text for readability
    pill_h = font_size + 20
    pill_y = y - font_size

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect x="0" y="{pill_y}" width="{width}" height="{pill_h}" '
        f'fill="black" fill-opacity="0.55" rx="12"/>'
        f'<text x="{width // 2}" y="{y}" '
        f'font-family="Arial, sans-serif" font-size="{font_size}" font-weight="bold" '
        f'fill="white" text-anchor="middle">{text}</text>'
        f"</svg>"
    )


def apply_volume_normalization(clip: openshot.Clip, target_lufs: float = -14.0) -> None:
    """
    Scale clip audio to approximate a target loudness level.

    OpenShot does not expose a full loudness meter via Python bindings, so
    we use a pragmatic gain approach: read a sample of frames, compute RMS,
    then set a corrective Keyframe on clip.volume.

    target_lufs: broadcast standard for online video is -14 LUFS (YouTube/
                 Spotify recommendation).  We approximate using RMS → dB
                 conversion (close enough for most content).
    """
    import math

    sample_count = 0
    sum_sq = 0.0

    clip.Open()
    total = int(clip.Reader().info.video_length)
    step = max(1, total // 200)  # sample ~200 frames

    for i in range(1, total, step):
        frame = clip.GetFrame(i)
        samples = frame.GetAudioSamplesCount()
        if samples == 0:
            continue
        for s in range(min(samples, 512)):
            val = frame.GetAudioSample(0, s, 1)
            sum_sq += val * val
            sample_count += 1

    if sample_count == 0 or sum_sq == 0:
        return

    rms = math.sqrt(sum_sq / sample_count)
    rms_db = 20 * math.log10(rms + 1e-9)

    # Rough mapping: assume RMS ≈ LUFS - 3 dB for typical speech/music
    current_lufs_est = rms_db - 3.0
    gain_db = target_lufs - current_lufs_est
    gain_linear = 10 ** (gain_db / 20.0)

    # Clamp to safe range
    gain_linear = max(0.1, min(gain_linear, 6.0))

    volume_kf = openshot.Keyframe(gain_linear)
    clip.volume = volume_kf
