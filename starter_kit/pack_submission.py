"""Create a portable CodeDuel submission package while offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.games import GAMES
from engine.sandbox import validate_bot_source


def create_submission(bot_path: Path, game_type: str, output_dir: Path) -> Path:
    """Validate a bot and package it with offline submission metadata."""
    if game_type not in GAMES:
        raise ValueError(f"Unknown game '{game_type}'. Choose from: {', '.join(GAMES)}")
    if bot_path.suffix.lower() != ".py" or not bot_path.is_file():
        raise ValueError("Choose an existing Python bot file (.py)")

    source_bytes = bot_path.read_bytes()
    if len(source_bytes) > 1024 * 1024:
        raise ValueError("Bot file exceeds the 1 MB competition limit")
    try:
        source = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Bot file must be saved as UTF-8") from exc

    valid, error = validate_bot_source(source)
    if not valid:
        raise ValueError(f"Bot validation failed: {error}")

    submission_id = str(uuid.uuid4())
    manifest = {
        "format": "codeduel-offline-submission",
        "version": 1,
        "submission_id": submission_id,
        "created_at_device": datetime.now().astimezone().isoformat(),
        "game_type": game_type,
        "bot_filename": bot_path.name,
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / f"{bot_path.stem}_{submission_id[:8]}.cdsubmit.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("bot.py", source_bytes)
    return package_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a bot and create an offline package to upload later on the CodeDuel profile page."
    )
    parser.add_argument("bot", type=Path, help="Path to your .py bot")
    parser.add_argument("--game", choices=sorted(GAMES), default="rps9x9")
    parser.add_argument("--output-dir", type=Path, default=Path("submissions"))
    args = parser.parse_args()

    try:
        package = create_submission(args.bot, args.game, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Offline package created: {package}")
    print("This is saved on this device; it is not an official submission until the server returns a receipt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
