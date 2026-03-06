from __future__ import annotations

from dataclasses import dataclass
import pygame as pg

Vec = pg.Vector2


@dataclass
class DamageEvent:
    pos: Vec
    radius: float
    damage: int
    source: str  # 'player' | 'enemy'
    time: float
    blockable: bool = True

