#!/usr/bin/env python3
"""Start or verify a local VOICEVOX Engine for short-video production."""

from __future__ import annotations

import argparse
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def engine_url(host: str, port: int, path: str = "/version") -> str:
    return f"http://{host}:{port}{path}"


def is_ready(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(engine_url(host, port), timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError):
        return False


def wait_until_ready(host: str, port: int, timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_ready(host, port):
            return True
        time.sleep(1.0)
    return is_ready(host, port)


def start_with_command(command: str, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("ab")
    subprocess.Popen(
        shlex.split(command),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def start_voicevox_app() -> bool:
    if platform.system() != "Darwin":
        return False
    commands = [
        ["open", "-a", "VOICEVOX"],
        ["open", "/Applications/VOICEVOX.app"],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            return True
    return False


def start_with_docker(host: str, port: int) -> bool:
    docker = shutil.which("docker")  # type: ignore[name-defined]
    if not docker:
        return False
    command = [
        docker,
        "run",
        "--rm",
        "-d",
        "-p",
        f"{host}:{port}:50021",
        "voicevox/voicevox_engine:cpu-latest",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start or verify VOICEVOX Engine.")
    parser.add_argument("--host", default=os.environ.get("VOICEVOX_ENGINE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("VOICEVOX_ENGINE_PORT", "50021")))
    parser.add_argument("--timeout", type=float, default=45.0, help="Seconds to wait for Engine readiness")
    parser.add_argument("--engine-cmd", default=os.environ.get("VOICEVOX_ENGINE_CMD", ""))
    parser.add_argument("--log", default="voicevox_engine.log", help="Log file for custom engine command")
    parser.add_argument("--no-open-app", action="store_true", help="Do not try opening the macOS VOICEVOX app")
    parser.add_argument("--check-only", action="store_true", help="Only check whether Engine is running")
    args = parser.parse_args()

    if is_ready(args.host, args.port):
        print(f"VOICEVOX Engine is ready: {engine_url(args.host, args.port)}")
        return 0

    if args.check_only:
        print(f"VOICEVOX Engine is not ready: {engine_url(args.host, args.port)}", file=sys.stderr)
        return 2

    if args.engine_cmd:
        start_with_command(args.engine_cmd, Path(args.log))
    elif not args.no_open_app:
        start_voicevox_app()

    if wait_until_ready(args.host, args.port, args.timeout):
        print(f"VOICEVOX Engine is ready: {engine_url(args.host, args.port)}")
        return 0

    print(
        "VOICEVOX Engine did not become ready. Start VOICEVOX manually, "
        "or set VOICEVOX_ENGINE_CMD to the engine launch command.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
