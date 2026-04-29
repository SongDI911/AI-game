from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pygame as pg

from .config import (
    PLAYER_COLOR,
    ENEMY_COLOR,
    TELEGRAPH_COLOR,
    TELEGRAPH_UNBLOCKABLE_COLOR,
    ATTACK_COLOR,
    WIDTH,
    HEIGHT,
    PLAYER_MAX_HP,
    PLAYER_MAX_ENERGY,
    PLAYER_SPEED,
    PLAYER_DASH_SPEED,
    PLAYER_DASH_TIME,
    PLAYER_BLOCK_ANGLE,
    PLAYER_BLOCK_REDUCTION,
    ENERGY_ON_HIT,
    ENERGY_ON_BLOCK,
    ENERGY_ON_PERFECT_DODGE,
    ATTACK_COOLDOWN,
    LIGHT_ATTACK_DAMAGE,
    ENEMY_BASE_HP,
    ENEMY_TELEGRAPH,
    ENEMY_RECOVERY,
    ENEMY_ATTACK_RANGE,
    ENEMY_ATTACK_DAMAGE,
    ENEMY_SPEED,
    SLOW_MO_SCALE,
    SLOW_MO_TIME,
)

from .utils import clamp, vec_norm, angle_between
from .skills import LungeSkill, ShockwaveSkill
from . import assets
from .events import DamageEvent
from .direction import eight_way, smooth_facing, hysteresis_flip
from .effects import ShockwaveRing, Particle, SlashArc, Explosion


Vec = pg.Vector2


# DamageEvent moved to events.py to avoid circular imports


class Entity:
    def __init__(self, pos: Tuple[int, int], radius: int = 16):
        self.pos = Vec(pos)
        self.radius = radius

    def draw_circle(self, surf: pg.Surface, color: Tuple[int, int, int]):
        pg.draw.circle(surf, color, self.pos, self.radius)


class Player(Entity):
    def __init__(self, pos=(WIDTH // 2, HEIGHT // 2)):
        super().__init__(pos, radius=14)
        self.hp = PLAYER_MAX_HP
        self.hp_max = PLAYER_MAX_HP  # 最大生命值（可被遗物修改）
        self.energy = 30
        self.energy_max = PLAYER_MAX_ENERGY
        self.fragments = 0  # 时之碎片（局内货币）
        self.vel = Vec(0, 0)
        self.facing = Vec(1, 0)
        self.attack_cd = 0.0
        self.attack_buffer = 0.0
        self.dash_time = 0.0
        self.blocking = False
        self.block_dir = Vec(1, 0)
        self.invuln = 0.0
        self.time_scale = 1.0
        self._slowmo = 0.0
        self.relics: List[str] = []  # names
        self.damage_over_time: List[Tuple[float, int, float]] = []  # (time_left, dps, tick)
        # skills
        self.skill_q = LungeSkill()
        self.skill_e = ShockwaveSkill()
        self.world = None  # type: ignore
        self.hurt_flash = 0.0
        # combo / sustained attack
        self.combo_step = 0
        self.attack_action = None  # type: ignore
        self.queued_attack = False
        self.anim_t = 0.0
        self.frames = assets.get_player_frames()
        self.flip_x = False
        self.dir_frames = assets.get_player_dir_frames()
        self.gen_dir_frames = None
        self.auto_fire_cd = 0.2
        
        # 遗物效果追踪
        self._attack_counter = 0  # 雷霆打击计数
        self._last_hit_enemy = None  # 生命偷取追踪
        self._damage_buff = 0  # 临时伤害加成

    # input
    def handle_input(self):
        keys = pg.key.get_pressed()
        move = Vec(0, 0)
        if keys[pg.K_w] or keys[pg.K_UP]:
            move.y -= 1
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            move.y += 1
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            move.x -= 1
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            move.x += 1

        if move.length_squared() > 0:
            move = move.normalize()
            # smooth facing rotation to avoid jitter
            self.facing = smooth_facing(self.facing, move, 0.3)
        speed = PLAYER_SPEED
        if self.dash_time > 0:
            speed = PLAYER_DASH_SPEED
        self.vel = move * speed

        # actions
        if pg.mouse.get_pressed(num_buttons=3)[0]:
            if self.attack_cd <= 0:
                self.try_attack()
            else:
                self.attack_buffer = 0.15

        # block (RMB or LSHIFT)
        self.blocking = pg.mouse.get_pressed(num_buttons=3)[2] or keys[pg.K_LSHIFT]
        if self.blocking and self.vel.length_squared() > 0:
            self.block_dir = self.vel.normalize()
        elif self.blocking:
            self.block_dir = self.facing

        # dash (SPACE)
        if keys[pg.K_SPACE] and self.dash_time <= 0 and self.energy >= 10:
            self.dash_time = PLAYER_DASH_TIME
            self.invuln = max(self.invuln, 0.12)
            self.energy = max(0, self.energy - 10)

        # skills
        if keys[pg.K_q]:
            self.skill_q.use(self)
        if keys[pg.K_e]:
            self.skill_e.use(self)

    def try_attack(self):
        if self.attack_cd <= 0:
            # soft auto-aim toward nearest enemy
            world = getattr(self, 'world', None)
            if world is not None:
                target = None
                best_d2 = 200 ** 2
                for e in world.enemies:
                    d2 = (e.pos - self.pos).length_squared()
                    if d2 < best_d2:
                        best_d2 = d2
                        target = e
                if target is not None:
                    d = (target.pos - self.pos)
                    if d.length_squared() > 0:
                        d = d.normalize()
                        ang = angle_between(self.facing.x, self.facing.y, d.x, d.y)
                        if ang <= 75:
                            self.facing = d
            # start a sustained attack (combo)
            self.start_combo_attack()
            self.attack_cd = 0.05
        else:
            self.queued_attack = True

    def start_combo_attack(self):
        from .combat import Attack
        self.combo_step = 1 if self.attack_action is None else min(3, self.combo_step + 1)
        # combo data: (radius, damage, offset, startup, active, recovery)
        if self.combo_step == 1:
            r, dmg, off, su, ac, re = 22, LIGHT_ATTACK_DAMAGE, 16, 0.06, 0.08, 0.18
        elif self.combo_step == 2:
            r, dmg, off, su, ac, re = 26, LIGHT_ATTACK_DAMAGE + 4, 18, 0.08, 0.10, 0.20
        else:
            r, dmg, off, su, ac, re = 30, LIGHT_ATTACK_DAMAGE + 10, 20, 0.10, 0.12, 0.28
        self.pos += self.facing * 6  # slight lunge
        self.attack_action = Attack(
            owner="player",
            origin=self.pos.copy(),
            facing=self.facing.copy(),
            offset=off,
            radius=r,
            damage=dmg,
            startup=su,
            active=ac,
            recovery=re,
        )
        # hand over to room manager to track collision
        if self.world is not None:
            self.world.hitboxes.append(self.attack_action)

    def _spawn_attack(self, radius: float, damage: int):
        now = pg.time.get_ticks() / 1000.0
        ev = DamageEvent(self.pos.copy() + self.facing * (self.radius + radius * 0.6), radius, damage, "player", now, True)
        from .rooms import GlobalEvents

        GlobalEvents.add_event(ev)

    def add_energy(self, amount: int):
        # relic: Energy Surge -> +50% gain
        if "Energy Surge" in self.relics:
            amount = int(amount * 1.5)
        self.energy = clamp(self.energy + amount, 0, self.energy_max)

    def add_relic(self, name: str):
        """添加遗物并应用即时效果"""
        if name not in self.relics:
            self.relics.append(name)
            
            # 应用即时效果
            if name == "坚韧护盾":
                self.hp_max += 20
                self.hp += 20
            elif name == "疾风步":
                pass  # 在 update 中处理速度加成
            elif name == "时间扭曲":
                pass  # 在子弹时间中处理

    def update(self, dt: float, world: "RoomManager"):
        # keep world ref for soft auto-aim
        self.world = world
        # cooldowns and timers
        self.attack_cd = max(0.0, self.attack_cd - dt)
        if self.attack_buffer > 0:
            self.attack_buffer = max(0.0, self.attack_buffer - dt)
            if self.attack_cd <= 0 and self.attack_buffer > 0:
                self.try_attack()
                self.attack_buffer = 0.0
        self.invuln = max(0.0, self.invuln - dt)
        if self.dash_time > 0:
            self.dash_time -= dt
        # slow-mo timer from perfect dodge
        if self._slowmo > 0:
            self._slowmo -= dt
            # 时间扭曲遗物增强子弹时间
            slowmo_scale = SLOW_MO_SCALE
            if "时间扭曲" in self.relics:
                slowmo_scale *= 0.8  # 更慢
            self.time_scale = slowmo_scale
        else:
            self.time_scale = 1.0

        # move - 疾风步遗物增加速度
        speed_mult = 1.15 if "疾风步" in self.relics else 1.0
        speed = PLAYER_SPEED * speed_mult
        if self.dash_time > 0:
            speed = PLAYER_DASH_SPEED * speed_mult
        self.vel = self.vel.normalize() * speed if self.vel.length_squared() > 0 else Vec(0, 0)
        
        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, 24, WIDTH - 24)
        self.pos.y = clamp(self.pos.y, 24, HEIGHT - 24)
        # animate (faster when moving)
        spd = self.vel.length()
        self.anim_t += dt * (2.0 if spd > 10 else 1.0)
        # update facing-based flip (left/right)
        self.flip_x = hysteresis_flip(self.flip_x, self.facing.x, 0.2)

        # auto-shoot nearest enemy
        self._auto_shoot(dt, world)

        # DoT processing (burn etc.)
        for i, (t, dps, tick) in enumerate(list(self.damage_over_time)):
            tick -= dt
            t -= dt
            if tick <= 0:
                self.hp -= dps
                tick = 0.5
            if t <= 0:
                self.damage_over_time.pop(0)
            else:
                self.damage_over_time[i] = (t, dps, tick)

    def on_hit_by_enemy(self, dmg: int, attacker_dir: Vec, telegraphed_time: float, attack_time: float, blockable: bool = True) -> str:
        # perfect dodge: within 120ms window around attack moment and during dash
        now = pg.time.get_ticks() / 1000.0
        window = 0.12
        perfect = self.dash_time > 0 and abs(now - attack_time) <= window

        if perfect:
            self.add_energy(ENERGY_ON_PERFECT_DODGE)
            self._slowmo = SLOW_MO_TIME
            return "perfect_dodge"

        if self.blocking:
            # angle check
            ang = angle_between(self.block_dir.x, self.block_dir.y, attacker_dir.x, attacker_dir.y)
            if ang <= PLAYER_BLOCK_ANGLE / 2:
                if not blockable:
                    # guard break: heavy blow smashes guard
                    self.hp -= int(dmg * 1.0)
                    self.hurt_flash = 0.2
                    return "guard_break"
                # parry window near attack time
                if abs(now - attack_time) <= 0.08:
                    self.add_energy(max(ENERGY_ON_BLOCK, ENERGY_ON_PERFECT_DODGE // 2))
                    self._slowmo = SLOW_MO_TIME * 0.6
                    return "parry"
                reduced = int(dmg * (1.0 - PLAYER_BLOCK_REDUCTION))
                self.hp -= max(1, reduced)
                self.add_energy(ENERGY_ON_BLOCK)
                if "Guard Convert" in self.relics:
                    self.hp = min(PLAYER_MAX_HP, self.hp + 2)
                self.hurt_flash = 0.1
                return "blocked"

        if self.invuln > 0:
            return "evade"

        self.hp -= dmg
        self.hurt_flash = 0.15
        return "hit"

    def _auto_shoot(self, dt: float, world: "RoomManager"):
        from .config import AUTO_SHOOT_INTERVAL, AUTO_BULLET_SPEED, AUTO_BULLET_DAMAGE
        if AUTO_SHOOT_INTERVAL <= 0:
            return
        self.auto_fire_cd -= dt
        if self.auto_fire_cd > 0:
            return
        # find nearest enemy
        target = None
        best_d2 = float('inf')
        for e in world.enemies:
            d2 = (e.pos - self.pos).length_squared()
            if d2 < best_d2:
                best_d2 = d2
                target = e
        if target is None:
            self.auto_fire_cd = 0.1
            return
        direction = (target.pos - self.pos)
        if direction.length_squared() == 0:
            self.auto_fire_cd = 0.1
            return
        direction = direction.normalize()
        # spawn projectile
        proj = Projectile(
            self.pos.copy() + direction * (self.radius + 6),
            direction * AUTO_BULLET_SPEED,
            5,
            AUTO_BULLET_DAMAGE,
            life=2.0,
            owner="player",
            homing=True,
            speed=AUTO_BULLET_SPEED,
        )
        world.projectiles.append(proj)
        self.auto_fire_cd = AUTO_SHOOT_INTERVAL

    def on_deal_damage(self, target: "Enemy", dmg: int) -> int:
        """Returns final damage after relic/condition modifiers and applies on-hit effects."""
        final = dmg
        
        # 低血暴：below 50% HP -> +20% damage
        if "低血暴" in self.relics and self.hp <= self.hp_max * 0.5:
            final = int(final * 1.2)
        
        # 复仇之心：below 30% HP -> +40% damage
        if "复仇之心" in self.relics and self.hp <= self.hp_max * 0.3:
            final = int(final * 1.4)
        
        # 连击大师：连击伤害递增
        if "连击大师" in self.relics:
            final = int(final * (1.0 + 0.1 * self.combo_step))

        self.add_energy(ENERGY_ON_HIT)
        
        # 吸血之刃：攻击时恢复生命
        if "吸血之刃" in self.relics:
            self.hp = min(self.hp_max, self.hp + 2)
        
        # 雷霆打击：每 5 次攻击触发闪电链
        self._attack_counter += 1
        if "雷霆打击" in self.relics and self._attack_counter >= 5:
            self._attack_counter = 0
            # 对附近所有敌人造成伤害
            for e in getattr(self, 'world', None).enemies if getattr(self, 'world', None) else []:
                if (e.pos - self.pos).length() <= 150:
                    e.hp -= 8
                    e.stun = 0.2
                    e.flash = 0.1
        
        # relics
        if "易燃" in self.relics:
            target.apply_burn(duration=3.0, dps=4)
        if "蔓延" in self.relics and target.is_burning:
            target.enable_burn_spread = True
        return final

    def draw(self, surf: pg.Surface):
        dir_frames = getattr(self, 'dir_frames', None)
        if dir_frames and len(dir_frames) >= 1:
            key = eight_way(self.facing)
            frames = dir_frames.get(key) or self.frames
            idx = int(self.anim_t * 10) % len(frames)
            img = frames[idx]
            rect = img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(img, rect)
        elif getattr(self, 'frames', None):
            if self.gen_dir_frames is None:
                self.gen_dir_frames = assets.build_dir_from_single(self.frames)
            key = eight_way(self.facing)
            frames = self.gen_dir_frames.get(key) or self.frames
            idx = int(self.anim_t * 10) % len(self.frames)
            img = frames[idx]
            rect = img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(img, rect)
        else:
            color = PLAYER_COLOR
            if self.hurt_flash > 0:
                mix = min(1.0, self.hurt_flash / 0.15)
                r = int(color[0] + (255 - color[0]) * mix)
                g = int(color[1] * (1 - 0.5 * mix))
                b = int(color[2] * (1 - 0.5 * mix))
                pg.draw.circle(surf, (r, g, b), self.pos, self.radius)
                self.hurt_flash = max(0.0, self.hurt_flash - 1/60)
            else:
                self.draw_circle(surf, color)
        # block direction
        if self.blocking:
            end = self.pos + self.block_dir * 28
            pg.draw.line(surf, (150, 200, 255), self.pos, end, 3)


class Enemy(Entity):
    def __init__(self, pos: Tuple[int, int]):
        super().__init__(pos, radius=13)
        self.hp = ENEMY_BASE_HP
        self.state = "chase"  # chase|telegraph|attack|recover
        self.timer = random.uniform(0.3, 0.7)
        self.attack_time = 0.0
        self.blockable = True
        self.is_burning = False
        self.burn: Tuple[float, int, float] | None = None  # (time_left, dps, tick)
        self.enable_burn_spread = False
        self.flash = 0.0
        self.stun = 0.0
        self.poise_max = 30
        self.poise = self.poise_max
        self.elite = False
        self.anim_t = 0.0
        self.frames = assets.get_melee_enemy_frames()
        self.dir_frames = assets.get_melee_enemy_dir_frames()
        self.gen_dir_frames = None
        self.facing = Vec(1, 0)
        self.flip_x = False

    def update(self, dt: float, player: Player, world: "RoomManager"):
        to_player = player.pos - self.pos
        dist = to_player.length()
        if dist > 0:
            dir = to_player / dist
        else:
            dir = Vec(1, 0)
        self.facing = smooth_facing(self.facing, dir, 0.25)

        # poise regen
        self.poise = min(self.poise_max, self.poise + 8 * dt)

        if self.stun > 0:
            self.stun -= dt
            # limited drift while stunned
        elif self.state == "chase":
            self.pos += dir * ENEMY_SPEED * dt
            self.timer -= dt
            if dist < ENEMY_ATTACK_RANGE and self.timer <= 0:
                self.state = "telegraph"
                self.timer = ENEMY_TELEGRAPH
                # decide if heavy (unblockable) or normal
                self.blockable = random.random() > 0.25  # 25% heavy

        elif self.state == "telegraph":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "attack"
                self.timer = 0.0
                self._perform_attack(world, dir)

        elif self.state == "attack":
            self.state = "recover"
            self.timer = ENEMY_RECOVERY

        elif self.state == "recover":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "chase"
                self.timer = random.uniform(0.4, 0.9)

        # burn DoT
        if self.burn:
            t, dps, tick = self.burn
            t -= dt
            tick -= dt
            if tick <= 0:
                self.hp -= dps
                tick = 0.5
                # spread burn to nearby enemies if enabled
                if self.enable_burn_spread:
                    for e in world.enemies:
                        if e is self:
                            continue
                        if (e.pos - self.pos).length() <= 80 and not e.is_burning:
                            e.apply_burn(2.0, max(1, dps // 2))
            if t <= 0:
                self.burn = None
                self.is_burning = False
            else:
                self.burn = (t, dps, tick)
        # animate
        self.anim_t += dt * 1.5
        self.flip_x = hysteresis_flip(self.flip_x, self.facing.x, 0.2)

    def _perform_attack(self, world: "RoomManager", dir: Vec):
        now = pg.time.get_ticks() / 1000.0
        self.attack_time = now
        dmg = ENEMY_ATTACK_DAMAGE * (1.4 if not self.blockable else 1.0)
        ev = DamageEvent(self.pos + dir * (self.radius + 10), 20, int(dmg), "enemy", now, self.blockable)
        from .rooms import GlobalEvents

        GlobalEvents.add_event(ev)

        # check hit vs player instantly (melee snapshot)
        player = world.player
        if (player.pos - ev.pos).length() <= (player.radius + ev.radius):
            outcome = player.on_hit_by_enemy(ev.damage, dir, ENEMY_TELEGRAPH, self.attack_time, self.blockable)
            # feedback via effects
            if outcome in ("hit",):
                world.effects.shake.add(3.0, 0.1)
                world.effects.hitstop.trigger(0.06)
            elif outcome in ("blocked",):
                world.effects.shake.add(1.0, 0.06)
                world.effects.hitstop.trigger(0.03)
            elif outcome in ("parry", "perfect_dodge"):
                world.effects.shake.add(2.0, 0.08)
                world.effects.hitstop.trigger(0.05)
            elif outcome == "guard_break":
                world.effects.shake.add(3.5, 0.12)
                world.effects.hitstop.trigger(0.07)

    def apply_burn(self, duration: float, dps: int):
        self.is_burning = True
        self.burn = (duration, dps, 0.25)

    def draw(self, surf: pg.Surface):
        drawn = False

        # 尝试绘制方向贴图
        dir_frames = getattr(self, 'dir_frames', None)
        if dir_frames and isinstance(dir_frames, dict) and len(dir_frames) > 0:
            key = eight_way(self.facing)
            frames = dir_frames.get(key)
            if frames and len(frames) > 0:
                idx = int(self.anim_t * 8) % len(frames)
                img = frames[idx]
                surf.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))
                drawn = True

        # 尝试绘制普通贴图
        if not drawn:
            frames = getattr(self, 'frames', None)
            if frames and len(frames) > 0:
                idx = int(self.anim_t * 8) % len(frames)
                img = frames[idx]
                surf.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))
                drawn = True

        # 如果没有贴图，绘制圆形
        if not drawn:
            color = ENEMY_COLOR
            if self.elite:
                color = (int(color[0]*0.9), int(color[1]*1.1), int(color[2]*1.2))
            if self.state == "telegraph":
                color = TELEGRAPH_COLOR if self.blockable else TELEGRAPH_UNBLOCKABLE_COLOR
            if self.flash > 0:
                mix = min(1.0, self.flash / 0.08)
                r = int(color[0] + (255 - color[0]) * mix)
                g = int(color[1] + (255 - color[1]) * mix)
                b = int(color[2] + (255 - color[2]) * mix)
                self.draw_circle(surf, (r, g, b))
                self.flash = max(0.0, self.flash - 1/60)
            else:
                self.draw_circle(surf, color)

        # 绘制 telegraph 预警圈（无论是否有贴图）
        if self.state == "telegraph" and drawn:
            col = TELEGRAPH_COLOR if self.blockable else TELEGRAPH_UNBLOCKABLE_COLOR
            pg.draw.circle(surf, col, self.pos, self.radius + 10, 2)

        # 受击闪光覆盖层（有贴图时也显示）
        if self.flash > 0 and drawn:
            mix = min(1.0, self.flash / 0.08)
            alpha = int(200 * mix)
            flash_surf = pg.Surface((self.radius * 2 + 10, self.radius * 2 + 10), pg.SRCALPHA)
            pg.draw.circle(flash_surf, (255, 255, 255, alpha),
                          (flash_surf.get_width() // 2, flash_surf.get_height() // 2),
                          self.radius + 5)
            surf.blit(flash_surf, (self.pos.x - flash_surf.get_width() // 2,
                                   self.pos.y - flash_surf.get_height() // 2))
            self.flash = max(0.0, self.flash - 1/60)


class Projectile:
    def __init__(self, pos: Vec, vel: Vec, radius: int, damage: int, life: float = 3.0, owner: str = "enemy", homing: bool = False, speed: float = 0.0):
        self.pos = Vec(pos)
        self.vel = Vec(vel)
        self.radius = radius
        self.damage = damage
        self.life = life
        self.owner = owner  # 'enemy'|'player'
        self.homing = homing
        self.speed = speed if speed > 0 else self.vel.length()

    def update(self, dt: float):
        self.life -= dt
        self.pos += self.vel * dt

    def draw(self, surf: pg.Surface):
        pg.draw.circle(surf, (255, 180, 120), self.pos, self.radius)


class RangerEnemy(Enemy):
    def __init__(self, pos):
        super().__init__(pos)
        self.state = "aim"
        self.timer = random.uniform(0.6, 1.1)
        self.frames = assets.get_ranger_enemy_frames()
        self.dir_frames = assets.get_ranger_enemy_dir_frames()
        self.gen_dir_frames = None

    def update(self, dt: float, player: Player, world: "RoomManager"):
        if self.stun > 0:
            self.stun -= dt
            # while stunned, drift minimally and skip shooting logic
            return
        to_player = player.pos - self.pos
        dist = to_player.length() or 1.0
        dir = to_player / dist
        self.facing = smooth_facing(self.facing, dir, 0.25)
        # keep distance
        desired = 220
        if dist < desired:
            self.pos -= dir * ENEMY_SPEED * 0.7 * dt
        elif dist > desired + 30:
            self.pos += dir * ENEMY_SPEED * 0.5 * dt

        self.timer -= dt
        if self.state == "aim":
            if self.timer <= 0:
                self.state = "shoot"
                self.timer = 0.1
        elif self.state == "shoot":
            self._shoot(world, dir)
            self.state = "recover"
            self.timer = 0.8
        elif self.state == "recover":
            if self.timer <= 0:
                self.state = "aim"
                self.timer = random.uniform(0.8, 1.2)

        # burn DoT / recovery timers from base
        if self.burn:
            t, dps, tick = self.burn
            t -= dt
            tick -= dt
            if tick <= 0:
                self.hp -= dps
                tick = 0.5
            if t <= 0:
                self.burn = None
                self.is_burning = False
            else:
                self.burn = (t, dps, tick)

    def _shoot(self, world: "RoomManager", dir: Vec):
        speed = 300
        vel = dir * speed
        proj = Projectile(self.pos.copy(), vel, 6, int(ENEMY_ATTACK_DAMAGE * 0.7), life=2.2, owner="enemy")
        world.projectiles.append(proj)

    def draw(self, surf: pg.Surface):
        dir_frames = getattr(self, 'dir_frames', None)
        if dir_frames and len(dir_frames) >= 1:
            key = eight_way(self.facing)
            frames = dir_frames.get(key) or self.frames
            idx = int(self.anim_t * 8) % len(frames)
            img = frames[idx]
            surf.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))
        elif getattr(self, 'frames', None):
            if self.gen_dir_frames is None:
                self.gen_dir_frames = assets.build_dir_from_single(self.frames)
            key = eight_way(self.facing)
            frames = self.gen_dir_frames.get(key) or self.frames
            idx = int(self.anim_t * 8) % len(frames)
            img = frames[idx]
            surf.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))
        else:
            pg.draw.circle(surf, (200, 150, 255), self.pos, self.radius)


class BossEnemy(Enemy):
    """Boss 敌人 - 拥有多种攻击模式和更高的属性"""

    def __init__(self, pos: Tuple[int, int]):
        super().__init__(pos)
        self.hp = ENEMY_BASE_HP * 8  # Boss 基础生命值为普通敌人 8 倍
        self.hp_max = ENEMY_BASE_HP * 8
        self.poise_max = 100  # 更高的韧性
        self.poise = self.poise_max
        self.radius = 28  # 更大的体型
        self.damage = 24  # 更高的伤害
        self.state = "chase"
        self.timer = 1.0
        self.attack_pattern = 0  # 当前攻击模式
        self.phase = 1  # Boss 阶段 (基于生命值)
        self.phase_changed = False  # 阶段转换标记
        self.anim_t = 0.0
        # Boss 专属贴图
        self.frames = assets.get_boss_frames()
        self.dir_frames = assets.get_boss_dir_frames()
        self.gen_dir_frames = None
        self.facing = Vec(1, 0)
        self.flip_x = False
        self.elite = True  # Boss 始终是精英
        # Boss 特效
        self.aura_timer = 0.0
        self.charge_effect = None  # 冲锋轨迹
        self.slam_aoe_pos = None  # 区域猛击 AOE 位置
        self.slam_timer = 0.0
        self.hurt_flash = 0.0
        self.death_effect = None
    
    def update(self, dt: float, player: Player, world: "RoomManager"):
        # 阶段转换 (基于生命值百分比)
        hp_percent = self.hp / self.hp_max
        old_phase = self.phase
        if hp_percent < 0.3:
            self.phase = 3
        elif hp_percent < 0.6:
            self.phase = 2

        # 阶段转换特效
        if self.phase != old_phase and not self.phase_changed:
            self.phase_changed = True
            self._on_phase_change(world)

        # 重置阶段转换标记
        if self.phase_changed and self.state == "chase":
            self.phase_changed = False

        to_player = player.pos - self.pos
        dist = to_player.length() or 1.0
        dir = to_player / dist
        self.facing = smooth_facing(self.facing, dir, 0.2)

        # 韧性恢复
        self.poise = min(self.poise_max, self.poise + 5 * dt)

        # Boss 光环特效计时
        if self.aura_timer > 0:
            self.aura_timer -= dt

        # 区域猛击 AOE 计时
        if self.slam_timer > 0:
            self.slam_timer -= dt
            if self.slam_timer <= 0:
                # 执行 AOE 伤害
                self._do_slam_attack(world)
                self.slam_aoe_pos = None

        if self.stun > 0:
            self.stun -= dt
            # 被击晕时缓慢漂移
            self.pos += dir * ENEMY_SPEED * 0.3 * dt
        elif self.state == "chase":
            # 追逐玩家
            if dist > 100:
                self.pos += dir * (ENEMY_SPEED * 0.6) * dt
            self.timer -= dt
            if self.timer <= 0 or dist < 120:
                self._choose_attack_pattern()
                self.state = "telegraph"
                self.timer = ENEMY_TELEGRAPH * 0.8  # Boss 前摇更短

        elif self.state == "telegraph":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "attack"
                self._perform_attack(world, dir)

        elif self.state == "attack":
            # 检查是否是双重打击的第二次攻击
            if self.attack_pattern == "double_strike_2":
                self.state = "recover"
                self.timer = ENEMY_RECOVERY * 0.7
            else:
                self.state = "recover"
                self.timer = ENEMY_RECOVERY * 0.7

        elif self.state == "recover":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "chase"
                self.timer = random.uniform(0.5, 1.2)

        # 燃烧 DoT
        if self.burn:
            t, dps, tick = self.burn
            t -= dt
            tick -= dt
            if tick <= 0:
                self.hp -= dps
                tick = 0.5
            if t <= 0:
                self.burn = None
                self.is_burning = False
            else:
                self.burn = (t, dps, tick)

        # 受击闪光
        if self.hurt_flash > 0:
            self.hurt_flash -= dt

        # 动画
        self.anim_t += dt * (1.5 if self.phase == 3 else 1.2)
        self.flip_x = hysteresis_flip(self.flip_x, self.facing.x, 0.2)
    
    def _choose_attack_pattern(self):
        """根据阶段和随机性选择攻击模式"""
        patterns = ["melee", "charge", "spin", "projectile"]
        if self.phase >= 2:
            patterns.append("double_strike")
        if self.phase >= 3:
            patterns.append("area_slam")
        
        self.attack_pattern = random.choice(patterns)
    
    def _perform_attack(self, world: "RoomManager", dir: Vec):
        """执行 Boss 攻击"""
        now = pg.time.get_ticks() / 1000.0
        self.attack_time = now

        if self.attack_pattern == "melee":
            # 普通近战攻击
            dmg = self.damage
            self._do_melee_attack(world, dir, dmg, radius=24)
            # 挥砍特效
            SlashArc.add(world.effects, self.pos.copy(), dir, length=50, width=30, color=(255, 200, 150))

        elif self.attack_pattern == "charge":
            # 冲锋攻击：向玩家方向突进
            dmg = self.damage * 1.2
            # 冲锋起点特效
            Particle.burst(world.effects, self.pos.copy(), count=15, speed=200, color=(255, 100, 100))
            self.pos += dir * 80  # 突进
            # 冲锋终点特效
            Particle.burst(world.effects, self.pos.copy(), count=20, speed=250, color=(255, 150, 150))
            ShockwaveRing.add(world.effects, self.pos.copy(), radius=40, color=(255, 80, 80), life=0.25)
            self._do_melee_attack(world, dir, dmg, radius=30)

        elif self.attack_pattern == "spin":
            # 旋转攻击：360 度范围伤害
            dmg = self.damage * 0.8
            # 旋转启动特效
            ShockwaveRing.add(world.effects, self.pos.copy(), radius=60, color=(255, 200, 100), life=0.4)
            self._do_melee_attack(world, dir, dmg, radius=50)
            # 多方向粒子
            for i in range(8):
                angle = i * (math.tau / 8)
                offset_pos = self.pos + Vec(math.cos(angle), math.sin(angle)) * 40
                Particle.burst(world.effects, offset_pos, count=3, speed=100, color=(255, 180, 100))

        elif self.attack_pattern == "projectile":
            # 发射投射物
            # 蓄力特效
            ShockwaveRing.add(world.effects, self.pos.copy(), radius=35, color=(150, 100, 255), life=0.2)
            self._shoot_projectile(world, dir)

        elif self.attack_pattern == "double_strike":
            # 双重打击：连续两次攻击
            dmg = self.damage * 0.9
            self._do_melee_attack(world, dir, dmg, radius=26)
            SlashArc.add(world.effects, self.pos.copy(), dir, length=45, width=25, color=(255, 220, 180))
            # 标记需要进行第二次攻击
            self.attack_pattern = "double_strike_2"
            self.timer = 0.3  # 300ms 后第二次攻击

        elif self.attack_pattern == "double_strike_2":
            # 双重打击第二次攻击
            dmg = self.damage * 0.9
            self._do_melee_attack(world, dir, dmg, radius=26)
            SlashArc.add(world.effects, self.pos.copy(), dir, length=45, width=25, color=(255, 200, 160))
            # 额外的冲击波
            ShockwaveRing.add(world.effects, self.pos.copy(), radius=35, color=(255, 150, 100), life=0.25)

        elif self.attack_pattern == "area_slam":
            # 区域猛击：大范围高伤害
            dmg = self.damage * 1.5
            # 在玩家位置生成 AOE 预警
            player = world.player
            self.slam_aoe_pos = (player.pos.x, player.pos.y)
            self.slam_timer = 0.6  # 0.6 秒后爆炸
            self._slam_damage = dmg  # 存储伤害值
            self._slam_target = player.pos.copy()
            # 预警特效
            ShockwaveRing.add(world.effects, player.pos.copy(), radius=60, color=(255, 50, 50), life=0.5)
            # 预警粒子
            for i in range(12):
                angle = i * (math.tau / 12)
                offset = player.pos + Vec(math.cos(angle), math.sin(angle)) * 50
                Particle.burst(world.effects, offset, count=2, speed=80, color=(255, 30, 30))
    
    def _do_melee_attack(self, world: "RoomManager", dir: Vec, dmg: int, radius: int):
        """执行近战攻击"""
        ev = DamageEvent(self.pos + dir * (self.radius + 10), radius, int(dmg), "enemy", self.attack_time, True)
        from .rooms import GlobalEvents
        GlobalEvents.add_event(ev)

        # 检测是否命中玩家
        player = world.player
        if (player.pos - ev.pos).length() <= (player.radius + ev.radius):
            outcome = player.on_hit_by_enemy(ev.damage, dir, ENEMY_TELEGRAPH, self.attack_time, True)
            if outcome == "hit":
                world.effects.shake.add(4.0, 0.15)
                world.effects.hitstop.trigger(0.1)
            elif outcome in ("blocked", "parry", "perfect_dodge"):
                world.effects.shake.add(2.0, 0.1)
                world.effects.hitstop.trigger(0.05)

    def _do_slam_attack(self, world: "RoomManager"):
        """执行区域猛击的延迟伤害"""
        if not hasattr(self, '_slam_target') or not hasattr(self, '_slam_damage'):
            return

        # 在目标位置生成伤害区域
        slam_pos = self._slam_target
        dmg = int(self._slam_damage)

        # 对范围内所有目标造成伤害
        player = world.player
        if (player.pos - slam_pos).length() <= 70:  # AOE 半径
            # 命中玩家
            dir = (player.pos - slam_pos)
            if dir.length_squared() > 0:
                dir = dir.normalize()
            outcome = player.on_hit_by_enemy(dmg, dir, ENEMY_TELEGRAPH, pg.time.get_ticks()/1000, False)  # 不可格挡
            if outcome == "hit":
                world.effects.shake.add(6.0, 0.3)
                world.effects.hitstop.trigger(0.15)
            elif outcome == "perfect_dodge":
                world.effects.shake.add(3.0, 0.15)

        # 猛击特效
        Explosion.add(world.effects, slam_pos, is_elite=True)
        ShockwaveRing.add(world.effects, slam_pos, radius=70, color=(255, 100, 100), life=0.5)
        Particle.burst(world.effects, slam_pos, count=35, speed=280, color=(255, 80, 80))

        # 清除存储
        delattr(self, '_slam_target')
        delattr(self, '_slam_damage')
    
    def _shoot_projectile(self, world: "RoomManager", dir: Vec):
        """发射 Boss 投射物"""
        speed = 250
        # 发射 3 个呈扇形分布的投射物
        for angle_offset in [-30, 0, 30]:
            import math
            rad = math.radians(angle_offset)
            rotated_dir = Vec(
                dir.x * math.cos(rad) - dir.y * math.sin(rad),
                dir.x * math.sin(rad) + dir.y * math.cos(rad)
            )
            vel = rotated_dir * speed
            proj = Projectile(self.pos.copy(), vel, 8, int(ENEMY_ATTACK_DAMAGE * 1.2), life=3.0, owner="enemy")
            world.projectiles.append(proj)

    def _on_phase_change(self, world: "RoomManager"):
        """阶段转换时的特效"""
        # 屏幕震动
        world.effects.shake.add(5.0, 0.3)
        # 爆炸特效
        Explosion.add(world.effects, self.pos.copy(), is_elite=True)
        # 生成粒子爆发
        Particle.burst(world.effects, self.pos.copy(), count=40, speed=300, color=(255, 100, 100))
        # 根据阶段播放不同效果
        if self.phase == 2:
            # 进入 P2：冲击波
            ShockwaveRing.add(world.effects, self.pos.copy(), radius=150, color=(255, 80, 80), life=0.5)
        elif self.phase == 3:
            # 进入 P3：多重冲击波 + 子弹时间
            ShockwaveRing.add(world.effects, self.pos.copy(), radius=200, color=(255, 50, 50), life=0.6)
            ShockwaveRing.add(world.effects, self.pos.copy(), radius=100, color=(255, 100, 100), life=0.4)
            # 短暂子弹时间
            player = world.player
            player._slowmo = 0.5  # 0.5 秒子弹时间

    def on_damage(self, damage: int, world: "RoomManager"):
        """Boss 受击时的特效"""
        self.hurt_flash = 0.1
        # 小概率触发受击停顿
        if random.random() < 0.3:
            world.effects.hitstop.trigger(0.03)
        # 阶段转换时不触发受击特效
        if self.phase_changed:
            return
        # 受击粒子
        Particle.burst(world.effects, self.pos.copy(), count=6, speed=150, color=(255, 150, 150))
    
    def draw(self, surf: pg.Surface):
        # 绘制 Boss 光环效果（P3 阶段）
        if self.phase == 3 and self.aura_timer > 0:
            aura_alpha = int(100 * (self.aura_timer / 0.5))
            aura_surf = pg.Surface((self.radius * 4, self.radius * 4), pg.SRCALPHA)
            pg.draw.circle(aura_surf, (255, 50, 50, aura_alpha),
                          (aura_surf.get_width() // 2, aura_surf.get_height() // 2),
                          self.radius + 10, width=3)
            surf.blit(aura_surf, (self.pos.x - aura_surf.get_width() // 2,
                                  self.pos.y - aura_surf.get_height() // 2))

        # 尝试绘制 Boss 贴图
        drawn = False
        dir_frames = getattr(self, 'dir_frames', None)
        if dir_frames and isinstance(dir_frames, dict) and len(dir_frames) > 0:
            key = eight_way(self.facing)
            frames = dir_frames.get(key)
            if frames and len(frames) > 0:
                idx = int(self.anim_t * 6) % len(frames)
                img = frames[idx]
                surf.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))
                drawn = True

        if not drawn:
            frames = getattr(self, 'frames', None)
            if frames and len(frames) > 0:
                idx = int(self.anim_t * 6) % len(frames)
                img = frames[idx]
                surf.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))
                drawn = True

        if not drawn:
            # 无贴图时绘制红色大圆 + 阶段颜色
            if self.hurt_flash > 0:
                color = (255, 255, 255)  # 受击闪光
            elif self.phase == 3:
                color = (255, 50, 50)  # P3 红色
            elif self.phase == 2:
                color = (255, 100, 100)  # P2 橙色
            else:
                color = (255, 150, 150)  # P1 粉色
            pg.draw.circle(surf, color, self.pos, self.radius)

        # 受击闪光覆盖
        if self.hurt_flash > 0:
            hurt_surf = pg.Surface((self.radius * 2 + 10, self.radius * 2 + 10), pg.SRCALPHA)
            alpha = int(200 * (self.hurt_flash / 0.1))
            pg.draw.circle(hurt_surf, (255, 255, 255, alpha),
                          (hurt_surf.get_width() // 2, hurt_surf.get_height() // 2),
                          self.radius + 5)
            surf.blit(hurt_surf, (self.pos.x - hurt_surf.get_width() // 2,
                                  self.pos.y - hurt_surf.get_height() // 2))

        # 显示 Boss 血条
        self._draw_boss_hp_bar(surf)

        # 攻击预警效果
        if self.state == "telegraph":
            if self.attack_pattern == "area_slam":
                # 区域猛击：显示 AOE 范围
                if self.slam_aoe_pos:
                    slam_surf = pg.Surface((160, 160), pg.SRCALPHA)
                    pg.draw.circle(slam_surf, (255, 0, 0, 80), (80, 80), 60, width=4)
                    pg.draw.circle(slam_surf, (255, 50, 50, 40), (80, 80), 60)
                    surf.blit(slam_surf, (self.slam_aoe_pos[0] - 80, self.slam_aoe_pos[1] - 80))
            else:
                # 其他攻击：显示预警圈
                col = TELEGRAPH_UNBLOCKABLE_COLOR if self.attack_pattern in ("charge", "area_slam") else TELEGRAPH_COLOR
                pg.draw.circle(surf, col, self.pos, self.radius + 15, 3)

        # 冲锋轨迹特效
        if self.attack_pattern == "charge" and self.state == "attack":
            trail_surf = pg.Surface((80, 40), pg.SRCALPHA)
            pg.draw.ellipse(trail_surf, (255, 100, 100, 150), (0, 0, 80, 40))
            angle = math.degrees(math.atan2(self.facing.y, self.facing.x))
            rotated = pg.transform.rotate(trail_surf, -angle)
            rect = rotated.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(rotated, rect)
    
    def _draw_boss_hp_bar(self, surf: pg.Surface):
        """绘制 Boss 血条"""
        hp_width = 160
        hp_height = 10
        hp_frac = max(0, self.hp / self.hp_max)

        x = self.pos.x - hp_width // 2
        y = self.pos.y - self.radius - 25

        # 背景
        pg.draw.rect(surf, (60, 30, 30), (x - 2, y - 2, hp_width + 4, hp_height + 4), border_radius=6)
        pg.draw.rect(surf, (40, 20, 20), (x, y, hp_width, hp_height), border_radius=4)

        # 血量 - 根据阶段变化颜色
        if self.phase == 3:
            hp_color = (255, 30, 30)  # P3 红色
        elif self.phase == 2:
            hp_color = (255, 80, 80)  # P2 橙色
        else:
            hp_color = (255, 120, 120)  # P1 粉色

        # 血条渐变效果
        hp_w = int(hp_width * hp_frac)
        if hp_w > 0:
            pg.draw.rect(surf, hp_color, (x, y, hp_w, hp_height), border_radius=4)
            # 高光
            pg.draw.rect(surf, (255, 200, 200), (x, y, hp_w, hp_height // 3), border_radius=2)

        # 边框
        pg.draw.rect(surf, (255, 180, 180), (x, y, hp_width, hp_height), 2, border_radius=4)

        # 阶段指示器
        phase_colors = {1: (255, 150, 150), 2: (255, 100, 100), 3: (255, 50, 50)}
        for i in range(3):
            px = x + hp_width + 8 + i * 12
            py = y + hp_height // 2 - 4
            color = phase_colors.get(i + 1, (100, 100, 100))
            if i + 1 <= self.phase:
                pg.draw.circle(surf, color, (px, py), 5)
                pg.draw.circle(surf, (255, 255, 255), (px, py), 5, width=1)
            else:
                pg.draw.circle(surf, (80, 80, 80), (px, py), 5)

    def on_death(self, world: "RoomManager"):
        """Boss 死亡特效"""
        # 大型爆炸
        Explosion.add(world.effects, self.pos.copy(), is_elite=True)
        # 多重粒子爆发
        Particle.burst(world.effects, self.pos.copy(), count=50, speed=350, color=(255, 100, 100))
        Particle.burst(world.effects, self.pos.copy(), count=30, speed=280, color=(255, 200, 100))
        # 冲击波
        ShockwaveRing.add(world.effects, self.pos.copy(), radius=200, color=(255, 150, 150), life=0.8)
        ShockwaveRing.add(world.effects, self.pos.copy(), radius=150, color=(255, 100, 100), life=0.6)
        # 屏幕震动
        world.effects.shake.add(8.0, 0.5)
        # 命中停顿
        world.effects.hitstop.trigger(0.2)
        # 漂浮文字
        world.effects.text.add("BOSS DEFEATED!", self.pos.copy(), color=(255, 200, 100))
