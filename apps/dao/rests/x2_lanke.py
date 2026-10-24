"""烂柯：任昉《述异记》王质观棋——“见童子数人棋而歌，质因听之。童子以一物与质，如枣核，质含之，不觉饥。
俄顷，童子谓曰：何不去？质起视，斧柯烂尽。既归，无复时人。”

山中空地，一方石枰（略俯视，刻着棋路）。小道士砍柴路过，把斧子靠在石头边，坐下与梳双髻的仙童对弈。
入场：石枰从地里弹起，仙童从石枰后冒出来，小道士扛着斧子走来，把斧子靠在石头边坐下。
持续（一局 96 秒）：两人你一子我一子（每 3 秒一手，落子“嗒”地一亮），背后日月每 10 秒轮转一次
      （山中一日、世上一年，夜里星星出来）；小道士的白胡子越长越长，斧柄一点点朽缺、长出蘑菇和青苔；
      第 30 秒仙童抛来一颗枣核，小道士含着嚼（“不觉饥”）。
      局终：斧柄烂断、斧头“当”地落地，小道士一惊；仙童问“何不去”，题“斧柯烂尽”；小道士捡起斧头
      走出画面，棋子收起，他又扛一把新斧子回来（胡子没了），再下一局。
退场：收圆。
点阵：小棋盘，最后一手闪烁，顶行一个点走过表示日月；斧头落地时换成斧头图标。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import TUFT, Clock, arm, iris, label, plate, put_arm, rock

FLOOR = 58
DX = 37                       # 小道士（盘坐，朝右）
KX = 93                       # 仙童（盘坐，朝左）
BX, BY = 46, 38               # 棋盘左上角
COLS, ROWS = 8, 3
GAME = 96.0
MOVE = 3.5
AXE = (17, FLOOR)             # 斧头着地点
DAY = 10.0


def cell(c: int, r: int):
    y = 2 + r * 3
    return BX + round(_colx(c, y)), BY + y


# ---------------------------------------------------------------- 造型

BW = 37                       # 石枰宽
FACE_H = 11                   # 枰面（俯视的梯形）高


def _colx(c: float, y: float) -> float:
    """第 c 路在枰面第 y 行的 x（近大远小）"""
    k = y / (FACE_H - 1)
    return BW / 2 - 0.5 + (c - (COLS - 1) / 2) * lerp(3.4, 4.2, k)


def _table():
    """石枰 37×24：枰面是俯视的梯形（浅色石面刻暗线，近宽远窄），厚枰沿，下面一块天然大石（裂纹、苔点、阴影）"""
    p = Part(BW, 24)
    p.shape("polygon", [(4, 0), (BW - 5, 0), (BW - 1, FACE_H - 1), (0, FACE_H - 1)], fill=1)
    p.d.polygon([(5, 1), (BW - 6, 1), (BW - 3, FACE_H - 2), (2, FACE_H - 2)], fill=0)
    for c in range(COLS):                                   # 纵线（往远处收），隔点刻
        x0, x1 = _colx(c, 1), _colx(c, FACE_H - 2)
        for y in range(2, FACE_H - 2):
            if y % 2 == 0 or y in (1, FACE_H - 3):
                p.px(round(lerp(x0, x1, (y - 1) / (FACE_H - 3))), y, 1)
    for r in range(ROWS):                                   # 横线
        y = 2 + r * 3
        if 1 < y < FACE_H - 2:
            for x in range(round(_colx(0, y)), round(_colx(COLS - 1, y)) + 1, 2):
                p.px(x, y, 1)
    p.shape("rectangle", (0, FACE_H, BW - 1, FACE_H + 2), fill=1)                     # 枰沿
    p.d.line((1, FACE_H + 1, BW - 2, FACE_H + 1), fill=0)
    p.dither((BW - 9, FACE_H, BW - 1, FACE_H + 2), 0.5, 0)
    top = FACE_H + 4
    p.shape("polygon", [(3, top), (BW - 4, top), (BW - 1, top + 3), (BW - 3, top + 6), (BW - 1, 23), (1, 23),
                        (3, top + 5), (1, top + 2)], fill=1)
    p.d.line((3, top + 2, 8, top + 1), fill=0)                                            # 石面的层理
    p.d.line((12, top + 4, 20, top + 3), fill=0)
    p.d.line((5, top + 6, 11, top + 7), fill=0)
    p.dither([(18, top), (BW, top), (BW, 24), (16, 24)], 0.5, 0)
    p.dither([(1, top + 5), (18, top + 5), (16, 24), (1, 24)], 0.25, 0)
    return p.sprite()


def _kid(reach: bool):
    """梳双髻的仙童（盘坐，朝左）16×23：头顶前后两个发髻扎红绳、绳尾飘在脑后；圆脸、短褂、腰带"""
    p = Part(17, 23)
    p.shape("ellipse", (8, 0, 12, 4), fill=1)              # 后髻
    p.shape("ellipse", (4, 1, 8, 5), fill=1)               # 前髻
    p.d.line((5, 4, 7, 4), fill=0)
    p.d.line((9, 4, 11, 3), fill=0)
    p.shape("line", (12, 4, 15, 7), fill=1)                # 发带尾巴
    p.shape("ellipse", (1, 4, 14, 15), fill=1)             # 头
    p.d.chord((3, 4, 14, 11), 200, 360, fill=0)            # 头发（只盖头顶和后脑）
    p.d.polygon([(10, 8), (13, 8), (13, 12), (11, 12)], fill=0)
    p.d.ellipse((1, 4, 14, 15), outline=1)
    p.px(7, 6, 1), p.px(8, 6, 1)                           # 发丝高光
    p.d.rectangle((3, 9, 3, 10), fill=0)                   # 眼（朝左）
    p.d.rectangle((7, 9, 7, 10), fill=0)
    p.px(2, 12, 0), p.px(8, 12, 0)                         # 腮
    p.px(4, 12, 0), p.px(5, 12, 0)                         # 嘴
    p.shape("polygon", [(4, 15), (11, 15), (13, 20), (2, 20)], fill=1)   # 短褂
    p.d.line((5, 15, 8, 18), fill=0)
    p.d.line((2, 18, 13, 18), fill=0)
    p.dither([(10, 16), (13, 16), (13, 19), (11, 19)], 0.5, 0)
    p.shape("ellipse", (0, 19, 16, 22), fill=1)            # 盘腿
    p.d.line((3, 20, 13, 20), fill=0)
    if not reach:
        p.shape("polygon", [(5, 15), (4, 19), (6, 19), (7, 15)], fill=1)
        p.d.line((5, 19, 6, 19), fill=0)
    return p.sprite()


def _axe_head():
    """斧头 9×7（刃朝右）：后面是銎（装柄的孔），刃口外张、一道磨亮的刃线"""
    return Sprite("""
 ##.
#..####
#..#####.
#..######
#..#####.
#..####
 ##.
""")


def _mushroom():
    return Sprite("""
 ###
#####
 .#.
  #
""")


def _beard(n: int):
    """白胡子：长 n 像素，尖下巴，两道暗须纹"""
    p = Part(6, max(n, 1) + 1)
    p.shape("polygon", [(0, 0), (5, 0), (4, n // 2), (3, n), (2, n), (1, n // 2)], fill=1)
    if n > 3:
        p.d.line((2, 1, 2, n - 2), fill=0)
        p.px(4, 2, 0)
    return p.sprite()


def _sun():
    return Sprite("""
 # # #
  ###
#######
 #####
#######
  ###
 # # #
""")


def _moon():
    return Sprite("""
  ###
 ##.
##.
##
##.
 ##.
  ###
""")


_P: dict = {}


def prop(name, *a):
    key = (name,) + a
    if key not in _P:
        _P[key] = {"table": _table, "kid": _kid, "axe": _axe_head, "mush": _mushroom, "beard": _beard,
                   "sun": _sun, "moon": _moon}[name](*a)
    return _P[key]


@register
class Lanke(Rest):
    id = "x2.lanke"
    name = "烂柯"
    desc = "小道士把斧子靠在石边与仙童对弈，日月飞转、白胡子越长越长、斧柄朽烂长蘑菇；局终斧头落地，“何不去”，换斧再来"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.ht = 0.0

    # ------------------------------------------------------------ 棋局（确定性）

    def moves(self, game: int):
        if getattr(self, "_mv_game", None) == game:
            return self._mv
        used, out = set(), []
        for i in range(24):
            mine = i % 2 == 0
            for j in range(20):
                c = int(rand(game * 131 + i * 7 + j, self.seed) * 5) + (0 if mine else 3)
                if j > 12:
                    c = int(rand(game * 131 + i * 7 + j, self.seed) * COLS)
                r = int(rand(game * 71 + i * 13 + j * 3, self.seed + 5) * ROWS)
                if (c, r) not in used:
                    break
            used.add((c, r))
            out.append((c, r, mine))
        self._mv_game, self._mv = game, out
        return out

    # ------------------------------------------------------------ 画面

    def sky(self, g: Gfx, t: float):
        """背后的山 + 日月轮转（山中一日）"""
        ph = (t % DAY) / DAY
        night = ph >= 0.5
        q = (ph % 0.5) / 0.5
        x = lerp(6, 118, q)
        y = 24 - math.sin(q * math.pi) * 18
        if night:
            for i in range(9):
                sx, sy = int(rand(i, 3) * 124) + 2, int(rand(i, 4) * 20) + 2
                if (t * 3 + i) % 4 > 0.6:
                    g.px(sx, sy)
        pix.blit(g, prop("moon" if night else "sun"), x - 3, y - 3)
        ridge = [(0, 36), (10, 30), (18, 33), (30, 24), (40, 30), (52, 27), (66, 34), (80, 26), (94, 31),
                 (106, 22), (118, 29), (127, 27)]
        g.d.polygon(ridge + [(127, FLOOR), (0, FLOOR)], fill=0)
        g.d.line(ridge, fill=1)
        for i in range(0, 128, 6):                 # 山脚的树
            yy = 36 + (i * 7) % 5
            g.px(i, yy), g.px(i + 1, yy - 1), g.px(i + 2, yy)
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
        for x in (4, 44, 84, 120):
            pix.blit(g, TUFT[(x // 4) % 3], x, FLOOR - 2, outline=False)

    def axe(self, g: Gfx, decay: float, snapped: float = -1.0, gone: bool = False):
        """靠在石头上的斧子：decay 0..1 斧柄朽烂（缺口、蘑菇、青苔）；snapped ≥ 0：断后几秒"""
        pix.blit(g, rock(13, 9), 2, FLOOR - 9)
        if gone:
            return
        hx, hy = AXE
        top = (7, 40)
        if snapped < 0:
            pts = 22
            for i in range(pts):
                k = i / (pts - 1)
                x, y = lerp(hx, top[0], k), lerp(hy - 4, top[1], k)
                if rand(i, 9) < decay * 0.55 and i > 3:
                    continue
                if k > 1 - decay * 0.25:
                    continue
                g.px(x, y), g.px(x + 1, y)
                if i % 5 == 2 and decay > 0.5:
                    g.px(x - 1, y, 0)
            if decay > 0.35:
                pix.blit(g, prop("mush"), lerp(hx, top[0], 0.45) - 1, lerp(hy - 4, top[1], 0.45) - 3)
            if decay > 0.65:
                pix.blit(g, prop("mush"), lerp(hx, top[0], 0.7) - 4, lerp(hy - 4, top[1], 0.7) - 2)
            pix.blit(g, prop("axe"), hx - 2, hy - 6)
        else:
            f = ease_out_bounce(span(snapped, 0, 0.6))
            ang = f * 1.2                                  # 斧头倒下
            pix.blit(g, prop("axe").rot90(-1) if f > 0.5 else prop("axe"), hx - 2 + f * 3, hy - 6 + f * 1)
            for i in range(6):                             # 断下来的一截柄躺在地上
                g.px(hx + 6 + i * 2, FLOOR - 1)

    def board(self, g: Gfx, game: int, n: int, t: float, fade: float = 0.0):
        mv = self.moves(game)
        for i, (c, r, mine) in enumerate(mv[:n]):
            if fade and rand(i, 77) < fade:
                continue
            x, y = cell(c, r)
            if mine:   # 黑子：亮圈暗心（扁圆）
                g.d.rectangle((x - 2, y - 1, x + 2, y + 1), fill=0)
                g.d.line((x - 1, y - 1, x + 1, y - 1), fill=1)
                g.d.line((x - 1, y + 1, x + 1, y + 1), fill=1)
                g.px(x - 2, y), g.px(x + 2, y)
            else:      # 白子：实心扁圆
                g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
                g.px(x - 2, y), g.px(x + 2, y)
            if i == n - 1 and int(t * 4) % 2 == 0:   # 最后一手闪一下
                g.d.rectangle((x - 2, y - 1, x + 2, y + 1), fill=0)
                g.px(x, y)

    def daoshi(self, g: Gfx, t: float, k: float, n: int, game: int, x: float | None = None, walk=None,
               beard: int = 0, face: str = "normal"):
        """下棋的小道士：轮到他时伸手落子；k 本局秒数"""
        if walk is not None:      # 走路（扛斧 / 拎斧头）
            spr, at = put_arm(4, -10, "fist", over=True) if walk == "shoulder" else put_arm(5, 9, "fist")
            h = figure(g, x, FLOOR, t, legs="walk", arm=spr, arm_at=at, face=face)
            hx, hy = h["hand"]
            if walk == "shoulder":   # 新斧子扛在肩上
                g.d.line((hx - 9, hy + 6, hx + 3, hy - 2), fill=1)
                pix.blit(g, prop("axe").rot90(1), hx - 12, hy + 3)
            elif walk == "head":
                pix.blit(g, prop("axe"), hx - 3, hy)
            return
        mine_turn = (int(k // MOVE) % 2 == 0)
        ph = (k % MOVE) / MOVE
        dx, dy = 8, 9
        if mine_turn and n < 24 and k < 84:
            c, r, _ = self.moves(game)[min(int(k // MOVE), 23)]
            cx, cy = cell(c, r)
            sx, sy = DX + 2, FLOOR - 18
            reach = span(ph, 0.25, 0.5) * (1 - span(ph, 0.62, 0.85))
            dx, dy = lerp(8, cx - sx, ease_in_out(reach)), lerp(9, cy - sy - 1, ease_in_out(reach))
        spr, at = put_arm(dx, dy, "pinch")

        def front(gg, at_):
            if beard > 0:
                pix.blit(gg, prop("beard", beard), DX + 1, FLOOR - 20)

        figure(g, DX if x is None else x, FLOOR, t, legs="sit", arm=spr, arm_at=at, face=face, front=front)

    def kid(self, g: Gfx, t: float, k: float, dy: float = 0.0):
        mine_turn = (int(k // MOVE) % 2 == 0)
        ph = (k % MOVE) / MOVE
        reach = (not mine_turn) and 0.2 < ph < 0.7 and k < 84
        bob = 1 if (t * 1.3) % 2 < 0.25 else 0              # 摇头晃脑地唱
        pix.blit(g, prop("kid", reach), KX - 8, FLOOR - 23 + dy + bob)
        return KX - 8, FLOOR - 23 + dy + bob

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, enter: float = 1.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        game = int(t // GAME) if on else 0
        k = t % GAME if on else 0.0
        n = min(int(k // MOVE + (1 if (k % MOVE) / MOVE > 0.5 else 0)), 24) if on else 0
        self.sky(g, t)
        decay = span(k, 3, 82) if on and k < 94 else 0.0
        snapped = k - 84 if on and 84 <= k < 94 else -1.0
        # 斧子
        if on and abs(k - 84) < dt * 1.01:                   # 斧柄烂断，斧头落地
            self.sparks.burst(AXE[0] + 2, FLOOR - 3, 14, 30, up=20, life=0.6, gravity=90)
            self.puffs.emit(AXE[0], FLOOR - 4, vy=-4, life=1.0, rmax=2.5)
        if on and 84 <= k < 84.3:
            pix.shake(g, t, 1.5)
        self.axe(g, decay, snapped, gone=on and 89.8 <= k < 94.0 or (not on and e3 < 2.0))
        # 石枰
        pop = ease_out_back(span(e3, 0.0, 0.6)) if not on else 1.0
        tdy = (1 - pop) * 24
        pix.blit(g, prop("table"), BX, BY - 1 + tdy)
        if tdy < 1:
            fade = span(k, 90.5, 92.5) if on else 0.0
            if not on or k < 92.5:
                self.board(g, game, n, t, fade)
            if on:
                mv = self.moves(game)
                if 0 < n <= 24 and abs(k - (n - 0.5) * MOVE) < dt * 1.01 and k < 84:
                    c, r, mine = mv[n - 1]
                    x, y = cell(c, r)
                    self.sparks.burst(x, y, 5, 12, up=8, life=0.3, gravity=30)
        # 仙童
        kdy = (1 - ease_out_back(span(e3, 0.5, 1.1))) * 20 if not on else 0.0
        kx, ky = self.kid(g, t, k, kdy)
        mine_turn = (int(k // MOVE) % 2 == 0)
        ph = (k % MOVE) / MOVE
        if on and not mine_turn and k < 84:                  # 仙童伸手落子
            c, r, _ = self.moves(game)[min(int(k // MOVE), 23)]
            cx, cy = cell(c, r)
            reach = ease_in_out(span(ph, 0.25, 0.5) * (1 - span(ph, 0.62, 0.85)))
            sx, sy = kx + 5, ky + 15
            hx, hy = lerp(sx - 3, cx + 1, reach), lerp(sy + 2, cy - 1, reach)
            g.d.line((sx, sy, hx, hy), fill=1, width=2)
            g.d.rectangle((hx - 1, hy - 1, hx + 1, hy), fill=1)
        # 小道士
        face = "normal"
        beard = int(span(k, 6, 84) * 10) if on else 0
        if on and 84 <= k < 86.5:
            face = "wow"
        chew = on and 31.0 <= k < 35.0
        if chew:
            face = "happy" if int(t * 5) % 2 else "sleep"
        if not on:
            if e3 < 2.0:
                self.daoshi(g, t, 0, 0, 0, x=lerp(-14, DX - 6, ease_out(span(e3, 0.6, 2.0))), walk="shoulder")
            else:
                pop2 = ease_out_back(span(e3, 2.0, 2.4))
                self.daoshi(g, t, 0, 0, 0, face=face)
        elif k < 89.0:
            self.daoshi(g, t, k, n, game, beard=beard, face=face)
        elif k < 92.0:      # 起身捡斧头，走出去
            w = span(k, 89.5, 92.0)
            if k < 89.5:
                figure(g, DX, FLOOR, t, arm="down", face="wow")
            else:
                self.daoshi(g, t, k, n, game, x=lerp(DX - 6, -16, ease_in(w)), walk="head", face="normal")
        elif k < 94.0:      # 扛着新斧子回来
            self.daoshi(g, t, k, n, game, x=lerp(-16, DX - 6, ease_out(span(k, 92.0, 94.0))), walk="shoulder")
        else:
            self.daoshi(g, t, k, n, game, face=face)
        # 枣核：仙童抛来，小道士接住含着
        if on and 30.0 <= k < 31.0:
            q = span(k, 30.0, 31.0)
            x0, y0 = kx + 2, ky + 12
            x1, y1 = DX + 4, FLOOR - 20
            px_, py_ = lerp(x0, x1, q), lerp(y0, y1, q) - math.sin(q * math.pi) * 14
            g.d.rectangle((px_ - 1, py_, px_, py_ + 1), fill=1)
            g.px(px_ + 1, py_ + 1, 0)
        if on and abs(k - 31.0) < dt * 1.01:
            self.sparks.burst(DX + 4, FLOOR - 21, 6, 14, up=6, life=0.4, gravity=0)
        if on and abs(k - 92.6) < dt * 1.01:                 # 收子：一团烟
            self.puffs.emit(BX + 16, BY + 3, vy=-6, life=1.0, rmax=3, spread=10)
            self.puffs.emit(BX + 8, BY + 3, vy=-5, life=0.9, rmax=2, spread=6)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 字
        if on and 85.0 <= k < 88.8:     # 仙童问：何不去
            bx, by = 82, 15
            w = 38
            plate(g, (bx - 2, by - 3, bx + w, by + 12), frame=True)
            g.d.line((bx + 26, by + 13, bx + 29, by + 16), fill=1)
            g.d.line((bx + 27, by + 13, bx + 29, by + 15), fill=0)
            label(g, bx + 1, by, "何不去", pad=0)
        if on and 89.0 <= k < 94.5:
            label(g, 64, 2, "斧柯烂尽", align="center")
        return k, n, game, snapped

    def mx(self, g: Gfx, t: float, k: float, n: int, game: int, snapped: float):
        if 0 <= snapped < 4:                      # 斧头图标
            g.mx_blit("""
..####..
.######.
########
.###.##.
.....#..
.....#..
....#...
....#...
""")
            return
        g.mx[7, :] = True                         # 棋盘边
        g.mx[1, :] = True
        ph = (t % DAY) / DAY
        g.mx[0, min(7, int((ph % 0.5) / 0.5 * 8))] = True
        if ph >= 0.5:
            g.mx[0, int(t * 3) % 8] = True
        mv = self.moves(game)
        for i, (c, r, mine) in enumerate(mv[:n]):
            yy = 2 + r * 1 + (r >= 2) * 0
            on = True
            if i == n - 1:
                on = int(t * 4) % 2 == 0
            if mine:
                g.mx[2 + r * 2, c] = on
            else:
                g.mx[2 + r * 2, c] = on if (int(t * 2) % 2 or i != n - 1) else False

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, min(t / self.T["enter"], 0.999))
        g.mx[7, :] = True
        g.mx[6, 1:7] = t > 0.6

    def hold(self, g: Gfx, t: float):
        self.ht = t
        k, n, game, sn = self.scene(g, t)
        self.mx(g, t, k, n, game, sn)

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        k, n, game, sn = self.scene(g, tt)
        self.mx(g, tt, k, n, game, sn)
        iris(g, t / self.T["exit"], 64, 40)
