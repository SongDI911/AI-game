"""小游戏基类"""
from __future__ import annotations

import pygame as pg

from ..config import WIDTH, HEIGHT


class BaseMinigame:
    """小游戏基类"""
    
    def __init__(self, level: int = 1):
        self.level = level
        self.completed = False
        self.score = 0
        self.timer = 0.0
    
    def handle_event(self, event: pg.Event) -> bool:
        """处理事件，返回是否完成"""
        return self.completed
    
    def update(self, dt: float):
        """更新游戏状态"""
        if not self.completed:
            self.timer += dt
    
    def draw(self, surface: pg.Surface):
        """绘制游戏"""
        raise NotImplementedError
    
    def get_score(self) -> int:
        """获取得分"""
        return self.score
