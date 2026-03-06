from __future__ import annotations

import math
import os
import random
from typing import List

import pygame as pg

from .config import WIDTH, HEIGHT, ATTACK_COLOR
from .entities import Enemy, RangerEnemy, Projectile
from .events import DamageEvent
from .effects import Effects
from .combat import Attack

# 加载地图背景
MAP_IMAGE = None
def _load_map_image():
    global MAP_IMAGE
    if MAP_IMAGE is None:
        map_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "map", "background.png")
        try:
            MAP_IMAGE = pg.image.load(map_path).convert()
            # 缩放到屏幕大小
            MAP_IMAGE = pg.transform.smoothscale(MAP_IMAGE, (WIDTH, HEIGHT))
            # 旋转 180 度修正方向（因为图片已手动翻转）
            MAP_IMAGE = pg.transform.rotate(MAP_IMAGE, 180)
        except Exception:
            MAP_IMAGE = None
    return MAP_IMAGE


class GlobalEvents:
    events: List[DamageEvent] = []

    @classmethod
    def add_event(cls, ev: DamageEvent):
        cls.events.append(ev)

    @classmethod
    def consume(cls) -> List[DamageEvent]:
        evs = cls.events
        cls.events = []
        return evs


class Room:
    def __init__(self, index: int, player, effects: Effects):
        self.index = index
        self.player = player
        self.effects = effects
        self.enemies: List[Enemy] = []
        self.room_cleared = False
        self.hitboxes: List[Attack] = []
        self.is_boss_room = False
        self.spawn_enemies()

    def spawn_enemies(self):
        # 每 5 个房间生成 Boss 房间
        self.is_boss_room = (self.index % 5 == 0)
        
        if self.is_boss_room:
            # Boss 房间：生成一个 Boss 敌人
            self._spawn_boss()
        else:
            # 普通房间：生成普通敌人
            n = 3 + (self.index % 3)
            radius = 180
            cx, cy = WIDTH // 2, HEIGHT // 2
            for i in range(n):
                ang = (i / n) * math.tau
                x = cx + math.cos(ang) * radius + random.randint(-60, 60)
                y = cy + math.sin(ang) * radius + random.randint(-60, 60)
                # spawn mix: 30% ranger, 70% melee
                e = RangerEnemy((int(x), int(y))) if random.random() < 0.3 else Enemy((int(x), int(y)))
                # small chance to spawn elite (more hp/poise)
                if random.random() < 0.15:
                    e.elite = True
                    e.hp = int(e.hp * 1.6)
                    e.poise_max = int(e.poise_max * 1.8)
                    e.poise = e.poise_max
                self.enemies.append(e)
    
    def _spawn_boss(self):
        """生成 Boss 敌人"""
        from .entities import BossEnemy
        # Boss 在房间中央生成
        boss = BossEnemy((WIDTH // 2, HEIGHT // 2))
        # 根据房间索引增加 Boss 强度
        boss.hp = int(boss.hp * (1 + self.index * 0.1))
        boss.poise_max = int(boss.poise_max * (1 + self.index * 0.1))
        boss.poise = boss.poise_max
        self.enemies.append(boss)

    def update(self, dt: float, mgr: "RoomManager"):
        prev_count = len(self.enemies)
        # collect dead for FX
        dead_list = []
        new_list: List[Enemy] = []
        for e in self.enemies:
            if e.hp > 0:
                new_list.append(e)
            else:
                dead_list.append(e)
        self.enemies = new_list
        for e in self.enemies:
            e.update(dt, self.player, mgr)

        # 处理伤害事件（玩家技能快照）
        # 玩家持续判定（Attack）
        alive_hit: List[Attack] = []
        for hb in self.hitboxes:
            hb.update(dt, self.player.pos, self.player.facing)
            if hb.is_active():
                for e in self.enemies:
                    if hb.hit_id(e) in hb.already_hit:
                        continue
                    if (e.pos - hb.center()).length() <= (e.radius + hb.radius):
                        final = self.player.on_deal_damage(e, hb.damage)
                        e.hp -= final
                        e.stun = max(e.stun, 0.12 + 0.04 * self.player.combo_step)
                        e.poise -= 12 + 3 * self.player.combo_step
                        if e.poise <= 0:
                            e.stun = max(e.stun, 0.5)
                            e.poise = e.poise_max
                        e.flash = 0.08
                        self.effects.hitstop.trigger(0.04)
                        self.effects.shake.add(2.0, 0.1)
                        self.effects.text.add(str(final), (e.pos.x, e.pos.y))
                        hb.already_hit.add(hb.hit_id(e))
            if not hb.done():
                alive_hit.append(hb)
        self.hitboxes = alive_hit

        # 死亡特效
        if dead_list:
            for de in dead_list:
                try:
                    from .effects import Explosion
                    Explosion.add(self.effects, de.pos, is_elite=de.elite)
                except Exception:
                    pass

        # 快照事件（玩家技能/敌人近战）
        for ev in GlobalEvents.consume():
            if ev.source == "player":
                for e in self.enemies:
                    if (e.pos - ev.pos).length() <= (e.radius + ev.radius):
                        final = self.player.on_deal_damage(e, ev.damage)
                        e.hp -= final
                        e.stun = max(e.stun, 0.12)
                        # feedback
                        e.flash = 0.08
                        self.effects.hitstop.trigger(0.05)
                        self.effects.shake.add(2.0, 0.12)
                        self.effects.text.add(str(final), (e.pos.x, e.pos.y))
                        try:
                            from .effects import Particle, QuickFlash
                            impact_dir = (e.pos - ev.pos)
                            Particle.spray(self.effects, e.pos, impact_dir, count=10, speed=180, spread_deg=50, color=(255,220,150))
                            QuickFlash.add(self.effects, e.pos, radius=14)
                        except Exception:
                            pass
                try:
                    from . import sound
                    sound.get().play('hit', volume=0.4)
                except Exception:
                    pass
            elif ev.source == "enemy":
                # 可视化由绘制层处理
                pass

        # 击杀奖励碎片
        killed = max(0, prev_count - len(self.enemies))
        if killed > 0:
            self.player.fragments += 3 * killed
            self.effects.shake.add(2.5, 0.1)

        if not self.enemies and not self.room_cleared:
            self.room_cleared = True
            self.player.fragments += 10  # clear bonus
            self.effects.shake.add(3.0, 0.15)

    def draw(self, surf: pg.Surface):
        # 绘制地图背景
        map_img = _load_map_image()
        if map_img:
            surf.blit(map_img, (0, 0))
        
        # draw damage effects (flash circles)
        now = pg.time.get_ticks() / 1000.0
        # draw enemies
        for e in self.enemies:
            e.draw(surf)
        # draw active hitboxes overlay
        for hb in self.hitboxes:
            hb.draw(surf)
        # draw recent enemy attack hints (simple flash)
        # Not storing history for simplicity


class RoomManager:
    def __init__(self, player, effects: Effects):
        self.player = player
        self.room_index = 1
        self.effects = effects
        self.room = Room(self.room_index, player, effects)
        self.room_cleared = False
        self._pending_reward = False
        self.projectiles: List[Projectile] = []

    @property
    def enemies(self):
        return self.room.enemies

    @property
    def hitboxes(self):
        # expose current room hitboxes for player attacks
        return self.room.hitboxes

    def update(self, dt: float):
        self.room.update(dt, self)
        # projectiles update and collisions
        player = self.player
        alive: List[Projectile] = []
        for p in self.projectiles:
            # homing logic
            if getattr(p, 'homing', False):
                if p.owner == "player":
                    # home to nearest enemy
                    target = None
                    best = 1e9
                    for e in self.enemies:
                        d2 = (e.pos - p.pos).length_squared()
                        if d2 < best:
                            best = d2
                            target = e
                    if target is not None:
                        dir = (target.pos - p.pos)
                        if dir.length_squared() > 0:
                            dir = dir.normalize()
                            p.vel = dir * p.speed
                else:
                    # enemy projectile -> home to player (optional)
                    dir = (player.pos - p.pos)
                    if dir.length_squared() > 0:
                        dir = dir.normalize()
                        p.vel = dir * p.speed

            p.update(dt)
            if p.life <= 0:
                continue
            # collisions
            if p.owner == "enemy":
                # reflect if blocking and facing projectile
                if (player.pos - p.pos).length() <= (player.radius + p.radius + 2):
                    dir = pg.Vector2(0, 0)
                    if p.vel.length_squared() > 0:
                        dir = p.vel.normalize()
                    # try block reflect
                    if player.blocking:
                        ang = 180.0
                        if player.block_dir.length_squared() > 0 and p.vel.length_squared() > 0:
                            bd = player.block_dir
                            v = p.vel.normalize()
                            # angle between block dir and incoming
                            dot = bd.x * (-v.x) + bd.y * (-v.y)
                            dot = max(-1, min(1, dot))
                            import math
                            ang = math.degrees(math.acos(dot))
                        if ang <= 55:  # within cone
                            # reflect
                            p.vel *= -1
                            p.owner = "player"
                            self.effects.shake.add(2.0, 0.08)
                            self.effects.hitstop.trigger(0.03)
                            continue  # no damage
                    # not reflected -> hit player
                    outcome = player.on_hit_by_enemy(p.damage, dir, 0.0, pg.time.get_ticks() / 1000.0, True)
                    if outcome == "hit":
                        self.effects.shake.add(3.0, 0.1)
                        self.effects.hitstop.trigger(0.06)
                    elif outcome == "blocked":
                        self.effects.shake.add(1.0, 0.06)
                        self.effects.hitstop.trigger(0.03)
                    elif outcome in ("parry", "perfect_dodge"):
                        self.effects.shake.add(2.0, 0.08)
                        self.effects.hitstop.trigger(0.05)
                    continue
            else:  # owner == 'player'
                # hit enemies
                hit_any = False
                for e in list(self.enemies):
                    if (e.pos - p.pos).length() <= (e.radius + p.radius):
                        final = self.player.on_deal_damage(e, p.damage)
                        e.hp -= final
                        e.stun = max(e.stun, 0.12)
                        e.flash = 0.08
                        self.effects.text.add(str(final), (e.pos.x, e.pos.y))
                        try:
                            from .effects import Particle, QuickFlash
                            impact_dir = (e.pos - p.pos)
                            Particle.spray(self.effects, e.pos, impact_dir, count=8, speed=170, spread_deg=45, color=(255,210,150))
                            QuickFlash.add(self.effects, e.pos, radius=12)
                        except Exception:
                            pass
                        hit_any = True
                if hit_any:
                    try:
                        from . import sound
                        sound.get().play('hit', volume=0.4)
                    except Exception:
                        pass
                    self.effects.shake.add(2.0, 0.08)
                    self.effects.hitstop.trigger(0.03)
                    continue
            alive.append(p)
        self.projectiles = alive

        self.room_cleared = self.room.room_cleared

    def draw(self, surf: pg.Surface):
        self.room.draw(surf)
        # draw projectiles on top
        for p in self.projectiles:
            p.draw(surf)

    def next_room(self):
        self.room_index += 1
        self.room = Room(self.room_index, self.player, self.effects)
        self.room_cleared = False
