# 关卡与小游戏系统

## 概述

游戏现在采用关卡（Chapter）制度，每 5 个房间为一个关卡，包含：
- 4 个普通房间
- 1 个 Boss 房间（第 5 个房间）

完成一个关卡后，玩家需要完成一个小游戏挑战才能进入下一关卡。

## 游戏流程

```
主菜单 → 教程 → 游戏开始
    ↓
房间战斗 → 清理完成 → 奖励选择
    ↓
下一个房间 → ... → Boss 房间
    ↓
关卡完成 → 过渡界面 → 小游戏挑战
    ↓
小游戏完成 → 下一关卡
```

## 新增文件

### 核心模块

- [`src/game/level_manager.py`](src/game/level_manager.py) - 关卡管理器
  - 跟踪当前关卡进度
  - 管理小游戏状态
  - 处理关卡过渡

### 小游戏模块

- [`src/game/minigames/__init__.py`](src/game/minigames/__init__.py) - 小游戏模块入口
- [`src/game/minigames/base.py`](src/game/minigames/base.py) - 小游戏基类
- [`src/game/minigames/puzzle.py`](src/game/minigames/puzzle.py) - 拼图小游戏
- [`src/game/minigames/transition.py`](src/game/minigames/transition.py) - 关卡过渡界面

### 修改文件

- [`src/main.py`](src/main.py) - 添加小游戏状态和过渡逻辑
- [`src/game/ui.py`](src/game/ui.py) - HUD 显示关卡信息

## 小游戏类型

### 拼图游戏 (PuzzleGame)

- **目标**: 交换方块，还原完整图案
- **难度**: 随关卡增加（3x3 到 5x5 网格）
- **图案**: 彩色渐变背景 + 关卡数字
- **得分**: 基于移动次数和时间计算

#### 操作方式
1. 点击第一个方块选中（黄色边框）
2. 点击第二个方块交换位置
3. 所有方块归位后完成挑战

#### UI 元素
- 移动次数计数器
- 时间计时器
- 完成提示

## 关卡进度显示

HUD 现在显示：
- 当前关卡数（金色文字）
- 房间进度（X/5）

## 游戏状态

新增状态：
- `chapter_transition` - 关卡过渡界面
- `minigame` - 小游戏挑战

## 扩展新小游戏

要添加新的小游戏类型：

1. 创建新的小游戏类继承 `BaseMinigame`：

```python
from .base import BaseMinigame

class MyNewGame(BaseMinigame):
    def handle_event(self, event):
        # 处理输入
        return self.completed
    
    def update(self, dt):
        # 更新逻辑
        super().update(dt)
    
    def draw(self, surface):
        # 绘制游戏
        pass
    
    def get_score(self) -> int:
        # 计算得分
        return self.score
```

2. 在 `LevelManager` 中更新 `start_minigame()` 方法

## 存档系统

当前关卡进度不保存到存档（每局游戏从头开始）
存档保留：
- 最高房间数
- 总击杀数
- 游戏次数
- 教程完成状态
