"""朱砂画符：小道士站在脚凳上，对着符架上垂下的一张黄符，转身蘸朱砂、回身逐笔写符。

依据：符的一般结构——符头（多画作三勾，象三清）、“敕令”、符身两侧护法纹、符胆（螺旋）、符脚；
画符前以咒敕笔，“笔点灵朱光，邪魔走茫茫”；画毕“以笔头撞符纸三次，然后用金刚剑指敕符”，最后盖印。

舞台（侧视）：左边供案（烛台、法印、朱砂碟），中间脚凳上的小道士，右边符架（横杆、立柱、垂下的亮纸）。
入场：符纸从横杆上一卷落下展开，烛台点亮，小道士走来跳上脚凳，转身从碟里提笔、蘸两下，回身持笔。
持续：一轮 300 秒写一道符。开头“敕笔”（举笔过额，笔尖一闪）；之后 9 笔，每笔一个 26 秒的槽：
      转身蘸朱砂 → 回身 → 笔尖沿弧线到起笔处 → 行笔（朱砂点溅出）→ 收笔；静候时吹墨、低头端详。
      9 笔写完：撞笔三下（符纸一闪一闪）→ 剑指敕符（光芒四射）→ 转身取印、举印、落印（震屏、火星）→ 作揖；
      符成后每隔几秒放一圈光。续：符离开横杆翻飞上天，新符纸落下展开，“第几道”加一。
中断：笔放回碟里，烛火熄成一缕烟，“停笔”。恢复：剑指一点烛火复燃，转身提笔，笔回到原处。
圆满：剩下的笔画一气呵成，撞笔，印一落，符纸反白一闪，光圈一层层涌出，“急急如律令”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import (act, boxed, vbox, brush, candle, dish_spr, fist, floor, glyph_reveal, hold_brush, mx_fu, mx_ring,
                        poly_len, polyline_part, ring, seal_spr, spiral, star4, table_spr)

FLOOR = 58
DAO_X = 62
STAND = FLOOR - 6                 # 脚凳面（小道士脚底）
PX0, PY0, PX1, PY1 = 77, 15, 96, 56   # 符纸（含边）
ROD_Y = 13
TABLE_X, TABLE_Y = 10, 44
CANDLE_X = 15
SEAL_AT = (21, TABLE_Y - 12)      # 法印在案上的位置（左上角）
DISH_X = 33                       # 朱砂碟左边
DIP = (38, TABLE_Y - 2)           # 蘸朱砂时笔尖的位置
REST_HAND = (DAO_X + 8, 44)       # 持笔静候：手的位置（笔竖在脸的右前方）
LEAD = 6.0                        # 每轮开头：敕笔 / 续符
SLOT = 26.0
RENEW = 6.0
SEAL_MARK = (PX0 + 1, 48)              # 印痕左上角（7×7）
CNT_X = 114                       # 竖牌中线
STEP = 4                          # 盖印时往前挪一步


def _hook(c):
    return [(c - 1, 18), (c + 1, 19), (c, 21), (c - 1, 23), (c + 1, 24)]


def _guard(x, s):
    return [(x, 27), (x - s, 30), (x + s, 33), (x - s, 36), (x + s, 39), (x - s, 42), (x, 46)]


# 笔画：("line", 点列) 或 ("char", (字, x, y))
STROKES = [
    ("line", _hook(PX0 + 4)), ("line", _hook(PX0 + 9)), ("line", _hook(PX0 + 14)),   # 符头：三清
    ("char", ("敕", PX0 + 4, 26)), ("char", ("令", PX0 + 4, 38)),                    # 敕令
    ("line", _guard(PX0 + 2, 1)), ("line", _guard(PX0 + 17, -1)),                  # 左右护法纹
    ("line", spiral(PX0 + 13, 50.5, 3.0, turns=1.8, n=20, start=-math.pi / 2)),     # 符胆
    ("line", [(PX0 + 9, 53), (PX0 + 10, 55), (PX0 + 17, 55), (PX0 + 18, 53)]),     # 符脚
]
N = len(STROKES)
DONE = LEAD + N * SLOT            # 9 笔写完
FIN = 13.0                        # 撞笔、剑指、盖印、作揖


def _start(s):
    return (s[1][1] + 6, s[1][2]) if s[0] == "char" else s[1][0]


def _end(s):
    return (s[1][1] + 6, s[1][2] + 10) if s[0] == "char" else s[1][-1]


def _dur(s):
    return 2.6 if s[0] == "char" else min(max(poly_len(s[1]) / 9, 1.2), 2.6)


def _arc(a, b, p, lift=8):
    q = ease_in_out(p)
    return lerp(a[0], b[0], q), lerp(a[1], b[1], q) - math.sin(q * math.pi) * lift


def _rest_tip(hand):
    return hand[0] + 3, hand[1] - 8


def _write_hand(tip):
    """写字时手的位置：高处的笔画手在左下（笔朝右上），低处手在左上（笔朝右下）"""
    k = (tip[1] - 18) / 38
    return min(tip[0] - 7, DAO_X + 13), max(29, min(48, tip[1] + lerp(7, -7, k)))


# ---------------------------------------------------------------- 道具

def _stool():
    """脚凳 22×6：凳面带厚边、两腿、横枨"""
    p = Part(22, 6)
    p.shape("rectangle", (0, 0, 21, 1), fill=1)
    p.d.line((1, 1, 20, 1), fill=0)
    for x in (2, 18):
        p.shape("rectangle", (x, 2, x + 1, 5), fill=1)
    p.shape("line", (3, 4, 18, 4), fill=1)
    return p.sprite()


def _stand():
    """符架 28×46：横杆两头的轴头、两根立柱（宝珠顶）、八字底座"""
    p = Part(28, 46)
    p.shape("rectangle", (0, 2, 27, 3), fill=1)         # 横杆
    p.d.line((1, 3, 26, 3), fill=0)
    for x in (0, 26):
        p.shape("rectangle", (x - 0, 1, x + 1, 4), fill=1)
    for x in (2, 24):                                  # 立柱
        p.shape("ellipse", (x - 1, 0, x + 2, 2), fill=1)
        p.shape("rectangle", (x, 4, x + 1, 43), fill=1)
        p.px(x, 20, 0), p.px(x + 1, 21, 0)
        p.shape("polygon", [(x - 2, 45), (x + 3, 45), (x + 1, 42), (x, 42)], fill=1)
    return p.sprite()


def _curtain():
    """顶上的帷幔 128×8：一道横楣 + 一排垂弧 + 弧间的流苏"""
    p = Part(128, 8)
    p.shape("rectangle", (0, 0, 127, 1), fill=1)
    for x in range(0, 128, 2):
        p.px(x, 1, 0)
    for x0 in range(-8, 128, 16):
        p.shape("chord", (x0, -3, x0 + 16, 5), 0, 180, fill=1)
        p.d.chord((x0 + 2, -3, x0 + 14, 3), 0, 180, fill=0)
        p.shape("line", (x0, 2, x0, 5), fill=1)
        p.px(x0 - 1, 6), p.px(x0, 6), p.px(x0 + 1, 6), p.px(x0, 7)
    return p.sprite()


def _mark():
    """印痕 7×7（亮纸上的朱印：黑框 + 四字的小方块）"""
    p = Part(7, 7)
    p.shape("rectangle", (0, 0, 6, 6), fill=0)
    p.d.rectangle((1, 1, 5, 5), fill=1)
    p.px(2, 2, 0), p.px(4, 2, 0), p.px(2, 4, 0), p.px(4, 4, 0), p.px(3, 3, 0)
    return p.sprite()


_P: dict = {}


def prop(name):
    if name not in _P:
        _P[name] = {"stool": _stool, "stand": _stand, "curtain": _curtain, "mark": _mark}[name]()
    return _P[name]


@register
class ZhuFu(Ritual):
    id = "r2.zhufu"
    name = "朱砂画符"
    desc = "小道士站在脚凳上，转身蘸朱砂、回身逐笔写出三清符头、敕令、护法纹、符胆、符脚，撞笔、剑指、盖印，符成放光"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 300.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.drops: list[list[float]] = []   # 朱砂点：x, y, vx, vy, age
        self.last_t = None

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    # ------------------------------------------------------------ 状态（e 的函数）

    def state(self, u: float) -> dict:
        """一轮内第 u 秒：已写笔数、当前笔进度、笔尖、朝向、手里拿什么、表情……"""
        S = dict(done=0, cur=None, tip=None, flip=False, item="brush", face="normal", head="up", pose=None,
                 seal=False, hit=0.0, glow=None, dip=False)
        hand_rest = REST_HAND
        if u < LEAD:                                   # 敕笔：举笔过额，笔尖一闪
            k = u / LEAD
            lift = math.sin(span(k, 0.1, 0.9) * math.pi)
            S["hand"] = (lerp(hand_rest[0], DAO_X + 9, lift), lerp(hand_rest[1], 27, lift))
            S["tip"] = (S["hand"][0] + lerp(3, 5, lift), S["hand"][1] - 9)
            S["spark"] = 0.4 < k < 0.7
            return S
        if u >= DONE:
            return self._finish(u - DONE, S)
        i = int((u - LEAD) // SLOT)
        k = (u - LEAD) - i * SLOT
        s = STROKES[i]
        d = _dur(s)
        S["done"] = i
        st = _start(s)
        rest_tip = _rest_tip(hand_rest)
        if k < 0.35:                                   # 转身
            S["hand"], S["tip"] = hand_rest, rest_tip
            S["flip"] = k > 0.15
        elif k < 2.0:                                  # 蘸朱砂两下
            S["flip"] = True
            q = span(k, 0.35, 0.8)
            bob = abs(math.sin(span(k, 0.8, 1.8) * 2 * math.pi)) * 3
            S["tip"] = (lerp(DAO_X - 3, DIP[0], ease_out(q)), lerp(rest_tip[1], DIP[1], ease_out(q)) - bob)
            S["hand"] = (S["tip"][0] + 8, S["tip"][1] - 8)
            S["dip"] = q >= 1 and bob < 0.5
        elif k < 2.3:                                  # 回身
            S["hand"], S["tip"] = hand_rest, rest_tip
        elif k < 3.2:                                  # 笔尖到起笔处
            S["tip"] = _arc(rest_tip, st, span(k, 2.3, 3.2), 6)
        elif k < 3.2 + d:                              # 行笔
            S["cur"] = (k - 3.2) / d
            S["face"] = "normal"
        elif k < 4.2 + d:                              # 收笔
            S["done"] = i + 1
            S["tip"] = _arc(_end(s), rest_tip, span(k, 3.2 + d, 4.2 + d), 4)
        else:
            S["done"] = i + 1
            S["hand"], S["tip"] = hand_rest, rest_tip
            if 13.0 < k < 14.6:                        # 吹墨
                S["face"] = "wow"
                S["blow"] = k - 13.0
            elif 19.0 < k < 20.4:                      # 低头端详
                S["head"] = "bow"
            elif 23.5 < k < 24.0:
                S["face"] = "happy"
        return S

    def _finish(self, f: float, S: dict) -> dict:
        """写完以后：撞笔三下 → 放笔 → 剑指 → 取印 → 盖印 → 放印 → 作揖 → 符光"""
        S["done"] = N
        S["seal"] = f >= 7.0
        hand_rest = REST_HAND
        mid = (PX0 - 1, 33)
        if f < 0.6:
            S["tip"] = _arc(_rest_tip(hand_rest), mid, f / 0.6, 5)
        elif f < 2.4:                                  # 撞笔三下
            ph = ((f - 0.6) / 0.6) % 1
            push = math.sin(min(ph / 0.35, 1) * math.pi) if ph < 0.35 else 0
            S["tip"] = (mid[0] + 2 * push, mid[1])
            S["hit"] = 1.0 if 0.12 < ph < 0.26 else 0.0
        elif f < 3.0:                                  # 转身放笔
            S["flip"] = True
            q = span(f, 2.4, 2.9)
            S["tip"] = (lerp(DAO_X - 3, DIP[0], q), lerp(30, DIP[1], q))
            S["hand"] = (S["tip"][0] + 8, S["tip"][1] - 8)
            S["item"] = "brush"
        elif f < 5.0:                                  # 剑指敕符
            S["item"] = None
            S["pose"] = "point"
            S["glow"] = span(f, 3.6, 5.0)
        elif f < 6.0:                                  # 转身取印
            S["item"] = "seal"
            q = span(f, 5.0, 5.6)
            S["flip"] = f < 5.7
            S["hand"] = (lerp(SEAL_AT[0] + 5, DAO_X - 8, q), lerp(SEAL_AT[1] + 1, 32, q) if q < 1 else 32) \
                if f < 5.7 else (DAO_X + 6, 32)
        elif f < 7.6:                                  # 举印 → 落印 → 提印
            S["item"] = "seal"
            S["dx"] = STEP * span(f, 6.0, 6.4)
            up = span(f, 6.0, 6.7)
            down = span(f, 6.8, 7.0)
            hi = (SEAL_MARK[0] + 1, 24)
            tgt = (SEAL_MARK[0] + 3, SEAL_MARK[1] - 5)
            S["hand"] = (lerp(DAO_X + 6, hi[0], ease_out(up)), lerp(32, hi[1], ease_out(up)))
            if down > 0:
                S["hand"] = (lerp(hi[0], tgt[0], down ** 2), lerp(hi[1], tgt[1], down ** 2))
            if f > 7.25:
                S["hand"] = (tgt[0], tgt[1] - 6 * ease_out(span(f, 7.25, 7.6)))
            S["hit"] = 1.0 if 7.0 <= f < 7.12 else 0.0
            S["slam"] = f >= 7.0
            S["squash"] = 7.0 <= f < 7.25
        elif f < 8.6:                                  # 转身放印
            S["item"] = "seal"
            q = span(f, 7.6, 8.3)
            S["flip"] = True
            S["dx"] = STEP * (1 - span(f, 7.6, 7.9))
            S["hand"] = (lerp(DAO_X - 8, SEAL_AT[0] + 5, q), lerp(32, SEAL_AT[1] + 1, q))
            if f > 8.3:
                S["item"] = None
                S["pose"] = "idle"
        else:
            S["item"] = None
            S["pose"] = "bow" if 9.0 < f < 10.2 else ("gongshou" if 8.6 < f < 11 else "idle")
            S["glow"] = 1.0
            S["pulse"] = f - 8.6
        S["done_brush"] = f >= 2.9
        S["seal_home"] = S["item"] != "seal"
        return S

    # ------------------------------------------------------------ 画面零件

    def stage(self, g: Gfx, t: float, lit: bool = True):
        floor(g, FLOOR)
        pix.blit(g, prop("curtain"), 0, 0)
        pix.blit(g, prop("stand"), PX0 - 4, ROD_Y - 2)
        pix.blit(g, table_spr(30, 14), TABLE_X, TABLE_Y)
        pix.blit(g, dish_spr(), DISH_X, TABLE_Y - 4)
        candle(g, CANDLE_X, TABLE_Y, t, lit)
        pix.blit(g, prop("stool"), DAO_X - 9, STAND)

    def paper(self, g: Gfx, done: int, cur: float | None, sealed: bool, drop: float = 1.0, dy: float = 0,
              sx: float = 1.0) -> tuple | None:
        """符纸（亮纸）与已写笔画；drop = 展开到的比例；返回行笔时的笔尖"""
        y1 = PY0 + (PY1 - PY0) * drop
        cx = (PX0 + PX1) / 2
        hw = (PX1 - PX0) / 2 * sx
        g.d.rectangle((cx - hw - 1, PY0 - 1 + dy, cx + hw + 1, y1 + 1 + dy), fill=0)
        g.d.rectangle((cx - hw, PY0 + dy, cx + hw, y1 + dy), fill=1)
        if drop < 1:  # 还卷着的一截：卷轴
            g.d.rectangle((cx - hw - 1, y1 - 1 + dy, cx + hw + 1, y1 + 2 + dy), fill=1)
            g.d.line((cx - hw, y1 + dy, cx + hw, y1 + dy), fill=0)
            return None
        if sx < 0.9:
            return None
        g.px(PX0 + 2, PY0 + 1 + dy, 0), g.px(PX1 - 2, PY0 + 1 + dy, 0)   # 两枚夹子
        tip = None
        for j in range(min(done + (cur is not None), N)):
            s = STROKES[j]
            k = cur if j == done and cur is not None else 1.0
            if s[0] == "char":
                ch, x, y = s[1]
                tp = glyph_reveal(g, x, y + dy, ch, k, ink=0)
            else:
                pts = [(x, y + dy) for x, y in s[1]]
                part, tp = polyline_part(pts, k)
                if len(part) > 1:
                    g.d.line(part, fill=0)
                else:
                    g.px(*tp, 0)
            if j == done:
                tip = tp
        if sealed:
            pix.blit(g, prop("mark"), SEAL_MARK[0], SEAL_MARK[1] + dy, outline=False)
        return tip

    def drops_step(self, g: Gfx, dt: float):
        keep = []
        for q in self.drops:
            q[4] += dt
            q[3] += 60 * dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            if q[4] < 0.5:
                keep.append(q)
                on_paper = PX0 <= q[0] <= PX1 and PY0 <= q[1] <= PY1
                g.px(q[0], q[1], 0 if on_paper else 1)
        self.drops = keep

    def splash(self, x, y, n=4):
        r = self.sparks.rng
        for _ in range(n):
            self.drops.append([x, y, (r.random() - 0.3) * 30, -r.random() * 25, 0.0])

    def dao(self, g: Gfx, t: float, S: dict, writing_tip=None):
        """按状态画小道士和手里的东西"""
        flip = S["flip"]
        tip = writing_tip or S.get("tip")
        lean = max(0.0, min(4.0, (tip[0] - 86) * 0.5)) if tip and S["item"] == "brush" and not flip else 0.0
        x = DAO_X + S.get("dx", lean)
        if S.get("pose"):
            daoshi(g, x, STAND, S["pose"], t, flip=flip)
            return
        item = S["item"]
        if item == "brush":
            tip = writing_tip or S["tip"]
            hand = S.get("hand") or _write_hand(tip)
            h = act(g, x, STAND, t, hand_to=hand, flip=flip, face=S["face"], head=S["head"])["hand"]
            hold_brush(g, h, tip, inked=True, past=2 if tip[0] > h[0] + 4 else 5)
            if S.get("spark"):
                star4(g, tip[0], tip[1] - 1, big=int(t * 10) % 2 == 0)
        elif item == "seal":
            h = act(g, x, STAND, t, hand_to=S["hand"], flip=flip, face="wow" if S.get("squash") else "normal")["hand"]
            spr = seal_spr()
            if S.get("squash"):
                sq = pix.stretch(spr, 1.3, 0.7)
                pix.blit(g, sq, h[0] - sq.w // 2, h[1] + 11 - sq.h)
            else:
                pix.blit(g, spr, h[0] - 5, h[1] - 1)
            fist(g, *h)

    def brush_in_dish(self, g: Gfx):
        brush(g, DIP[0], DIP[1], -1.15, 13)

    def seal_on_table(self, g: Gfx):
        pix.blit(g, seal_spr(), SEAL_AT[0], SEAL_AT[1])

    def counter(self, g: Gfx, e: float, label: str | None = None):
        """右边墙上挂的竖牌：“第几道”（竖排）"""
        n = int(e // self.CYCLE) + 1
        s = label or ("第" + (cn_num(n) if n < 100 else str(n)) + "道")
        vbox(g, CNT_X, 16, s)

    def glow(self, g: Gfx, t: float, k: float, pulse: float | None = None):
        """符光：纸的四周长出一圈短光芒（k 0..1），符成后每 5 秒从纸边扩出一圈虚线光框，纸边闪星"""
        x0, y0, x1, y1 = PX0 - 3, PY0 - 2, PX1 + 3, PY1 + 1
        n = int(k * 7)
        on = int(t * 5) % 2
        for i in range(n):  # 左右两侧的光芒（不压纸）
            y = y0 + 4 + i * 6
            ln = 2 + (i + on) % 2
            g.d.line((x1 + 1, y, x1 + ln, y), fill=1)
            if i not in (4, 5):
                g.d.line((x0 - 1, y, x0 - ln, y), fill=1) if x0 - ln > DAO_X + 9 else None
        if pulse is not None:
            r = (pulse % 5.0) * 7
            if r < 22:
                pix.dotted(g, x1 + r, y0 - r * 0.5, x1 + r, y1 + r * 0.3, step=2, phase=int(t * 8))
                pix.dotted(g, x0 + 2, y0 - 1 - r * 0.5, x1 + r, y0 - 1 - r * 0.5, step=2, phase=int(t * 8)) \
                    if y0 - 1 - r * 0.5 > 2 else None
            for j in range(3):
                ph = (pulse * 0.7 + j * 0.37) % 1
                if ph < 0.2:
                    star4(g, PX1 + 4 + (j * 7) % 18, PY0 + 6 + j * 13, big=ph < 0.1)

    # ------------------------------------------------------------ 阶段

    def draw_hold(self, g: Gfx, t: float, e: float, dt: float):
        u = e % self.CYCLE
        S = self.state(u)
        if e >= self.CYCLE and u < RENEW:
            return self.renew(g, t, e, u, dt)
        self.stage(g, t)
        tip = self.paper(g, S["done"], S["cur"], S["seal"])
        if S["item"] != "seal":
            self.seal_on_table(g)
        if S["item"] is None or (S.get("done_brush") and S["item"] != "brush"):
            self.brush_in_dish(g)
        if S["cur"] is not None and tip is not None:
            if S["cur"] < 0.08 and int(e * 30) % 6 == 0:
                self.splash(*tip)
        if S.get("glow") is not None:
            self.glow(g, t, S["glow"], S.get("pulse"))
        if S["hit"]:
            g.invert((PX0, PY0, PX1 + 1, PY1 + 1))
            pix.shake(g, t, 1.0)
            if S.get("slam"):
                self.sparks.burst(SEAL_MARK[0] + 3, SEAL_MARK[1] + 3, 3, 30, life=0.4)
        if S.get("slam") and S["hit"]:
            self.sparks.burst(PX0 - 1, SEAL_MARK[1] + 3, 10, 34, up=10, life=0.6, gravity=50)
        self.dao(g, t, S, writing_tip=tip if S["cur"] is not None else None)
        if S.get("blow") is not None:
            b = S["blow"]
            for j in range(3):
                q = (b * 1.6 - j * 0.25)
                if 0 < q < 1:
                    g.px(DAO_X + 8 + q * 10, 30 + math.sin(q * 6 + j) * 1.5)
        if S.get("glow") is not None and S["glow"] > 0 and S.get("pulse") is None and S["pose"] == "point":
            star4(g, DAO_X + 16, STAND - 14, big=int(t * 8) % 2 == 0)
        self.drops_step(g, dt)
        self.sparks.step(dt)
        self.sparks.draw(g)
        rows = S["done"] * 8 / N + (S["cur"] or 0) * 8 / N
        mx_fu(g, rows, blink_row=int(rows) if S["cur"] is not None and int(t * 6) % 2 else None)
        if S["hit"]:
            g.mx_level = 6
        return S

    def renew(self, g: Gfx, t: float, e: float, u: float, dt: float):
        """续：旧符翻飞上天 → 新符纸落下展开 → 转身蘸笔，回到持笔静候"""
        self.stage(g, t)
        self.seal_on_table(g)
        fly = span(u, 0.3, 2.2)
        if fly < 1:
            dy = -ease_in(fly) * 70
            sx = abs(math.cos(fly * 9)) if fly > 0 else 1
            self.paper(g, N, None, True, dy=dy, sx=max(sx, 0.15))
            if 0 < fly and int(u * 20) % 2 == 0:
                self.sparks.burst((PX0 + PX1) / 2, PY1 + dy, 1, 10, life=0.5, gravity=30)
        drop = span(u, 2.2, 3.2)
        if drop > 0:
            self.paper(g, 0, None, False, drop=ease_out(drop))
        if 2.2 <= u < 2.25:
            pix.shake(g, t, 0.8)
        if u < 2.4:
            daoshi(g, DAO_X, STAND, "raise" if 0.3 < u < 1.8 else "idle", t, face="wow" if u > 0.6 else "normal")
            self.brush_in_dish(g)
        elif u < 3.6:
            daoshi(g, DAO_X, STAND, "idle", t)
            self.brush_in_dish(g)
        else:  # 转身提笔、蘸两下、回身
            k = u - 3.6
            S = dict(flip=True, item="brush", face="normal", head="up", pose=None, tip=None)
            if k < 1.6:
                bob = abs(math.sin(span(k, 0.4, 1.4) * 2 * math.pi)) * 3
                S["tip"] = (DIP[0], DIP[1] - bob - 1)
                S["hand"] = (DIP[0] + 8, DIP[1] - 9)
            else:
                S["flip"] = False
                q = span(k, 1.6, 2.2)
                S["hand"] = REST_HAND
                S["tip"] = _rest_tip(REST_HAND)
            self.dao(g, t, S)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e if u > 2.2 else e - u - 1)
        if u < 2.2:  # 点阵：小符往上飞走
            off = int(span(u, 0.3, 2.2) * 9)
            for y in range(8 - off):
                for x in range(8):
                    g.mx[y, x] = _FU8[y + off][x] == "#"
        else:
            mx_fu(g, 0)

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        floor(g, FLOOR)
        pix.blit(g, prop("curtain"), 0, 0)
        pix.blit(g, prop("stand"), PX0 - 4, ROD_Y - 2)
        pix.blit(g, table_spr(30, 14), TABLE_X, TABLE_Y)
        pix.blit(g, dish_spr(), DISH_X, TABLE_Y - 4)
        candle(g, CANDLE_X, TABLE_Y, t, lit=t > 0.9)
        if 0.85 < t < 0.9:
            self.sparks.burst(CANDLE_X, TABLE_Y - 16, 6, 16, up=8, life=0.4)
        pix.blit(g, prop("stool"), DAO_X - 9, STAND)
        self.seal_on_table(g)
        drop = span(t, 0.2, 1.2)
        self.paper(g, 0, None, False, drop=ease_out_back(drop) if drop < 1 else 1)
        if 1.2 <= t < 1.4:
            pix.shake(g, t, 0.6)
        if t < 2.3:  # 走来
            x = lerp(-12, DAO_X - 14, ease_out(span(t, 0.0, 2.3)))
            daoshi(g, x, FLOOR, "walk", t)
            self.brush_in_dish(g)
        elif t < 2.8:  # 跳上脚凳
            q = span(t, 2.3, 2.8)
            x = lerp(DAO_X - 14, DAO_X, q)
            y = lerp(FLOOR, STAND, q) - math.sin(q * math.pi) * 7
            daoshi(g, x, y, "raise" if q < 0.7 else "idle", t, face="happy")
            self.brush_in_dish(g)
            if t + dt >= 2.8 > t:
                self.puffs.emit(DAO_X - 6, STAND, vx=-6, vy=-3, life=0.5, rmax=1.5)
                self.puffs.emit(DAO_X + 6, STAND, vx=6, vy=-3, life=0.5, rmax=1.5)
        else:  # 转身提笔，蘸两下，回身持笔
            k = t - 2.8
            S = dict(flip=True, item="brush", face="normal", head="up", pose=None)
            if k < 0.3:
                daoshi(g, DAO_X, STAND, "idle", t, flip=True)
                self.brush_in_dish(g)
                S = None
            elif k < 2.4:
                bob = abs(math.sin(span(k, 0.8, 1.9) * 2 * math.pi)) * 3
                lift = ease_out(span(k, 0.3, 0.7))
                S["tip"] = (DIP[0], DIP[1] - bob - lift * 1)
                S["hand"] = (DIP[0] + 8, DIP[1] - 9)
            else:
                S["flip"] = False
                S["hand"] = REST_HAND
                S["tip"] = _rest_tip(REST_HAND)
            if S:
                self.dao(g, t, S)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, 0.0)
        mx_fu(g, 0)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        S = self.draw_hold(g, t, e, dt)
        u = e % self.CYCLE
        if S is not None:
            if u < LEAD and e < self.CYCLE:
                g.text(4, 9, "笔点灵朱光")
            elif S.get("pulse") is not None:
                g.text(4, 9, "急急如律令")
            self.counter(g, e)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        S = self.state(u)
        self.stage(g, t, lit=t < 0.9)
        self.paper(g, S["done"], S["cur"] if S["cur"] is not None else None, S["seal"])
        self.seal_on_table(g)
        if abs(t - 0.9) < dt:
            self.puffs.emit(CANDLE_X, TABLE_Y - 16, vy=-6, life=1.2, rmax=1.8, spread=0)
        tip0 = S["tip"] or _rest_tip(REST_HAND)
        if t < 0.8 and S["item"] == "brush":
            q = ease_in_out(span(t, 0.0, 0.7))
            S2 = dict(flip=True, item="brush", face="normal", head="up", pose=None)
            S2["tip"] = (lerp(tip0[0], DIP[0], q), lerp(tip0[1], DIP[1], q) - math.sin(q * math.pi) * 6)
            S2["hand"] = (S2["tip"][0] + 8, S2["tip"][1] - 8)
            S2["flip"] = t > 0.15
            self.dao(g, t, S2)
        else:
            self.brush_in_dish(g)
            daoshi(g, DAO_X, STAND, "gongshou" if t > 1.0 else "idle", t, face="sleep" if t > 1.2 else "normal")
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.counter(g, e, "停笔")
        mx_fu(g, S["done"] * 8 / N)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        S = self.state(u)
        self.stage(g, t, lit=t > 0.6)
        self.paper(g, S["done"], S["cur"], S["seal"])
        self.seal_on_table(g)
        if t < 0.7:
            h = daoshi(g, DAO_X, STAND, "point", t, flip=True)["hand"]
            q = span(t, 0.1, 0.6)
            if 0 < q < 1:
                x, y = lerp(h[0], CANDLE_X, q), lerp(h[1], TABLE_Y - 16, q) - math.sin(q * math.pi) * 6
                star4(g, x, y)
            self.brush_in_dish(g)
        elif t < 1.0:
            daoshi(g, DAO_X, STAND, "idle", t, flip=True)
            self.brush_in_dish(g)
        else:
            q = ease_in_out(span(t, 1.0, 1.7))
            if S["item"] == "brush":
                tgt = S["tip"] or _rest_tip(REST_HAND)
                if S["cur"] is not None:
                    tgt = self.paper_tip(S)
                S2 = dict(S)
                S2["tip"] = (lerp(DIP[0], tgt[0], q), lerp(DIP[1], tgt[1], q) - math.sin(q * math.pi) * 8)
                S2["flip"] = S["flip"] if q >= 1 else (q < 0.3)
                S2["cur"] = None
                if q >= 1:
                    S2 = S
                    S2["tip"] = tgt
                else:
                    S2["hand"] = None if not S2["flip"] else (S2["tip"][0] + 8, S2["tip"][1] - 8)
                    if not S2["flip"]:
                        S2.pop("hand", None)
                self.dao(g, t, S2, writing_tip=tgt if q >= 1 and S["cur"] is not None else None)
            else:
                self.brush_in_dish(g)
                self.dao(g, t, S)
        if abs(t - 0.6) < dt:
            self.sparks.burst(CANDLE_X, TABLE_Y - 16, 8, 18, up=8, life=0.4)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        mx_fu(g, S["done"] * 8 / N)

    def paper_tip(self, S):
        s = STROKES[S["done"]]
        if s[0] == "char":
            return _start(s)
        _, tp = polyline_part(s[1], S["cur"])
        return tp

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        S = self.state(u) if u < DONE else dict(done=N, cur=None)
        start = S["done"] + (S["cur"] or 0)
        prog = lerp(start, N, ease_in_out(span(t, 0.0, 1.6)))
        done, cur = int(prog), prog - int(prog)
        self.stage(g, t)
        sealed = t >= 2.6
        tip = self.paper(g, min(done, N), cur if done < N else None, sealed)
        self.seal_on_table(g) if t < 1.9 else None
        if t < 1.6:
            if tip is None:
                tip = (PX0 - 1, 40)
            h = act(g, DAO_X, STAND, t, hand_to=_write_hand(tip), face="normal")["hand"]
            hold_brush(g, h, tip)
            if int(t * 30) % 4 == 0:
                self.splash(*tip, n=2)
        elif t < 2.0:  # 笔一扔进碟，法印飞到手里
            q = span(t, 1.6, 1.9)
            x, y = lerp(PX0 - 4, DIP[0], q), lerp(36, DIP[1], q) - math.sin(q * math.pi) * 12
            brush(g, x, y, -1.15 - q * 3, 13)
            sq = span(t, 1.7, 2.0)
            h = act(g, DAO_X + STEP * sq, STAND, t, hand_to=(SEAL_MARK[0] + 1, 24))["hand"]
            sx, sy = lerp(SEAL_AT[0], h[0] - 5, sq), lerp(SEAL_AT[1], h[1] - 1, sq) - math.sin(sq * math.pi) * 10
            pix.blit(g, seal_spr(), sx, sy)
        else:
            self.brush_in_dish(g)
            if t < 2.95:
                q = span(t, 2.3, 2.6) ** 2
                tgt = (SEAL_MARK[0] + 3, SEAL_MARK[1] - 5)
                hand = (lerp(SEAL_MARK[0] + 1, tgt[0], q), lerp(24, tgt[1], q) - 6 * ease_out(span(t, 2.75, 2.95)))
                S = dict(flip=False, item="seal", hand=hand, squash=2.6 <= t < 2.75, dx=STEP)
                self.dao(g, t, S)
            else:
                pix.blit(g, seal_spr(), SEAL_AT[0], SEAL_AT[1]) if t > 3.2 else None
                daoshi(g, DAO_X, STAND, "bow" if 3.0 < t < 4.4 else "gongshou", t, face="happy")
        if abs(t - 2.6) < dt * 0.6 + 1e-6 or (2.6 <= t < 2.6 + dt):
            pix.flash(g)
            self.sparks.burst(PX0 + 10, 36, 30, 46, up=10, life=1.0, gravity=30)
        if 2.6 < t < 2.9:
            pix.shake(g, t, 1.5)
        if t > 2.8:  # 光圈一层层涌出
            for j in range(3):
                r = ((t - 2.8) * 22 - j * 9)
                if r > 0:
                    ring(g, (PX0 + PX1) / 2, (PY0 + PY1) / 2, 14 + r, step=2, sy=1.4)
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_fu(g, prog * 8 / N)
        if t > 2.6:
            mx_ring(g, (t - 2.6) * 4)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.6, 4.0)))
        if t > 3.0:
            pop = ease_out_back(span(t, 3.0, 3.4))
            boxed(g, 4, 9, "急急如律令", size=12, pop=pop)
        self.counter(g, e, "符成" if t > 2.6 else None)


_FU8 = ["#.####.#", "#..##..#", "#.####.#", "##.#..##", "#.#..#.#", "#..##..#", "#.#.##.#", "##.#..##"]
_RS: dict = {}


def _rot_seal():
    if "r" not in _RS:
        _RS["r"] = seal_spr().rot90(1)
    return _RS["r"]
