"""
Core formatting engine — wraps OpenShot's Timeline, Clip, and FFmpegWriter
to reframe and export video for a given platform preset.

How OpenShot's rendering pipeline works:
  1. A Timeline is the master canvas (resolution, fps, sample rate).
  2. Clips are added to Layers on the timeline.  Layer 1 is background,
     higher layers composite on top (like Photoshop layers).
  3. Scale/position Keyframes on each clip control how it sits in the frame.
  4. FFmpegWriter iterates frames from the timeline and encodes to disk.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import openshot

from .presets import PRESETS
from .effects import build_title_overlay, apply_volume_normalization


class VideoFormatter:
    """
    Formats a single source video for one or more social media platforms.

    Usage:
        fmt = VideoFormatter("input.mp4")
        fmt.format("tiktok", "out_tiktok.mp4", title="My Trip to Japan")
        fmt.close()

    Or use as a context manager:
        with VideoFormatter("input.mp4") as fmt:
            fmt.format("youtube", "out.mp4")
    """

    def __init__(self, input_path: str | Path) -> None:
        self.input_path = str(input_path)
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        # Open the source clip once; reuse it across multiple format() calls.
        self._source = openshot.Clip(self.input_path)
        self._source.Open()

        info = self._source.Reader().info
        self.source_width: int = info.width
        self.source_height: int = info.height
        self.source_fps: float = info.fps.ToFloat()
        self.source_duration: float = info.duration
        self.source_frames: int = int(info.video_length)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(
        self,
        platform: str,
        output_path: str | Path,
        *,
        title: str = "",
        trim_start: float = 0.0,
        trim_end: float | None = None,
        normalize_audio: bool = True,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> None:
        """
        Render the source video into output_path for the given platform.

        platform      : key from presets.PRESETS
        output_path   : destination file (.mp4 recommended)
        title         : optional text overlay shown at the bottom
        trim_start    : seconds to skip from the beginning
        trim_end      : seconds to cut at (None = end of clip)
        normalize_audio: apply RMS-based volume levelling
        progress_cb   : optional callback(current_frame, total_frames)
        """
        if platform not in PRESETS:
            raise ValueError(
                f"Unknown platform '{platform}'. "
                f"Available: {', '.join(PRESETS)}"
            )

        preset = PRESETS[platform]
        output_path = str(output_path)

        # Respect platform max duration
        actual_end = trim_end if trim_end is not None else self.source_duration
        if preset["max_duration"] and actual_end - trim_start > preset["max_duration"]:
            actual_end = trim_start + preset["max_duration"]

        timeline = self._build_timeline(preset)
        clip = self._build_clip(preset, trim_start, actual_end, normalize_audio)
        timeline.AddClip(clip)

        if title:
            total_tl_frames = int((actual_end - trim_start) * preset["fps"])
            overlay = build_title_overlay(
                title,
                preset["width"],
                preset["height"],
                start_frame=1,
                end_frame=total_tl_frames,
                font_size=max(40, preset["height"] // 24),
            )
            if overlay:
                timeline.AddClip(overlay)

        timeline.Open()
        self._write(timeline, preset, output_path, progress_cb)
        timeline.Close()

    def format_all(
        self,
        platforms: list[str],
        output_dir: str | Path,
        stem: str | None = None,
        **kwargs,
    ) -> dict[str, str]:
        """
        Convenience wrapper — formats for every platform in the list and
        writes files into output_dir.  Returns {platform: output_path}.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        base = stem or Path(self.input_path).stem
        results: dict[str, str] = {}

        for platform in platforms:
            out = str(output_dir / f"{base}_{platform}.mp4")
            print(f"  → {PRESETS[platform]['label']} ({platform})")
            self.format(platform, out, **kwargs)
            results[platform] = out

        return results

    def close(self) -> None:
        self._source.Close()

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "VideoFormatter":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_timeline(self, preset: dict) -> openshot.Timeline:
        return openshot.Timeline(
            preset["width"],
            preset["height"],
            openshot.Fraction(preset["fps"], preset["fps_den"]),
            preset["sample_rate"],
            preset["channels"],
            openshot.LAYOUT_STEREO,
        )

    def _build_clip(
        self,
        preset: dict,
        trim_start: float,
        trim_end: float,
        normalize_audio: bool,
    ) -> openshot.Clip:
        clip = openshot.Clip(self.input_path)
        clip.Open()

        # Trim
        clip.Start(trim_start)
        clip.End(trim_end)
        clip.Position(0)
        clip.Layer(1)

        # Compute scale to fill the target frame ("cover" fit — same as
        # CSS background-size: cover).  We scale up the smaller axis until
        # both dimensions meet or exceed the target, then centre-crop.
        src_ar = self.source_width / self.source_height
        tgt_ar = preset["width"] / preset["height"]

        if src_ar > tgt_ar:
            # Source is wider than target → fit height, crop sides
            scale = preset["height"] / self.source_height
        else:
            # Source is taller than target → fit width, crop top/bottom
            scale = preset["width"] / self.source_width

        clip.scale_x = openshot.Keyframe(scale)
        clip.scale_y = openshot.Keyframe(scale)

        # Centre the clip on the timeline canvas (OpenShot uses -0.5…+0.5
        # normalised coordinates relative to the timeline size)
        clip.location_x = openshot.Keyframe(0.0)
        clip.location_y = openshot.Keyframe(0.0)

        if normalize_audio:
            apply_volume_normalization(clip)

        return clip

    def _write(
        self,
        timeline: openshot.Timeline,
        preset: dict,
        output_path: str,
        progress_cb: Callable[[int, int], None] | None,
    ) -> None:
        writer = openshot.FFmpegWriter(output_path)

        writer.SetVideoOptions(
            True,
            preset["codec"],
            openshot.Fraction(preset["fps"], preset["fps_den"]),
            preset["width"],
            preset["height"],
            openshot.Fraction(1, 1),
            False,
            False,
            preset["bitrate"],
        )

        writer.SetAudioOptions(
            True,
            preset["audio_codec"],
            preset["sample_rate"],
            preset["channels"],
            openshot.LAYOUT_STEREO,
            preset["audio_bitrate"],
        )

        writer.Open()

        total = timeline.GetMaxFrame()
        for frame_num in range(1, total + 1):
            writer.WriteFrame(timeline.GetFrame(frame_num))
            if progress_cb:
                progress_cb(frame_num, total)

        writer.Close()
