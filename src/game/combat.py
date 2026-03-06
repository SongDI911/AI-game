from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set, Optional

import pygame as pg


@dataclass
class Attack:
    owner: str  # 拥有者（'player'）
    origin: pg.Vector2  # 生成时的参考位置（会随玩家更新）
    facing: pg.Vector2  # 朝向
    offset: float  # 相对中心的前向偏移
    radius: int  # 判定半径
    damage: int  # 伤害
    startup: float  # 前摇时间
    active: float  # 生效时间
    recovery: float  # 后摇时间
    time: float = 0.0  # 累计时间
    already_hit: Set[int] = field(default_factory=set)  # 已命中的对象 id

    def total(self) -> float:
        return self.startup + self.active + self.recovery

    def is_active(self) -> bool:
        # 是否处于生效帧
        return self.startup <= self.time < self.startup + self.active

    def can_chain(self) -> bool:
        # 后段生效帧至前段后摇为连段窗口
        return self.startup + self.active * 0.6 <= self.time < self.startup + self.active + 0.12

    def done(self) -> bool:
        return self.time >= self.total()

    def update(self, dt: float, new_origin: pg.Vector2, new_facing: pg.Vector2):
        self.time += dt
        # 跟随拥有者位置/朝向
        self.origin.update(new_origin)
        self.facing.update(new_facing)

    def center(self) -> pg.Vector2:
        return self.origin + self.facing * (self.offset + self.radius * 0.6)

    def hit_id(self, obj) -> int:
        # simple id based on object identity
        return id(obj)

    def draw(self, surf: pg.Surface, color=(255, 120, 120)):
        # 调试/可视化：按朝向画出楔形
        if not self.is_active():
            return
        c = self.origin
        # 绘制沿朝向的三角楔形
        length = self.offset + self.radius
        width = max(8, int(self.radius * 0.8))
        # 三角形三个点：中心 -> 左/右偏移
        f = self.facing.normalize() if self.facing.length_squared() > 0 else pg.Vector2(1, 0)
        n = pg.Vector2(-f.y, f.x)  # perpendicular
        p0 = (c.x, c.y)
        p1 = (c + f * length + n * width * 0.5)
        p2 = (c + f * length - n * width * 0.5)
        pts = [(int(p0[0]), int(p0[1])), (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y))]
        pg.draw.polygon(surf, color, pts, width=0)
        pg.draw.polygon(surf, (255, 200, 200), pts, width=2)
