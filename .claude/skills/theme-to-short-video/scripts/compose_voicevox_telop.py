#!/usr/bin/env python3
"""Compose a Higgsfield clip with VOICEVOX audio and burned-in ASS telops."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def find_ffmpeg() -> str:
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - depends on local env
        raise RuntimeError(
            "ffmpeg was not found. Install ffmpeg, set FFMPEG, or install imageio-ffmpeg."
        ) from exc


def ffmpeg_info(ffmpeg: str, video: Path) -> str:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(video)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stderr + result.stdout


def probe_duration(ffmpeg: str, video: Path) -> float:
    info = ffmpeg_info(ffmpeg, video)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", info)
    if not match:
        raise RuntimeError(f"Could not read video duration from {video}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    cs = round(seconds * 100)
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\\\N", r"\N").replace("\n", r"\N")


def parse_caption(value: str) -> tuple[float, float, str]:
    parts = value.split(",", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("caption must be start,end,text")
    try:
        start = float(parts[0])
        end = float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("caption start/end must be numbers") from exc
    if end <= start:
        raise argparse.ArgumentTypeError("caption end must be after start")
    return start, end, ass_escape(parts[2])


def write_ass(path: Path, duration: float, badge: str, captions: list[tuple[float, float, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Hiragino Sans,74,&H00FFFFFF,&H000000FF,&H00111111,&H99000000,-1,0,0,0,100,100,0,0,1,8,2,2,80,80,360,1",
        "Style: Badge,Hiragino Sans,36,&H002EEBFF,&H000000FF,&H00111111,&H66000000,-1,0,0,0,100,100,0,0,1,5,1,8,80,80,130,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if badge:
        lines.append(f"Dialogue: 0,{ass_time(0)},{ass_time(duration)},Badge,,0,0,0,,{ass_escape(badge)}")
    for start, end, text in captions:
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def filter_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "\\\\").replace("'", r"\\'")
    return f"'{value}'"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Burn ASS telops and VOICEVOX audio into a Higgsfield mp4."
    )
    parser.add_argument("--video", required=True, help="Input Higgsfield mp4")
    parser.add_argument("--audio", required=True, help="Input VOICEVOX wav")
    parser.add_argument("--output", required=True, help="Output mp4")
    parser.add_argument("--subtitle-ass", help="Existing ASS subtitle file. Created if omitted.")
    parser.add_argument("--badge", default="", help="Small top badge text")
    parser.add_argument(
        "--caption",
        action="append",
        default=[],
        type=parse_caption,
        help="Caption as start,end,text. Use \\N for a line break.",
    )
    parser.add_argument("--audio-delay-ms", type=int, default=0)
    parser.add_argument("--duration", type=float, help="Override output duration in seconds")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--crf", type=int, default=18)
    args = parser.parse_args()

    ffmpeg = find_ffmpeg()
    video = Path(args.video).expanduser().resolve()
    audio = Path(args.audio).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = args.duration if args.duration is not None else probe_duration(ffmpeg, video)

    if args.subtitle_ass:
        ass_path = Path(args.subtitle_ass).expanduser().resolve()
    else:
        ass_path = output.with_suffix(".ass")
        write_ass(ass_path, duration, args.badge, args.caption)

    delay = max(0, args.audio_delay_ms)
    video_filter = (
        f"[0:v]scale={args.width}:{args.height}:force_original_aspect_ratio=increase,"
        f"crop={args.width}:{args.height},subtitles={filter_path(ass_path)}[v]"
    )
    audio_filter = f"[1:a]adelay={delay}:all=1,apad[a]"
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-filter_complex",
        f"{video_filter};{audio_filter}",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        f"{duration:.3f}",
        "-r",
        str(args.fps),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(args.crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True)
    print(output)
    print(ass_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
