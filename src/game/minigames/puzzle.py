"""拼图小游戏模块"""
from __future__ import annotations

import random
import pygame as pg

from ..config import WIDTH, HEIGHT
from .. import fonts


class PuzzleTile:
    """拼图方块"""
    
    def __init__(self, x: int, y: int, size: int, correct_pos: tuple, image=None):
        self.x = x  # 当前显示位置
        self.y = y
        self.size = size
        self.correct_pos = correct_pos  # 正确位置 (cx, cy)
        self.image = image  # 该方块对应的图片部分
        self.selected = False
        self.in_correct_place = False
    
    def is_in_correct_place(self) -> bool:
        """检查是否在正确位置"""
        return (abs(self.x - self.correct_pos[0]) < 2 and 
                abs(self.y - self.correct_pos[1]) < 2)
    
    def contains_point(self, px: int, py: int) -> bool:
        """检查点是否在方块内"""
        return (self.x <= px <= self.x + self.size and
                self.y <= py <= self.y + self.size)
    
    def draw(self, surface: pg.Surface):
        """绘制方块"""
        rect = pg.Rect(self.x, self.y, self.size, self.size)
        
        if self.image:
            # 绘制图片部分
            surface.blit(self.image, (self.x, self.y))
        
        # 绘制边框
        if self.selected:
            pg.draw.rect(surface, (255, 255, 0), rect, 3)
        elif self.in_correct_place:
            pg.draw.rect(surface, (0, 255, 0), rect, 2)
        else:
            pg.draw.rect(surface, (255, 255, 255), rect, 1)


class PuzzleGame:
    """拼图小游戏"""
    
    def __init__(self, level: int = 1):
        self.level = level
        self.grid_size = min(3 + level, 5)  # 3x3 到 5x5，随关卡增加难度
        self.tile_size = 100
        self.puzzle_size = self.grid_size * self.tile_size
        
        # 计算居中位置
        self.start_x = (WIDTH - self.puzzle_size) // 2
        self.start_y = (HEIGHT - self.puzzle_size) // 2 - 30
        
        # 生成拼图
        self.tiles: list[PuzzleTile] = []
        self.selected_tile: PuzzleTile | None = None
        self.completed = False
        self.moves = 0
        self.timer = 0.0
        
        self._generate_puzzle()
        
        # UI 字体
        self.title_font = fonts.get_font(24)
        self.info_font = fonts.get_font(16)
        self.tip_font = fonts.get_font(14)
    
    def _generate_puzzle(self):
        """生成拼图"""
        # 创建一个表面作为拼图图片
        puzzle_surface = pg.Surface((self.puzzle_size, self.puzzle_size))
        
        # 生成渐变背景作为拼图图案
        for y in range(self.puzzle_size):
            for x in range(self.puzzle_size):
                # 创建彩色渐变图案
                r = int(100 + 100 * (x / self.puzzle_size) + 55 * (y / self.puzzle_size))
                g = int(150 + 50 * (x / self.puzzle_size) - 50 * (y / self.puzzle_size))
                b = int(200 - 100 * (x / self.puzzle_size) + 50 * (y / self.puzzle_size))
                puzzle_surface.set_at((x, y), (r, g, b))
        
        # 添加关卡数字
        level_text = self.title_font.render(f"Level {self.level}", True, (255, 255, 255))
        text_rect = level_text.get_rect(center=(self.puzzle_size // 2, self.puzzle_size // 2))
        puzzle_surface.blit(level_text, text_rect)
        
        # 创建方块
        positions = []
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                x = self.start_x + col * self.tile_size
                y = self.start_y + row * self.tile_size
                correct_pos = (x, y)
                
                # 裁剪该方块对应的图片部分
                tile_image = pg.Surface((self.tile_size, self.tile_size))
                tile_image.blit(puzzle_surface, (0, 0), 
                               (col * self.tile_size, row * self.tile_size, 
                                self.tile_size, self.tile_size))
                
                tile = PuzzleTile(x, y, self.tile_size, correct_pos, tile_image)
                self.tiles.append(tile)
                positions.append((row, col))
        
        # 打乱拼图（交换位置）
        random.shuffle(positions)
        for i, tile in enumerate(self.tiles):
            row, col = positions[i]
            tile.x = self.start_x + col * self.tile_size
            tile.y = self.start_y + row * self.tile_size
            tile.in_correct_place = tile.is_in_correct_place()
        
        # 确保不是已完成状态
        if self._check_completed():
            # 交换前两个方块
            if len(self.tiles) >= 2:
                self._swap_tiles(self.tiles[0], self.tiles[1])
    
    def _swap_tiles(self, tile1: PuzzleTile, tile2: PuzzleTile):
        """交换两个方块的位置"""
        tile1.x, tile2.x = tile2.x, tile1.x
        tile1.y, tile2.y = tile2.y, tile1.y
        tile1.in_correct_place = tile1.is_in_correct_place()
        tile2.in_correct_place = tile2.is_in_correct_place()
        self.moves += 1
    
    def handle_event(self, event: pg.Event) -> bool:
        """处理事件，返回是否完成"""
        if self.completed:
            return True
        
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            # 检查是否点击了方块
            for tile in self.tiles:
                if tile.contains_point(mx, my):
                    if self.selected_tile is None:
                        # 选择第一个方块
                        self.selected_tile = tile
                        tile.selected = True
                    else:
                        # 选择第二个方块，交换
                        if self.selected_tile != tile:
                            self._swap_tiles(self.selected_tile, tile)
                            self.selected_tile.selected = False
                            self.selected_tile = None
                            
                            # 检查是否完成
                            if self._check_completed():
                                self.completed = True
                        else:
                            # 点击同一个，取消选择
                            tile.selected = False
                            self.selected_tile = None
                    break
        
        return self.completed
    
    def _check_completed(self) -> bool:
        """检查拼图是否完成"""
        for tile in self.tiles:
            if not tile.is_in_correct_place():
                return False
        return True
    
    def update(self, dt: float):
        """更新游戏状态"""
        if not self.completed:
            self.timer += dt
    
    def draw(self, surface: pg.Surface):
        """绘制拼图游戏"""
        # 绘制半透明背景
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # 绘制标题
        title = self.title_font.render(f"拼图挑战 - 第 {self.level} 关", True, (255, 255, 255))
        title_rect = title.get_rect(centerx=WIDTH // 2, top=20)
        surface.blit(title, title_rect)
        
        # 绘制拼图区域背景
        puzzle_bg = pg.Surface((self.puzzle_size + 10, self.puzzle_size + 10), pg.SRCALPHA)
        puzzle_bg.fill((50, 50, 50, 200))
        surface.blit(puzzle_bg, (self.start_x - 5, self.start_y - 5))
        
        # 绘制所有方块
        for tile in self.tiles:
            tile.draw(surface)
        
        # 绘制信息
        moves_text = self.info_font.render(f"移动次数：{self.moves}", True, (255, 255, 255))
        surface.blit(moves_text, (self.start_x, self.start_y + self.puzzle_size + 10))
        
        timer_text = self.info_font.render(f"时间：{self.timer:.1f}s", True, (255, 255, 255))
        surface.blit(timer_text, (self.start_x + 150, self.start_y + self.puzzle_size + 10))
        
        # 绘制提示
        if self.selected_tile is None:
            tip = self.tip_font.render("点击方块选择，再点击另一个方块交换", True, (200, 200, 200))
        else:
            tip = self.tip_font.render("点击另一个方块进行交换", True, (200, 200, 200))
        tip_rect = tip.get_rect(centerx=WIDTH // 2, top=self.start_y + self.puzzle_size + 40)
        surface.blit(tip, tip_rect)
        
        # 完成提示
        if self.completed:
            complete_text = self.title_font.render("拼图完成！按任意键继续...", True, (0, 255, 0))
            complete_rect = complete_text.get_rect(centerx=WIDTH // 2, top=self.start_y + self.puzzle_size + 70)
            surface.blit(complete_text, complete_rect)
    
    def get_score(self) -> int:
        """计算得分（基于移动次数和时间）"""
        if not self.completed:
            return 0
        # 基础分 - 移动惩罚 - 时间惩罚
        base_score = 1000
        move_penalty = self.moves * 10
        time_penalty = int(self.timer * 5)
        return max(0, base_score - move_penalty - time_penalty)
