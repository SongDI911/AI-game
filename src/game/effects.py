from __future__ import annotations

import random
from dataclasses import dataclass
import math
from typing import List, Tuple

import pygame as pg


class HitStop:
    def __init__(self):
        self.timer = 0.0

    def trigger(self, duration: float):
        self.timer = max(self.timer, duration)

    def update(self, dt_unscaled: float):
        if self.timer > 0:
            self.timer -= dt_unscaled

    def time_scale(self) -> float:
        # 命中停顿期间，世界时间为 0
        return 0.0 if self.timer > 0 else 1.0


class ScreenShake:
    def __init__(self):
        self.timer = 0.0
        self.amplitude = 0.0

    def add(self, amplitude: float, duration: float):
        # 叠加强度与时长
        self.amplitude = max(self.amplitude, amplitude)
        self.timer = max(self.timer, duration)

    def update(self, dt_unscaled: float):
        if self.timer > 0:
            self.timer -= dt_unscaled
            # decay amplitude
            self.amplitude *= 0.9
            if self.timer <= 0:
                self.timer = 0
                self.amplitude = 0

    def offset(self) -> Tuple[int, int]:
        if self.timer <= 0 or self.amplitude <= 0:
            return 0, 0
        ox = int(random.uniform(-self.amplitude, self.amplitude))
        oy = int(random.uniform(-self.amplitude, self.amplitude))
        return ox, oy


@dataclass
class FloatingTextItem:
    text: str
    pos: pg.Vector2
    vel: pg.Vector2
    life: float
    color: Tuple[int, int, int]


class FloatingText:
    def __init__(self):
        self.items: List[FloatingTextItem] = []
        from . import fonts
        self.font = fonts.get_font(16)

    def add(self, text: str, pos, color=(255, 230, 180)):
        self.items.append(FloatingTextItem(text, pg.Vector2(pos), pg.Vector2(0, -40), 0.8, color))

    def update(self, dt_unscaled: float):
        alive: List[FloatingTextItem] = []
        for it in self.items:
            it.life -= dt_unscaled
            it.pos += it.vel * dt_unscaled
            it.vel.y -= 20 * dt_unscaled
            if it.life > 0:
                alive.append(it)
        self.items = alive

    def draw(self, surf: pg.Surface):
        for it in self.items:
            alpha = max(0, min(255, int(255 * (it.life / 0.8))))
            img = self.font.render(it.text, True, it.color)
            img.set_alpha(alpha)
            surf.blit(img, (it.pos.x, it.pos.y))


class Effects:
    def __init__(self):
        self.hitstop = HitStop()
        self.shake = ScreenShake()
        self.text = FloatingText()
        self.rings: list[ShockwaveRing] = []
        self.particles: list[Particle] = []
        self.slash_arcs: list[SlashArc] = []
        self.explosions: list[Explosion] = []

    def update(self, dt_unscaled: float):
        self.hitstop.update(dt_unscaled)
        self.shake.update(dt_unscaled)
        self.text.update(dt_unscaled)
        alive = []
        for r in self.rings:
            r.update(dt_unscaled)
            if not r.dead:
                alive.append(r)
        self.rings = alive

        # particles
        alive_p = []
        for p in self.particles:
            p.update(dt_unscaled)
            if not p.dead:
                alive_p.append(p)
        self.particles = alive_p

        # slash arcs
        alive_a = []
        for a in self.slash_arcs:
            a.update(dt_unscaled)
            if not a.dead:
                alive_a.append(a)
        self.slash_arcs = alive_a

        # explosions
        alive_e = []
        for e in self.explosions:
            e.update(dt_unscaled)
            if not e.dead:
                alive_e.append(e)
        self.explosions = alive_e

    def time_scale(self) -> float:
        return self.hitstop.time_scale()

    def draw_overlay(self, surf: pg.Surface):
        # 冲击波环绘制在 HUD 之前
        for r in self.rings:
            r.draw(surf)
        for a in self.slash_arcs:
            a.draw(surf)
        for e in self.explosions:
            e.draw(surf)
        for p in self.particles:
            p.draw(surf)
        self.text.draw(surf)


class ShockwaveRing:
    def __init__(self, pos: pg.Vector2, radius: float, life: float = 0.3, color=(200, 230, 255)):
        self.pos = pg.Vector2(pos)
        self.r = 0.0
        self.r_max = radius
        self.life = life
        self.t = 0.0
        self.dead = False
        self.color = color
        self.width = max(2, int(radius * 0.06))

    def update(self, dt: float):
        if self.dead:
            return
        self.t += dt
        if self.t >= self.life:
            self.dead = True
            return
        # expand linearly to r_max
        self.r = (self.t / self.life) * self.r_max

    def draw(self, surf: pg.Surface):
        if self.dead:
            return
        alpha = max(30, int(180 * (1.0 - self.t / self.life)))
        s = pg.Surface((int(self.r * 2 + 6), int(self.r * 2 + 6)), pg.SRCALPHA)
        pg.draw.circle(s, (*self.color, alpha), (s.get_width() // 2, s.get_height() // 2), int(self.r), width=self.width)
        surf.blit(s, (self.pos.x - s.get_width() // 2, self.pos.y - s.get_height() // 2))

    @staticmethod
    def add(effects: 'Effects', pos: pg.Vector2, radius: float, color=(200, 230, 255), life=0.3):
        from .config import MAX_RINGS
        if len(effects.rings) >= MAX_RINGS:
            effects.rings.pop(0)
        effects.rings.append(ShockwaveRing(pos, radius, life=life, color=color))


class Particle:
    def __init__(self, pos: pg.Vector2, vel: pg.Vector2, color=(255, 220, 150), size=3, life=0.35, gravity=0.0):
        self.pos = pg.Vector2(pos)
        self.vel = pg.Vector2(vel)
        self.color = color
        self.size = size
        self.life = life
        self.t = 0.0
        self.dead = False
        self.gravity = gravity

    def update(self, dt: float):
        if self.dead:
            return
        self.t += dt
        if self.t >= self.life:
            self.dead = True
            return
        self.vel.y += self.gravity * dt
        self.pos += self.vel * dt

    def draw(self, surf: pg.Surface):
        if self.dead:
            return
        alpha = max(20, int(255 * (1.0 - self.t / self.life)))
        s = pg.Surface((self.size*2, self.size*2), pg.SRCALPHA)
        pg.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        surf.blit(s, (self.pos.x - self.size, self.pos.y - self.size))

    @staticmethod
    def burst(effects: 'Effects', pos: pg.Vector2, count=8, speed=180, spread=math.tau, color=(255, 220, 150)):
        import random
        for _ in range(count):
            ang = random.uniform(0, spread)
            v = pg.Vector2(math.cos(ang), math.sin(ang)) * random.uniform(0.5*speed, speed)
            size = random.randint(2, 4)
            from .config import MAX_PARTICLES
            if len(effects.particles) >= MAX_PARTICLES:
                effects.particles.pop(0)
            effects.particles.append(Particle(pos, v, color=color, size=size, life=random.uniform(0.2, 0.4)))

    @staticmethod
    def spray(effects: 'Effects', pos: pg.Vector2, direction: pg.Vector2, count=10, speed=200, spread_deg=40, color=(255, 220, 150)):
        import random
        dirn = pg.Vector2(direction)
        if dirn.length_squared() == 0:
            Particle.burst(effects, pos, count=count, speed=speed, color=color)
            return
        dirn = dirn.normalize()
        base = math.atan2(dirn.y, dirn.x)
        spread = math.radians(spread_deg)
        for _ in range(count):
            ang = base + random.uniform(-spread/2, spread/2)
            v = pg.Vector2(math.cos(ang), math.sin(ang)) * random.uniform(0.6*speed, speed)
            from .config import MAX_PARTICLES
            if len(effects.particles) >= MAX_PARTICLES:
                effects.particles.pop(0)
            size = random.randint(2, 4)
            effects.particles.append(Particle(pos, v, color=color, size=size, life=random.uniform(0.18, 0.35)))


class SlashArc:
    """攻击特效 - 爆炸光环"""
    def __init__(self, pos: pg.Vector2, facing: pg.Vector2, length=48, width=28, life=0.25, color=(255, 240, 180)):
        self.pos = pg.Vector2(pos)
        self.facing = pg.Vector2(facing).normalize() if facing.length_squared() > 0 else pg.Vector2(1, 0)
        self.color = color
        self.life = life
        self.t = 0.0
        self.dead = False
        # 爆炸光环参数
        self.inner_radius = 10
        self.max_radius = 60
        self.rings = 3  # 光环层数
        self.ring_width = 8

    def update(self, dt: float):
        if self.dead:
            return
        self.t += dt
        if self.t >= self.life:
            self.dead = True

    def draw(self, surf: pg.Surface):
        if self.dead:
            return
        # 计算当前半径和透明度
        progress = self.t / self.life
        current_radius = self.inner_radius + (self.max_radius - self.inner_radius) * progress
        alpha = max(0, int(200 * (1.0 - progress)))
        
        # 绘制多层爆炸光环
        for i in range(self.rings):
            ring_radius = current_radius - i * self.ring_width * 0.6
            if ring_radius <= 0:
                continue
            ring_alpha = max(0, int(alpha * (1.0 - i * 0.3)))
            
            # 创建光环表面
            ring_size = int(ring_radius * 2 + 10)
            ring_surf = pg.Surface((ring_size, ring_size), pg.SRCALPHA)
            
            # 绘制光环（空心圆环）
            ring_color = (*self.color, ring_alpha)
            pg.draw.circle(ring_surf, ring_color, (ring_size // 2, ring_size // 2), int(ring_radius), int(self.ring_width))
            
            # 绘制内层光晕
            if i == 0:
                inner_alpha = max(0, int(alpha * 0.5))
                inner_radius_val = max(5, ring_radius * 0.4)
                pg.draw.circle(ring_surf, (*self.color, inner_alpha), (ring_size // 2, ring_size // 2), int(inner_radius_val))
            
            surf.blit(ring_surf, (self.pos.x - ring_size // 2, self.pos.y - ring_size // 2))
        
        # 添加中心亮点
        center_alpha = max(0, int(255 * (1.0 - progress * 1.5)))
        center_size = 20
        center_surf = pg.Surface((center_size, center_size), pg.SRCALPHA)
        pg.draw.circle(center_surf, (255, 255, 200, center_alpha), (center_size // 2, center_size // 2), center_size // 2)
        surf.blit(center_surf, (self.pos.x - center_size // 2, self.pos.y - center_size // 2))

    @staticmethod
    def add(effects: 'Effects', pos: pg.Vector2, facing: pg.Vector2, length=48, width=28, color=(255,240,180)):
        from .config import MAX_ARCS
        if len(effects.slash_arcs) >= MAX_ARCS:
            effects.slash_arcs.pop(0)
        effects.slash_arcs.append(SlashArc(pos, facing, length=length, width=width, color=color))


class QuickFlash:
    def __init__(self, pos: pg.Vector2, radius=18, life=0.12, color=(255, 255, 200)):
        self.pos = pg.Vector2(pos)
        self.radius = radius
        self.life = life
        self.t = 0.0
        self.dead = False
        self.color = color

    def update(self, dt: float):
        if self.dead:
            return
        self.t += dt
        if self.t >= self.life:
            self.dead = True

    def draw(self, surf: pg.Surface):
        if self.dead:
            return
        alpha = max(20, int(255 * (1.0 - self.t / self.life)))
        s = pg.Surface((self.radius*2+4, self.radius*2+4), pg.SRCALPHA)
        pg.draw.circle(s, (*self.color, alpha), (s.get_width()//2, s.get_height()//2), self.radius)
        surf.blit(s, (self.pos.x - s.get_width()//2, self.pos.y - s.get_height()//2))

    @staticmethod
    def add(effects: 'Effects', pos: pg.Vector2, radius=18, color=(255,255,200)):
        from .config import MAX_RINGS
        # reuse ring cap loosely for flashes
        effects.rings.append(QuickFlash(pos, radius=radius, color=color))


class Explosion:
    """复合爆炸效果，包含主爆炸环、粒子爆发、闪光和烟雾残留"""
    def __init__(self, pos: pg.Vector2, is_elite: bool = False):
        self.pos = pos
        self.is_elite = is_elite
        self.time = 0.0
        self.life = 0.6
        self.dead = False
        
        # 根据敌人类型设置参数
        if is_elite:
            self.main_radius = 80
            self.main_color = (255, 220, 150)
            self.particle_count = 28
            self.particle_speed = 260
            self.secondary_radius = 50
            self.secondary_color = (100, 200, 255)
            self.flash_radius = 25
        else:
            self.main_radius = 60
            self.main_color = (255, 180, 100)
            self.particle_count = 18
            self.particle_speed = 200
            self.secondary_radius = None
            self.secondary_color = None
            self.flash_radius = 18
            
        # 初始化子效果
        self.main_ring = None
        self.secondary_ring = None
        self.flash = None
        self.particles_spawned = False
        self.smoke_spawned = False
        
    def update(self, dt: float):
        if self.dead:
            return
            
        self.time += dt
        if self.time >= self.life:
            self.dead = True
            return
            
        # 0ms: 闪光效果
        if self.flash is None and self.time <= 0.05:
            self.flash = QuickFlash(self.pos, radius=self.flash_radius, color=self.main_color, life=0.15)
            
        # 0-100ms: 主爆炸环
        if self.main_ring is None and self.time <= 0.01:
            self.main_ring = ShockwaveRing(self.pos, self.main_radius, life=0.3, color=self.main_color)
            
        # 100-200ms: 粒子爆发
        if not self.particles_spawned and self.time >= 0.05:
            self.particles_spawned = True
            # 将在 draw 时通过 effects 系统生成粒子
            
        # 100-400ms: 二层烟雾环（仅精英）
        if self.is_elite and self.secondary_ring is None and self.time >= 0.1:
            self.secondary_ring = ShockwaveRing(self.pos, self.secondary_radius, life=0.4, color=self.secondary_color)
            
        # 200-800ms: 烟雾残留
        if not self.smoke_spawned and self.time >= 0.2:
            self.smoke_spawned = True
            # 将在 draw 时生成烟雾粒子
            
    def draw(self, surf: pg.Surface):
        if self.dead:
            return
            
        # 绘制闪光
        if self.flash and not self.flash.dead:
            self.flash.draw(surf)
            
        # 绘制主爆炸环
        if self.main_ring and not self.main_ring.dead:
            self.main_ring.draw(surf)
            
        # 绘制二层环（精英）
        if self.secondary_ring and not self.secondary_ring.dead:
            self.secondary_ring.draw(surf)
            
    @staticmethod
    def add(effects: 'Effects', pos: pg.Vector2, is_elite: bool = False):
        """添加爆炸效果到特效系统"""
        from .config import MAX_PARTICLES, MAX_RINGS
        
        # 检查特效数量限制
        if len(effects.explosions) >= MAX_RINGS:
            effects.explosions.pop(0)
            
        explosion = Explosion(pos, is_elite)
        effects.explosions.append(explosion)
        
        # 立即生成粒子爆发
        Particle.burst(effects, pos, count=explosion.particle_count,
                      speed=explosion.particle_speed, color=explosion.main_color)
        
        # 精英敌人额外生成金色粒子
        if is_elite:
            Particle.burst(effects, pos, count=12, speed=180, color=(255, 220, 150))
            
        # 播放音效
        try:
            from . import sound
            sound.get().play('death', volume=0.8 if is_elite else 0.6)
        except Exception:
            pass
