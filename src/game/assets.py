from __future__ import annotations

import glob
import os
from functools import lru_cache
from typing import List, Tuple, Dict

import pygame as pg

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datas"))
ASSET_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))


def _load_sequence(prefix: str, target_size: Tuple[int, int]) -> List[pg.Surface]:
    pattern = os.path.join(DATA_ROOT, f"{prefix}-*.png")
    files = sorted(glob.glob(pattern), key=lambda p: int(os.path.basename(p).split("-")[1].split(".")[0]))
    frames: List[pg.Surface] = []
    for fp in files:
        try:
            img = pg.image.load(fp).convert_alpha()
            if target_size:
                img = pg.transform.smoothscale(img, target_size)
            frames.append(img)
        except Exception:
            continue
    return frames


def _load_from_dir(dirpath: str, target_size: Tuple[int, int]) -> List[pg.Surface]:
    if not os.path.isdir(dirpath):
        return []
    files = sorted(
        [os.path.join(dirpath, f) for f in os.listdir(dirpath) if f.lower().endswith('.png')],
        key=lambda p: int(os.path.basename(p).split('-')[-1].split('.')[0]) if '-' in os.path.basename(p) else 0,
    )
    frames: List[pg.Surface] = []
    for fp in files:
        try:
            img = pg.image.load(fp).convert_alpha()
            if target_size:
                img = pg.transform.smoothscale(img, target_size)
            frames.append(img)
        except Exception:
            continue
    return frames


def _load_directional(root: str, target_size: Tuple[int, int]) -> Dict[str, List[pg.Surface]]:
    if not os.path.isdir(root):
        return {}
    dirs = [
        "up",
        "down",
        "left",
        "right",
        "up_left",
        "up_right",
        "down_left",
        "down_right",
    ]
    out: Dict[str, List[pg.Surface]] = {}
    for d in dirs:
        frames = _load_from_dir(os.path.join(root, d), target_size)
        if frames:
            out[d] = frames
    return out


# Predefined eight-way keys and angles (right-based)
DIR_KEYS = [
    "right",
    "up_right",
    "up",
    "up_left",
    "left",
    "down_left",
    "down",
    "down_right",
]
DIR_ANGLES = {
    "right": 0,
    "up_right": 45,
    "up": 90,
    "up_left": 135,
    "left": 180,
    "down_left": 225,
    "down": 270,
    "down_right": 315,
}


def build_dir_from_single(frames: List[pg.Surface]) -> Dict[str, List[pg.Surface]]:
    """Generate 8-direction variants by rotating right-facing frames.
    This is an approximation suitable when only a single direction exists.
    注意：如果已有方向性贴图，请使用 _load_directional 而非此函数。
    """
    out: Dict[str, List[pg.Surface]] = {}
    if not frames:
        return out
    # 只旋转 180 度修正上下方向，不再按方向旋转
    rotated_frames = [pg.transform.rotate(f, 180) for f in frames]
    for key in DIR_KEYS:
        out[key] = rotated_frames
    return out


def preload():
    """预加载常用序列帧，避免在首个房间切换/生成时卡顿。"""
    try:
        _ = get_player_frames()
        _ = get_player_dir_frames()
        _ = get_melee_enemy_frames()
        _ = get_melee_enemy_dir_frames()
        _ = get_ranger_enemy_frames()
        _ = get_ranger_enemy_dir_frames()
    except Exception:
        # 预加载失败不影响运行
        pass


@lru_cache(maxsize=None)
def get_player_frames() -> List[pg.Surface]:
    # 优先使用 assets 目录
    frames = _load_from_dir(os.path.join(ASSET_ROOT, 'player'), (48, 48))
    if len(frames) >= 4:
        return frames
    # 回退到 src/datas 按前缀组装
    for prefix in ("1216", "1217", "1155"):
        frames = _load_sequence(prefix, (48, 48))
        if len(frames) >= 8:
            return frames
    return []


@lru_cache(maxsize=None)
def get_player_dir_frames() -> Dict[str, List[pg.Surface]]:
    return _load_directional(os.path.join(ASSET_ROOT, 'player'), (48, 48))


@lru_cache(maxsize=None)
def get_melee_enemy_frames() -> List[pg.Surface]:
    frames = _load_from_dir(os.path.join(ASSET_ROOT, 'enemy', 'melee'), (44, 44))
    if len(frames) >= 4:
        return frames
    for prefix in ("1633", "1615", "364"):
        frames = _load_sequence(prefix, (44, 44))
        if len(frames) >= 6:
            return frames
    return []


@lru_cache(maxsize=None)
def get_melee_enemy_dir_frames() -> Dict[str, List[pg.Surface]]:
    return _load_directional(os.path.join(ASSET_ROOT, 'enemy', 'melee'), (44, 44))


@lru_cache(maxsize=None)
def get_ranger_enemy_frames() -> List[pg.Surface]:
    frames = _load_from_dir(os.path.join(ASSET_ROOT, 'enemy', 'ranger'), (44, 44))
    if len(frames) >= 4:
        return frames
    for prefix in ("1295", "1530", "1180"):
        frames = _load_sequence(prefix, (44, 44))
        if len(frames) >= 6:
            return frames
    # 未找到则回退近战序列
    return get_melee_enemy_frames()


@lru_cache(maxsize=None)
def get_ranger_enemy_dir_frames() -> Dict[str, List[pg.Surface]]:
    return _load_directional(os.path.join(ASSET_ROOT, 'enemy', 'ranger'), (44, 44))
