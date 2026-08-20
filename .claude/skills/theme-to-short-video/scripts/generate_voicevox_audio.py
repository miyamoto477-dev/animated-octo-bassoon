#!/usr/bin/env python3
"""Generate VOICEVOX wav files from scripts/voicevox_lines.tsv."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path


def parse_speaker_map(items: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for item in items:
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"speaker map must be name=id: {item}")
        name, value = item.split("=", 1)
        mapping[name.strip()] = int(value.strip())
    return mapping


def request_json(url: str, method: str = "GET", body: bytes | None = None) -> object:
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str, body: bytes) -> bytes:
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def engine_ready(base_url: str) -> bool:
    try:
        request_json(f"{base_url}/version")
        return True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def start_engine_if_needed(base_url: str, start_script: Path) -> None:
    if engine_ready(base_url):
        return
    result = subprocess.run([sys.executable, str(start_script)], text=True)
    if result.returncode != 0 or not engine_ready(base_url):
        raise RuntimeError("VOICEVOX Engine is not ready")


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / float(wav.getframerate())


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate VOICEVOX audio line by line.")
    parser.add_argument("--project", default=".", help="Project folder containing scripts/voicevox_lines.tsv")
    parser.add_argument("--input", default="scripts/voicevox_lines.tsv", help="TSV path relative to project")
    parser.add_argument("--out-dir", default="audio/voicevox", help="Output dir relative to project")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50021)
    parser.add_argument("--speaker", type=int, default=3, help="Default VOICEVOX speaker id")
    parser.add_argument("--speaker-map", nargs="*", default=[], help="Speaker overrides like narrator=3 character_a=2")
    parser.add_argument("--speed", type=float, default=1.08)
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--intonation", type=float, default=1.0)
    parser.add_argument("--volume", type=float, default=1.0)
    parser.add_argument("--pre-phoneme", type=float, default=0.08)
    parser.add_argument("--post-phoneme", type=float, default=0.08)
    parser.add_argument("--skip-start", action="store_true", help="Do not try to start VOICEVOX Engine")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    input_path = project / args.input
    out_dir = project / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    base_url = f"http://{args.host}:{args.port}"
    if not args.skip_start:
        start_script = Path(__file__).with_name("start_voicevox_engine.py")
        start_engine_if_needed(base_url, start_script)
    elif not engine_ready(base_url):
        raise RuntimeError(f"VOICEVOX Engine is not ready: {base_url}")

    speaker_map = parse_speaker_map(args.speaker_map)
    outputs: list[dict[str, object]] = []

    with input_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            line_id = (row.get("line_id") or "").strip()
            text = (row.get("text") or "").strip()
            if not line_id or not text:
                continue
            speaker_name = (row.get("speaker") or "narrator").strip()
            speaker_id = speaker_map.get(speaker_name, args.speaker)

            query_params = urllib.parse.urlencode({"text": text, "speaker": speaker_id})
            query = request_json(f"{base_url}/audio_query?{query_params}", method="POST")
            assert isinstance(query, dict)
            query["speedScale"] = args.speed
            query["pitchScale"] = args.pitch
            query["intonationScale"] = args.intonation
            query["volumeScale"] = args.volume
            query["prePhonemeLength"] = args.pre_phoneme
            query["postPhonemeLength"] = args.post_phoneme

            synthesis_params = urllib.parse.urlencode({"speaker": speaker_id})
            wav_bytes = request_bytes(
                f"{base_url}/synthesis?{synthesis_params}",
                json.dumps(query, ensure_ascii=False).encode("utf-8"),
            )
            wav_path = out_dir / f"{line_id}.wav"
            wav_path.write_bytes(wav_bytes)
            outputs.append(
                {
                    "line_id": line_id,
                    "speaker": speaker_name,
                    "speaker_id": speaker_id,
                    "text": text,
                    "file": str(wav_path.relative_to(project)),
                    "duration": round(wav_duration(wav_path), 3),
                }
            )

    manifest_path = out_dir / "voicevox_audio_manifest.json"
    manifest_path.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
