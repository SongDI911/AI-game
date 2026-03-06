"""关卡过渡界面"""
from __future__ import annotations

import pygame as pg

from ..config import WIDTH, HEIGHT
from .. import fonts


class ChapterTransitionUI:
    """关卡过渡界面 - 显示关卡完成和即将进入小游戏"""
    
    def __init__(self, chapter: int):
        self.chapter = chapter
        self.font = fonts.get_font(24)
        self.title_font = fonts.get_font(36)
        self.small_font = fonts.get_font(16)
        
        self.timer = 0.0
        self.fade_in = 0.0
        self.fade_out = 0.0
        self.state = "fade_in"  # fade_in, display, fade_out, done
        self.display_duration = 2.0  # 显示时间（秒）
        self.fade_duration = 0.5  # 淡入淡出时间（秒）
    
    def update(self, dt: float) -> bool:
        """更新状态，返回是否完成"""
        if self.state == "fade_in":
            self.fade_in += dt / self.fade_duration
            if self.fade_in >= 1.0:
                self.fade_in = 1.0
                self.state = "display"
                self.timer = 0.0
        elif self.state == "display":
            self.timer += dt
            if self.timer >= self.display_duration:
                self.state = "fade_out"
        elif self.state == "fade_out":
            self.fade_out += dt / self.fade_duration
            if self.fade_out >= 1.0:
                self.fade_out = 1.0
                self.state = "done"
        
        return self.state == "done"
    
    def draw(self, surface: pg.Surface):
        """绘制过渡界面"""
        # 计算 alpha
        if self.state == "fade_in":
            alpha = int(255 * self.fade_in)
        elif self.state == "display":
            alpha = 255
        elif self.state == "fade_out":
            alpha = int(255 * (1.0 - self.fade_out))
        else:
            return
        
        # 绘制半透明背景
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180 * alpha // 255))
        surface.blit(overlay, (0, 0))
        
        # 绘制文字
        chapter_text = self.title_font.render(f"第 {self.chapter} 关 完成!", True, (255, 215, 0))
        chapter_rect = chapter_text.get_rect(centerx=WIDTH // 2, top=HEIGHT // 2 - 60)
        surface.blit(chapter_text, chapter_rect)
        
        minigame_text = self.font.render("准备进入小游戏挑战...", True, (200, 200, 255))
        minigame_rect = minigame_text.get_rect(centerx=WIDTH // 2, top=HEIGHT // 2 + 10)
        surface.blit(minigame_text, minigame_rect)
        
        continue_text = self.small_font.render("完成小游戏后继续下一关", True, (150, 150, 150))
        continue_rect = continue_text.get_rect(centerx=WIDTH // 2, top=HEIGHT // 2 + 50)
        surface.blit(continue_text, continue_rect)
