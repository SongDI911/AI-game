import math
from typing import Tuple


def clamp(x: float, a: float, b: float) -> float:
    """将数值限制在 [a, b] 区间"""
    return max(a, min(b, x))


def vec_norm(dx: float, dy: float, length: float) -> Tuple[float, float]:
    """将 (dx, dy) 归一化后缩放到指定长度"""
    mag = math.hypot(dx, dy)
    if mag == 0:
        return 0.0, 0.0
    f = length / mag
    return dx * f, dy * f


def angle_between(ax: float, ay: float, bx: float, by: float) -> float:
    """返回两向量的夹角（度）"""
    a_mag = math.hypot(ax, ay)
    b_mag = math.hypot(bx, by)
    if a_mag == 0 or b_mag == 0:
        return 180.0
    dot = (ax * bx + ay * by) / (a_mag * b_mag)
    dot = clamp(dot, -1.0, 1.0)
    return math.degrees(math.acos(dot))


def sign(x: float) -> int:
    """符号函数"""
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0
