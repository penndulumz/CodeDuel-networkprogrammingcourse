"""Offline auto-grader for student bots - no server or internet required.

Plays your bot against the reference opponents of a game and prints a score
out of 10. Teachers can run it on each student's file to grade a whole class
during an offline session.

Usage:
    python starter_kit/grade.py <bot.py> [--game connect4|caro|rps9x9] [--games N]
    python starter_kit/grade.py bots_folder/ --game caro --csv results.csv

Examples:
    python starter_kit/grade.py starter_kit/connect4_template.py --game connect4
    python starter_kit/grade.py submissions/ --game caro --csv diem.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.games import SUPPORTED_GAMES  # noqa: E402
from engine.grader import grade_bot  # noqa: E402


def print_report(path: Path, report: dict) -> None:
    """Print a readable grading report for one bot."""
    print(f"\n=== {path.name} - {report['game_name']} ===")
    if not report["valid"]:
        print(f"  {report['error']}")
    for row in report["opponents"]:
        print(
            f"  {row['name']:<18} thắng {row['wins']}  hòa {row['draws']}  thua {row['losses']}"
            f"  (trọng số {row['weight']})"
        )
        for err in row["errors"][:2]:
            print(f"      lỗi: {err}")
    print(f"  ĐIỂM: {report['score']:.1f} / 10  ({report['label']})")


def main(argv: list[str] | None = None) -> int:
    """Grade one bot file or every .py file in a folder."""
    parser = argparse.ArgumentParser(description="Offline bot grader (score out of 10)")
    parser.add_argument("target", help="Bot file, or a folder of bot files to grade in bulk")
    parser.add_argument("--game", choices=SUPPORTED_GAMES, default="connect4")
    parser.add_argument("--games", type=int, default=4, help="Games per reference opponent")
    parser.add_argument("--timeout", type=float, default=1.0, help="Seconds per move")
    parser.add_argument("--csv", help="Write a CSV summary (useful for teachers)")
    args = parser.parse_args(argv)

    target = Path(args.target)
    files = sorted(target.glob("*.py")) if target.is_dir() else [target]
    files = [f for f in files if f.name != "__init__.py"]
    if not files:
        print(f"Không tìm thấy file bot nào trong: {target}")
        return 1

    rows = []
    for path in files:
        report = grade_bot(
            path, args.game, games_per_opponent=args.games, timeout_per_turn=args.timeout,
            progress=lambda line: print(f"  . {line}"),
        )
        print_report(path, report)
        rows.append((path.name, report))

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["file", "game", "score", "label", "error"])
            for name, report in rows:
                writer.writerow([name, report["game_type"], report["score"], report["label"],
                                 report["error"] or ""])
        print(f"\nĐã ghi bảng điểm: {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
