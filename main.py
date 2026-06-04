"""
social-clip — Social Media Video Formatter
Powered by OpenShot (libopenshot Python bindings)

Usage examples:
    # Format for a single platform
    python main.py input.mp4 --platform tiktok --output out_tiktok.mp4

    # Format for all platforms at once
    python main.py input.mp4 --all --output-dir ./exports

    # Trim, add a title, and normalise audio
    python main.py input.mp4 --platform youtube \
        --title "My Travel Vlog" \
        --trim-start 5.0 --trim-end 60.0 \
        --output out.mp4

    # List available platforms
    python main.py --list-platforms
"""

import argparse
import sys
import time
from pathlib import Path

from formatter import VideoFormatter, PRESETS


# ---------------------------------------------------------------------------
# Progress bar (no external deps)
# ---------------------------------------------------------------------------

def _make_progress_cb(label: str):
    start = time.time()

    def cb(current: int, total: int) -> None:
        pct = current / total
        bar_len = 30
        filled = int(bar_len * pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        elapsed = time.time() - start
        eta = (elapsed / pct - elapsed) if pct > 0 else 0
        print(
            f"\r  {label}  [{bar}] {pct:5.1%}  ETA {eta:4.0f}s",
            end="",
            flush=True,
        )
        if current >= total:
            print()  # newline when done

    return cb


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="social-clip",
        description="Reformat any video for social media platforms using OpenShot.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument("input", nargs="?", help="Path to source video file")
    p.add_argument(
        "--list-platforms", "-l",
        action="store_true",
        help="Print available platform presets and exit",
    )

    # Output
    out_group = p.add_mutually_exclusive_group()
    out_group.add_argument("--output", "-o", help="Output file path (single platform)")
    out_group.add_argument(
        "--output-dir", "-d",
        help="Output directory when using --all (default: ./exports)",
        default="./exports",
    )

    # Platform selection
    platform_group = p.add_mutually_exclusive_group()
    platform_group.add_argument(
        "--platform", "-p",
        choices=list(PRESETS.keys()),
        help="Target platform",
    )
    platform_group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Export for all supported platforms",
    )

    # Editing options
    p.add_argument("--title", "-t", default="", help="Text overlay displayed on the video")
    p.add_argument("--trim-start", type=float, default=0.0, metavar="SECONDS",
                   help="Skip this many seconds from the start")
    p.add_argument("--trim-end", type=float, default=None, metavar="SECONDS",
                   help="Cut at this timestamp (default: end of clip)")
    p.add_argument("--no-normalize", action="store_true",
                   help="Disable automatic audio normalization")

    return p


def list_platforms() -> None:
    print("\nAvailable platforms:\n")
    col1, col2, col3 = 12, 22, 14
    print(f"  {'KEY':<{col1}} {'LABEL':<{col2}} {'RESOLUTION':<{col3}}  DESCRIPTION")
    print(f"  {'-'*col1} {'-'*col2} {'-'*col3}  -----------")
    for key, p in PRESETS.items():
        res = f"{p['width']}×{p['height']}"
        max_d = f" (max {p['max_duration']}s)" if p["max_duration"] else ""
        print(f"  {key:<{col1}} {p['label']:<{col2}} {res:<{col2}}{p['description']}{max_d}")
    print()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_platforms:
        list_platforms()
        return 0

    if not args.input:
        parser.error("Provide an input video file, or use --list-platforms.")

    if not args.platform and not args.all:
        parser.error("Specify --platform <name> or --all.")

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found — {input_path}", file=sys.stderr)
        return 1

    print(f"\nsocial-clip  |  source: {input_path.name}\n")

    try:
        with VideoFormatter(str(input_path)) as fmt:
            print(
                f"  Source info: {fmt.source_width}×{fmt.source_height}  "
                f"{fmt.source_fps:.2f} fps  {fmt.source_duration:.1f}s\n"
            )

            shared_kwargs = dict(
                title=args.title,
                trim_start=args.trim_start,
                trim_end=args.trim_end,
                normalize_audio=not args.no_normalize,
            )

            if args.all:
                output_dir = Path(args.output_dir)
                print(f"  Exporting all platforms → {output_dir}/\n")
                for platform in PRESETS:
                    out = output_dir / f"{input_path.stem}_{platform}.mp4"
                    print(f"  [{platform}]  {PRESETS[platform]['label']}")
                    fmt.format(
                        platform,
                        str(out),
                        progress_cb=_make_progress_cb(platform),
                        **shared_kwargs,
                    )
            else:
                out = args.output or f"{input_path.stem}_{args.platform}.mp4"
                fmt.format(
                    args.platform,
                    out,
                    progress_cb=_make_progress_cb(args.platform),
                    **shared_kwargs,
                )
                print(f"\n  Saved → {out}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print("\nDone.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
