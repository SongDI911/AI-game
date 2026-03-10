"""拼图小游戏模块 - 使用实际图片切割"""
from __future__ import annotations

import random
import pygame as pg
import os

from ..config import WIDTH, HEIGHT
from .. import fonts
from .. import assets as game_assets


class PuzzleTile:
    """拼图方块"""
    
    def __init__(self, x: int, y: int, size: int, correct_pos: tuple, image=None, number: int = 0, source_row: int = 0, source_col: int = 0, start_x: int = 0, start_y: int = 0):
        self.x = x  # 当前显示位置
        self.y = y
        self.size = size
        self.correct_pos = correct_pos  # 正确位置 (cx, cy) - 基于 source 行列计算
        self.image = image  # 该方块对应的图片部分
        self.number = number  # 方块编号（用于显示）
        self.selected = False
        self.in_correct_place = False
        # 记录该方块在原始图片中的行列（用于重新切割图片）
        self.source_row = source_row
        self.source_col = source_col
        # 记录起始位置（用于计算目标位置）
        self.start_x = start_x
        self.start_y = start_y
    
    def is_in_correct_place(self) -> bool:
        """检查是否在正确位置 - 基于 correct_pos 判断"""
        return (abs(self.x - self.correct_pos[0]) < 2 and
                abs(self.y - self.correct_pos[1]) < 2)
    
    def update_image(self, puzzle_image: pg.Surface, tile_size: int, grid_size: int):
        """根据当前位置重新计算并更新图片部分"""
        # 计算该位置应该显示的图片部分（基于目标位置的行列）
        target_row = (self.y - (480 - grid_size * tile_size) // 2) // tile_size
        target_col = (self.x - (640 - grid_size * tile_size) // 2) // tile_size
        
        if 0 <= target_row < grid_size and 0 <= target_col < grid_size:
            # 从 puzzle_image 切割对应部分
            self.image = pg.Surface((tile_size, tile_size))
            self.image.blit(puzzle_image, (0, 0),
                           (target_col * tile_size, target_row * tile_size,
                            tile_size, tile_size))
    
    def contains_point(self, px: int, py: int) -> bool:
        """检查点是否在方块内"""
        return (self.x <= px <= self.x + self.size and
                self.y <= py <= self.y + self.size)
    
    def draw(self, surface: pg.Surface, show_numbers: bool = True):
        """绘制方块"""
        rect = pg.Rect(self.x, self.y, self.size, self.size)
        
        if self.image:
            # 绘制图片部分
            surface.blit(self.image, (self.x, self.y))
        else:
            # 无图片时绘制灰色背景
            pg.draw.rect(surface, (100, 100, 100), rect)
        
        # 绘制编号
        if show_numbers:
            font = pg.font.Font(None, max(16, self.size // 3))
            number_text = font.render(str(self.number), True, (255, 255, 255))
            # 绘制文字描边
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        surface.blit(number_text, (self.x + 4 + dx, self.y + 4 + dy))
            surface.blit(number_text, (self.x + 4, self.y + 4))
        
        # 绘制边框
        if self.selected:
            pg.draw.rect(surface, (255, 255, 0), rect, 3)
        elif self.in_correct_place:
            pg.draw.rect(surface, (0, 255, 0), rect, 2)
        else:
            pg.draw.rect(surface, (255, 255, 255), rect, 1)


class PuzzleGame:
    """拼图小游戏 - 使用实际图片切割"""
    
    # 拼图图片路径
    PUZZLE_IMAGES = [
        "assets/puzzle/1.png",
    ]
    
    def __init__(self, level: int = 1, puzzle_image_path: str = None):
        self.level = level
        self.grid_size = min(3 + (level - 1) // 2, 5)  # 3x3 到 5x5，随关卡增加难度
        self.tile_size = 100
        self.puzzle_size = self.grid_size * self.tile_size
        
        # 计算居中位置
        self.start_x = (WIDTH - self.puzzle_size) // 2
        self.start_y = (HEIGHT - self.puzzle_size) // 2 - 30
        
        # 加载拼图图片
        self.puzzle_image = None
        if puzzle_image_path:
            self.puzzle_image = self._load_puzzle_image(puzzle_image_path)
        else:
            # 使用默认图片
            default_path = self.PUZZLE_IMAGES[(level - 1) % len(self.PUZZLE_IMAGES)]
            self.puzzle_image = self._load_puzzle_image(default_path)
        
        # 生成拼图
        self.tiles: list[PuzzleTile] = []
        self.selected_tile: PuzzleTile | None = None
        self.completed = False
        self.moves = 0
        self.timer = 0.0
        self.show_numbers = True  # 是否显示编号
        
        self._generate_puzzle()
        
        # UI 字体
        self.title_font = fonts.get_font(24)
        self.info_font = fonts.get_font(16)
        self.tip_font = fonts.get_font(14)
    
    def _load_puzzle_image(self, path: str) -> pg.Surface:
        """加载拼图图片"""
        try:
            if os.path.exists(path):
                img = pg.image.load(path).convert()
                # 缩放到拼图大小
                img = pg.transform.smoothscale(img, (self.puzzle_size, self.puzzle_size))
                return img
        except Exception as e:
            print(f"Failed to load puzzle image: {e}")
        
        # 加载失败时创建渐变背景
        surface = pg.Surface((self.puzzle_size, self.puzzle_size))
        for y in range(self.puzzle_size):
            for x in range(self.puzzle_size):
                r = int(100 + 100 * (x / self.puzzle_size) + 55 * (y / self.puzzle_size))
                g = int(150 + 50 * (x / self.puzzle_size) - 50 * (y / self.puzzle_size))
                b = int(200 - 100 * (x / self.puzzle_size) + 50 * (y / self.puzzle_size))
                surface.set_at((x, y), (r, g, b))
        return surface
    
    def _generate_puzzle(self):
        """生成拼图 - 使用图片切割"""
        # 创建方块 - 每个方块记住自己在原始图片中的位置
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                x = self.start_x + col * self.tile_size
                y = self.start_y + row * self.tile_size
                
                # 切割该方块对应的图片部分（基于原始行列）
                tile_image = None
                if self.puzzle_image:
                    tile_image = pg.Surface((self.tile_size, self.tile_size))
                    tile_image.blit(self.puzzle_image, (0, 0),
                                   (col * self.tile_size, row * self.tile_size,
                                    self.tile_size, self.tile_size))
                
                # 编号（从 1 开始）
                number = row * self.grid_size + col + 1
                
                # correct_pos 基于 source 行列计算（方块应该去的最终位置）
                correct_pos = (self.start_x + col * self.tile_size, self.start_y + row * self.tile_size)
                
                tile = PuzzleTile(x, y, self.tile_size, correct_pos, tile_image, number, row, col, self.start_x, self.start_y)
                self.tiles.append(tile)
        
        # 打乱拼图：随机交换方块的位置（图片跟着方块走）
        # 确保进行足够多次的交换
        num_swaps = self.grid_size * self.grid_size * 3
        for _ in range(num_swaps):
            tile1 = random.choice(self.tiles)
            tile2 = random.choice(self.tiles)
            if tile1 != tile2:
                self._swap_tiles(tile1, tile2)
        
        # 确保不是已完成状态
        if self._check_completed():
            if len(self.tiles) >= 2:
                self._swap_tiles(self.tiles[0], self.tiles[1])
    
    def _swap_tiles(self, tile1: PuzzleTile, tile2: PuzzleTile):
        """交换两个方块的位置"""
        # 交换位置（x, y）
        tile1.x, tile2.x = tile2.x, tile1.x
        tile1.y, tile2.y = tile2.y, tile1.y
        # 注意：不交换 image 和 source_row/col
        # 因为 image 和 source 是方块的"身份"，跟着方块对象走
        # 更新位置状态
        tile1.in_correct_place = tile1.is_in_correct_place()
        tile2.in_correct_place = tile2.is_in_correct_place()
        self.moves += 1
    
    def handle_event(self, event: pg.Event) -> bool:
        """处理事件，返回是否完成"""
        # 如果已经完成，按回车或空格返回 True
        if self.completed:
            if event.type == pg.KEYDOWN and event.key in (pg.K_RETURN, pg.K_SPACE):
                return True
            return True  # 已完成状态一直返回 True
        
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_n:
                # 按 N 切换编号显示
                self.show_numbers = not self.show_numbers
            elif event.key in (pg.K_RETURN, pg.K_SPACE):
                # 按回车或空格继续（但未完成时不响应）
                pass
            return False
        
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
                                return True
                        else:
                            # 点击同一个，取消选择
                            tile.selected = False
                            self.selected_tile = None
                    break
        
        return False
    
    def _check_completed(self) -> bool:
        """检查拼图是否完成 - 检查每个方块是否在它的归属位置"""
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
            tile.draw(surface, show_numbers=self.show_numbers)
        
        # 绘制信息
        moves_text = self.info_font.render(f"移动次数：{self.moves}", True, (255, 255, 255))
        surface.blit(moves_text, (self.start_x, self.start_y + self.puzzle_size + 10))
        
        timer_text = self.info_font.render(f"时间：{self.timer:.1f}s", True, (255, 255, 255))
        surface.blit(timer_text, (self.start_x + 150, self.start_y + self.puzzle_size + 10))
        
        # 绘制提示
        if self.selected_tile is None:
            tip = self.tip_font.render("点击方块选择，再点击另一个方块交换 [N 切换编号]", True, (200, 200, 200))
        else:
            tip = self.tip_font.render("点击另一个方块进行交换 [N 切换编号]", True, (200, 200, 200))
        tip_rect = tip.get_rect(centerx=WIDTH // 2, top=self.start_y + self.puzzle_size + 40)
        surface.blit(tip, tip_rect)
        
        # 完成提示
        if self.completed:
            complete_text = self.title_font.render("拼图完成！按回车或空格继续...", True, (0, 255, 0))
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
