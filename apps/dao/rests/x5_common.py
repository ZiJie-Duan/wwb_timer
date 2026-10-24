"""x5 道观日常：共用零件——小道士（可摆姿势的人偶）、抖动填充、事件计时。

小道士 daoshi()：侧身，头顶发髻插簪，交领道袍（抖动灰度），宽袖。手的位置由场景直接给（绝对坐标），
肘部用两段式 IK 自动算。f=1 面朝右，f=-1 面朝左。脚底在 (x, gy)。
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw

from ..engine.anim import clamp, rand
from ..engine.gfx import BAYER, Gfx, H, W

# ---------------------------------------------------------------- 抖动填充（只在包围盒里做，便宜）

_PATS: dict[int, Image.Image] = {}


def _pat(level: float) -> Image.Image:
    k = int(round(clamp(level) * 16))
    if k not in _PATS:
        _PATS[k] = Image.fromarray(BAYER < k)
    return _PATS[k]


def dpoly(g: Gfx, pts, level: float, outline: int | None = 1):
    """多边形：内部清空后填抖动灰度（level 0..1），可带轮廓。比 g.shade_poly 便宜（不转整屏）"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = max(int(min(xs)) - 1, 0), max(int(min(ys)) - 1, 0)
    x1, y1 = min(int(max(xs)) + 2, W), min(int(max(ys)) + 2, H)
    if x1 <= x0 or y1 <= y0:
        return
    m = Image.new("1", (x1 - x0, y1 - y0))
    ImageDraw.Draw(m).polygon([(px - x0, py - y0) for px, py in pts], fill=1)
    g.img.paste(0, (x0, y0), m)
    if level > 0:
        g.img.paste(1, (x0, y0), ImageChops.logical_and(m, _pat(level).crop((x0, y0, x1, y1))))
    if outline is not None:
        g.d.polygon(pts, outline=outline)


def dbox(g: Gfx, box, level: float):
    """矩形抖动填充（只画亮点）"""
    x0, y0, x1, y1 = (int(v) for v in box)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0 or level <= 0:
        return
    g.img.paste(1, (x0, y0), _pat(level).crop((x0, y0, x1, y1)))


def dellipse(g: Gfx, box, level: float, outline: int | None = 1):
    x0, y0, x1, y1 = box
    n = 16
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    pts = [(cx + math.cos(i / n * 2 * math.pi) * rx, cy + math.sin(i / n * 2 * math.pi) * ry) for i in range(n)]
    dpoly(g, pts, level, None)
    if outline is not None:
        g.d.ellipse(box, outline=outline)


def fade_box(g: Gfx, level: float, box=None):
    """g.fade 的包装（level≥1 不做事）"""
    if level < 1:
        g.fade(max(level, 0), box)


# ---------------------------------------------------------------- 时间

def phase(t: float, period: float) -> tuple[int, float]:
    """→ (第几轮, 本轮内秒数)"""
    n = int(t // period)
    return n, t - n * period


def event(t: float, period: float, dur: float, seed: int, jitter: float = 0.35, skip: float = 0.0):
    """每隔约 period 秒发生一次、持续 dur 秒的小事件（确定性）。
    返回 (第几次, 事件内秒数) 或 None。jitter：开始时刻在一轮里浮动的比例；skip：这一轮不发生的概率"""
    n, k = phase(t, period)
    if rand(n * 7 + 3, seed) < skip:
        return None
    start = period * (1 - jitter) * 0.5 + rand(n, seed) * period * jitter
    start = min(start, period - dur)
    if n == 0:
        start = max(start, min(period * 0.35, period - dur))  # 第一轮别太早
    if start <= k < start + dur:
        return n, k - start
    return None


# ---------------------------------------------------------------- 小道士

def _ik(sx, sy, hx, hy, l1, l2, bend):
    """两段臂：肩 (sx,sy)、手 (hx,hy) → 肘；bend=±1 选弯向"""
    dx, dy = hx - sx, hy - sy
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return sx, sy + l1, hx, hy
    if d > l1 + l2 - 0.01:  # 够不着：手拉到最远
        k = (l1 + l2 - 0.01) / d
        hx, hy = sx + dx * k, sy + dy * k
        dx, dy, d = hx - sx, hy - sy, l1 + l2 - 0.01
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0))
    mx, my = sx + dx * a / d, sy + dy * a / d
    ex, ey = mx - dy / d * h * bend, my + dx / d * h * bend
    return ex, ey, hx, hy


def _sleeve(g: Gfx, sx, sy, ex, ey, hx, hy, s, level, cuff=True):
    """宽袖：肩→肘→腕，袖口下垂"""
    def nrm(ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        d = math.hypot(dx, dy) or 1
        return -dy / d, dx / d

    n1 = nrm(sx, sy, ex, ey)
    n2 = nrm(ex, ey, hx, hy)
    if n1[1] < 0:
        n1 = (-n1[0], -n1[1])
    if n2[1] < 0:  # 让法线朝下（袖子往下垂）
        n2 = (-n2[0], -n2[1])
    w0, w1, w2 = 1.6 * s, 1.8 * s, 2.0 * s
    drop = (3.2 if cuff else 1.8) * s
    # 腕处往回缩一点（袖口在手前）
    dx, dy = hx - ex, hy - ey
    d = math.hypot(dx, dy) or 1
    cx, cy = hx - dx / d * 1.5 * s, hy - dy / d * 1.5 * s
    pts = [(sx - n1[0] * w0, sy - n1[1] * w0), (ex - n2[0] * w1, ey - n2[1] * w1), (cx - n2[0] * w1, cy - n2[1] * w1),
           (cx + n2[0] * (w2 + drop), cy + n2[1] * (w2 + drop) + drop * 0.4),
           (ex + n2[0] * w2, ey + n2[1] * w2 + drop * 0.3), (sx + n1[0] * w0, sy + n1[1] * w0)]
    dpoly(g, pts, level, 0 if level >= 1 else 1)
    g.d.rectangle((hx - s * 0.8, hy - s * 0.8, hx + s * 0.8, hy + s * 0.8), fill=1)


class Pose:
    """daoshi() 返回的关键点，方便场景把工具挂在手上 / 头上"""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def daoshi(g: Gfx, x: float, gy: float, f: int = 1, hands=None, lean: float = 0.0, crouch: float = 0.0,
           step: float | None = None, s: float = 1.0, level: float = 1.0, bend=(1, 1), head_dy: float = 0.0,
           eye: str = "open", look: float = 0.0, sit: bool = False, draw_far: bool = True,
           draw_near: bool = True) -> Pose:
    """小道士。hands = [(近手x,y), (远手x,y)] 绝对坐标，None 为自然下垂。
    lean：上身前倾像素（朝 f）；crouch 0..1 下蹲；step：走路相位（弧度）；sit：盘坐 / 坐小凳（不画脚）
    eye：open / closed / x（被烟呛）；look：头抬（负）低（正）"""
    lx = lean * f
    hem_y = gy - 1
    sy = gy - (21 - 6 * crouch) * s
    sx = x + lx
    hcx, hcy = sx + f * 0.8 * s, sy - (4.8 - head_dy) * s + look * s
    r = 4.0 * s
    # 两肩、默认手
    near_s = (sx + f * 0.6 * s, sy + 1.6 * s)
    far_s = (sx - f * 0.8 * s, sy + 1.4 * s)
    if hands is None:
        hands = [None, None]
    hn = hands[0] or (near_s[0] + f * 1.5 * s, near_s[1] + 11 * s)
    hf = hands[1] or (far_s[0] - f * 0.5 * s, far_s[1] + 11 * s)
    l1, l2 = 6.2 * s, 6.0 * s
    # 远臂（在身后）
    if draw_far:
        e = _ik(*far_s, *hf, l1, l2, bend[1] * -f)
        _sleeve(g, *far_s, *e, s, 0.5)
    # 脚
    hw = (6.0 + 3.0 * crouch) * s
    if not sit:
        if step is None:
            fa, fb = 2.0, -2.0
            la = lb = 0.0
        else:
            fa, fb = 3.0 * math.sin(step), -3.0 * math.sin(step)
            la, lb = max(0, math.cos(step)) * 1.5, max(0, -math.cos(step)) * 1.5
        for off, lift in ((fb, lb), (fa, la)):
            fx = x + f * off * s
            g.d.rectangle((fx - (1 if f > 0 else 2) * s, gy - 1 * s - lift, fx + (2 if f > 0 else 1) * s, gy - lift),
                          fill=1)
    # 道袍
    wy = sy + (9.5 - 2.5 * crouch) * s  # 腰
    robe = [(sx - 3.4 * s, sy), (sx + 3.4 * s, sy), (x + lx * 0.3 + hw, hem_y - 1 * s), (x + lx * 0.3 - hw, hem_y - 1 * s)]
    if sit:
        robe = [(sx - 3.4 * s, sy), (sx + 3.4 * s, sy), (x + hw + 2 * s, hem_y), (x - hw - 2 * s, hem_y)]
    dpoly(g, robe, level)
    # 腰带
    k = (wy - sy) / max(hem_y - sy, 1)
    wl = lerp_pt(robe[0], robe[3], k)
    wr = lerp_pt(robe[1], robe[2], k)
    ink = 0 if level >= 0.5 else 1
    g.d.line((wl[0] + 1, wy, wr[0] - 1, wy), fill=ink)
    g.d.line((sx - f * 1.5 * s, wy, sx - f * 2.5 * s, wy + 4 * s), fill=ink)  # 带尾
    # 交领
    g.d.line((sx - f * 2.2 * s, sy, sx + f * 1.6 * s, sy + 4.5 * s), fill=ink)
    # 衣摆下缘一道镶边
    g.d.line((robe[3][0] + 1, robe[3][1] - 2 * s, robe[2][0] - 1, robe[2][1] - 2 * s), fill=ink)
    # 头：脸挖空 + 后脑头发 + 发髻 + 簪
    g.d.ellipse((hcx - r, hcy - r, hcx + r, hcy + r), fill=0, outline=1)
    g.d.chord((hcx - r, hcy - r, hcx + r, hcy + r), 195, 345, fill=1)  # 头发梳上去：头顶一片
    # 后脑整片头发（面朝右时左半边）
    if f > 0:
        g.d.rectangle((hcx - r, hcy - r * 0.2, hcx - r * 0.35, hcy + r * 0.5), fill=1)
    else:
        g.d.rectangle((hcx + r * 0.35, hcy - r * 0.2, hcx + r, hcy + r * 0.5), fill=1)
    g.d.ellipse((hcx - r, hcy - r, hcx + r, hcy + r), outline=1)
    bx, by = hcx - f * 0.6 * s, hcy - r - 1.2 * s
    g.d.ellipse((bx - 1.6 * s, by - 1.6 * s, bx + 1.6 * s, by + 1.4 * s), fill=1)
    g.d.line((bx - f * 3.2 * s, by + 0.2 * s, bx + f * 2.6 * s, by - 0.6 * s), fill=1)  # 簪
    # 眼
    ex_, ey_ = hcx + f * 1.6 * s, hcy + 0.2 * s
    if eye == "open":
        g.d.rectangle((ex_, ey_, ex_ + (s > 1.4) * s * 0.6, ey_ + (s > 1.4) * s * 0.6), fill=1)
    elif eye == "closed":
        g.d.line((ex_ - f * 0.8 * s, ey_, ex_ + f * 0.6 * s, ey_), fill=1)
    elif eye == "x":
        g.d.line((ex_ - 1, ey_ - 1, ex_ + 1, ey_ + 1), fill=1)
        g.d.line((ex_ - 1, ey_ + 1, ex_ + 1, ey_ - 1), fill=1)
    # 近臂
    pose = Pose(x=x, gy=gy, f=f, sx=sx, sy=sy, head=(hcx, hcy), r=r, near=hn, far=hf, bun=(bx, by), waist=wy,
                near_s=near_s, s=s, level=level, bend=bend[0] * -f)
    if draw_near:
        pose.near = near_arm(g, pose, hn)
    return pose


def near_arm(g: Gfx, pose: Pose, hand) -> tuple:
    """单独画近手臂（比如手要压在别的东西上面时，先画人、再画东西、最后画手臂）"""
    l1, l2 = 6.2 * pose.s, 6.0 * pose.s
    e = _ik(*pose.near_s, *hand, l1, l2, pose.bend)
    _sleeve(g, *pose.near_s, *e, pose.s, pose.level)
    return e[2:]


def lerp_pt(a, b, k):
    return a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k


# ---------------------------------------------------------------- 小零件

def sweat(g: Gfx, x: float, y: float, k: float):
    """一滴汗：k 0..1 甩出去"""
    if 0 <= k < 1:
        xx, yy = x + k * 5, y - 2 + k * k * 8
        g.d.polygon([(xx, yy - 2), (xx - 1, yy), (xx + 1, yy)], fill=1)


def note(g: Gfx, x: float, y: float):
    """哼歌的小音符"""
    g.d.line((x + 2, y, x + 2, y + 4), fill=1)
    g.d.rectangle((x, y + 4, x + 2, y + 5), fill=1)
    g.d.line((x + 2, y, x + 4, y + 1), fill=1)


def bubble(g: Gfx, x: float, y: float, s: str, size: int = 12):
    """小对话框（右下角有尾巴），(x, y) 为框左上角"""
    from ..engine.gfx import text_width
    w = text_width(s, size) + 4
    hh = (11 if size == 12 else 7) + 4
    g.d.rectangle((x, y, x + w, y + hh), fill=0, outline=1)
    g.d.polygon([(x + 3, y + hh), (x + 7, y + hh), (x + 2, y + hh + 4)], fill=0, outline=1)
    g.d.line((x + 4, y + hh, x + 6, y + hh), fill=0)
    g.text(x + 2, y + 2, s, size)


def ground(g: Gfx, gy: int, seed: int = 0, x0: int = 0, x1: int = 128, tufts: int = 6):
    g.d.line((x0, gy, x1 - 1, gy), fill=1)
    for i in range(tufts):
        x = x0 + rand(i, seed) * (x1 - x0)
        g.d.line((x, gy + 2, x + 2, gy + 2), fill=1)
