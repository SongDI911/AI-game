from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame as pg

from .config import LIGHT_ATTACK_DAMAGE
from .events import DamageEvent


class Skill:
    name: str = "Skill"
    cost: int = 20

    def can_use(self, player: "Player") -> bool:
        return player.energy >= self.cost

    def spend(self, player: "Player"):
        player.energy -= self.cost

    def use(self, player: "Player") -> bool:
        return False


class LungeSkill(Skill):
    name = "冲刺斩"
    cost = 20

    def __init__(self, variant: Optional[str] = None):
        self.variant = variant  # None|破甲|连环|幽灵|追影|裂空

    def use(self, player: "Player") -> bool:
        if not self.can_use(player):
            return False
        self.spend(player)
        # move forward and attack
        dist = 60
        start = player.pos.copy()
        
        # 幽灵：冲刺期间无敌
        ghost = (self.variant == "幽灵")
        if ghost:
            player.invuln = max(player.invuln, 0.15)
        
        # 追影：冲刺距离增加
        if self.variant == "追影":
            dist = 90
        
        player.pos += player.facing * dist

        dmg = LIGHT_ATTACK_DAMAGE + 10
        
        # 破甲：额外伤害
        if self.variant == "破甲":
            dmg += 8
        
        # 连环：返还部分能量
        if self.variant == "连环":
            player.energy = min(player.energy + int(self.cost * 0.5), player.energy_max)
        
        # 裂空：增加攻击范围
        radius = 28
        if self.variant == "裂空":
            radius = 42
            dmg += 5

        now = pg.time.get_ticks() / 1000.0
        ev = DamageEvent(player.pos.copy() + player.facing * 36, radius, dmg, "player", now)
        from .rooms import GlobalEvents
        GlobalEvents.add_event(ev)
        
        # Visual: slash arc + sparks
        if getattr(player, 'world', None) is not None:
            try:
                from .effects import SlashArc, Particle
                length = 56 if self.variant != "裂空" else 72
                SlashArc.add(player.world.effects, start + player.facing * 12, player.facing, length=length, width=26)
                count = 12 if self.variant == "裂空" else 8
                Particle.burst(player.world.effects, start + player.facing * 36, count=count, speed=220)
            except Exception:
                pass
        try:
            from . import sound
            sound.get().play('slash', volume=0.5)
        except Exception:
            pass
        return True


class ShockwaveSkill(Skill):
    name = "冲击波"
    cost = 25

    def __init__(self, variant: Optional[str] = None):
        self.variant = variant  # None|宽域|连锁|冻伤 | 聚能|爆裂

    def use(self, player: "Player") -> bool:
        if not self.can_use(player):
            return False
        self.spend(player)

        radius = 46
        dmg = 8
        
        # 宽域：增加范围
        if self.variant == "宽域":
            radius = 64
        
        # 连锁：增加伤害
        if self.variant == "连锁":
            dmg = 10
        
        # 冻伤：降低伤害但添加减速效果（简化为低伤害）
        if self.variant == "冻伤":
            dmg = 6
        
        # 聚能：减少范围但增加伤害
        if self.variant == "聚能":
            radius = 32
            dmg = 14
        
        # 爆裂：增加范围但减少伤害
        if self.variant == "爆裂":
            radius = 72
            dmg = 5

        now = pg.time.get_ticks() / 1000.0
        ev = DamageEvent(player.pos.copy(), radius, dmg, "player", now)
        from .rooms import GlobalEvents
        GlobalEvents.add_event(ev)

        # Visual: expanding shockwave ring(s)
        if getattr(player, 'world', None) is not None:
            try:
                from .effects import ShockwaveRing, Particle
                
                # 根据变异设置颜色
                if self.variant == "冻伤":
                    color = (160, 200, 255)
                elif self.variant == "聚能":
                    color = (255, 200, 100)
                elif self.variant == "爆裂":
                    color = (255, 150, 150)
                else:
                    color = (200, 230, 255)
                
                ShockwaveRing.add(player.world.effects, player.pos.copy(), radius, color=color, life=0.32)
                
                # 连锁：二次冲击波
                if self.variant == "连锁":
                    ShockwaveRing.add(player.world.effects, player.pos.copy(), int(radius * 0.7), color=color, life=0.28)
                
                # 聚能：额外的小范围冲击波
                if self.variant == "聚能":
                    ShockwaveRing.add(player.world.effects, player.pos.copy(), int(radius * 0.5), color=(255, 255, 200), life=0.2)
                
                # 爆裂：更多粒子
                particle_count = 28 if self.variant == "爆裂" else 18
                Particle.burst(player.world.effects, player.pos.copy(), count=particle_count, speed=240, color=(210,210,220))
            except Exception:
                pass
        try:
            from . import sound
            sound.get().play('shockwave', volume=0.5)
        except Exception:
            pass

        # 连锁：再次产生一次较小伤害
        if self.variant == "连锁":
            ev2 = DamageEvent(player.pos.copy(), int(radius * 0.7), 6, "player", now)
            GlobalEvents.add_event(ev2)
        
        # 聚能：中心高伤害
        if self.variant == "聚能":
            ev3 = DamageEvent(player.pos.copy(), int(radius * 0.3), 8, "player", now)
            GlobalEvents.add_event(ev3)
        
        return True
