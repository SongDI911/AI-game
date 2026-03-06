from __future__ import annotations

import pygame as pg

from .config import WIDTH, HEIGHT
from . import fonts


class TutorialOverlay:
    """游戏教程/引导提示系统"""
    
    def __init__(self):
        self.font = fonts.get_font(16)
        self.title_font = fonts.get_font(20)
        self.small_font = fonts.get_font(14)
        
        # 教程页面
        self.pages = [
            {
                "title": "欢迎来到残响编年史",
                "content": [
                    "这是一款 2D 动作肉鸽游戏，",
                    "你需要击败敌人，清理房间，",
                    "选择遗物和技能变异来变强。",
                    "",
                    "按任意键继续..."
                ]
            },
            {
                "title": "移动与闪避",
                "content": [
                    "WASD 或 方向键 - 移动",
                    "空格键 - 闪避冲刺（消耗 10 能量）",
                    "",
                    "闪避期间拥有短暂无敌时间，",
                    "在敌人攻击瞬间闪避可触发",
                    "完美闪避，获得大量能量和子弹时间。",
                    "",
                    "按任意键继续..."
                ]
            },
            {
                "title": "攻击与连段",
                "content": [
                    "鼠标左键 - 近战攻击",
                    "",
                    "连续点击可进行三段连击，",
                    "每段伤害和范围递增。",
                    "",
                    "攻击命中敌人可恢复能量。",
                    "",
                    "按任意键继续..."
                ]
            },
            {
                "title": "格挡与弹反",
                "content": [
                    "鼠标右键 或 LShift - 格挡",
                    "",
                    "面向敌人攻击方向可格挡，",
                    "减少 70% 伤害并恢复能量。",
                    "",
                    "在攻击命中瞬间格挡可触发弹反，",
                    "获得大量能量和子弹时间。",
                    "",
                    "按任意键继续..."
                ]
            },
            {
                "title": "技能系统",
                "content": [
                    "Q - 冲刺斩（消耗 20 能量）",
                    "    向前突进并造成伤害",
                    "",
                    "E - 冲击波（消耗 25 能量）",
                    "    对周围敌人造成伤害",
                    "",
                    "清理房间后可获得技能变异，",
                    "强化你的技能效果。",
                    "",
                    "按任意键继续..."
                ]
            },
            {
                "title": "遗物系统",
                "content": [
                    "清理房间后可以选择遗物，",
                    "每个遗物提供独特的被动效果。",
                    "",
                    "例如：",
                    "• 易燃：攻击附加燃烧效果",
                    "• Energy Surge: 能量获取 +50%",
                    "• 低血暴：低生命值时伤害增加",
                    "",
                    "按任意键继续..."
                ]
            },
            {
                "title": "商店系统",
                "content": [
                    "按 B 键打开商店",
                    "",
                    "使用时之碎片购买道具：",
                    "• 生命药水 - 恢复生命值",
                    "• 能量水晶 - 恢复能量",
                    "• 攻击强化 - 临时增加伤害",
                    "",
                    "按任意键继续..."
                ]
            },
            {
                "title": "Boss 战",
                "content": [
                    "每 5 个房间会遇到一个 Boss！",
                    "",
                    "Boss 拥有多种攻击模式：",
                    "• 近战攻击",
                    "• 冲锋攻击",
                    "• 旋转攻击",
                    "• 投射物攻击",
                    "",
                    "观察 Boss 的攻击前摇，",
                    "适时闪避或格挡。",
                    "",
                    "按任意键开始游戏..."
                ]
            }
        ]
        
        self.current_page = 0
        self.active = False
        self.completed = False
    
    def start(self):
        """开始教程"""
        self.current_page = 0
        self.active = True
        self.completed = False
    
    def handle_input(self) -> bool:
        """处理输入，返回是否完成教程"""
        if not self.active:
            return False
        
        self.current_page += 1
        if self.current_page >= len(self.pages):
            self.active = False
            self.completed = True
            return True
        return False
    
    def draw(self, surf: pg.Surface):
        if not self.active:
            return
        
        page = self.pages[self.current_page]
        
        # 半透明背景
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surf.blit(overlay, (0, 0))
        
        # 标题
        title = self.title_font.render(page["title"], True, (100, 200, 255))
        title_x = WIDTH // 2 - title.get_width() // 2
        title_y = HEIGHT // 3 - 60
        surf.blit(title, (title_x, title_y))
        
        # 内容
        y = HEIGHT // 3
        for line in page["content"]:
            color = (200, 200, 200)
            if "按任意键" in line:
                color = (150, 180, 200)
            text = self.font.render(line, True, color)
            text_x = WIDTH // 2 - text.get_width() // 2
            surf.blit(text, (text_x, y))
            y += 28
        
        # 进度指示
        progress = f"{self.current_page + 1} / {len(self.pages)}"
        prog_text = self.small_font.render(progress, True, (100, 100, 100))
        surf.blit(prog_text, (WIDTH // 2 - prog_text.get_width() // 2, HEIGHT - 50))


class MainMenu:
    """主菜单界面"""
    
    def __init__(self):
        self.title_font = fonts.get_font(48)
        self.menu_font = fonts.get_font(24)
        self.small_font = fonts.get_font(16)
        
        # 菜单选项
        self.options = [
            {"label": "开始游戏", "action": "start"},
            {"label": "退出游戏", "action": "quit"},
        ]
        self.selected = 0
        self.blink_timer = 0.0
        
        # 预渲染文本
        self._render_texts()
    
    def _render_texts(self):
        """预渲染所有文本"""
        self.title_surface = self.title_font.render("残响编年史", True, (100, 200, 255))
        self.subtitle_surface = self.small_font.render("Chronicles of Echoes", True, (150, 180, 200))
        
        self.option_surfaces = []
        for i, opt in enumerate(self.options):
            color = (255, 255, 255) if i == self.selected else (180, 180, 180)
            prefix = "► " if i == self.selected else "  "
            text = f"{prefix}{opt['label']}"
            self.option_surfaces.append(self.menu_font.render(text, True, color))
    
    def handle_input(self) -> str | None:
        """处理输入，返回选中的动作"""
        keys = pg.key.get_pressed()
        
        # 导航
        if keys[pg.K_UP] or keys[pg.K_w]:
            if not hasattr(self, '_last_nav') or pg.time.get_ticks() - self._last_nav > 150:
                self.selected = (self.selected - 1) % len(self.options)
                self._last_nav = pg.time.get_ticks()
                self._render_texts()
        
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            if not hasattr(self, '_last_nav') or pg.time.get_ticks() - self._last_nav > 150:
                self.selected = (self.selected + 1) % len(self.options)
                self._last_nav = pg.time.get_ticks()
                self._render_texts()
        
        # 确认
        if keys[pg.K_RETURN] or keys[pg.K_SPACE]:
            if not hasattr(self, '_last_confirm') or pg.time.get_ticks() - self._last_confirm > 200:
                self._last_confirm = pg.time.get_ticks()
                return self.options[self.selected]["action"]
        
        return None
    
    def update(self, dt: float):
        """更新动画"""
        self.blink_timer += dt
    
    def draw(self, surf: pg.Surface):
        """绘制主菜单"""
        # 半透明背景
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))
        
        # 标题
        title_x = WIDTH // 2 - self.title_surface.get_width() // 2
        title_y = HEIGHT // 3 - 40
        surf.blit(self.title_surface, (title_x, title_y))
        
        # 副标题
        sub_x = WIDTH // 2 - self.subtitle_surface.get_width() // 2
        surf.blit(self.subtitle_surface, (sub_x, title_y + 45))
        
        # 菜单选项
        start_y = HEIGHT // 2
        for i, surface in enumerate(self.option_surfaces):
            x = WIDTH // 2 - surface.get_width() // 2
            y = start_y + i * 50
            surf.blit(surface, (x, y))
        
        # 操作提示
        hint = self.small_font.render("使用 ↑↓ 或 W/S 选择，回车确认", True, (120, 120, 120))
        hint_x = WIDTH // 2 - hint.get_width() // 2
        surf.blit(hint, (hint_x, HEIGHT - 60))


class PauseMenu:
    """暂停菜单"""
    
    def __init__(self):
        self.title_font = fonts.get_font(36)
        self.menu_font = fonts.get_font(20)
        
        self.options = [
            {"label": "继续游戏", "action": "resume"},
            {"label": "返回主菜单", "action": "main_menu"},
            {"label": "退出游戏", "action": "quit"},
        ]
        self.selected = 0
        self._render_texts()
    
    def _render_texts(self):
        self.title_surface = self.title_font.render("游戏暂停", True, (255, 255, 255))
        self.option_surfaces = []
        for i, opt in enumerate(self.options):
            color = (255, 255, 255) if i == self.selected else (180, 180, 180)
            prefix = "► " if i == self.selected else "  "
            text = f"{prefix}{opt['label']}"
            self.option_surfaces.append(self.menu_font.render(text, True, color))
    
    def handle_input(self) -> str | None:
        keys = pg.key.get_pressed()
        
        if keys[pg.K_UP] or keys[pg.K_w]:
            if not hasattr(self, '_last_nav') or pg.time.get_ticks() - self._last_nav > 150:
                self.selected = (self.selected - 1) % len(self.options)
                self._last_nav = pg.time.get_ticks()
                self._render_texts()
        
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            if not hasattr(self, '_last_nav') or pg.time.get_ticks() - self._last_nav > 150:
                self.selected = (self.selected + 1) % len(self.options)
                self._last_nav = pg.time.get_ticks()
                self._render_texts()
        
        if keys[pg.K_RETURN] or keys[pg.K_SPACE] or keys[pg.K_ESCAPE]:
            if not hasattr(self, '_last_confirm') or pg.time.get_ticks() - self._last_confirm > 200:
                self._last_confirm = pg.time.get_ticks()
                return self.options[self.selected]["action"]
        
        return None
    
    def draw(self, surf: pg.Surface):
        # 半透明背景
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # 标题
        title_x = WIDTH // 2 - self.title_surface.get_width() // 2
        title_y = HEIGHT // 3 - 30
        surf.blit(self.title_surface, (title_x, title_y))
        
        # 菜单选项
        start_y = HEIGHT // 2 - 40
        for i, surface in enumerate(self.option_surfaces):
            x = WIDTH // 2 - surface.get_width() // 2
            y = start_y + i * 45
            surf.blit(surface, (x, y))


class ShopUI:
    """商店界面 - 使用时之碎片购买道具"""
    
    def __init__(self, player, room_mgr):
        self.player = player
        self.room_mgr = room_mgr
        self.title_font = fonts.get_font(36)
        self.menu_font = fonts.get_font(18)
        self.small_font = fonts.get_font(14)
        
        # 商店物品
        self.items = [
            {"name": "生命药水", "cost": 15, "effect": "heal", "value": 30, "desc": "恢复 30 点生命值"},
            {"name": "能量水晶", "cost": 10, "effect": "energy", "value": 40, "desc": "恢复 40 点能量"},
            {"name": "攻击强化", "cost": 25, "effect": "damage_buff", "value": 3, "desc": "本房间伤害 +3"},
            {"name": "护盾发生器", "cost": 20, "effect": "shield", "value": 20, "desc": "获得 20 点临时护盾"},
        ]
        self.selected = 0
        self.message = ""
        self.message_timer = 0.0
        self._render_texts()
    
    def _render_texts(self):
        self.title_surface = self.title_font.render("时之商店", True, (255, 220, 100))
        self.fragments_surface = self.menu_font.render(f"时之碎片：{self.player.fragments}", True, (255, 210, 130))
        
        self.item_surfaces = []
        for i, item in enumerate(self.items):
            can_afford = self.player.fragments >= item["cost"]
            color = (255, 255, 255) if i == self.selected else (150, 150, 150)
            prefix = "► " if i == self.selected else "  "
            cost_color = (100, 255, 100) if can_afford else (255, 100, 100)
            text = f"{prefix}{item['name']} - [{item['cost']}]"
            self.item_surfaces.append({
                "main": self.menu_font.render(text, True, color),
                "desc": self.small_font.render(item["desc"], True, (180, 180, 180)),
                "cost": self.small_font.render(f"消耗：{item['cost']}", True, cost_color),
            })
    
    def handle_input(self) -> str | None:
        keys = pg.key.get_pressed()
        
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            if not hasattr(self, '_last_nav') or pg.time.get_ticks() - self._last_nav > 150:
                self.selected = (self.selected - 1) % len(self.items)
                self._last_nav = pg.time.get_ticks()
                self._render_texts()
        
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            if not hasattr(self, '_last_nav') or pg.time.get_ticks() - self._last_nav > 150:
                self.selected = (self.selected + 1) % len(self.items)
                self._last_nav = pg.time.get_ticks()
                self._render_texts()
        
        if keys[pg.K_RETURN] or keys[pg.K_SPACE]:
            if not hasattr(self, '_last_confirm') or pg.time.get_ticks() - self._last_confirm > 200:
                self._last_confirm = pg.time.get_ticks()
                return "buy"
        
        if keys[pg.K_ESCAPE]:
            if not hasattr(self, '_last_esc') or pg.time.get_ticks() - self._last_esc > 200:
                return "close"
        
        return None
    
    def buy_item(self):
        """购买选中的物品"""
        item = self.items[self.selected]
        if self.player.fragments >= item["cost"]:
            self.player.fragments -= item["cost"]
            
            # 应用效果
            if item["effect"] == "heal":
                self.player.hp = min(100, self.player.hp + item["value"])
            elif item["effect"] == "energy":
                self.player.energy = min(100, self.player.energy + item["value"])
            elif item["effect"] == "damage_buff":
                # 临时伤害加成（可通过遗物或状态实现）
                pass
            elif item["effect"] == "shield":
                # 护盾逻辑
                pass
            
            self.message = f"购买了 {item['name']}!"
            self.message_timer = 2.0
            self._render_texts()
            return True
        else:
            self.message = "碎片不足!"
            self.message_timer = 1.5
            return False
    
    def update(self, dt: float):
        if self.message_timer > 0:
            self.message_timer -= dt
    
    def draw(self, surf: pg.Surface):
        from .config import WIDTH, HEIGHT
        
        # 半透明背景
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # 标题
        title_x = WIDTH // 2 - self.title_surface.get_width() // 2
        surf.blit(self.title_surface, (title_x, 80))
        
        # 碎片数量
        frag_x = WIDTH // 2 - self.fragments_surface.get_width() // 2
        surf.blit(self.fragments_surface, (frag_x, 130))
        
        # 物品列表
        start_y = 180
        item_height = 70
        total_height = len(self.items) * item_height
        start_x = WIDTH // 2 - 200
        
        for i, surfaces in enumerate(self.item_surfaces):
            y = start_y + i * item_height
            
            # 物品框
            rect = pg.Rect(start_x - 10, y - 10, 420, item_height)
            pg.draw.rect(surf, (50, 50, 60), rect, border_radius=8)
            if i == self.selected:
                pg.draw.rect(surf, (255, 220, 100), rect, 2, border_radius=8)
            
            surf.blit(surfaces["main"], (start_x + 10, y + 5))
            surf.blit(surfaces["desc"], (start_x + 10, y + 30))
            surf.blit(surfaces["cost"], (start_x + 300, y + 30))
        
        # 提示信息
        if self.message_timer > 0:
            alpha = int(255 * (self.message_timer / 2.0))
            msg_surface = self.small_font.render(self.message, True, (255, 255, 100))
            msg_surface.set_alpha(alpha)
            msg_x = WIDTH // 2 - msg_surface.get_width() // 2
            surf.blit(msg_surface, (msg_x, HEIGHT - 80))
        
        # 操作提示
        hint = self.small_font.render("使用 ←→ 或 A/D 选择，回车购买，ESC 关闭", True, (120, 120, 120))
        hint_x = WIDTH // 2 - hint.get_width() // 2
        surf.blit(hint, (hint_x, HEIGHT - 50))
