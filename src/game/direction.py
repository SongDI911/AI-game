import math
from typing import Tuple

import pygame as pg


def eight_way(v: pg.Vector2) -> str:
    """将向量映射为八方向键名：up/down/left/right 以及四个对角。
    当向量接近 0 时回退为 right。
    """
    if v.length_squared() <= 1e-4:
        return "right"
    ang = math.degrees(math.atan2(-v.y, v.x))  # screen y down, so invert y for compass-like
    # Normalize angle to [0,360)
    ang = (ang + 360) % 360
    # 8 个方向扇区（以 0/45/90 ... 为中心）
    sectors = [
        ("right", 0),
        ("up_right", 45),
        ("up", 90),
        ("up_left", 135),
        ("left", 180),
        ("down_left", 225),
        ("down", 270),
        ("down_right", 315),
    ]
    best = "right"
    best_diff = 1e9
    for name, center in sectors:
        diff = min(abs(ang - center), 360 - abs(ang - center))
        if diff < best_diff:
            best = name
            best_diff = diff
    return best


def smooth_facing(current: pg.Vector2, desired: pg.Vector2, factor: float = 0.25) -> pg.Vector2:
    """平滑插值朝向，避免瞬时抖动"""
    if desired.length_squared() == 0:
        return current
    out = current.lerp(desired.normalize(), factor)
    if out.length_squared() == 0:
        out.update(1, 0)
    else:
        out = out.normalize()
    return out


def hysteresis_flip(current_flip: bool, facing_x: float, threshold: float = 0.2) -> bool:
    """带回滞的左右翻转：降低接近水平时的抖动"""
    if current_flip:
        # currently left; flip back to right only if strong right
        return True if facing_x < threshold else False
    else:
        # currently right; flip to left only if strong left
        return False if facing_x > -threshold else True
