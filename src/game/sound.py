from __future__ import annotations

import os
from typing import Optional, Dict

import pygame as pg


class Sound:
    def __init__(self):
        self.sounds: Dict[str, Optional[pg.mixer.Sound]] = {}
        self.initialized = False

    def init(self):
        if self.initialized:
            return
        try:
            pg.mixer.init()
        except Exception:
            # 无窗口/无声卡环境使用 dummy 驱动
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
            try:
                pg.mixer.init()
            except Exception:
                pass
        self.initialized = True
        self._load_optional()

    def _load_optional(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sfx"))
        def load(name):
            path = os.path.join(root, f"{name}.wav")
            if os.path.isfile(path):
                try:
                    self.sounds[name] = pg.mixer.Sound(path)
                except Exception:
                    self.sounds[name] = None
            else:
                self.sounds[name] = None
        for n in ("slash", "shockwave", "hit", "death"):
            load(n)

    def play(self, name: str, volume: float = 0.5):
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.set_volume(max(0.0, min(1.0, volume)))
                snd.play()
            except Exception:
                pass


_mgr: Optional[Sound] = None


def init():
    get().init()


def get() -> Sound:
    global _mgr
    if _mgr is None:
        _mgr = Sound()
    return _mgr
