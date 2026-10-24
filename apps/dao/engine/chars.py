"""角色：Q 版小道士（贯穿全部场景的主角），像素风，约 24×32。

身体由清晰的像素形状（无抗锯齿）拼成，再逐像素加细节：大眼睛带高光、眉、腮红网点、发髻插簪、
交领、腰带与结、袖口镶边、衣褶、背光面网点阴影、鞋底。部件之间自动描 1 像素黑边。
每个动作的每一帧只生成一次（缓存）。

    daoshi(g, x, y, pose="idle", t=0.0, flip=False, face="normal")
        (x, y) = 两脚中间的地面点；朝右画，flip=True 朝左
        pose：idle 站（呼吸、眨眼）/ walk 走 / offer 双手前伸 / gongshou 拱手 / bow 作揖鞠躬 /
              raise 举手 / point 剑指前指 / sit 盘坐 / meditate 闭目打坐 / kneel 跪拜 / sleep 坐着睡
        face：normal / sleep / happy / wow
        返回 {"hand": (x, y)}：手的位置（拿香、笔、剑、铃）

    figure(g, x, y, t, legs=..., arm=自己画的 Sprite, arm_at=(dx, dy), head=..., face=..., behind=, front=)
        自由拼装新动作（扫地、劈柴、抚琴、喝茶……）：手臂用 Part 自己画（设 spr.hand），道具在 behind/front 里画
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from .gfx import Gfx, Sprite
from .pix import blit

_CACHE: dict = {}


class _Part:
    """在小画布上画一个部件：on = 亮像素，mask = 不透明范围"""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.on = Image.new("1", (w, h))
        self.mk = Image.new("1", (w, h))
        self.d = ImageDraw.Draw(self.on)
        self.m = ImageDraw.Draw(self.mk)

    def shape(self, fn, *a, fill=1, **k):
        """fn 为 ImageDraw 的方法名：同时画进 on（fill）与 mask"""
        getattr(self.d, fn)(*a, fill=fill, **k)
        getattr(self.m, fn)(*a, fill=1, **k)

    def px(self, x, y, v=1):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.on.putpixel((x, y), v)
            self.mk.putpixel((x, y), 1)

    def dither(self, box_or_poly, level=0.5, v=0):
        """在已画区域里加网点（阴影）：v=0 挖暗点，v=1 加亮点"""
        m = Image.new("1", (self.w, self.h))
        dm = ImageDraw.Draw(m)
        if len(box_or_poly) == 4 and not isinstance(box_or_poly[0], tuple):
            dm.rectangle(box_or_poly, fill=1)
        else:
            dm.polygon(box_or_poly, fill=1)
        a = np.array(m, bool) & np.array(self.mk, bool)
        ys, xs = np.mgrid[0:self.h, 0:self.w]
        pat = ((xs + ys) % 2 == 0) if level >= 0.5 else ((xs % 2 == 0) & (ys % 2 == 0))
        on = np.array(self.on, bool)
        on[a & pat] = bool(v)
        self.on = Image.fromarray(on)
        self.d = ImageDraw.Draw(self.on)

    def sprite(self) -> Sprite:
        return Sprite(on=np.array(self.on, bool), mask=np.array(self.mk, bool))


def _head(blink=False, look=0, bow=False, face="normal") -> tuple[Sprite, int, int]:
    """头 17×17：大圆脸，头发只盖头顶和后脑；发髻插簪。返回 (精灵, 颈部 x, y)"""
    p = _Part(17, 17)
    p.shape("ellipse", (6, 0, 11, 5), fill=0)        # 发髻
    p.d.ellipse((6, 0, 11, 5), outline=1)
    p.d.line((8, 1, 9, 1), fill=1)
    p.shape("line", (4, 2, 13, 2), fill=1)          # 簪（短）
    p.shape("ellipse", (1, 3, 15, 16), fill=1)      # 脸
    p.d.chord((2, 4, 14, 13), 180, 360, fill=0)     # 头顶的头发（只到额头）
    p.d.polygon([(2, 8), (5, 8), (5, 12), (3, 13)], fill=0)  # 后脑
    p.d.ellipse((1, 3, 15, 16), outline=1)
    p.d.line((5, 5, 8, 4), fill=1)                  # 发丝高光
    p.px(10, 9, 0), p.px(11, 9, 0), p.px(13, 9, 0)  # 刘海碎发
    if bow:
        return p.sprite(), 8, 16
    ex = 8 + look
    if face == "sleep":   # 闭眼（下弯的线）
        for x in (ex, ex + 4):
            p.d.line((x, 12, x + 1, 12), fill=0)
            p.px(x - 1, 11, 0) if x == ex else p.px(x + 2, 11, 0)
        p.d.line((ex + 2, 14, ex + 3, 14), fill=0)
        return p.sprite(), 8, 16
    if face == "happy":   # 笑眼 ^^、张嘴笑
        for x in (ex, ex + 4):
            p.px(x, 12, 0), p.px(x + 1, 11, 0), p.px(x + 2, 12, 0)
        p.d.rectangle((ex + 2, 14, ex + 3, 15), fill=0)
        p.px(ex - 1, 14, 0), p.px(ex + 6, 14, 0)
        return p.sprite(), 8, 16
    if face == "wow":     # 惊讶：圆眼、o 嘴
        for x in (ex, ex + 4):
            p.d.rectangle((x, 10, x + 1, 12), fill=0)
        p.d.rectangle((ex + 2, 13, ex + 3, 15), outline=0)
        return p.sprite(), 8, 16
    if blink:
        p.d.line((ex, 12, ex + 1, 12), fill=0)
        p.d.line((ex + 4, 12, ex + 5, 12), fill=0)
    else:
        for x in (ex, ex + 4):
            p.d.rectangle((x, 10, x + 1, 12), fill=0)
            p.px(x, 10)                               # 眼睛高光
    p.px(ex - 1, 14, 0), p.px(ex + 6, 14, 0)       # 腮红
    p.d.line((ex + 2, 14, ex + 3, 14), fill=0)      # 嘴
    return p.sprite(), 8, 16


def _torso(breath=False) -> Sprite:
    """袍身（不含袖）15×16：上窄下宽；一道交领、腰带与小结、下摆一道边；背光面窄条网点"""
    p = _Part(15, 16)
    top = 1 if breath else 0
    p.shape("polygon", [(4, top), (10, top), (12, 6), (14, 14), (0, 14), (2, 6)], fill=1)
    p.d.line((5, top, 9, 5), fill=0)                 # 交领（右衽）
    p.d.line((1, 7, 13, 7), fill=0)                  # 腰带
    p.px(7, 7), p.px(7, 8, 0), p.px(6, 8, 0)         # 结
    p.d.line((0, 12, 14, 12), fill=0)                # 下摆镶边
    p.dither([(12, 8), (14, 14), (12, 14)], 0.5, 0)  # 背光面
    return p.sprite()


def _sleeve(kind="down") -> tuple[Sprite, int, int]:
    """袖子。返回 (精灵, 肩部挂点 x, y)、手的位置在 Sprite 上的坐标存在属性里"""
    if kind == "down":   # 垂手：钟形宽袖，袖口镶边，露手
        p = _Part(9, 14)
        p.shape("polygon", [(2, 0), (5, 0), (8, 11), (0, 11)], fill=1)
        p.d.line((0, 10, 8, 10), fill=0)
        p.dither([(5, 3), (8, 11), (6, 11)], 0.5, 0)
        p.shape("rectangle", (3, 11, 5, 13), fill=1)   # 手
        p.px(3, 13, 0)
        spr = p.sprite()
        spr.hand = (4, 13)
        return spr, 3, 0
    if kind == "offer":  # 双手平伸向前（捧香 / 捧物）
        p = _Part(14, 9)
        p.shape("polygon", [(0, 0), (4, 0), (10, 3), (10, 7), (2, 7), (0, 5)], fill=1)
        p.d.line((9, 3, 9, 7), fill=0)
        p.dither([(2, 5), (10, 5), (10, 7), (2, 7)], 0.5, 0)
        p.shape("rectangle", (10, 3, 12, 6), fill=1)
        p.d.line((11, 4, 12, 4), fill=0)               # 指缝
        spr = p.sprite()
        spr.hand = (12, 4)
        return spr, 1, 0
    if kind == "gong":   # 拱手：两袖在胸前合拢，左手包右拳
        p = _Part(12, 9)
        p.shape("polygon", [(0, 0), (4, 0), (9, 2), (11, 5), (9, 8), (1, 8)], fill=1)
        p.d.line((8, 2, 8, 8), fill=0)
        p.shape("ellipse", (8, 2, 11, 6), fill=1)
        p.d.arc((8, 2, 11, 6), 90, 270, fill=0)
        p.dither([(1, 6), (9, 6), (9, 8), (1, 8)], 0.5, 0)
        spr = p.sprite()
        spr.hand = (10, 4)
        return spr, 1, 0
    if kind == "raise":  # 举手过头：手臂斜向上，宽袖从小臂垂下
        p = _Part(10, 16)
        p.shape("polygon", [(0, 15), (3, 15), (8, 3), (6, 1)], fill=1)     # 手臂（袖筒）
        p.shape("polygon", [(2, 13), (6, 6), (6, 12), (3, 15)], fill=1)    # 下垂的袖子
        p.d.line((6, 7, 6, 12), fill=0)                                    # 袖口内侧
        p.dither([(3, 13), (6, 9), (6, 12), (3, 15)], 0.5, 0)
        p.shape("rectangle", (6, 0, 8, 2), fill=1)                          # 手
        p.d.line((7, 0, 8, 0), fill=0)
        spr = p.sprite()
        spr.hand = (7, 0)
        return spr, 1, 15
    if kind == "point":  # 剑指前指：食中二指并拢伸直
        p = _Part(16, 8)
        p.shape("polygon", [(0, 0), (4, 0), (10, 2), (10, 5), (2, 6), (0, 4)], fill=1)
        p.d.line((9, 2, 9, 5), fill=0)
        p.dither([(2, 4), (10, 4), (10, 6), (2, 6)], 0.5, 0)
        p.shape("rectangle", (10, 2, 12, 5), fill=1)
        p.shape("line", (12, 3, 15, 3), fill=1)
        p.shape("line", (12, 2, 15, 2), fill=1)
        spr = p.sprite()
        spr.hand = (15, 2)
        return spr, 1, 0
    raise ValueError(kind)


def _feet(frame=0) -> Sprite:
    """两只白色圆头布鞋"""
    p = _Part(15, 3)
    offs = [(1, 9), (3, 7), (0, 10)][frame % 3]
    for ox in offs:
        p.shape("ellipse", (ox, 0, ox + 4, 2), fill=1)
    return p.sprite()


def _get(key, fn):
    v = _CACHE.get(key)
    if v is None:
        v = _CACHE[key] = fn()
    return v


ARM_AT = {  # 各种袖子挂在身上的位置（相对脚底中点，按朝右）
    "down": (-1, -16), "offer": (-3, -16), "gong": (-3, -16), "raise": (3, -31), "point": (-3, -16),
}


def arm_sprite(kind: str) -> Sprite:
    """内置袖子：down 垂手 / offer 前伸 / gong 拱手 / raise 举手 / point 剑指"""
    return _get(("sleeve", kind), lambda: _sleeve(kind)[0])


def figure(g: Gfx, x: float, y: float, t: float = 0.0, legs: str = "stand", arm="down", arm_at=None,
           head: str = "up", face: str = "normal", flip: bool = False, bob: bool = True, dy: int = 0,
           behind=None, front=None) -> dict:
    """自由拼装小道士（自定义动作用）。
    legs：stand / walk / sit（盘坐）/ kneel（跪坐）
    arm：内置袖子名，或自己画的 Sprite（用 Part 画，设 .hand=(x,y) 表示手在精灵里的位置）；None 不画手臂
    arm_at：手臂精灵左上角相对脚底中点的偏移（自定义手臂时必给）；手臂精灵设 .over_head=True 时画在头前面
    head：up 抬头 / bow 低头；face：normal / sleep / happy / wow（normal 会自动眨眼）
    behind(g, at) / front(g, at)：在身体后面 / 前面画东西的回调；at(dx, dy, sprite) 按同一坐标系贴精灵
    返回 {"hand": (x, y)}（屏幕坐标）"""
    x, y = int(round(x)), int(round(y)) + dy

    def at(ox, oy, spr):
        px = x + ox if not flip else x - ox - spr.w
        blit(g, spr, px, y + oy, flip=flip)

    def pt(ox, oy):
        return (x + ox if not flip else x - ox, y + oy)

    breath = bob and (t * 0.7) % 1 > 0.5
    lift = 1 if breath and legs == "stand" else 0
    blink = face == "normal" and (t % 3.7) < 0.12
    torso = _get(("torso", breath), lambda: _torso(breath))
    if head == "bow":
        hd = _get(("head", False, 0, True, face), lambda: _head(False, 0, True, face))[0]
    else:
        hd = _get(("head", blink, 0, False, face), lambda: _head(blink, 0, False, face))[0]
    if behind:
        behind(g, at)
    bounce = 0
    if legs == "walk":
        step = int(t * 8) % 4
        bounce = step % 2
        at(-7, -2, _get(("feet", step % 3), lambda: _feet(step % 3)))
        at(-7, -18 - bounce, torso)
        body_top = -33 - bounce
    elif legs == "sit":
        at(-11, -5, _get(("legs_sit",), _sit_legs))
        at(-7, -19 + lift, torso)
        body_top = -34 + lift
    elif legs == "kneel":
        at(-9, -5, _get(("legs_kneel",), _kneel_legs))
        at(-6, -17, torso)
        body_top = -31
    else:
        at(-7, -2, _get(("feet", 0), lambda: _feet(0)))
        at(-7, -18 + lift, torso)
        body_top = -33 + lift
    out = {}
    arm_over_head = arm == "raise" or getattr(arm, "over_head", False)

    def draw_arm():
        spr = arm_sprite(arm) if isinstance(arm, str) else arm
        ox, oy = arm_at if arm_at is not None else ARM_AT[arm]
        oy += lift - bounce if legs in ("stand", "walk") else (-3 if legs == "sit" else 2 if legs == "kneel" else 0)
        if legs == "walk" and arm == "down":
            ox += int(round(math.sin(t * 8 * math.pi / 2) * 1.5))
        at(ox, oy, spr)
        hx, hy = getattr(spr, "hand", (spr.w // 2, spr.h - 1))
        out["hand"] = pt(ox + hx, oy + hy)

    if arm is not None and not arm_over_head:
        draw_arm()
    if head == "bow":
        at(-6 if legs != "kneel" else -1, body_top + 3 if legs != "kneel" else body_top + 7, hd)
    else:
        at(-8, body_top, hd)
    if arm is not None and arm_over_head:  # 举过头顶的手臂画在头前面
        draw_arm()
    if front:
        front(g, at)
    return out


def daoshi(g: Gfx, x: float, y: float, pose: str = "idle", t: float = 0.0, flip: bool = False,
           face: str = "normal", bob: bool = True) -> dict:
    """常用动作：idle 站 / walk 走 / offer 双手前伸 / gongshou 拱手 / bow 作揖鞠躬 / raise 举手 /
    point 剑指 / sit 盘坐（拱手）/ meditate 盘坐闭目 / kneel 跪拜 / sleep 坐着睡"""
    P = {
        "idle": dict(arm="down"), "walk": dict(legs="walk", arm="down"), "offer": dict(arm="offer"),
        "gongshou": dict(arm="gong"), "bow": dict(arm="gong", head="bow"), "raise": dict(arm="raise"),
        "point": dict(arm="point"), "sit": dict(legs="sit", arm="gong"),
        "meditate": dict(legs="sit", arm="gong", face="sleep"), "kneel": dict(legs="kneel", arm="gong", head="bow"),
        "sleep": dict(legs="sit", arm="gong", face="sleep", head="bow"),
    }[pose]
    if face != "normal" and "face" not in P:
        P["face"] = face
    return figure(g, x, y, t, flip=flip, bob=bob, **P)


Part = _Part  # 公开：自己画手臂 / 道具 / 新部件


def _sit_legs() -> Sprite:
    p = _Part(22, 6)
    p.shape("ellipse", (0, 0, 21, 6), fill=1)
    p.d.line((3, 3, 18, 3), fill=0)
    p.dither([(12, 3), (21, 3), (21, 6), (12, 6)], 0.5, 0)
    p.shape("rectangle", (16, 1, 19, 3), fill=0)
    p.d.line((16, 3, 19, 3), fill=1)
    return p.sprite()


def _kneel_legs() -> Sprite:
    """跪坐：小腿压在身下（侧面），脚掌在后"""
    p = _Part(19, 6)
    p.shape("polygon", [(0, 5), (1, 1), (14, 1), (16, 5)], fill=1)
    p.d.line((2, 3, 13, 3), fill=0)
    p.dither([(9, 3), (16, 3), (16, 5), (9, 5)], 0.5, 0)
    p.shape("ellipse", (0, 2, 4, 5), fill=1)      # 脚底朝后
    p.d.line((1, 4, 3, 4), fill=0)
    return p.sprite()
