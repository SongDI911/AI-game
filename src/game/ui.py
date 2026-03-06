from __future__ import annotations

import random
from typing import List, Optional

import pygame as pg

from .config import WIDTH, HEIGHT, PLAYER_MAX_HP, PLAYER_MAX_ENERGY
from . import fonts


def draw_bar(surf: pg.Surface, x, y, w, h, frac, fg, bg):
    pg.draw.rect(surf, bg, (x, y, w, h), border_radius=3)
    pg.draw.rect(surf, fg, (x, y, int(w * max(0.0, min(1.0, frac))), h), border_radius=3)


class MiniMap:
    """小地图/迷你地图系统"""
    
    def __init__(self, room_mgr):
        self.room_mgr = room_mgr
        self.map_size = 140
        self.scale = self.map_size / WIDTH
        self.margin = 10
    
    def draw(self, surf: pg.Surface):
        # 小地图位置：右上角
        map_x = WIDTH - self.map_size - self.margin
        map_y = self.margin + 60  # 在房间信息下方
        
        # 背景
        bg_rect = pg.Rect(map_x - 4, map_y - 4, self.map_size + 8, self.map_size + 8)
        pg.draw.rect(surf, (30, 30, 40), bg_rect, border_radius=6)
        pg.draw.rect(surf, (80, 80, 100), bg_rect, 2, border_radius=6)
        
        # 房间边界
        room_rect = pg.Rect(map_x, map_y, self.map_size, self.map_size)
        pg.draw.rect(surf, (60, 60, 70), room_rect, 1, border_radius=4)
        
        # 绘制敌人位置（红色点）
        for enemy in self.room_mgr.enemies:
            ex = map_x + enemy.pos.x * self.scale
            ey = map_y + enemy.pos.y * self.scale
            pg.draw.circle(surf, (255, 80, 80), (int(ex), int(ey)), 4)
        
        # 绘制 Boss 位置（大红色点）
        if hasattr(self.room_mgr.room, 'is_boss_room') and self.room_mgr.room.is_boss_room:
            for enemy in self.room_mgr.enemies:
                if hasattr(enemy, 'phase'):  # BossEnemy has phase attribute
                    bx = map_x + enemy.pos.x * self.scale
                    by = map_y + enemy.pos.y * self.scale
                    pg.draw.circle(surf, (255, 30, 30), (int(bx), int(by)), 7)
                    # Boss 标记
                    pg.draw.circle(surf, (255, 200, 200), (int(bx), int(by)), 9, 2)
        
        # 绘制玩家位置（蓝色点）
        player = self.room_mgr.player
        px = map_x + player.pos.x * self.scale
        py = map_y + player.pos.y * self.scale
        pg.draw.circle(surf, (80, 180, 255), (int(px), int(py)), 5)
        
        # 小地图标题
        title = fonts.get_font(12).render("小地图", True, (180, 180, 200))
        surf.blit(title, (map_x + self.map_size // 2 - title.get_width() // 2, map_y - 18))


class HUD:
    def __init__(self, player, room_mgr, level_mgr=None):
        self.player = player
        self.room_mgr = room_mgr
        self.level_mgr = level_mgr
        self.font = fonts.get_font(16)
        self.minimap = MiniMap(room_mgr)

    def draw(self, surf: pg.Surface):
        # HP
        draw_bar(surf, 16, 16, 240, 12, self.player.hp / self.player.hp_max, (230, 90, 90), (50, 30, 30))
        hp_txt = self.font.render(f"HP {self.player.hp}/{self.player.hp_max}", True, (240, 240, 240))
        surf.blit(hp_txt, (16, 32))
        # Energy
        draw_bar(surf, 16, 56, 240, 12, self.player.energy / PLAYER_MAX_ENERGY, (80, 200, 255), (20, 40, 60))
        en_txt = self.font.render(f"残响能量 {int(self.player.energy)}/{PLAYER_MAX_ENERGY}", True, (200, 230, 255))
        surf.blit(en_txt, (16, 72))
        # Chapter/Level info
        if self.level_mgr:
            chapter = self.level_mgr.get_current_chapter()
            rooms_in_chapter = self.level_mgr.get_rooms_in_chapter()
            total_rooms = self.level_mgr.get_total_rooms()
            chapter_txt = self.font.render(f"第{chapter}关", True, (255, 215, 0))
            surf.blit(chapter_txt, (WIDTH - 220, 16))
            progress_txt = self.font.render(f"房间 {rooms_in_chapter + 1}/5", True, (200, 200, 200))
            surf.blit(progress_txt, (WIDTH - 220, 36))
        else:
            # Room info
            room_txt = self.font.render(f"Room {self.room_mgr.room_index}", True, (200, 200, 200))
            surf.blit(room_txt, (WIDTH - 120, 16))
        # Fragments
        frag_txt = self.font.render(f"时之碎片：{self.player.fragments}", True, (230, 210, 130))
        surf.blit(frag_txt, (WIDTH - 200, 36))
        # Skills
        qname = getattr(self.player.skill_q, "name", "Q")
        qvar = getattr(self.player.skill_q, "variant", None)
        enq = getattr(self.player.skill_q, "cost", 0)
        enq_txt = self.font.render(f"Q: {qname}{'·'+qvar if qvar else ''} ({enq})", True, (200, 220, 240))
        surf.blit(enq_txt, (16, 150))
        ename = getattr(self.player.skill_e, "name", "E")
        evar = getattr(self.player.skill_e, "variant", None)
        ene = getattr(self.player.skill_e, "cost", 0)
        ene_txt = self.font.render(f"E: {ename}{'·'+evar if evar else ''} ({ene})", True, (200, 220, 240))
        surf.blit(ene_txt, (16, 172))
        # Relics list
        surf.blit(self.font.render("遗物：", True, (220, 220, 220)), (16, 102))
        for i, name in enumerate(self.player.relics[:6]):
            surf.blit(self.font.render(f"- {name}", True, (200, 200, 200)), (26, 122 + i * 18))
        
        # 绘制小地图
        self.minimap.draw(surf)


RELIC_POOL = [
    # 基础遗物
    "易燃",  # attacks apply burn DoT
    "蔓延",  # burn spreads to nearby enemies
    "Energy Surge",  # +50% energy gains
    "Guard Convert",  # block grants tiny heal
    "低血暴",  # below 50% hp -> +20% damage
    
    # 新增遗物
    "疾风步",  # 移动速度 +15%
    "吸血之刃",  # 攻击时恢复 2 点生命
    "雷霆打击",  # 每 5 次攻击触发一次闪电链
    "时间扭曲",  # 子弹时间效果增强 20%
    "坚韧护盾",  # 最大生命值 +20
    "能量护盾",  # 能量满时减少 10% 伤害
    "连击大师",  # 连击伤害递增 +10%
    "致命节奏",  # 攻击速度 +15%
    "复仇之心",  # 生命值低于 30% 时伤害 +40%
    "生命偷取",  # 击杀敌人恢复 5 点生命
]

Q_MUTATIONS = ["破甲", "连环", "幽灵", "追影", "裂空"]
E_MUTATIONS = ["宽域", "连锁", "冻伤", "聚能", "爆裂"]


class RewardUI:
    def __init__(self, player, room_mgr):
        self.player = player
        self.room_mgr = room_mgr
        self.font = fonts.get_font(20)
        self.active = False
        self.choices: List[dict] = []
        self._title_surface = None
        self._choice_surfaces: List[pg.Surface] = []

    def activate(self):
        self.active = True
        # Weighted choice: 2 relics + 1 skill mutation
        picks: List[dict] = []
        relics = random.sample(RELIC_POOL, k=2)
        for r in relics:
            picks.append({"type": "relic", "label": r})
        if random.random() < 0.5:
            picks.append({"type": "skillQ", "label": random.choice(Q_MUTATIONS)})
        else:
            picks.append({"type": "skillE", "label": random.choice(E_MUTATIONS)})
        random.shuffle(picks)
        self.choices = picks
        # 预渲染标题与选项文本，避免每帧反复渲染
        self._title_surface = self.font.render("选择一个奖励 (1/2/3)", True, (240, 240, 240))
        self._choice_surfaces = [self.font.render(self._choice_text(c), True, (220, 220, 230)) for c in self.choices]

    def handle_event(self, event) -> Optional[int]:
        if not self.active:
            return None
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_1, pg.K_KP1):
                return 0
            if event.key in (pg.K_2, pg.K_KP2):
                return 1
            if event.key in (pg.K_3, pg.K_KP3):
                return 2
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i in range(3):
                rect = self._choice_rect(i)
                if rect.collidepoint(mx, my):
                    return i
        return None

    def apply_choice(self, idx: int):
        if not self.active:
            return
        choice = self.choices[idx]
        if choice["type"] == "relic":
            self.player.add_relic(choice["label"])
        elif choice["type"] == "skillQ":
            self.player.skill_q.variant = choice["label"]
        elif choice["type"] == "skillE":
            self.player.skill_e.variant = choice["label"]
        self.active = False

    def _choice_rect(self, idx: int) -> pg.Rect:
        W, H = 220, 80
        gap = 24
        x = (WIDTH - (W * 3 + gap * 2)) // 2 + idx * (W + gap)
        y = HEIGHT // 2 - H // 2
        return pg.Rect(x, y, W, H)

    def draw(self, surf: pg.Surface):
        if not self.active:
            return
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))
        title = self._title_surface or self.font.render("选择一个奖励 (1/2/3)", True, (240, 240, 240))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 120))
        for i, name in enumerate(self.choices):
            rect = self._choice_rect(i)
            pg.draw.rect(surf, (60, 60, 80), rect, border_radius=8)
            pg.draw.rect(surf, (150, 150, 200), rect, 2, border_radius=8)
            if i < len(self._choice_surfaces):
                label = self._choice_surfaces[i]
            else:
                label = self.font.render(f"[{i+1}] {self._choice_text(name)}", True, (220, 220, 230))
            # 补充编号前缀
            if label:
                surf.blit(self.font.render(f"[{i+1}] ", True, (220, 220, 230)), (rect.x + 12, rect.y + 24))
                surf.blit(label, (rect.x + 12 + 26, rect.y + 24))

    def _choice_text(self, choice: dict) -> str:
        if choice["type"] == "relic":
            return f"遗物·{choice['label']}"
        if choice["type"] == "skillQ":
            return f"Q 变异·{choice['label']}"
        if choice["type"] == "skillE":
            return f"E 变异·{choice['label']}"
        return str(choice)
