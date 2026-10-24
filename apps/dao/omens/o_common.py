"""起卦共用（像素风）：场景基类、文字队列、卦牌（小卦象）、揭晓版式、小道士的自定义手臂、地面。

版式约定（所有起卦一致）：
    侧视小舞台，地面线 FLOOR=58，小道士站在左边（x≈20），道具在右边。
    起卦过程中已成之爻记在左上角的“卦牌”上（tally），点阵同步显示。
    揭晓（最后 REVEAL 秒）：一闪一震，大卦象一爻一爻砸下来（x 38–64），右边写卦名、第几卦，
    顶行打出卦辞摘句，下面一道虚线。地上的道具可以留着（只占 y ≥ 47）。

文字规则：所有字都经 self.say() 进队列，play() 最后 self.flush(g) 统一画（压在一切特效之上），
需要时先铺黑底板（plate=True），保证字的范围里没有别的亮点。
"""
from __future__ import annotations

from ..engine import pix
from ..engine.anim import clamp, ease_out, ease_out_back, span
from ..engine.chars import Part
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, text_width
from ..engine.scene import Omen
from ..engine.symbols import TRIGRAMS, changing, full_name, hexagram, mx_hexagram, yang
from .o_data import CI

FLOOR = 58
REVEAL = 2.0
YAO_NAME = {6: "老阴", 7: "少阳", 8: "少阴", 9: "老阳"}
YAO_NUM = {6: "六", 7: "七", 8: "八", 9: "九"}

# 揭晓版式
RHX, RHY, RHW, RHH, RHS = 38, 17, 26, 3, 5     # 大卦象：左、上爻顶、宽、爻厚、步距
RNX, RNY = 73, 18                              # 卦名
RCY = 2                                        # 卦辞（顶行）


def lines_of(upper: str, lower: str, moving: int = 0) -> list[int]:
    """上卦、下卦 → 6 爻（7/8）；moving = 1-6 时该爻为变爻（9/6）"""
    bits = TRIGRAMS[lower][2] + TRIGRAMS[upper][2]
    out = [7 if b else 8 for b in bits]
    if 1 <= moving <= 6:
        out[moving - 1] = 9 if out[moving - 1] == 7 else 6
    return out


def yao(g: Gfx, x: float, y: float, w: float, h: int, v, grow: float = 1.0, fill: int = 1):
    """一爻（grow 0..1 从中间向两边长出）。阴爻中间断开"""
    grow = clamp(grow)
    hw = w / 2 * grow
    if hw < 1:
        return
    cx = x + w / 2
    x0, x1 = int(round(cx - hw)), int(round(cx + hw)) - 1
    y = int(round(y))
    if yang(v):
        g.d.rectangle((x0, y, x1, y + h - 1), fill=fill)
    else:
        gap = max(2, int(w) // 5)
        g0, g1 = int(round(cx - gap / 2)), int(round(cx + gap / 2))
        if x0 < g0:
            g.d.rectangle((x0, y, g0 - 1, y + h - 1), fill=fill)
        if g1 <= x1:
            g.d.rectangle((g1, y, x1, y + h - 1), fill=fill)


# ---------------------------------------------------------------- 卦牌（左上角的小卦象）

def _tally_plate():
    """卦牌 19×24：挂绳、云头、双线边框"""
    p = Part(19, 25)
    p.shape("line", (9, 0, 9, 2), fill=1)
    p.shape("ellipse", (7, 0, 11, 3), fill=0)
    p.d.ellipse((7, 0, 11, 3), outline=1)
    p.shape("rectangle", (0, 3, 18, 24), fill=1)
    p.d.rectangle((1, 4, 17, 23), fill=0)
    p.d.rectangle((2, 5, 16, 22), outline=1)
    p.d.rectangle((3, 6, 15, 21), fill=0)
    for x, y in ((0, 3), (18, 3), (0, 24), (18, 24)):
        p.px(x, y, 0)
    return p.sprite()


_PL = {}


def tally(g: Gfx, lines, count: float, x: int = 2, y: int = 1, glint: float = -1.0):
    """左上角的卦牌：已成之爻（count 可为小数：正在长出的一爻）。glint ∈ [0,1) 时新爻闪一下"""
    if "t" not in _PL:
        _PL["t"] = _tally_plate()
    pix.blit(g, _PL["t"], x, y)
    n = int(count)
    for i in range(min(6, n + 1)):
        grow = 1.0 if i < n else ease_out_back(count - n)
        yy = y + 19 - i * 3
        yao(g, x + 4, yy, 11, 2, lines[i], grow)
        if i < n and changing(lines[i]):
            g.px(x + 16, yy)
    if 0 <= glint < 1 and n > 0:
        yy = y + 19 - (n - 1) * 3
        r = int(1 + glint * 3)
        sx = x + 16 + r
        for dx, dy in ((0, -r), (0, r), (-1, 0), (1, 0)):
            g.px(sx + dx, yy + dy)


# ---------------------------------------------------------------- 小道士的自定义手臂（朝右画，figure(arm=..., arm_at=...)）

def _arm_toss():
    """抛：手臂斜向前上方伸直，宽袖垂下；手在右上角"""
    p = Part(13, 13)
    p.shape("polygon", [(0, 9), (2, 12), (11, 3), (9, 1)], fill=1)        # 袖筒
    p.shape("polygon", [(2, 11), (7, 6), (7, 11), (4, 12)], fill=1)       # 垂袖
    p.d.line((7, 6, 7, 11), fill=0)
    p.dither([(3, 11), (7, 8), (7, 11), (4, 12)], 0.5, 0)
    p.shape("rectangle", (10, 0, 12, 2), fill=1)                          # 手
    p.px(12, 0, 0)
    spr = p.sprite()
    spr.hand = (11, 0)
    return spr


def _arm_hold():
    """托：小臂竖起、手在胸前偏上（托着签筒 / 举着东西）"""
    p = Part(11, 12)
    p.shape("polygon", [(0, 0), (4, 0), (8, 5), (8, 10), (3, 10), (0, 5)], fill=1)
    p.d.line((3, 10, 8, 10), fill=0)
    p.dither([(1, 6), (8, 6), (8, 9), (1, 9)], 0.5, 0)
    p.shape("rectangle", (7, 2, 10, 5), fill=1)
    p.d.line((8, 3, 10, 3), fill=0)
    spr = p.sprite()
    spr.hand = (9, 3)
    return spr


def _arm_reach():
    """斜向前下方伸手（拿长杆、点地、拾东西）"""
    p = Part(14, 10)
    p.shape("polygon", [(0, 0), (4, 0), (12, 6), (10, 9), (2, 6), (0, 4)], fill=1)
    p.d.line((9, 5, 8, 8), fill=0)
    p.dither([(2, 5), (9, 7), (8, 9), (2, 7)], 0.5, 0)
    p.shape("rectangle", (11, 6, 13, 9), fill=1)
    spr = p.sprite()
    spr.hand = (12, 8)
    return spr


def _arm_lift():
    """双手前伸上举（捧签筒、捧物过胸）"""
    p = Part(15, 10)
    p.shape("polygon", [(0, 3), (4, 2), (11, 0), (12, 4), (5, 8), (0, 8)], fill=1)
    p.d.line((10, 1, 11, 4), fill=0)
    p.dither([(1, 6), (8, 5), (5, 8), (1, 8)], 0.5, 0)
    p.shape("rectangle", (11, 0, 14, 3), fill=1)
    p.d.line((12, 1, 14, 1), fill=0)
    spr = p.sprite()
    spr.hand = (13, 1)
    return spr


ARMS = {}


def arm(name: str):
    """自定义手臂：toss 抛 / hold 托 / reach 前下伸 / lift 前伸上举。返回 (精灵, arm_at)"""
    if name not in ARMS:
        spr = {"toss": _arm_toss, "hold": _arm_hold, "reach": _arm_reach, "lift": _arm_lift}[name]()
        at = {"toss": (0, -27), "hold": (-3, -19), "reach": (-3, -16), "lift": (-3, -18)}[name]
        if name == "toss":
            spr.over_head = False
        ARMS[name] = (spr, at)
    return ARMS[name]


# ---------------------------------------------------------------- 地面与小件

def floor(g: Gfx, style: str = "stone", y: int = FLOOR, x0: int = 0, x1: int = 127):
    """地面：stone 石板（错缝）/ tile 方砖（斜线）/ earth 泥地（草丛）"""
    g.d.line((x0, y, x1, y), fill=1)
    if style == "tile":
        for x in range(-40, 168, 16):
            g.d.line((x, y + 1, x - 12, 63), fill=1)
        pix.checker(g, (x0, y + 1, x1 + 1, 64), 0.125)
    elif style == "stone":
        g.d.line((x0, y + 3, x1, y + 3), fill=1)
        for x in range(x0 + 6, x1, 20):
            g.d.line((x, y + 1, x, y + 2), fill=1)
            g.d.line((x + 10, y + 4, x + 10, 63), fill=1)
        pix.checker(g, (x0, y + 4, x1 + 1, 64), 0.125)
    else:
        pix.checker(g, (x0, y + 2, x1 + 1, 64), 0.125)
        for x in range(x0 + 3, x1, 13):
            g.px(x, y - 1), g.px(x + 2, y - 1), g.px(x + 1, y - 2)


def star4(g: Gfx, x: float, y: float, r: int = 2, v: int = 1):
    """四角小星（闪光点缀）"""
    x, y = int(round(x)), int(round(y))
    g.px(x, y, v)
    for k in range(1, r + 1):
        g.px(x + k, y, v), g.px(x - k, y, v), g.px(x, y + k, v), g.px(x, y - k, v)


def speed_lines(g: Gfx, x: float, y: float, side: int = 1, t: float = 0.0):
    """手边的“沙沙”声线：两三道小弧"""
    ph = int(t * 16) % 2
    for k in range(2):
        r = 3 + k * 2 + ph
        cx = x + side * (2 + k)
        for dy in (-1, 0, 1):
            g.px(cx + side * (r - abs(dy) * 1), y + dy * r * 0.6)


# ---------------------------------------------------------------- 基类

class Stage:
    """舞台工具（起卦与特殊场景共用）：dt、一次性事件、粒子、文字队列"""

    def stage_init(self):
        self.sparks = pix.Sparks(self.seed + 11)
        self.puffs = pix.Puffs(self.seed + 12)
        self.prev_t = None
        self.dt = 1 / 30
        self._pt = -1.0
        self._q: list = []

    def init(self):
        pass

    # ------------------------------------------------------------ 时间
    def tick(self, t: float):
        """每帧开头调用：算 dt；t 回退时清空粒子"""
        if self.prev_t is None or t < self.prev_t:
            self.dt = 1 / 30
            if self.prev_t is not None:
                self.sparks.p.clear(), self.puffs.p.clear()
            self._pt = -1.0
        else:
            self.dt = min(t - self.prev_t, 0.2)
            self._pt = self.prev_t
        self.prev_t = t
        self._q = []

    def hit(self, t: float, at: float) -> bool:
        """本帧是否刚越过时刻 at（一次性事件：落地、爆裂）"""
        return self._pt < at <= t

    # ------------------------------------------------------------ 粒子
    def particles(self, g: Gfx, wind: float = 0.0):
        self.puffs.step(self.dt, wind=wind)
        self.puffs.draw(g)
        self.sparks.step(self.dt)
        self.sparks.draw(g)

    def impact(self, g: Gfx, x: float, y: float, power: float = 1.0, dust: bool = True):
        """落地 / 击中：火星 + 两团尘 + 震屏"""
        self.sparks.burst(x, y, int(5 + 6 * power), 22 + 14 * power, up=14 * power, life=0.45, gravity=90)
        if dust:
            for s in (-1, 1):
                self.puffs.emit(x + s * 5, y - 1, vx=s * 10, vy=-4, life=0.5, rmax=0.9 + power * 0.4, spread=1)

    # ------------------------------------------------------------ 文字（队列，最后画）
    def say(self, x: float, y: float, s: str, size: int = 12, align: str = "left", plate: bool = True,
            frame: bool = False):
        self._q.append(("t", x, y, s, size, align, plate, frame))

    def say_v(self, x: float, y: float, s: str, size: int = 12, plate: bool = True):
        self._q.append(("v", x, y, s, size, plate))

    def clear(self, x0: float, y0: float, x1: float, y1: float):
        """进队列：在这里铺一块黑底（多段字共用一块底板）"""
        self._q.append(("box", x0, y0, x1, y1))

    def flush(self, g: Gfx):
        for it in self._q:
            if it[0] == "box":
                g.d.rectangle(it[1:], fill=0)
            elif it[0] == "t":
                _, x, y, s, size, align, plate, frame = it
                w = text_width(s, size)
                lx = x - w / 2 if align == "center" else x - w if align == "right" else x
                hh = 11 if size == 12 else 7
                if plate or frame:
                    g.d.rectangle((lx - 2, y - 2, lx + w + 1, y + hh + 1), fill=0)
                if frame:
                    g.d.rectangle((lx - 3, y - 3, lx + w + 2, y + hh + 2), outline=1)
                    g.d.rectangle((lx - 2, y - 2, lx + w + 1, y + hh + 1), outline=0)
                g.text(x, y, s, size=size, align=align)
            else:
                _, x, y, s, size, plate = it
                step = (11 if size == 12 else 7) + 1
                if plate:
                    g.d.rectangle((x - 1, y - 2, x + size, y + len(s) * step), fill=0)
                g.vtext(x, y, s, size=size)
        self._q = []

    def pop(self, cx: float, y: float, s: str, k: float, size: int = 12):
        """弹出的小标签（k = 出现后秒数）：带框，先放大再定住"""
        if k <= 0:
            return
        p = ease_out_back(span(k, 0, 0.16))
        yy = y + (1 - p) * 5
        self.say(cx, yy, s, size=size, align="center", frame=True)



class Base(Stage, Omen):
    """起卦基类：舞台工具 + 揭晓"""
    T = {"play": 7.0}

    def setup(self):
        Omen.setup(self)  # 默认三钱法；子类在 init() 里覆盖 self.lines
        self.stage_init()
        self.init()

    # ------------------------------------------------------------ 揭晓
    def reveal(self, g: Gfx, t: float, r0: float, hx: int = RHX, hy: int = RHY, nx: int = RNX, ny: int = RNY,
               ci_y: int = RCY, num: bool = True, slam: bool = True, vname: bool = False,
               mark: bool = True):
        """r0 = 揭晓开始的时刻。图形立即画，字进队列"""
        k = t - r0
        lines = self.lines
        n, name, up, lo = hexagram(lines)
        if self.hit(t, r0):  # 揭晓的那一帧
            pix.flash(g)
        if k < 0.3:
            pix.shake(g, k, 1.5 * (1 - k / 0.3))
        land = []
        for i in range(6):
            a = 0.08 + i * 0.075
            q = span(k, a, a + 0.12)
            if q <= 0:
                continue
            yy = hy + (5 - i) * RHS
            if slam and q < 1:  # 从上方砸下，越落越窄
                drop = (1 - ease_out(q)) * 10
                wide = RHW + (1 - q) * 4
                yao(g, hx - (wide - RHW) / 2, yy - drop, wide, RHH, lines[i])
            else:
                yao(g, hx, yy, RHW, RHH, lines[i])
            if self.hit(t, r0 + a + 0.12):
                land.append(yy)
            if mark and q >= 1 and changing(lines[i]) and int(k * 4) % 2 == 0:  # 变爻：右侧一个小菱形闪
                cx, cy = hx + RHW + 3, yy + 1
                g.px(cx, cy - 1), g.px(cx - 1, cy), g.px(cx + 1, cy), g.px(cx, cy + 1)
        for yy in land:
            self.sparks.burst(hx - 1, yy + 1, 3, 18, life=0.3, gravity=30)
            self.sparks.burst(hx + RHW, yy + 1, 3, 18, life=0.3, gravity=30)
        done = k > 0.08 + 5 * 0.075 + 0.12
        if done:  # 卦象四角闪烁的小星
            for j, (sx, sy) in enumerate(((hx - 4, hy - 3), (hx + RHW + 4, hy + 26), (hx + RHW + 2, hy - 4))):
                ph = (k * 1.6 + j * 0.37) % 1
                if ph < 0.5:
                    star4(g, sx, sy, 1 + int(ph * 4) % 2)
        # 字
        if k > 0.45:
            s = full_name(lines)
            m = int(clamp((k - 0.45) * 12 / len(s)) * len(s))
            if m and vname:
                self.say_v(nx, ny, s[:m])
            elif m:
                self.say(nx, ny, s[:m])
        if num and k > 0.8:
            self.say(nx, ny + 15, f"第{cn_num(n)}卦", size=8)
        if k > 0.95:
            s = CI[n]
            m = int(clamp((k - 0.95) * 16 / len(s)) * len(s))
            p = ease_out(span(k, 0.95, 1.3))
            for xx in range(int(64 - 60 * p), int(64 + 60 * p), 2):
                g.px(xx, ci_y + 13)
            if m:
                w = text_width(s)
                self.say(64 - w / 2, ci_y, s[:m], plate=True)
        mx_hexagram(g, lines)
        lv = 0.08 + 6 * 0.075 + 0.12
        g.mx_level = 6 if k < lv else 1


_ROT: dict = {}


def rotated(spr, deg: float, step: int = 15):
    """精灵旋转（最近邻，按 step 度量化缓存）：做翻滚的道具"""
    import numpy as np
    from PIL import Image
    from ..engine.gfx import Sprite
    q = int(round(deg / step)) * step % 360
    if q == 0:
        return spr
    key = (id(spr), q)
    s = _ROT.get(key)
    if s is None:
        on = Image.fromarray(spr.on).rotate(q, Image.NEAREST, expand=True)
        mk = Image.fromarray(spr.mask).rotate(q, Image.NEAREST, expand=True)
        s = _ROT[key] = Sprite(on=np.array(on, bool), mask=np.array(mk, bool))
    return s


def blit_center(g: Gfx, spr, cx: float, cy: float, **kw):
    pix.blit(g, spr, cx - spr.w / 2, cy - spr.h / 2, **kw)
