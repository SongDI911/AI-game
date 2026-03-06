import numpy as np

# 给定的关键采样点（示例数据结构）
# 你需要把实际的点按“截面段”为不同的段落放入
# 下面示例仅展示数据结构，需你填写实际点
bottle_points = {
    "neck_opening": [  # 瓶口采样点，z 维度可取固定的关键点对应的多组点
        # (x, y, z) 例：若你提供的是 3D 坐标，直接填写；若只有 x,y，需添加对应的 z
        (9.094563, 0.2, 0.0)  # 示例
    ],
    "body_upper_arc1": [
        (0.139249, 0.0, 0.839161),
        # 继续添加 ... 需要你填充
    ],
    "body_upper_arc2": [
        (0.161994, 0.0, 0.817953),
        # ...
    ],
    "body_upper_arc3": [
        (0.182925, 0.0, 0.77579),
        # ...
    ],
    "body_upper_arc_end": [
        (0.193856, 0.0, 0.719015),
    ],
    "body_lower_arc_end": [
        (0.193856, 9.0, 0.98003),
    ],
    "bottom_arc2": [
        (0.186585, 9.0, 0.053227),
    ],
    "bottom_arc1": [
        (9.166719, 0.0, 0.033606),
    ],
    "bottom_opening": [
        # 最后一个点集
        (0.139582, 0.0, 0.026424),
    ]
}

def interpolate_segment(pnts, z_target):
    """
    对一个点集 pnts（按轮廓顺序排列的点）在给定 z_target 处进行线性插值，
    结果为该段在 z_target 的 x,y 坐标点序列。
    pnts: list of (x,y,z)
    z_target: float
    返回：list[(x,y)]
    """
    pts = np.array(pnts)
    xs, ys, zs = pts[:,0], pts[:,1], pts[:,2]

    # 如果只有一个点，直接返回该点在该 z 的投影
    if len(pts) == 1:
        return [(xs[0], ys[0])]

    # 需要确保 z 的序列单调以便分段插值
    order = np.argsort(zs)
    zs, xs, ys = zs[order], xs[order], ys[order]

    # 找到所有跨越 z_target 的线性段
    result = []
    for i in range(len(zs) - 1):
        z0, z1 = zs[i], zs[i+1]
        if z0 == z1:
            continue
        if (z_target < min(z0, z1)) or (z_target > max(z0, z1)):
            continue
        t = (z_target - z0) / (z1 - z0)
        x = xs[i] + t * (xs[i+1] - xs[i])
        y = ys[i] + t * (ys[i+1] - ys[i])
        result.append((float(x), float(y)))
    # 去重并尽量保持顺序
    # 如果目标高度正好等于某些点的 z，还可直接包括那些点
    return result

def generate_bottle_cross_section(z_target, bottle_points):
    """
    根据分段点集合，在目标 z 高度处生成横截面轮廓点序列。
    返回一个轮廓点列表，形如 [(x1,y1), (x2,y2), ...]
    """
    contour = []
    # 遍历每一段，并将其在目标 z 处的点收集到 contour
    for seg_key in bottle_points:
        seg_pts = bottle_points[seg_key]
        seg_points_2d = interpolate_segment(seg_pts, z_target)  # 每段得到若干点
        contour.extend(seg_points_2d)

    # 可选：对轮廓点进行简化或顺序整理，确保闭合（若需要）：
    # 这里提供一个简单的闭合策略：若首尾点距离近则视为闭合
    if len(contour) >= 3:
        first = contour[0]
        last = contour[-1]
        if np.hypot(first[0]-last[0], first[1]-last[1]) > 1e-6:
            contour.append(first)  # 闭合

    return contour

# 示例用法
if __name__ == "__main__":
    z_target = 0.5  # 例如你需要的高度
    contour = generate_bottle_cross_section(z_target, bottle_points)
    print("Cross-section contour at z =", z_target)
    for p in contour:
        print(p)
