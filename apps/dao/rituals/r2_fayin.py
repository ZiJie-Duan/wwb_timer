"""盖法印：小道士在翘头书案前，法印“道经师宝”蘸印泥、跳起来落印，一张张文书盖好，亮给你看，再飞到右边叠起来。

依据：正一派常用法印“道经师宝”（道、经、师三宝），画符、写疏文毕须“敕符盖印”；
印文四字按古印读法右起竖读（右列“道经”、左列“师宝”）；龟钮为古印常见印钮。

舞台（侧视）：月洞窗、翘头案；案上从左到右是印泥盒、一叠待盖的文书、盖好的一叠、烛台。
入场：小道士走进来，一叠白文书从天落到案上（咚），站定在印泥盒前。
持续：一轮 600 秒盖 15 张（每张 39 秒）：拿起法印在印泥里按两下 → 走到文书前 → 下蹲、跳起、举印 →
      落印（印身压扁、震屏、火星、案上扬灰）→ 左右压实 → 提印走回、把印放回盒上 → 剑指一点，
      盖好的文书飘起来正对镜头，朱印“道经师宝”一闪 → 飞到右边那叠上。其余时间作揖、伸懒腰、印钮闪光，烛火一直跳。
      续：盖好的一叠扎上红绳、蹦一下飞出画外，新的一叠白文书从天而降。
中断：印放回盒上，烛火熄灭冒烟，小道士拱手闭目，“暂歇”。恢复：剑指点亮烛火，接着刚才的动作。
圆满：法印飞起，一张大文书升到正中，放大的法印砸下（闪白、震屏、金星），大大的“道经师宝”朱印现出来，光圈外扩，小道士跪拜。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r2_common import act, candle, fist, floor, ring, seal_face_spr, seal_spr, star4, vbox

FLOOR = 58
DESK_X0, DESK_X1, DESK_Y = 22, 112, 52   # 翘头案：案面 y（东西底边在 DESK_Y-1）
PAD_X = 39                                # 印泥盒左边（11 宽）
PAD_HAND = (40, 43)                       # 法印放在盒上时，手握印身的位置
SEAL_REST = (39, 36)                      # 法印放在盒上（左上角）
STK = (52, 66)                            # 待盖的一叠
DONE_STK = (80, 96)                       # 盖好的一叠
CANDLE_X = 105
XA, XB = 31, 46                           # 小道士：印泥盒前 / 文书前
SHOW = (62, 20)                           # 文书亮相的位置（中心）
WIN = (98, 19, 12)                        # 月洞窗
CNT_X = 120
PER = 15
SLOT = 39.0
LEAD = 6.0


# ---------------------------------------------------------------- 道具

def _desk() -> Sprite:
    """翘头矮案 91×8：案面两头翘起、牙板回纹、两条短腿带马蹄足"""
    w = DESK_X1 - DESK_X0 + 1
    p = Part(w, FLOOR - DESK_Y + 2)
    p.shape("rectangle", (0, 2, w - 1, 3), fill=1)
    p.d.line((2, 3, w - 3, 3), fill=0)
    for x in (0, w - 4):                                  # 翘头
        p.shape("polygon", [(x, 2), (x + 3, 2), (x + 3, 1), (x + (0 if x else 3), 0)], fill=1)
    p.shape("rectangle", (4, 4, w - 5, 5), fill=1)        # 牙板
    for x in range(6, w - 6, 5):
        p.px(x, 4, 0), p.px(x + 1, 5, 0)
    for x in (5, w - 8):                                  # 腿
        p.shape("rectangle", (x, 6, x + 2, 7), fill=1)
        p.px(x - 1, 7), p.px(x + 3, 7)
    return p.sprite()


def _pad() -> Sprite:
    """印泥盒 11×4：盒口一圈、里面朱红印泥（网点）、盒身一道阴线、底足"""
    p = Part(11, 4)
    p.shape("rectangle", (0, 0, 10, 2), fill=1)
    for x in range(1, 10):
        p.px(x, 0, x % 2)
    p.d.line((1, 2, 9, 2), fill=0)
    p.shape("rectangle", (1, 3, 9, 3), fill=1)
    p.px(3, 1, 0), p.px(7, 1, 0)
    return p.sprite()


def _lid() -> Sprite:
    """盒盖 11×3：拱顶、一颗钮"""
    p = Part(11, 4)
    p.shape("rectangle", (5, 0, 5, 0), fill=1)
    p.shape("chord", (0, 1, 10, 6), 180, 360, fill=1)
    p.d.line((1, 3, 9, 3), fill=0)
    return p.sprite()


def _sheet() -> Sprite:
    """盖好的文书 28×32（正面）：右边三列疏文（长短不一的墨点），左下一方朱印“道经师宝”（亮纸上的黑字）"""
    on = np.ones((32, 28), bool)
    on[0, :] = on[-1, :] = on[:, 0] = on[:, -1] = True
    for c, x in enumerate((24, 21, 18)):
        y = 3
        i = 0
        while y < (29 if c == 0 else 11 if c == 2 else 10):
            ln = 1 + int(rand(i + c * 40, 11) * 2.5)
            on[y:y + ln, x] = False
            on[y + 1 if ln == 1 else y, x + 1] = False
            y += ln + 1
            i += 1
    face = seal_face_spr(18)
    on[12:30, 1:19] = ~face.on
    return Sprite(on=on, mask=np.ones_like(on))


_P: dict = {}


def prop(name):
    if name not in _P:
        _P[name] = {"desk": _desk, "pad": _pad, "lid": _lid, "sheet": _sheet}[name]()
    return _P[name]


def big_face() -> Sprite:
    if "big" not in _P:
        f = seal_face_spr(18).scale(2)
        _P["big"] = Sprite(on=~f.on, mask=np.ones_like(f.on))
    return _P["big"]


MX_SEAL = ["########", "#.##.#.#", "#.#..###", "#.##.#.#", "#......#", "#.#.##.#", "#.##.#.#", "########"]


def mx_seal(g: Gfx, dy: int = 0, inv: bool = False):
    for y in range(8):
        for x in range(8):
            yy = y + dy
            if 0 <= yy < 8:
                g.mx[yy, x] = (MX_SEAL[y][x] == "#") != inv


def stack_rows(n: int) -> int:
    return (n + 2) // 3


def draw_stack(g: Gfx, x0: int, x1: int, n: int, seed: int, dy: float = 0.0, tied: float = 0.0):
    """侧视的一叠纸：每一行一张（两张算一行），左右错落一像素；tied：红绳捆上的进度"""
    rows = stack_rows(n)
    if rows <= 0:
        return DESK_Y - 1
    top = DESK_Y - rows * 2 + dy
    g.d.rectangle((x0 - 2, top - 1, x1 + 2, DESK_Y - 1 + dy), fill=0)
    for r in range(rows):  # 一行亮（纸边）一行暗（纸缝），左右微微错落
        off = int(rand(r, seed) * 3) - 1
        y = DESK_Y - 2 - r * 2 + dy
        g.d.line((x0 + off, y, x1 + off, y), fill=1)
        g.px(x0 + off, y + 1), g.px(x1 + off, y + 1)
    g.d.line((x0 + 1, DESK_Y - 1 + dy, x1 - 1, DESK_Y - 1 + dy), fill=1)
    if tied > 0:
        cx = (x0 + x1) // 2
        h = (DESK_Y - 1 - top + 2) * min(tied * 1.5, 1)
        g.d.line((cx, top - 1, cx, top - 1 + h), fill=0, width=3)
        g.d.line((cx, top - 1, cx, top - 1 + h), fill=1)
        if tied > 0.7:  # 打结
            g.px(cx - 1, top - 2), g.px(cx + 1, top - 2), g.px(cx - 2, top - 3), g.px(cx + 2, top - 3)
    return top


def window(g: Gfx, t: float):
    """月洞窗：圆环窗框 + 冰裂纹窗棂（只画在圆里）+ 窗外一枝竹"""
    cx, cy, r = WIN
    g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    g.d.ellipse((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), outline=1)
    for x in range(cx - r + 4, cx + r - 2, 5):
        h = math.sqrt(max((r - 3) ** 2 - (x - cx) ** 2, 0))
        g.d.line((x, cy - h, x, cy + h), fill=1)
    for y in range(cy - r + 5, cy + r - 2, 6):
        w = math.sqrt(max((r - 3) ** 2 - (y - cy) ** 2, 0))
        pix.dotted(g, cx - w, y, cx + w, y, step=2)
    sw = int(math.sin(t * 0.8) * 1.2)
    for i, (dx, dy) in enumerate(((-4, -6), (-1, -3), (2, -7))):  # 窗里的竹叶（随风摆）
        x, y = cx + dx + sw, cy + dy
        g.d.line((x, y, x + 3, y + 1 + i % 2), fill=0)


def tassel(g: Gfx, x: float, y: float, t: float):
    """印钮上挂的绶带穗子：一根绳、一个结、一绺穗，随动作摆"""
    sw = round(math.sin(t * 5) * 0.8)
    g.d.line((x, y, x - 1, y + 3), fill=1)
    g.px(x - 2, y + 4), g.px(x, y + 4), g.px(x - 1, y + 4)
    g.d.line((x - 2 + sw, y + 5, x - 2 + sw, y + 7), fill=1)
    g.d.line((x + sw, y + 5, x + sw, y + 7), fill=1)


def lantern(g: Gfx, x: float, t: float):
    """左上挂一盏小灯笼：吊绳、上下木箍、灯身竖纹、下垂流苏，轻轻摆"""
    sw = math.sin(t * 1.3) * 1.5
    g.d.line((x, 0, x + sw * 0.5, 5), fill=1)
    cx, cy = x + sw, 12
    g.d.rectangle((cx - 3, 5, cx + 3, 6), fill=1)
    g.d.ellipse((cx - 6, 6, cx + 6, 18), fill=1)
    for dx in (-3, 0, 3):
        g.d.line((cx + dx, 8, cx + dx, 16), fill=0)
    g.px(cx - 4, 10), g.px(cx + 2, 9)
    g.d.rectangle((cx - 3, 18, cx + 3, 19), fill=1)
    g.d.line((cx, 20, cx + sw * 0.5, 24), fill=1)
    g.px(cx - 1 + sw * 0.5, 25), g.px(cx + 1 + sw * 0.5, 25), g.px(cx + sw * 0.5, 26)


@register
class FaYin(Ritual):
    id = "r2.fayin"
    name = "盖法印"
    desc = "小道士拿“道经师宝”法印在印泥里按两下，跳起来落印、左右压实，文书飘起来亮出朱印，再飞到右边叠起来"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.last_t = None
        self.events: set = set()

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    def once(self, key) -> bool:
        if key in self.events:
            return False
        if len(self.events) > 200:
            self.events.clear()
        self.events.add(key)
        return True

    # ------------------------------------------------------------ 状态（e 的函数）

    def state(self, u: float) -> dict:
        S = dict(x=XA, legs="stand", pose="idle", hand=None, seal="pad", face="normal", head="up", sheet=None,
                 blank=PER, done=0, hit=False, squash=False, wig=0, hop=0.0, star=None, point_star=None)
        if u < LEAD:
            S["pose"] = "gongshou" if 0.5 < u < 2.0 or 3.5 < u < 4.2 else ("bow" if 2.0 <= u < 3.5 else "idle")
            return S
        i = min(int((u - LEAD) // SLOT), PER)
        if i >= PER:
            S.update(blank=0, done=PER, pose="gongshou" if u % 20 < 3 else "idle")
            return S
        k = (u - LEAD) - i * SLOT
        S["blank"], S["done"] = PER - i, i
        top = DESK_Y - 2 * stack_rows(PER - i)
        stamp = (54, top - 5)
        if k < 0.5:                                             # 伸手拿印
            S.update(pose=None, seal="hand")
            q = ease_out(span(k, 0, 0.5))
            S["hand"] = (lerp(XA + 7, PAD_HAND[0], q), lerp(44, PAD_HAND[1], q))
            S["seal"] = "pad" if q < 1 else "hand"
        elif k < 1.7:                                           # 在印泥里按两下
            S.update(pose=None, seal="hand")
            b = abs(math.sin((k - 0.5) / 1.2 * 2 * math.pi)) * 3
            S["hand"] = (PAD_HAND[0], PAD_HAND[1] - b)
        elif k < 2.5:                                           # 走到文书前
            q = span(k, 1.7, 2.5)
            x = lerp(XA, XB, ease_in_out(q))
            S.update(pose=None, seal="hand", x=x, legs="walk" if q < 0.95 else "stand")
            S["hand"] = (x + 10, lerp(PAD_HAND[1], 36, span(q, 0, 0.3)))
        elif k < 3.4:                                           # 下蹲 → 跳起 → 举印
            S.update(pose=None, seal="hand", x=XB, face="normal")
            crouch = span(k, 2.5, 2.9)
            jump = span(k, 2.9, 3.2)
            S["hop"] = 1 * math.sin(crouch * math.pi) if jump == 0 else -6 * math.sin(min(jump * 1.2, 1) * math.pi / 2)
            S["hand"] = (lerp(XB + 10, XB + 7, ease_out(jump)), lerp(36, 28, ease_out(jump)) + S["hop"])
            if jump >= 1:   # 砸下
                d = span(k, 3.25, 3.4)
                S["hop"] = lerp(-6, 0, ease_in(d))
                S["hand"] = (lerp(XB + 7, stamp[0], ease_in(d)), lerp(22, stamp[1], ease_in(d)))
            S["star"] = 2.6 < k < 3.25
        elif k < 4.4:                                           # 落印、压实
            S.update(pose=None, seal="hand", x=XB, face="wow" if k < 3.7 else "happy")
            S["squash"] = k < 3.55
            S["hit"] = k < 3.48
            S["wig"] = 0 if k < 3.6 else (1 if int((k - 3.6) * 8) % 2 == 0 else -1)
            S["hand"] = (stamp[0] + S["wig"], stamp[1])
        elif k < 4.8:                                           # 提印
            S.update(pose=None, seal="hand", x=XB)
            q = ease_out(span(k, 4.4, 4.8))
            S["hand"] = (stamp[0], lerp(stamp[1], 35, q))
        elif k < 5.6:                                           # 走回印泥盒
            q = span(k, 4.8, 5.6)
            x = lerp(XB, XA, ease_in_out(q))
            S.update(pose=None, seal="hand", x=x, legs="walk" if q < 0.95 else "stand", flip=False)
            S["hand"] = (x + 10 - q, 35 + 8 * q)
        elif k < 6.1:                                           # 放回盒上
            q = span(k, 5.6, 6.1)
            S.update(pose=None, seal="pad" if q > 0.5 else "hand")
            S["hand"] = PAD_HAND if q < 0.6 else (lerp(PAD_HAND[0], XA + 7, span(q, 0.6, 1)),
                                                  lerp(PAD_HAND[1], 44, span(q, 0.6, 1)))
        elif k < 6.8:                                           # 剑指一点
            S["pose"] = "point"
            S["point_star"] = span(k, 6.2, 6.8)
        elif k < 9.8:                                           # 文书飘起亮相
            S["pose"] = "gongshou" if k < 9.0 else "idle"
            S["face"] = "happy" if k > 7.4 else "normal"
            S["blank"] = PER - i - 1
            q = span(k, 6.8, 7.6)
            S["sheet"] = (lerp(59, SHOW[0], ease_out(q)), lerp(top, SHOW[1], ease_out(q)), 1.0,
                          max(0.1, ease_out_back(q)), k - 7.6)
        elif k < 10.6:                                          # 飞到右边那叠上
            S["blank"] = PER - i - 1
            q = span(k, 9.8, 10.6)
            dtop = DESK_Y - 1 - 2 * stack_rows(i + 1)
            S["sheet"] = (lerp(SHOW[0], 88, ease_in_out(q)), lerp(SHOW[1], dtop - 1, ease_in(q)) - math.sin(q * math.pi) * 6,
                          max(0.15, abs(math.cos(q * 7)) * (1 - q * 0.45)), max(0.1, 1 - q), None)
        else:
            S["blank"], S["done"] = PER - i - 1, i + 1
            ph = k - 10.6
            if 5.0 < ph < 6.4:
                S["pose"] = "bow"
            elif 4.2 < ph < 5.0:
                S["pose"] = "gongshou"
            elif 12.0 < ph < 13.6:
                S.update(pose="raise", face="happy")
            elif 20.0 < ph < 21.4:
                S.update(pose="gongshou", face="sleep")
            S["glint"] = int(ph // 7) % 2 == 0 and ph % 7 < 0.5
        S["landed"] = (i, k >= 10.6)
        S["slot"] = (i, k)
        return S

    # ------------------------------------------------------------ 画面

    def stage(self, g: Gfx, t: float, S: dict, lit: bool = True, lid: float = 0.0, renew_drop: float | None = None,
              tied: float = 0.0, done_dy: float = 0.0, done_dx: float = 0.0):
        floor(g, FLOOR)
        window(g, t)
        pix.blit(g, prop("desk"), DESK_X0, DESK_Y - 2)
        pix.blit(g, prop("pad"), PAD_X, DESK_Y - 5)
        candle(g, CANDLE_X, DESK_Y - 1, t, lit)
        if done_dx < 40:
            draw_stack(g, DONE_STK[0] + int(done_dx), DONE_STK[1] + int(done_dx), S["done"], self.seed + 7, dy=done_dy,
                       tied=tied)
        if renew_drop is None:
            draw_stack(g, STK[0], STK[1], S["blank"], self.seed + 3)
        elif renew_drop > 0:
            draw_stack(g, STK[0], STK[1], PER, self.seed + 3, dy=-(1 - ease_in(renew_drop)) * 50)
        lantern(g, 13, t)
        if S["seal"] == "pad":
            pix.blit(g, seal_spr(), *SEAL_REST)
            tassel(g, SEAL_REST[0] + 3, SEAL_REST[1] + 2, t)
            if S.get("glint"):
                star4(g, SEAL_REST[0] + 9, SEAL_REST[1] + 1)
        if lid > 0:
            pix.blit(g, prop("lid"), PAD_X, DESK_Y - 5 - 4 - (1 - ease_out(lid)) * 10)

    def dao(self, g: Gfx, t: float, S: dict):
        x, y = S["x"], FLOOR + S.get("hop", 0)
        if S["pose"]:
            h = daoshi(g, x, y, S["pose"], t, face=S["face"])
            if S.get("point_star") is not None and 0 < S["point_star"] < 1:
                q = S["point_star"]
                top = DESK_Y - 1 - 2 * stack_rows(S["blank"])
                star4(g, lerp(h["hand"][0], 59, q), lerp(h["hand"][1], top - 2, q) - math.sin(q * math.pi) * 6, big=True)
            return h
        h = act(g, x, y, t, hand_to=S["hand"], legs=S["legs"], face=S["face"], head=S["head"])["hand"]
        if S["seal"] == "hand":
            spr = seal_spr()
            if S["squash"]:
                sq = pix.stretch(spr, 1.3, 0.7)
                pix.blit(g, sq, h[0] + 4 - sq.w // 2, h[1] + 5 - sq.h)
            else:
                pix.blit(g, spr, h[0] - 1, h[1] - 7)
                tassel(g, h[0] + 2, h[1] - 5, t)
            fist(g, *h)
            if S.get("star"):
                star4(g, h[0] + 12, h[1] - 8, big=int(t * 10) % 2 == 0)
        return {"hand": h}

    def sheet(self, g: Gfx, sh, t: float):
        if not sh:
            return
        cx, cy, sx, sy, show = sh
        spr = pix.stretch(prop("sheet"), sx, sy)
        pix.blit(g, spr, cx - spr.w / 2, cy - spr.h / 2)
        if show is not None and show > 0:  # 朱印一闪：印的四角闪星、一圈光
            x0, y0 = cx - 14, cy - 16
            r = show * 26
            if r < 22:
                ring(g, x0 + 10, y0 + 21, 12 + r, step=3)
            if int(t * 4) % 3 == 0:
                star4(g, x0 - 3, y0 + 10)
                star4(g, x0 + 31, y0 + 26)

    def effects(self, g: Gfx, t: float, S: dict, dt: float, key):
        if S["hit"] and self.once(("hit", key)):
            top = DESK_Y - 1 - 2 * stack_rows(S["blank"])
            self.sparks.burst(59, top, 14, 34, up=16, life=0.6, gravity=60)
            self.puffs.emit(STK[0] - 2, DESK_Y - 2, vx=-10, vy=-4, life=0.6, rmax=1.6)
            self.puffs.emit(STK[1] + 2, DESK_Y - 2, vx=10, vy=-4, life=0.6, rmax=1.6)
        if S["hit"]:
            pix.shake(g, t, 1.5)
            g.mx_level = 7
        lk = S.get("landed")
        if lk and lk[1] and self.once(("land", key, lk[0])):
            self.puffs.emit(88, DESK_Y - 1 - 2 * stack_rows(S["done"]) - 1, vx=0, vy=-5, life=0.5, rmax=1.5, spread=8)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def mx(self, g: Gfx, S: dict, t: float):
        if S["sheet"]:
            mx_seal(g, inv=True)
        elif S["seal"] == "hand":
            mx_seal(g, dy=-2 if S.get("star") else (0 if S["hit"] or S["squash"] else -1))
        else:
            mx_seal(g)
            if S.get("glint"):
                g.mx[0, 7] = g.mx[1, 6] = True

    def counter(self, g: Gfx, S: dict, label: str | None = None):
        n = min(S["done"] + 1, PER)
        vbox(g, CNT_X, 10, label or f"第{cn_num(n)}印")

    def render(self, g: Gfx, t: float, e: float, S: dict, dt: float, **stage_kw):
        self.stage(g, t, S, **stage_kw)
        self.dao(g, t, S)
        self.sheet(g, S["sheet"], t)
        self.effects(g, t, S, dt, int(e // SLOT) if e else 0)
        self.mx(g, S, t)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        S = self.state(0.0)
        S["pose"] = "walk" if t < 2.4 else ("raise" if 3.4 < t < 4.0 else "idle")
        S["face"] = "happy" if 3.4 < t < 4.4 else "normal"
        S["x"] = lerp(-12, XA, ease_out(span(t, 0, 2.4)))
        drop = span(t, 0.6, 1.2)
        self.stage(g, t, S, lit=t > 4.6, renew_drop=drop)
        if 1.2 <= t < 1.2 + dt * 1.5 and self.once("enter-drop"):
            self.puffs.emit(STK[0] - 2, DESK_Y - 2, vx=-12, vy=-3, life=0.6, rmax=1.8)
            self.puffs.emit(STK[1] + 2, DESK_Y - 2, vx=12, vy=-3, life=0.6, rmax=1.8)
        if 1.2 <= t < 1.45:
            pix.shake(g, t, 1.2)
        if 4.0 < t < 4.6:  # 剑指点烛
            S["pose"] = "point"
            q = span(t, 4.0, 4.6)
            star4(g, lerp(XA + 15, CANDLE_X, q), lerp(44, DESK_Y - 17, q) - math.sin(q * math.pi) * 14, big=True)
        if 4.6 <= t < 4.6 + dt * 1.5 and self.once("enter-lit"):
            self.sparks.burst(CANDLE_X, DESK_Y - 17, 10, 20, up=8, life=0.5)
        self.dao(g, t, S)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, S, t)
        self.counter(g, S)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        if e >= self.CYCLE and u < LEAD:
            return self.renew(g, t, e, u, dt)
        S = self.state(u)
        self.render(g, t, e, S, dt)
        self.counter(g, S)

    def renew(self, g: Gfx, t: float, e: float, u: float, dt: float):
        """续：盖好的一叠扎红绳 → 蹦起飞出画外 → 新的一叠白文书从天而降"""
        S = self.state(LEAD + PER * SLOT + 1)
        S["pose"] = "point" if u < 2.6 else ("gongshou" if 4.0 < u < 5.4 else "idle")
        S["face"] = "happy" if u > 3.4 else "normal"
        tied = span(u, 0.3, 1.2)
        fly = span(u, 1.4, 2.6)
        dx = ease_in(fly) * 60
        dy = -math.sin(min(fly * 1.4, 1) * math.pi) * 10 if fly > 0 else 0
        hop = span(u, 1.2, 1.4)
        dy -= math.sin(hop * math.pi) * 3
        drop = span(u, 2.6, 3.4)
        S["blank"] = 0 if drop <= 0 else PER
        self.stage(g, t, S, renew_drop=drop if drop < 1 else None, tied=tied, done_dy=dy, done_dx=dx)
        if 0 < fly < 1 and int(u * 20) % 2 == 0:
            self.sparks.burst(88 + dx, DESK_Y - 8 + dy, 1, 8, life=0.4, gravity=20)
        if 3.4 <= u < 3.4 + dt * 1.5 and self.once(("renew-drop", int(e // self.CYCLE))):
            self.puffs.emit(STK[0] - 2, DESK_Y - 2, vx=-12, vy=-3, life=0.6, rmax=1.8)
            self.puffs.emit(STK[1] + 2, DESK_Y - 2, vx=12, vy=-3, life=0.6, rmax=1.8)
        if 3.4 <= u < 3.65:
            pix.shake(g, t, 1.2)
        if tied > 0.7 and u < 1.6:
            star4(g, 88, DESK_Y - 1 - 2 * stack_rows(PER) - 4, big=int(t * 10) % 2 == 0)
        self.dao(g, t, S)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_seal(g, dy=-int(fly * 8) if u < 2.6 else -int((1 - drop) * 8))
        vbox(g, CNT_X, 10, f"第{cn_num(1)}印" if u > 3.4 else "成叠")

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        S = self.state(e % self.CYCLE) if not (e >= self.CYCLE and e % self.CYCLE < LEAD) else self.state(0.0)
        q = ease_in_out(span(t, 0.0, 0.6))
        R = dict(S)
        if S["seal"] == "hand" or S["pose"] is None:
            h0 = S["hand"] or PAD_HAND
            R.update(x=lerp(S["x"], XA, q), hand=(lerp(h0[0], PAD_HAND[0], q), lerp(h0[1], PAD_HAND[1], q)),
                     legs="stand", hop=lerp(S.get("hop", 0), 0, q), squash=False, hit=False, star=False)
            if q >= 1:
                R.update(seal="pad", pose="gongshou" if t > 0.9 else "idle")
        else:
            R["pose"] = "gongshou" if t > 0.5 else S["pose"]
        if t > 1.1:
            R["face"] = "sleep"
        if S["sheet"]:
            cx, cy, sx, sy, sh = S["sheet"]
            R["sheet"] = (lerp(cx, 88, q), lerp(cy, DESK_Y - 4, q), max(0.15, sx * (1 - q)), max(0.1, sy * (1 - q)), None) \
                if q < 1 else None
        R["point_star"] = None
        self.stage(g, t, R, lit=t < 0.8, lid=span(t, 0.7, 1.1) if R["seal"] == "pad" else 0.0)
        if 0.8 <= t < 0.8 + dt * 1.5 and self.once(("int-puff", round(e))):
            self.puffs.emit(CANDLE_X, DESK_Y - 17, vy=-6, life=1.2, rmax=1.8, spread=0)
        self.dao(g, t, R)
        self.sheet(g, R["sheet"], t)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_seal(g)
        vbox(g, CNT_X, 10, "暂歇")

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        S = self.state(u) if not (e >= self.CYCLE and u < LEAD) else self.state(LEAD + PER * SLOT + 1)
        if t < 1.0:  # 揭盖、剑指点烛
            R = dict(S, x=XA, pose="point" if t < 0.7 else "idle", seal="pad", sheet=None, hand=None, face="normal",
                     hop=0, point_star=None)
            self.stage(g, t, R, lit=t > 0.7, lid=1 - span(t, 0.0, 0.3))
            h = self.dao(g, t, R)
            q = span(t, 0.2, 0.7)
            if 0 < q < 1:
                star4(g, lerp(h["hand"][0], CANDLE_X, q), lerp(h["hand"][1], DESK_Y - 17, q) - math.sin(q * math.pi) * 14,
                      big=True)
            if 0.7 <= t < 0.7 + dt * 1.5 and self.once(("res-lit", round(e))):
                self.sparks.burst(CANDLE_X, DESK_Y - 17, 10, 20, up=8, life=0.5)
            mx_seal(g)
        else:  # 回到刚才的动作
            q = ease_in_out(span(t, 1.0, 1.7))
            R = dict(S)
            if S["pose"] is None:
                h1 = S["hand"]
                R.update(x=lerp(XA, S["x"], q), hand=(lerp(PAD_HAND[0], h1[0], q), lerp(PAD_HAND[1], h1[1], q)),
                         hop=S.get("hop", 0) * q, hit=False)
                if S["seal"] == "pad":
                    R["seal"] = "pad"
            if S["sheet"] and q < 1:
                cx, cy, sx, sy, sh = S["sheet"]
                R["sheet"] = (cx, cy, max(0.15, sx * q), max(0.1, sy * q), None)
            self.stage(g, t, R)
            self.dao(g, t, R)
            self.sheet(g, R["sheet"], t)
            self.mx(g, R, t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.counter(g, S)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        S = self.state(LEAD + PER * SLOT + 1)
        S["done"] = PER
        S["blank"] = 0
        S["seal"] = "air"
        S["pose"] = "raise" if t < 1.8 else ("kneel" if 2.4 < t < 4.6 else "gongshou")
        S["face"] = "wow" if 1.8 < t < 2.4 else ("happy" if t > 2.4 else "normal")
        self.stage(g, t, S)
        h = self.dao(g, t, S)["hand"]
        big = ease_out_back(span(t, 0.5, 1.2))
        cx, cy = 66, 25
        if big > 0:  # 一张大文书升到正中
            w, hh = 42 * big, 42 * big
            g.d.rectangle((cx - w / 2 - 1, cy - hh / 2 - 1, cx + w / 2 + 1, cy + hh / 2 + 1), fill=0)
            g.d.rectangle((cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2), fill=1)
            if big > 0.9:
                for j, x in enumerate((cx + 17, cx + 14)):  # 疏文
                    for y in range(int(cy - 18), int(cy - 14 + j * 2), 2):
                        g.px(x, y, 0)
        if t >= 1.8:
            pix.blit(g, big_face(), cx - 18, cy - 17, outline=False)
        if t < 1.8:  # 法印从手里飞起、变大、砸下
            q = span(t, 0.9, 1.8)
            sx = lerp(h[0] - 5, cx - 16, ease_in_out(q))
            sy = lerp(h[1] - 12, cy - 30, ease_out(q)) + ease_in(span(t, 1.5, 1.8)) * 14
            sc = 1 + 2 * ease_out(q)
            spr = pix.stretch(seal_spr(), sc, sc)
            pix.blit(g, spr, sx + 16 - spr.w / 2 if q > 0 else h[0] - 5, sy if q > 0 else h[1] - 12)
            if q > 0 and int(t * 12) % 2 == 0:
                self.sparks.burst(sx + 16, sy, 1, 10, life=0.4, gravity=10)
        elif t < 2.1:  # 压扁的大印
            spr = pix.stretch(seal_spr(), 3.6, 1.6)
            pix.blit(g, spr, cx - spr.w / 2, cy + 18 - spr.h)
        if 1.8 <= t < 1.8 + dt * 1.5 and self.once(("comp-hit", round(e))):
            pix.flash(g)
            self.sparks.burst(cx, cy, 36, 50, up=10, life=1.2, gravity=30)
        if 1.8 <= t < 2.2:
            pix.shake(g, t, 2.0)
        if t > 2.0:
            for j in range(3):
                r = (t - 2.0) * 24 - j * 10
                if r > 0:
                    ring(g, cx, cy, 24 + r, step=2, sy=0.9)
            for j in range(4):
                if int(t * 5 + j) % 4 == 0:
                    star4(g, cx + (-26, 26, -24, 24)[j], cy + (-14, -10, 12, 16)[j], big=True)
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_seal(g, inv=t > 1.8 and int(t * 4) % 2 == 0)
        if t > 1.8:
            g.mx_level = 1 + int(6 * (1 - span(t, 1.8, 3.4)))
        vbox(g, CNT_X, 10, "印成" if t > 1.8 else "道经师宝")
