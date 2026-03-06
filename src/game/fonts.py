from __future__ import annotations

import os
import glob
from functools import lru_cache
from typing import Optional

import pygame as pg


PREFERRED_FONTS = [
    # macOS
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    "Songti SC",
    "STHeiti",
    "STSong",
    # Windows
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    # Linux / cross-platform
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    "Source Han Sans CN",
    "Source Han Sans SC",
]


SEARCH_DIRS = [
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/usr/share/fonts/truetype",
    "C:/Windows/Fonts",
]


def _match_font_by_name(name: str) -> Optional[str]:
    try:
        path = pg.font.match_font(name)
        return path
    except Exception:
        return None


def _search_files(patterns):
    for d in SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        for pat in patterns:
            for p in glob.glob(os.path.join(d, pat)):
                if os.path.isfile(p):
                    return p
    return None


def _match_font_by_files() -> Optional[str]:
    # Try to find known Chinese-capable font files directly
    patterns = [
        "*PingFang*.ttf", "*PingFang*.otf",
        "*HiraginoSansGB*.ttf", "*Hiragino*.otf",
        "*Heiti*.ttf", "*Heiti*.otf",
        "*Song*.ttf", "*Song*.otf", "*STSong*.ttf", "*STSong*.otf",
        "*YaHei*.ttf", "*YaHei*.otf",
        "*SimHei*.ttf", "*SimSun*.ttf",
        "*NotoSansCJK*.ttf", "*Noto*.otf",
        "*SourceHanSans*.otf", "*SourceHanSans*.ttf",
        "*WenQuanYi*.ttf",
    ]
    return _search_files(patterns)


@lru_cache(maxsize=None)
def get_font(size: int) -> pg.font.Font:
    # 1) Try by family names
    for name in PREFERRED_FONTS:
        path = _match_font_by_name(name)
        if path:
            try:
                return pg.font.Font(path, size)
            except Exception:
                continue

    # 2) Try by searching known font files in system dirs
    path = _match_font_by_files()
    if path:
        try:
            return pg.font.Font(path, size)
        except Exception:
            pass

    # 3) Fall back to default font (may not fully support CJK but prevents crash)
    return pg.font.SysFont(None, size)

