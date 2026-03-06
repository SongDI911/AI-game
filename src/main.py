import os
import sys
import json
import random
import pygame as pg

from src.game.config import WIDTH, HEIGHT, FPS, BG_COLOR
from src.game.rooms import RoomManager
from src.game.ui import HUD, RewardUI
from src.game.entities import Player
from src.game.effects import Effects
from src.game import fonts
from src.game import sound
from src.game import assets
from src.game.menu import MainMenu, PauseMenu, ShopUI, TutorialOverlay
from src.game.level_manager import LevelManager


# 存档文件路径
SAVE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "save_data.json")


def ensure_pygame():
    try:
        import pygame  # noqa: F401
    except Exception as e:
        print("Pygame is required. Install with: pip install pygame")
        print(f"Error: {e}")
        sys.exit(1)


def maybe_headless():
    # Enable headless dummy video driver when HEADLESS is set
    if os.environ.get("HEADLESS"):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


class Game:
    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        # 初始化音频（在无声卡/无窗口环境会自动降级）
        try:
            sound.init()
        except Exception:
            pass
        # 预加载贴图资源，减少首次房间切换卡顿
        try:
            assets.preload()
        except Exception:
            pass
        pg.display.set_caption("残响编年史 - 原型 Prototype")
        self.clock = pg.time.Clock()
        self.font = fonts.get_font(16)

        # 游戏状态：main_menu | tutorial | playing | paused | reward | shop | minigame | gameover | quit
        self.state = "main_menu"
        
        # 主菜单
        self.main_menu = MainMenu()
        
        # 教程系统
        self.tutorial = TutorialOverlay()
        
        # 存档数据
        self.save_data = self._load_save()
        
        # 游戏对象（在开始游戏时创建）
        self.player = None
        self.effects = None
        self.room_mgr = None
        self.hud = None
        self.reward_ui = None
        self.shop_ui = None
        
        # 关卡管理器
        self.level_mgr = None
        
        self.accumulator = 0.0
        self.time_scale = 1.0
        self.frames = 0
        self.max_frames = int(os.environ.get("MAX_FRAMES", "0"))
        self.capture_path = os.environ.get("CAPTURE_PATH")
        self.capture_frame = int(os.environ.get("CAPTURE_FRAME", "0"))
        self.pending_next_room = False

    def _load_save(self) -> dict:
        """加载存档数据"""
        default_save = {
            "max_room": 0,
            "total_kills": 0,
            "times_played": 0,
        }
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                    return {**default_save, **data}
        except Exception:
            pass
        return default_save

    def _save_game(self):
        """保存游戏数据"""
        try:
            os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
            with open(SAVE_FILE, "w") as f:
                json.dump(self.save_data, f, indent=2)
        except Exception:
            pass

    def run(self):
        while self.state != "quit":
            dt_raw = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            
            # 更新逻辑
            if self.state == "main_menu":
                self.main_menu.update(dt_raw)
                self._draw_main_menu()
                pg.display.flip()
            elif self.state == "tutorial":
                self.tutorial.draw(self.screen)
                pg.display.flip()
            elif self.state == "playing":
                # 先以真实时间更新特效
                self.effects.update(dt_raw)
                # 应用时间缩放：玩家子弹时间与命中停顿
                dt_scaled = dt_raw * self.player.time_scale * self.effects.time_scale()
                self.update(dt_scaled)
                self.draw()
            elif self.state == "paused":
                self._draw_paused()
                pg.display.flip()
            elif self.state == "reward":
                # 奖励选择时只绘制静态背景，不更新游戏逻辑
                self._draw_static_background()
                self.reward_ui.draw(self.screen)
                pg.display.flip()
            elif self.state == "chapter_transition":
                # 关卡过渡界面
                self._update_and_draw_transition(dt_raw)
                pg.display.flip()
            elif self.state == "shop":
                self.draw()  # 背景保持
                self.shop_ui.update(dt_raw)
                self.shop_ui.draw(self.screen)
                pg.display.flip()
            elif self.state == "minigame":
                # 小游戏状态
                self._update_and_draw_minigame(dt_raw)
                pg.display.flip()
            elif self.state == "gameover":
                self.draw()
                self._draw_gameover()
                pg.display.flip()

            self.frames += 1
            # optional capture for headless verification
            if self.capture_path and self.capture_frame and self.frames == self.capture_frame:
                try:
                    pg.image.save(self.screen, self.capture_path)
                except Exception:
                    pass
            if self.max_frames and self.frames >= self.max_frames:
                self.state = "quit"

        pg.quit()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.state = "quit"
                return
            
            # 主菜单输入
            if self.state == "main_menu":
                action = self.main_menu.handle_input()
                if action == "start":
                    # 检查是否需要显示教程
                    if not self.save_data.get("tutorial_completed", False):
                        self.tutorial.start()
                        self.state = "tutorial"
                    else:
                        self._start_new_game()
                elif action == "quit":
                    self.state = "quit"
                continue
            
            # 教程输入
            if self.state == "tutorial":
                if event.type == pg.KEYDOWN:
                    if self.tutorial.handle_input():
                        # 教程完成
                        self.save_data["tutorial_completed"] = True
                        self._save_game()
                        self._start_new_game()
                continue
            
            # 暂停菜单输入
            if self.state == "paused":
                action = self.pause_menu.handle_input()
                if action == "resume":
                    self.state = "playing"
                elif action == "main_menu":
                    self.state = "main_menu"
                elif action == "quit":
                    self.state = "quit"
                continue
            
            # 商店输入
            if self.state == "shop":
                action = self.shop_ui.handle_input()
                if action == "buy":
                    self.shop_ui.buy_item()
                elif action == "close":
                    self.state = "playing"
                continue
            
            # 关卡过渡输入
            if self.state == "chapter_transition":
                # 过渡界面自动进行，无需输入
                continue
            
            # 奖励选择
            if self.state == "reward":
                choice = self.reward_ui.handle_event(event)
                if choice is not None:
                    self.reward_ui.apply_choice(choice)
                    # 推迟到下一帧创建房间，避免事件处理阶段卡顿
                    self.pending_next_room = True
                    self.state = "playing"
                continue

            # 小游戏输入
            if self.state == "minigame":
                if event.type == pg.KEYDOWN and self.level_mgr.minigame_completed:
                    # 小游戏完成后按任意键继续
                    self.level_mgr.complete_minigame()
                    self._start_chapter()
                elif event.type == pg.MOUSEBUTTONDOWN:
                    # 处理小游戏鼠标事件
                    self.level_mgr.handle_minigame_event(event)
                continue

            # gameover input
            if self.state == "gameover" and event.type == pg.KEYDOWN:
                if event.key in (pg.K_r, pg.K_RETURN, pg.K_SPACE):
                    self._restart_run()
                    self.state = "playing"
                elif event.key == pg.K_ESCAPE:
                    self.state = "main_menu"
                continue
            
            # 游戏内输入（仅 playing 状态）
            if self.state == "playing":
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        self._toggle_pause()
                    elif event.key == pg.K_p:
                        self._toggle_pause()
                    elif event.key == pg.K_b:
                        self._open_shop()
                    elif event.key == pg.K_h:
                        # 按 H 显示帮助提示
                        pass
                self.player.handle_input()

    def _start_new_game(self):
        """开始新游戏"""
        self.player = Player(pos=(WIDTH // 2, HEIGHT // 2))
        self.effects = Effects()
        self.level_mgr = LevelManager()
        self.room_mgr = RoomManager(self.player, self.effects)
        self.hud = HUD(self.player, self.room_mgr, self.level_mgr)
        self.reward_ui = RewardUI(self.player, self.room_mgr)
        self.shop_ui = ShopUI(self.player, self.room_mgr)
        self.pause_menu = PauseMenu()
        self.state = "playing"
        self.save_data["times_played"] = self.save_data.get("times_played", 0) + 1

    def _toggle_pause(self):
        """切换暂停状态"""
        if self.state == "playing":
            self.pause_menu = PauseMenu()
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def _open_shop(self):
        """打开商店"""
        if self.state == "playing":
            self.shop_ui = ShopUI(self.player, self.room_mgr)
            self.state = "shop"

    def update(self, dt: float):
        # 更新房间与实体
        if self.pending_next_room:
            self.room_mgr.next_room()
            self.pending_next_room = False
        self.room_mgr.update(dt)
        self.player.update(dt, self.room_mgr)

        # 清空房间 -> 进入奖励选择
        if self.room_mgr.room_cleared and not self.reward_ui.active:
            # 更新关卡进度
            if self.level_mgr:
                self.level_mgr.on_room_cleared()
                # 检查是否需要进入小游戏
                if self.level_mgr.is_chapter_complete():
                    # 关卡完成，进入过渡界面
                    self.level_mgr.start_transition()
                    self.state = "chapter_transition"
                else:
                    # 普通房间，进入奖励选择
                    self.reward_ui.activate()
                    self.state = "reward"

        # 更新存档：最高房间数
        if self.room_mgr.room_index > self.save_data.get("max_room", 0):
            self.save_data["max_room"] = self.room_mgr.room_index
            self._save_game()

        # 玩家死亡
        if self.player.hp <= 0:
            self.state = "gameover"
            # 更新存档：总击杀数
            total_kills = self.save_data.get("total_kills", 0)
            self.save_data["total_kills"] = total_kills + getattr(self.room_mgr, '_kills_this_run', 0)
            self._save_game()

    def draw(self):
        # 绘制到离屏表面以添加屏幕震动
        world = pg.Surface((WIDTH, HEIGHT))
        world.fill(BG_COLOR)
        self.room_mgr.draw(world)
        self.player.draw(world)
        # 应用屏幕震动偏移
        ox, oy = self.effects.shake.offset()
        self.screen.fill(BG_COLOR)
        self.screen.blit(world, (ox, oy))
        # 覆盖层与 HUD
        self.effects.draw_overlay(self.screen)
        self.hud.draw(self.screen)
        pg.display.flip()

    def _draw_main_menu(self):
        """绘制主菜单"""
        self.screen.fill(BG_COLOR)
        self.main_menu.draw(self.screen)
        
        # 显示存档信息
        max_room = self.save_data.get("max_room", 0)
        total_kills = self.save_data.get("total_kills", 0)
        times_played = self.save_data.get("times_played", 0)
        
        info_font = fonts.get_font(12)
        info_text = f"最高房间：{max_room} | 总击杀：{total_kills} | 游戏次数：{times_played}"
        info_surface = info_font.render(info_text, True, (100, 100, 100))
        info_x = WIDTH // 2 - info_surface.get_width() // 2
        self.screen.blit(info_surface, (info_x, HEIGHT - 30))
        
        pg.display.flip()

    def _draw_paused(self):
        """绘制暂停菜单"""
        # 先绘制游戏画面作为背景
        self.draw()
        # 覆盖暂停菜单
        self.pause_menu.draw(self.screen)
        pg.display.flip()

    def _draw_gameover(self):
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        big = fonts.get_font(40)
        t1 = big.render("你被击败了", True, (255, 200, 200))
        t2 = self.font.render("按 R 或 回车重开", True, (230, 230, 230))
        t3 = self.font.render("按 ESC 返回主菜单", True, (180, 180, 180))
        
        # 显示本次游戏数据
        room_reached = self.room_mgr.room_index if self.room_mgr else 0
        t4 = self.font.render(f"到达房间：{room_reached}", True, (200, 200, 200))
        
        self.screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, HEIGHT // 2 - 60))
        self.screen.blit(t4, (WIDTH // 2 - t4.get_width() // 2, HEIGHT // 2 - 20))
        self.screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, HEIGHT // 2 + 20))
        self.screen.blit(t3, (WIDTH // 2 - t3.get_width() // 2, HEIGHT // 2 + 55))

    def _restart_run(self):
        self.player = Player(pos=(WIDTH // 2, HEIGHT // 2))
        self.effects = Effects()
        self.level_mgr = LevelManager()
        self.room_mgr = RoomManager(self.player, self.effects)
        self.hud = HUD(self.player, self.room_mgr, self.level_mgr)
        self.reward_ui = RewardUI(self.player, self.room_mgr)
        self.shop_ui = ShopUI(self.player, self.room_mgr)

    def _draw_static_background(self):
        """绘制静态背景（用于奖励选择等界面）"""
        # 绘制到离屏表面
        world = pg.Surface((WIDTH, HEIGHT))
        world.fill(BG_COLOR)
        self.room_mgr.draw(world)
        self.player.draw(world)
        # 应用屏幕震动偏移（但不更新震动）
        ox, oy = self.effects.shake.offset()
        self.screen.fill(BG_COLOR)
        self.screen.blit(world, (ox, oy))
        # 覆盖层（但不绘制新的效果）
        self.effects.draw_overlay(self.screen)
        # 不绘制 HUD，让奖励 UI 覆盖在上面

    def _prepare_minigame(self):
        """准备进入小游戏"""
        # 标记关卡已完成，等待奖励选择后进入小游戏
        pass

    def _start_chapter(self):
        """开始新章节"""
        if self.level_mgr:
            self.level_mgr.start_next_chapter()
        self.room_mgr.next_room()
        self.room_mgr.room_cleared = False
        self.reward_ui.active = False

    def _update_and_draw_transition(self, dt: float):
        """更新并绘制关卡过渡界面"""
        if self.level_mgr:
            if self.level_mgr.transition:
                done = self.level_mgr.update_transition(dt)
                self.level_mgr.draw_transition(self.screen)
                if done:
                    # 过渡完成，进入小游戏
                    self.state = "minigame"
            else:
                # 没有过渡界面，直接进入小游戏
                self.state = "minigame"

    def _update_and_draw_minigame(self, dt: float):
        """更新并绘制小游戏"""
        if self.level_mgr and self.level_mgr.minigame:
            self.level_mgr.update_minigame(dt)
            self.level_mgr.minigame.draw(self.screen)


if __name__ == "__main__":
    maybe_headless()
    ensure_pygame()
    Game().run()
