"""拼图游戏测试脚本"""
import pygame as pg
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.minigames.puzzle import PuzzleGame, PuzzleTile
from game.config import WIDTH, HEIGHT


def test_puzzle_tile():
    """测试拼图方块类"""
    print("测试 PuzzleTile 类...")
    
    # 创建测试方块
    tile = PuzzleTile(
        x=100, y=100, size=100,
        correct_pos=(100, 100),
        image=None,
        number=1,
        source_row=0, source_col=0,
        start_x=64, start_y=48
    )
    
    # 测试 is_in_correct_place
    assert tile.is_in_correct_place(), "方块应该在正确位置"
    
    # 移动方块后测试
    tile.x = 200
    tile.y = 200
    assert not tile.is_in_correct_place(), "方块不在正确位置"
    
    print("✓ PuzzleTile 测试通过")
    return True


def test_puzzle_generation():
    """测试拼图生成逻辑"""
    print("测试拼图生成...")
    
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    
    # 创建拼图游戏
    puzzle = PuzzleGame(level=1)
    
    # 检查方块数量
    expected_tiles = puzzle.grid_size * puzzle.grid_size
    assert len(puzzle.tiles) == expected_tiles, f"应该有{expected_tiles}个方块"
    
    # 检查每个方块的属性
    for i, tile in enumerate(puzzle.tiles):
        assert tile.source_row >= 0 and tile.source_row < puzzle.grid_size
        assert tile.source_col >= 0 and tile.source_col < puzzle.grid_size
        assert tile.number == tile.source_row * puzzle.grid_size + tile.source_col + 1
    
    print(f"✓ 拼图生成测试通过 (grid_size={puzzle.grid_size}, tiles={len(puzzle.tiles)})")
    
    pg.quit()
    return True


def test_puzzle_completion():
    """测试拼图完成检测"""
    print("测试拼图完成检测...")
    
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    
    # 创建拼图游戏
    puzzle = PuzzleGame(level=1)
    
    # 初始状态应该未完成
    assert not puzzle.completed, "初始状态应该未完成"
    
    # 将所有方块归位
    for tile in puzzle.tiles:
        # 计算该方块应该在的位置
        target_x = puzzle.start_x + tile.source_col * puzzle.tile_size
        target_y = puzzle.start_y + tile.source_row * puzzle.tile_size
        tile.x = target_x
        tile.y = target_y
        tile.in_correct_place = tile.is_in_correct_place()
    
    # 检查完成状态
    completed = puzzle._check_completed()
    assert completed, "所有方块归位后应该完成"
    
    print("✓ 拼图完成检测测试通过")
    
    pg.quit()
    return True


def test_puzzle_swap():
    """测试方块交换逻辑"""
    print("测试方块交换...")
    
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    
    # 创建拼图游戏
    puzzle = PuzzleGame(level=1)
    
    # 获取前两个方块
    tile1 = puzzle.tiles[0]
    tile2 = puzzle.tiles[1]
    
    # 记录原始位置
    orig_x1, orig_y1 = tile1.x, tile1.y
    orig_x2, orig_y2 = tile2.x, tile2.y
    
    # 交换
    puzzle._swap_tiles(tile1, tile2)
    
    # 验证位置交换
    assert tile1.x == orig_x2 and tile1.y == orig_y2, "tile1 位置应该交换"
    assert tile2.x == orig_x1 and tile2.y == orig_y1, "tile2 位置应该交换"
    
    # 验证 moves 增加
    assert puzzle.moves == 1, "moves 应该为 1"
    
    print("✓ 方块交换测试通过")
    
    pg.quit()
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("拼图游戏测试")
    print("=" * 50)
    
    tests = [
        ("方块类测试", test_puzzle_tile),
        ("拼图生成测试", test_puzzle_generation),
        ("完成检测测试", test_puzzle_completion),
        ("交换逻辑测试", test_puzzle_swap),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"✗ {name} 失败：{e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name} 错误：{e}")
            failed += 1
    
    print("=" * 50)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 50)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
