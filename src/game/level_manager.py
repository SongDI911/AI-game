"""关卡管理系统"""
from __future__ import annotations

from .minigames.puzzle import PuzzleGame
from .minigames.transition import ChapterTransitionUI


class LevelManager:
    """
    关卡管理器
    
    游戏进度结构：
    - 每 5 个房间为一个关卡（Chapter）
    - 每个关卡包含：4 个普通房间 + 1 个 Boss 房间
    - 完成一个关卡后，进入小游戏挑战
    - 小游戏成功后，进入下一关卡
    """
    
    def __init__(self):
        self.current_chapter = 1  # 当前章节（关卡）
        self.rooms_in_chapter = 0  # 当前关卡已通过的房间数
        self.rooms_per_chapter = 5  # 每关卡房间数
        self.in_minigame = False  # 是否在小游戏状态
        self.minigame: PuzzleGame | None = None
        self.minigame_completed = False
        self.total_rooms_cleared = 0  # 总共清理的房间数
        
        # 过渡界面
        self.transition: ChapterTransitionUI | None = None
        self.showing_transition = False
    
    def get_current_chapter(self) -> int:
        """获取当前关卡"""
        return self.current_chapter
    
    def get_rooms_in_chapter(self) -> int:
        """获取当前关卡已通过的房间数"""
        return self.rooms_in_chapter
    
    def get_total_rooms(self) -> int:
        """获取总房间进度"""
        return self.total_rooms_cleared
    
    def is_chapter_complete(self) -> bool:
        """检查当前关卡是否完成"""
        return self.rooms_in_chapter >= self.rooms_per_chapter
    
    def on_room_cleared(self):
        """房间清理完成时调用"""
        self.rooms_in_chapter += 1
        self.total_rooms_cleared += 1
    
    def start_next_chapter(self):
        """开始下一关卡"""
        self.current_chapter += 1
        self.rooms_in_chapter = 0
    
    def start_transition(self):
        """开始关卡完成过渡"""
        self.transition = ChapterTransitionUI(self.current_chapter)
        self.showing_transition = True
    
    def update_transition(self, dt: float) -> bool:
        """更新过渡界面，返回是否完成"""
        if not self.transition:
            return True
        done = self.transition.update(dt)
        if done:
            self.showing_transition = False
            self.start_minigame()
        return done
    
    def draw_transition(self, screen):
        """绘制过渡界面"""
        if self.transition and not self.transition.state == "done":
            self.transition.draw(screen)
    
    def start_minigame(self):
        """开始小游戏挑战"""
        self.in_minigame = True
        self.minigame = PuzzleGame(level=self.current_chapter)
        self.minigame_completed = False
    
    def update_minigame(self, dt: float):
        """更新小游戏状态"""
        if self.minigame:
            self.minigame.update(dt)
    
    def handle_minigame_event(self, event) -> bool:
        """处理小游戏事件，返回是否完成"""
        if self.minigame:
            result = self.minigame.handle_event(event)
            if result:
                self.minigame_completed = True
            return result
        return False
    
    def complete_minigame(self):
        """完成小游戏"""
        self.in_minigame = False
        self.minigame = None
        self.start_next_chapter()
    
    def get_minigame_score(self) -> int:
        """获取小游戏得分"""
        if self.minigame:
            return self.minigame.get_score()
        return 0
    
    def reset(self):
        """重置关卡进度"""
        self.current_chapter = 1
        self.rooms_in_chapter = 0
        self.in_minigame = False
        self.minigame = None
        self.minigame_completed = False
        self.total_rooms_cleared = 0
        self.transition = None
        self.showing_transition = False
