#!/usr/bin/env python3
import argparse
import glob
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATAS = ROOT / "src" / "datas"
ASSETS = ROOT / "assets"


def copy_set(prefix: str, dest: Path):
    patterns = sorted(glob.glob(str(DATAS / f"{prefix}-*.png")))
    if not patterns:
        raise SystemExit(f"No frames found for prefix {prefix} in {DATAS}")
    dest.mkdir(parents=True, exist_ok=True)
    # clean dest
    for p in dest.glob("*.png"):
        p.unlink()
    for src in patterns:
        shutil.copy2(src, dest / Path(src).name)
    print(f"Copied {len(patterns)} frames to {dest}")


def auto_pick(candidates: list[str]) -> str:
    # Choose the candidate with the most frames
    best = None
    best_count = -1
    for p in candidates:
        count = len(glob.glob(str(DATAS / f"{p}-*.png")))
        if count > best_count:
            best = p
            best_count = count
    if best is None or best_count <= 0:
        raise SystemExit("No suitable candidates found in datas")
    return best


def main():
    parser = argparse.ArgumentParser(description="Select sprite sequences from src/datas into assets/")
    parser.add_argument("--player", help="datas prefix for player (e.g., 1216)")
    parser.add_argument("--melee", help="datas prefix for melee enemy (e.g., 1633)")
    parser.add_argument("--ranger", help="datas prefix for ranger enemy (e.g., 1295)")
    args = parser.parse_args()

    player = args.player or auto_pick(["1216", "1217", "1155"])
    melee = args.melee or auto_pick(["1633", "1615", "364"])
    ranger = args.ranger or auto_pick(["1295", "1530", "1180"]) 

    print(f"Using prefixes: player={player}, melee={melee}, ranger={ranger}")

    copy_set(player, ASSETS / "player")
    copy_set(melee, ASSETS / "enemy" / "melee")
    copy_set(ranger, ASSETS / "enemy" / "ranger")

    print("Done.")


if __name__ == "__main__":
    main()

