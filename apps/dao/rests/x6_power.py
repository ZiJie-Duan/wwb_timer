"""x6 赛博歇（一）：电源与散热——插电、散热、待机（像素风，小道士出镜）"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from ..engine.symbols import taiji
from .x6_common import (FLOOR, Clock, bezier, cable, crossed, cushion, cyc, eye_open, head_box, mx_icon, sit, spr)


def _lattice():
    """方格窗 27×21：双线窗框、窗棂（井字 + 回纹角花）"""
    p = Part(27, 21)
    for box in ((0, 0, 26, 1), (0, 19, 26, 20), (0, 0, 1, 20), (25, 0, 26, 20)):   # 窗框（只画框，窗格透明）
        p.shape("rectangle", box, fill=1)
    p.d.line((1, 1, 25, 1), fill=0)
    for x in (9, 17):
        p.shape("line", (x, 2, x, 18), fill=1)
    p.shape("line", (2, 10, 24, 10), fill=1)
    for cx, cy in ((9, 10), (17, 10)):  # 交叉处的小方块
        p.shape("rectangle", (cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
    return p.sprite()


def night_window(g: Gfx, x: int, y: int, t: float):
    """夜窗：窗棂后一弯月、两颗星闪"""
    g.d.ellipse((x + 18, y + 2, x + 24, y + 8), fill=1)
    g.d.ellipse((x + 16, y + 1, x + 22, y + 7), fill=0)
    for i, (sx, sy) in enumerate(((5, 5), (6, 14), (22, 15))):
        if (t * 0.7 + i * 0.37) % 1 < 0.7:
            g.px(x + sx, y + sy)
    pix.blit(g, spr("lattice", _lattice), x, y, outline=False)
    g.d.line((x + 2, y + 21, x + 24, y + 21), fill=1)  # 窗台
    g.d.line((x, y + 22, x + 26, y + 22), fill=1)


def _port():
    """背上的充电口：一截插头 4×5"""
    p = Part(5, 5)
    p.shape("rectangle", (0, 0, 3, 4), fill=1)
    p.d.line((1, 1, 1, 3), fill=0)
    p.shape("rectangle", (4, 1, 4, 3), fill=1)
    return p.sprite()


def room_floor(g: Gfx, base: bool = True):
    """木地板：地面线 + 透视板缝 + 稀网点；踢脚线"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-30, 170, 18):
        g.d.line((x, FLOOR + 1, x - 10, 63), fill=1)
    pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)
    if base:
        g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)


def spark_star(g: Gfx, x: float, y: float, p: float, r: float = 6):
    """“噼”一下的火花：八道放射短线，p 0..1"""
    if not 0 <= p < 1:
        return
    for i in range(8):
        a = i * math.pi / 4
        r0, r1 = 1 + r * p, 2 + r * min(1, p + 0.4) * (0.6 if i % 2 else 1)
        g.d.line((x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a) * r1, y + math.sin(a) * r1), fill=1)


# ====================================================================== 插电

def _socket():
    """墙上五孔插座 15×17（正视）：圆角面板、内框阴线、上两孔、下三孔（一竖 + 八字）、螺丝"""
    p = Part(15, 17)
    p.shape("rounded_rectangle", (0, 0, 14, 16), radius=2, fill=1)
    p.d.rounded_rectangle((2, 2, 12, 14), radius=1, fill=0)
    p.d.rounded_rectangle((3, 3, 11, 13), radius=1, fill=1)
    p.d.line((5, 5, 5, 6), fill=0), p.d.line((9, 5, 9, 6), fill=0)        # 上：两孔
    p.d.line((7, 8, 7, 9), fill=0)                                        # 下：一竖
    p.d.line((5, 11, 4, 12), fill=0), p.d.line((9, 11, 10, 12), fill=0)   # 八字
    p.dither([(12, 3), (14, 3), (14, 16), (3, 16), (3, 14), (12, 14)], 0.5, 0)
    p.px(1, 1, 0), p.px(13, 15, 0)
    return p.sprite()


def _plug_front():
    """插着的插头（正视）9×9：方头、防滑竖纹、底下出线护套"""
    p = Part(9, 9)
    p.shape("rounded_rectangle", (0, 0, 8, 6), radius=1, fill=1)
    for x in (2, 4, 6):
        p.d.line((x, 1, x, 4), fill=0)
    p.px(1, 1, 0)
    p.shape("rectangle", (3, 7, 5, 8), fill=1)
    p.px(4, 7, 0)
    return p.sprite()


def _plug_side():
    """拔出来的插头（侧视）12×7：圆头、竖纹、两根铜片；线从左边进"""
    p = Part(12, 7)
    p.shape("rectangle", (0, 2, 1, 4), fill=1)                  # 护套
    p.shape("rounded_rectangle", (2, 0, 8, 6), radius=1, fill=1)
    for x in (4, 6):
        p.d.line((x, 1, x, 5), fill=0)
    p.shape("line", (9, 1, 11, 1), fill=1)                      # 铜片
    p.shape("line", (9, 5, 11, 5), fill=1)
    p.px(3, 1, 0)
    return p.sprite()


BOLT = Sprite("""
  ##
 ##
####
  ##
 ##
 #
""")

HEART_FX = pix.frames("""
 # #
#####
 ###
  #
""")


def battery(g: Gfx, cx: float, y: float, level: float, charging: bool, t: float):
    """手机式电池 27×11：圆角外壳、内缝、五格电、正极帽；充电时下一格闪、中间压一道闪电；低电量最后一格闪"""
    x0 = int(round(cx - 14))
    y = int(round(y))
    g.d.rounded_rectangle((x0, y, x0 + 25, y + 10), radius=2, fill=0, outline=1)
    g.d.rectangle((x0 + 26, y + 3, x0 + 27, y + 7), fill=1)
    g.px(x0 + 27, y + 3, 0)
    n = level * 5
    for i in range(5):
        bx = x0 + 3 + i * 4
        full = i < int(n + 1e-6)
        nxt = charging and i == int(n + 1e-6) and i < 5 and (t * 2) % 1 < 0.5
        low = not charging and level < 0.25 and i == 0 and (t * 2.5) % 1 < 0.5
        if (full and not low) or nxt:
            g.d.rectangle((bx, y + 3, bx + 2, y + 7), fill=1)
            g.px(bx, y + 3, 0)
    g.d.line((x0 + 2, y + 1, x0 + 6, y + 1), fill=1)  # 外壳高光
    if charging:
        pix.blit(g, BOLT, x0 + 11, y + 2)


@register
class Charge(Rest):
    id = "x6.charge"
    name = "插电"
    desc = "小道士背上插着电线坐在蒲团上充电，头顶电池充到 99% 卡住，他睁一只眼——插头自己蹦了出来：持而盈之，不如其已"
    T = {"enter": 2.6, "exit": 1.2}
    C = 110.0           # 一轮：充电 0–70，99% 卡住，74 插头蹦出，浮空放电，104 插头跳回

    X = 44                            # 道士（朝左坐，背对插座）
    SOCK = (104, 30)                  # 插座左上
    HOME = (107, 40)                  # 插着的插头左上（正视）
    FLOORPLUG = (82, FLOOR - 7)       # 落在地上的插头左上（侧视）

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.loose = False
        self._wp = [(0, 0), (1, 1)]

    # ------------------------------------------------------------ 状态（都是本轮秒数 u 的函数）

    def level(self, u: float) -> float:
        if u < 70:
            return 0.2 + 0.79 * (1 - (1 - u / 70) ** 2.2)
        if u < 77:
            return 0.99
        if u < 104:
            return lerp(0.99, 0.2, span(u, 77, 101))
        return 0.2

    def lift(self, u: float, t: float) -> float:
        up = ease_in_out(span(u, 77, 79.5)) * (1 - ease_out_bounce(span(u, 100.5, 102.2)))
        return up * (5 + math.sin(t * 1.7) * 1.5)

    def plug(self, u: float):
        """插头：('in', x, y) 插着 / ('side', x, y) 侧放在地上或在空中"""
        if u < 74 or u >= 107.6:
            return "in", self.HOME[0], self.HOME[1]
        fx, fy = self.FLOORPLUG
        if u < 75.3:  # 蹦出：抛物线落地再弹一下
            k = span(u, 74, 75.3)
            x = lerp(self.HOME[0] + 2, fx, k)
            y = lerp(self.HOME[1], fy, ease_out_bounce(k)) - math.sin(min(k * 1.4, 1) * math.pi) * 10
            return "side", x, y
        if u < 104:
            wig = 1 if 90 < u < 91.2 and int(u * 10) % 2 else 0  # 中间抖一下（想家了）
            return "side", fx + wig, fy
        k = span(u, 104, 107.6)  # 一跳一跳爬回去，最后一跃插进插座
        if k < 0.75:
            q = k / 0.75
            hop = abs(math.sin(q * math.pi * 4)) * 4
            return "side", lerp(fx, self.HOME[0] - 8, q), fy - hop
        q = (k - 0.75) / 0.25
        return "side", lerp(self.HOME[0] - 8, self.HOME[0] - 2, q), lerp(fy, self.HOME[1], ease_out(q)) - math.sin(
            q * math.pi) * 6

    # ------------------------------------------------------------ 画

    def back_port(self, dy: float):
        return self.X + 8, FLOOR - 15 + dy

    def wire(self, g: Gfx, plug, dy: float, flow: float | None, upto: float = 1.0):
        bx, by = self.back_port(dy)
        kind, px, py = plug
        if self.loose:  # 退场：线从背上脱开，散在地上
            end = (px, py + 3)
            pts = [(self.X + 14, FLOOR - 1), (self.X + 20, FLOOR - 2), ((self.X + 20 + end[0]) / 2, FLOOR - 1), end]
            cable(g, pts)
            return pts
        if kind == "in":
            end = (px + 4, py + 9)
            pts = [(bx, by), (bx + 6, by + 4)]
            pts += [bezier((bx + 6, by + 4), (bx + 10, FLOOR - 1), (bx + 20, FLOOR - 1), k / 4) for k in range(1, 5)]
            pts += [(end[0] - 4, FLOOR - 1), end]
        else:
            end = (px, py + 3)
            mid = ((bx + end[0]) / 2, FLOOR + 1)
            pts = [(bx, by)] + [bezier((bx, by), mid, end, k / 8) for k in range(1, 9)]
        if upto < 1:
            n = max(2, int(len(pts) * upto + 1))
            pts = pts[:n]
        cable(g, pts, phase=flow)
        return pts

    def scene(self, g: Gfx, u: float, t: float, dt: float, show_bat: float = 1.0, plug_override=None,
              dy_override: float | None = None, face_override: str | None = None):
        room_floor(g)
        night_window(g, 94, 2, t)
        pix.blit(g, spr("socket", _socket), *self.SOCK)
        lvl = self.level(u)
        charging = u < 74 or u >= 107.6
        dy = -self.lift(u, t) if dy_override is None else dy_override
        plug = plug_override or self.plug(u)
        # 影子（浮起来时蒲团上一小片网点）
        cushion(g, self.X)
        if dy < -1:
            w = 9 - int(-dy * 0.5)
            pix.checker(g, (self.X - w, FLOOR - 7, self.X + w, FLOOR - 5), 0.5, 0)
        # 电线（在人后面）、插头
        flow = -t * 14 if charging else None
        self.wire(g, plug, dy, flow)
        kind, px, py = plug
        if kind == "in":
            pix.blit(g, spr("plug_f", _plug_front), px, py)
        else:
            pix.blit(g, spr("plug_s", _plug_side), px, py)
        # 小道士
        face = face_override or ("happy" if 34.6 < u < 36.2 else "wow" if 52.2 < u < 53.0 else "sleep")
        sit(g, self.X, t, flip=True, face=face, dy=dy)
        if not self.loose:
            bx, by = self.back_port(dy)
            pix.blit(g, spr("port", _port), bx - 1, by - 2)
        hx, hy = head_box(self.X, FLOOR - 3 + dy, "sit", flip=True)
        if 71 < u < 77 and face == "sleep":  # 卡在 99%：睁一只眼往上瞄
            eye_open(g, hx, hy, 0, flip=True, look_up=True)
        if 52 < u < 54.5:  # 静电：头发炸起来，几道小电弧
            for i, (ax, ay) in enumerate(((-6, 2), (0, -2), (6, 2))):
                if (t * 12 + i) % 3 < 2:
                    x, y = hx + 8 + ax, hy + ay
                    g.d.line((x, y, x + (1 if i % 2 else -1), y - 2, x, y - 4), fill=1)
        # 充电时，气点从肩头两侧升起
        if charging:
            for i in range(5):
                k = (t * 0.45 + i / 5) % 1
                side = -1 if i % 2 else 1
                x = self.X + side * (12 + rand(i, 3) * 6) + math.sin(t * 2 + i) * 1.5
                y = FLOOR - 10 - k * 26 + dy
                if 0.3 < k < 0.6 and i % 2 == 0:
                    for ox, oy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                        g.px(x + ox, y + oy)
                else:
                    g.px(x, y)
        # 33 秒：一团灵气顺着线流进来，扑在背上（开心一下）
        if 33 < u < 34.6:
            pts = self.wire_pts
            k = 1 - span(u, 33, 34.6)
            i = min(int(k * (len(pts) - 1)), len(pts) - 2)
            q = k * (len(pts) - 1) - i
            x = lerp(pts[i][0], pts[i + 1][0], q)
            y = lerp(pts[i][1], pts[i + 1][1], q)
            g.k.ellipse((x - 3, y - 3, x + 3, y + 3), fill=1)
            g.d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=1)
        if crossed(u, dt, 34.6):
            bx, by = self.back_port(dy)
            self.sparks.burst(bx, by, 10, 24, up=10, life=0.6, gravity=20)
        if 34.6 < u < 36.2:  # 头顶冒一颗小心
            k = span(u, 34.6, 36.2)
            pix.blit(g, HEART_FX[0], hx - 6, hy + 4 - k * 8)
        # 插拔瞬间
        if crossed(u, dt, 74):
            self.sparks.burst(self.HOME[0] + 4, self.HOME[1] + 2, 14, 30, up=10, life=0.5, gravity=60)
        for a in (74.0, 107.6):
            if a <= u < a + 0.25:
                pix.shake(g, t, 1.0)
                spark_star(g, self.HOME[0] + 4, self.HOME[1] + 3, span(u, a, a + 0.25), 7)
        if crossed(u, dt, 107.6):
            self.sparks.burst(self.HOME[0] + 4, self.HOME[1] + 3, 10, 26, up=8, life=0.5, gravity=60)
        if crossed(u, dt, 75.3) or crossed(u, dt, 102.2):
            x = self.FLOORPLUG[0] + 6 if u < 80 else self.X
            for s in (-1, 1):
                self.puffs.emit(x + s * 8, FLOOR - 2, vx=s * 6, vy=-3, life=0.6, rmax=1.6, spread=1)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 电池与字（最后画）
        if show_bat > 0:
            by = lerp(-14, 3, ease_out_back(show_bat))
            battery(g, self.X, by, lvl, charging, t)
            if show_bat >= 1:
                g.text(self.X + 17, by + 2, f"{int(lvl * 100 + 0.5)}%", size=8)
        if 71.5 < u < 77.5:
            g.vtext(4, 6, "持而盈之")
        elif 77.5 <= u < 86:
            g.vtext(4, 6, "不如其已")
        self.mx(g, lvl, charging, t)
        if 74 <= u < 74.5 or 107.6 <= u < 108.1:
            g.mx_level = 4

    @property
    def wire_pts(self):
        return self._wp

    def mx(self, g: Gfx, lvl: float, charging: bool, t: float):
        mx_icon(g, ["", "####### ", "#     ##", "#     ##", "#     ##", "#     ##", "####### "])
        n = lvl * 5
        for i in range(5):
            on = i < int(n + 1e-6) or (charging and i == int(n + 1e-6) and (t * 2) % 1 < 0.5)
            if not charging and lvl < 0.25 and i == 0:
                on = (t * 2.5) % 1 < 0.5
            if on:
                for r in (2, 3, 4, 5):
                    g.mx_set(1 + i, r)

    def frame(self, g: Gfx, u: float, t: float, **kw):
        dt = self.clock(t)
        dy = kw.get("dy_override")
        self._wp = self._pts(u, t, dy)
        self.scene(g, u, t, dt, **kw)

    def _pts(self, u, t, dy):
        bx, by = self.back_port(-self.lift(u, t) if dy is None else dy)
        kind, px, py = self.plug(u)
        end = (px + 4, py + 9) if kind == "in" else (px, py + 3)
        return [(end[0], end[1]), (end[0] - 4, FLOOR - 1), (bx + 20, FLOOR - 1), (bx + 6, by + 4), (bx, by)]

    def enter(self, g: Gfx, t: float):
        """落座（0–0.9）→ 电线甩出去插进插座（0.9–1.6）→ 电池弹出 20%（1.7–2.6）"""
        dt = self.clock(t)
        u = 0.0
        fall = span(t, 0, 0.9)
        dy = -70 * (1 - ease_out_bounce(fall)) if t < 0.9 else 0
        self._wp = self._pts(u, t, dy)
        if t < 0.9:  # 还没插：插头跟着他
            room_floor(g)
            night_window(g, 94, 2, t)
            pix.blit(g, spr("socket", _socket), *self.SOCK)
            cushion(g, self.X)
            sit(g, self.X, t, flip=True, face="wow" if t < 0.6 else "sleep", dy=dy)
            if crossed(t, dt, 0.62):
                for s in (-1, 1):
                    self.puffs.emit(self.X + s * 12, FLOOR - 2, vx=s * 10, vy=-4, life=0.6, rmax=2, spread=1)
            self.puffs.step(dt)
            self.puffs.draw(g)
            self.mx(g, 0.2, False, t)
            return
        k = span(t, 0.9, 1.6)
        if k < 1:  # 插头沿弧线飞向插座，线跟着拉出去
            bx, by = self.back_port(0)
            q = ease_in_out(k)
            px = lerp(bx + 4, self.HOME[0] - 2, q)
            py = lerp(by, self.HOME[1], q) - math.sin(q * math.pi) * 18
            plug = ("side", px, py)
        else:
            plug = None
        if crossed(t, dt, 1.6):
            self.sparks.burst(self.HOME[0] + 4, self.HOME[1] + 3, 14, 28, up=8, life=0.5, gravity=60)
        self.scene(g, 0.0, t, dt, show_bat=span(t, 1.7, 2.4),
                   plug_override=plug, dy_override=0, face_override="sleep")
        if 1.6 <= t < 1.85:
            spark_star(g, self.HOME[0] + 4, self.HOME[1] + 3, span(t, 1.6, 1.85), 7)
            pix.shake(g, t, 1)
            g.mx_level = 4

    def hold(self, g: Gfx, t: float):
        n, u = cyc(t, self.C)
        self.frame(g, u, t)

    def exit(self, g: Gfx, t: float):
        """插头弹出、电池缩回上方、小道士飞升出画"""
        dt = self.clock(t)
        n, u0 = cyc(self.hold_t, self.C)
        u = u0 if u0 < 74 or u0 >= 107.6 else 0.0
        k = span(t, 0.25, 1.2)
        dy = -ease_in(k) * 80 + (-self.lift(u0, self.hold_t) if 74 <= u0 < 104 else 0)
        self._wp = self._pts(u, t, dy)
        plug = ("side", lerp(self.HOME[0], self.FLOORPLUG[0], span(t, 0, 0.6)),
                lerp(self.HOME[1], self.FLOORPLUG[1], ease_out_bounce(span(t, 0, 0.6))) - math.sin(
                    span(t, 0, 0.6) * math.pi) * 8)
        if crossed(t, dt, 0.05):
            self.sparks.burst(self.HOME[0] + 4, self.HOME[1] + 3, 12, 28, up=8, life=0.5, gravity=60)
        self.loose = True
        self.scene(g, u, t, dt, show_bat=1 - span(t, 0, 0.5), plug_override=plug, dy_override=dy,
                   face_override="happy")
        self.loose = False
        g.fade(1 - span(t, 0.8, 1.2))


# ====================================================================== 散热

FAN_C = (30, 26)       # 风扇中心
FAN_R = 16


_ANN: dict = {}


def _annulus(cx: int, cy: int):
    m = _ANN.get(cx)
    if m is None:
        import numpy as np
        ys, xs = np.mgrid[0:64, 0:128]
        d = np.hypot(xs - cx, ys - cy)
        m = _ANN[cx] = (d > 6.5) & (d < 14.5)
        if len(_ANN) > 200:
            _ANN.clear()
    return m


def _fan_stand():
    """风扇脚 26×16：颈管（带关节旋钮）、圆底座、三个档位键"""
    p = Part(26, 16)
    p.shape("rectangle", (11, 0, 14, 8), fill=1)
    p.d.line((12, 1, 12, 7), fill=0)
    p.shape("ellipse", (9, 1, 16, 6), fill=1)        # 关节
    p.d.ellipse((11, 2, 14, 5), fill=0)
    p.px(12, 3)
    p.shape("polygon", [(4, 9), (21, 9), (25, 14), (0, 14)], fill=1)
    p.shape("rectangle", (0, 14, 25, 15), fill=1)
    p.d.line((2, 13, 23, 13), fill=0)
    p.dither([(17, 9), (25, 9), (25, 15), (17, 15)], 0.5, 0)
    for i in range(3):                                # 档位键（亮的那个另画）
        p.d.rectangle((6 + i * 4, 10, 8 + i * 4, 11), fill=0)
    return p.sprite()


def _thermo():
    """温度计 9×40：玻璃管（双线）、底部球泡、右侧刻度"""
    p = Part(9, 40)
    p.shape("rounded_rectangle", (1, 0, 7, 33), radius=3, fill=1)
    p.d.rounded_rectangle((2, 1, 6, 32), radius=2, fill=0)
    p.shape("ellipse", (0, 30, 8, 39), fill=1)
    p.d.ellipse((1, 31, 7, 38), fill=0)
    return p.sprite()


def _thought():
    """杂念气泡 15×12：云朵气泡 + 两颗小泡"""
    p = Part(15, 12)
    p.shape("ellipse", (2, 0, 14, 9), fill=1)
    p.d.ellipse((3, 1, 13, 8), fill=0)
    p.shape("ellipse", (0, 8, 3, 11), fill=1)
    p.px(1, 9, 0), p.px(2, 9, 0), p.px(1, 10, 0), p.px(2, 10, 0)
    return p.sprite()


ICONS = pix.frames("""
.###.
#.#.#
##.##
#.#.#
.###.
---
.#.#.
#####
#####
.###.
..#..
---
..#..
.###.
.###.
#####
..#..
""")  # 方孔钱、心、铃（杂念）

FLAME = pix.frames("""
  #
 ##
 ###
#.##
#..#
 ##
---
 #
 ##
###
##.#
#..#
 ##
---
  #
  ##
 ###
#.#.
#..#
 ##
""")

DROP = Sprite("""
 #
###
.#
""")


@register
class Cooling(Rest):
    id = "x6.fan"
    name = "散热"
    desc = "小道士盘坐在台扇前纳凉，满头大汗，温度一点点降下来、风扇慢慢停；每隔一阵杂念一起又热起来——躁胜寒，静胜热"
    T = {"enter": 2.6, "exit": 1.2}
    BASE = 26.0
    TAU = 14.0
    X = 82

    def setup(self):
        self.clock = Clock()
        self.ang = 0.0
        self.puffs = pix.Puffs(self.seed)
        self.t0 = 92.0 if self.ctx.finished else 81.0
        self.s = self.rng.randrange(1000)
        self.stop_t = None

    # ------------------------------------------------------------ 温度（t 的函数）

    def spike(self, k: int) -> tuple[float, float, int]:
        """第 k 次杂念：(时刻, 升温幅度, 气泡图标)"""
        at = 22 + k * 47 + (rand(k, self.s) - 0.5) * 12
        return at, 22 + rand(k + 50, self.s) * 18, int(rand(k + 90, self.s) * 3)

    def temp(self, t: float) -> float:
        T = self.BASE + (self.t0 - self.BASE) * math.exp(-t / self.TAU)
        k0 = max(0, int((t - 22) / 47) - 3)
        for k in range(k0, k0 + 6):
            at, amp, _ = self.spike(k)
            if t < at:
                break
            d = t - at
            T += amp * (ease_in_out(d / 2.5) if d < 2.5 else math.exp(-(d - 2.5) / self.TAU))
        return T

    def event(self, t: float):
        """最近一次杂念：(距今秒数, 图标) ；没有则 (None, 0)"""
        k = max(0, math.floor((t - 22 + 12) / 47) + 1)
        for kk in range(k, max(-1, k - 3), -1):
            at, _, ic = self.spike(kk)
            if at - 1.2 <= t:
                return t - at, ic
        return None, 0

    @staticmethod
    def speed(T: float) -> float:
        """0..1：40℃ 以下停转"""
        return clamp((T - 40) / 40)

    # ------------------------------------------------------------ 画

    def fan(self, g: Gfx, x: float, ang: float, w: float, t: float):
        cx, cy = FAN_C[0] + x, FAN_C[1]
        ix = int(round(x))
        pix.blit(g, spr("fanstand", _fan_stand), cx - 13, cy + FAN_R - 1)
        lv = 0 if w <= 0 else 1 + min(2, int(w * 3))
        if lv:
            g.d.rectangle((cx - 7 + (lv - 1) * 4, cy + FAN_R + 9, cx - 5 + (lv - 1) * 4, cy + FAN_R + 10), fill=1)
        g.d.ellipse((cx - FAN_R - 1, cy - FAN_R - 1, cx + FAN_R + 1, cy + FAN_R + 1), fill=0)
        fast = w > 0.55
        if fast:  # 转得快：叶子糊成一圈网点，只剩几道残影弧
            pix.checker_mask(g, _annulus(int(round(cx)), cy), 0.25)
            a0 = math.degrees(ang) % 72
            for j in range(5):
                s0 = a0 + j * 72
                g.d.arc((cx - 13, cy - 13, cx + 13, cy + 13), s0, s0 + 30, fill=1)
                g.d.arc((cx - 9, cy - 9, cx + 9, cy + 9), s0 + 10, s0 + 30, fill=1)
        else:
            for i in range(5):  # 五片扇叶：前缘弯、叶尖圆
                a = ang + i * 2 * math.pi / 5
                pts = [(cx + math.cos(a + da) * r, cy + math.sin(a + da) * r)
                       for r, da in ((6, -0.12), (10, -0.36), (13.2, -0.46), (14.4, -0.26), (14.6, 0.0), (13.8, 0.2),
                                     (10, 0.26), (6, 0.3))]
                g.d.polygon(pts, fill=1)
                g.px(cx + math.cos(a - 0.2) * 12, cy + math.sin(a - 0.2) * 12, 0)  # 叶面一点反光
        g.d.ellipse((cx - FAN_R, cy - FAN_R, cx + FAN_R, cy + FAN_R), outline=1)
        for i in range(20):  # 网罩辐条（外圈一截）
            a = i * math.pi / 10
            g.d.line((cx + math.cos(a) * 15, cy + math.sin(a) * 15, cx + math.cos(a) * 17, cy + math.sin(a) * 17),
                     fill=1)
        g.d.ellipse((cx - FAN_R - 2, cy - FAN_R - 2, cx + FAN_R + 2, cy + FAN_R + 2), outline=1)
        g.d.arc((cx - FAN_R + 2, cy - FAN_R + 2, cx + FAN_R - 2, cy + FAN_R - 2), 200, 250, fill=1)  # 罩上高光
        g.d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=0)
        g.d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline=1)
        taiji(g, cx, cy, 4, -ang)

    def thermo(self, g: Gfx, T: float, t: float):
        x, y = 114, 14
        pix.blit(g, spr("thermo", _thermo), x, y)
        h = clamp((T - 15) / 85) * 28
        g.d.ellipse((x + 2, y + 32, x + 6, y + 36), fill=1)
        g.d.rectangle((x + 3, y + 31 - h, x + 5, y + 32), fill=1)
        for i in range(6):  # 刻度
            yy = y + 4 + i * 5
            g.d.line((x - 3, yy, x - 2 if i % 2 else x - 4, yy), fill=1)
        if T > 70 and (t * 3) % 1 < 0.5:  # 太烫：管顶冒热气
            g.px(x + 4, y - 2), g.px(x + 3, y - 4)

    def ribbon(self, g: Gfx, hx: int, hy: int, w: float, t: float):
        """发带：从发髻后飘出来，风越大飘得越平、抖得越快"""
        x0, y0 = hx + 13, hy + 3
        L = 4 + w * 6
        droop = (1 - w) * 5
        pts = []
        for j in range(6):
            q = j / 5
            pts.append((x0 + q * L, y0 + q * droop + math.sin(t * (4 + w * 14) - q * 4) * q * (1 + w * 1.5)))
        g.d.line(pts, fill=1)
        g.d.line([(px, py + 1) for px, py in pts[:4]], fill=1)

    def scene(self, g: Gfx, t: float, dt: float, T: float, fan_x: float = 0.0, spin: float | None = None,
              phrase: bool = True, panel: float = 1.0):
        w = self.speed(T) if spin is None else spin
        self.ang += dt * w * 22
        room_floor(g)
        ev, ic = self.event(t)
        # 风：一道道虚线从风扇吹向小道士
        if w > 0.05:
            for i, y in enumerate((17, 26, 35)):
                ph = (t * (30 + 50 * w) + i * 23) % 60
                x0 = 50 + fan_x + ph * 0.5
                pix.dotted(g, x0, y + math.sin(t * 5 + i) * 1, x0 + 4 + 6 * w, y + math.sin(t * 5 + i), 2, 0)
        cushion(g, self.X)
        hot = T > 58
        face = "sleep"
        if ev is not None and -1.2 <= ev < 4:
            face = "wow"
        elif hot:
            face = "normal"
        sit(g, self.X, t, flip=True, face=face)
        hx, hy = head_box(self.X, FLOOR - 3, "sit", flip=True)
        self.ribbon(g, hx, hy, w, t)
        self.fan(g, fan_x, self.ang, w, t)
        # 汗珠：热的时候从额头甩出去
        if hot:
            for i in range(2):
                k = (t * 0.9 + i * 0.5) % 1
                x = hx + 13 + k * 8 * (1 if i else 0.6)
                y = hy + 6 - math.sin(k * math.pi) * 6 + k * 10
                if k < 0.8:
                    pix.blit(g, DROP, x, y, outline=False)
        if T > 72 and int((t + dt) * 2.5) != int(t * 2.5):  # 头顶冒热气
            self.puffs.emit(hx + 8, hy - 1, vx=1, vy=-6, life=1.2, rmax=1.6, spread=3)
        # 杂念：气泡 → 头顶起火 → 再静下来
        if ev is not None and -1.2 <= ev < 1.0:
            b = ease_out_back(span(ev, -1.2, -0.8))
            if b > 0.1:
                bx, by = hx + 12, hy - 12 + (1 - b) * 4
                pix.blit(g, spr("thought", _thought), bx, by)
                pix.blit(g, ICONS[ic], bx + 6, by + 2, outline=False)
        if ev is not None and 0 <= ev < 6:
            pix.blit(g, pix.anim(FLAME, t, 10), hx + 6, hy - 6)
            if int((t + dt) * 4) != int(t * 4):
                self.puffs.emit(hx + 8, hy - 7, vy=-8, life=0.9, rmax=1.4, spread=2)
        if w <= 0:  # 停转：一粒灰慢慢落在扇叶上
            k = ((t - self.stop_t) * 0.12) if self.stop_t is not None else 0
            if 0 < k < 1:
                g.px(FAN_C[0] + fan_x + 3, lerp(2, FAN_C[1] - 12, ease_out(k)))
            elif k >= 1:
                g.px(FAN_C[0] + fan_x + 3, FAN_C[1] - 12)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.thermo(g, T, t)
        if panel > 0:
            s = f"{int(T + 0.5)}℃"
            g.text(110, 2, s, size=8, align="right")
            if phrase:
                rising = ev is not None and -0.5 <= ev < 6
                txt = "躁胜寒" if rising else "清静" if w <= 0 else "静胜热"
                g.text(66, 3, txt, align="center")
        self.mx_fan(g, self.ang, w)

    def mx_fan(self, g: Gfx, ang: float, w: float):
        for i in range(3):
            a = ang + i * 2 * math.pi / 3
            for r in (1.2, 2.2, 3.2):
                g.mx_set(int(round(3.5 + math.cos(a) * r)), int(round(3.5 + math.sin(a) * r)))
                g.mx_set(int(round(3.5 + math.cos(a + 0.4) * r * 0.8)), int(round(3.5 + math.sin(a + 0.4) * r * 0.8)))
        g.mx[3:5, 3:5] = True
        g.mx_level = 1 + int(round(w * 3))

    def enter(self, g: Gfx, t: float):
        """风扇从左边弹进来，扇叶由慢到快；温度从室温蹿到 81℃（圆满后 92℃），“过热”反白闪"""
        dt = self.clock(t)
        self.stop_t = None
        fx = lerp(-60, 0, ease_out_back(span(t, 0, 0.8)))
        T = lerp(self.BASE, self.t0, ease_out(span(t, 0.8, 2.3)))
        self.scene(g, 0.0, dt, T, fan_x=fx, spin=span(t, 0.6, 2.4) * self.speed(self.t0), phrase=False)
        if 0.9 < t < 2.4 and (t * 4) % 1 < 0.6:
            g.d.rectangle((50, 2, 79, 14), fill=1)
            g.text(65, 3, "过热", fill=0, align="center")

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        T = self.temp(t)
        w = self.speed(T)
        if w <= 0 and (self.stop_t is None or self.stop_t > t):
            self.stop_t = t
        elif w > 0:
            self.stop_t = None
        self.scene(g, t, dt, T)

    def exit(self, g: Gfx, t: float):
        """扇叶猛转（开工了），整台风扇向左滑出，画面淡出"""
        dt = self.clock(t)
        T = self.temp(self.hold_t)
        fx = -ease_in(span(t, 0.3, 1.1)) * 70
        self.scene(g, self.hold_t + t, dt, T, fan_x=fx, spin=1.0, phrase=False)
        g.fade(1 - span(t, 0.6, 1.2))


# ====================================================================== 待机

def breath(t: float) -> float:
    """7 秒一息：吸 3 秒（0→1）、呼 4 秒（1→0）"""
    k = t % 7.0
    return ease_in_out(k / 3) if k < 3 else 1 - ease_in_out((k - 3) / 4)


def _desk():
    """矮几 64×14：几面（前沿阴线、两头翘角）、卷云足、横枨"""
    p = Part(64, 14)
    p.shape("rectangle", (1, 0, 62, 2), fill=1)
    p.px(0, 0), p.px(63, 0)
    p.d.line((2, 1, 61, 1), fill=0)
    for x0 in (4, 54):  # 两条腿：上细下翻卷
        p.shape("rectangle", (x0, 3, x0 + 5, 4), fill=1)
        p.shape("rectangle", (x0 + 1, 5, x0 + 3, 11), fill=1)
        p.shape("ellipse", (x0 - 1, 10, x0 + 5, 13), fill=1)
        p.d.ellipse((x0, 11, x0 + 3, 12), fill=0)
        p.px(x0 + 2, 6, 0), p.px(x0 + 2, 8, 0)
    p.shape("line", (10, 7, 53, 7), fill=1)          # 横枨
    p.dither([(2, 3), (62, 3), (62, 4), (2, 4)], 0.5, 0)
    return p.sprite()


MOTH = pix.frames("""
#   #
## ##
 ###
## ##
#   #
---
.#.#.
.###.
..#..
""")

ZZ = [Sprite("##\n.#\n##"), Sprite("###\n..#\n.#.\n###")]


@register
class Standby(Rest):
    id = "x6.standby"
    name = "待机"
    desc = "夜里小道士合上笔记本，坐在矮几前打盹；本子前沿的呼吸灯七秒一息，他也跟着一呼一吸；隔一阵盖子缝里有眼睛偷看、飞蛾绕灯"
    T = {"enter": 3.0, "exit": 1.3}
    X = 34
    DESK = (52, 45)        # 几面左上
    LED = (98, 44)

    def setup(self):
        self.clock = Clock()
        self.puffs = pix.Puffs(self.seed)
        self.s = self.rng.randrange(1000)

    def laptop(self, g: Gfx, c: float, screen: float = 0.0, content: str = "", peek: float = 0.0, look: int = 0,
               b: float = 0.0):
        """c 合盖程度（0 开 1 合）；screen 屏幕亮度；content："pause" / "play"；peek 盖子掀缝 0..1；b 呼吸灯"""
        x0, x1 = 60, 102
        yb = 44           # 机身底
        # 机身：前沿 + 顶面（打开时看到键盘）
        g.d.rectangle((x0, yb - 2, x1, yb), fill=1)
        g.d.line((x0 + 1, yb - 1, x1 - 1, yb - 1), fill=0)
        g.d.line((x0 + 16, yb, x0 + 24, yb), fill=0)  # 前沿开盖凹口
        h = lerp(27, 0, ease_in(c))
        if h > 3:  # 屏幕立着（越合越扁）
            top = yb - 4 - h
            g.d.polygon([(x0 + 3, yb - 3), (x1 - 3, yb - 3), (x1 - 1, yb - 2), (x0 + 1, yb - 2)], fill=1)
            for i in range(9):  # 键盘一排排小点
                g.px(x0 + 6 + i * 3.4, yb - 3, 0)
            g.d.rectangle((x0 + 2, top, x1 - 2, yb - 4), fill=1)
            g.d.rectangle((x0 + 4, top + 2, x1 - 4, yb - 6), fill=0)
            if h > 10:
                g.px((x0 + x1) // 2, top + 1, 0)       # 摄像头
            if screen > 0 and h > 16:
                cx, cy = (x0 + x1) // 2, (top + yb - 4) // 2
                if content == "pause":
                    g.d.rectangle((cx - 5, cy - 7, cx - 3, cy - 1), fill=1)
                    g.d.rectangle((cx + 2, cy - 7, cx + 4, cy - 1), fill=1)
                elif content == "play":
                    g.d.polygon([(cx - 3, cy - 8), (cx - 3, cy), (cx + 3, cy - 4)], fill=1)
                if screen < 1:
                    g.fade(screen, (x0 + 4, top + 2, x1 - 3, yb - 5))
        else:  # 合上：盖子顶面（俯视的梯形）+ 太极贴纸
            lift = peek * 5
            ty = yb - 3 - lift
            if peek > 0:  # 掀开一条缝：缝里漆黑，两只眼睛左右看
                g.d.rectangle((x0 + 2, ty, x1 - 2, yb - 3), fill=0)
                g.d.line((x0 + 2, yb - 3, x1 - 2, yb - 3), fill=1)
                if peek > 0.6 and abs(look) < 5:
                    ex = (x0 + x1) // 2 + look * 5
                    for dx in (-4, 2):
                        g.d.rectangle((ex + dx, ty + 1, ex + dx + 1, ty + 2), fill=1)
            top = ty - 8
            g.d.polygon([(x0 + 4, top), (x1 - 4, top), (x1, ty), (x0, ty)], fill=1)
            g.d.line((x0 + 5, top + 1, x0 + 12, top + 1), fill=0)            # 盖面一道反光的阴线
            pix.checker(g, (x1 - 12, top + 1, x1 - 1, ty), 0.5, 0)          # 右边背光
            g.d.line((x0 + 1, ty, x1 - 1, ty), fill=0)                       # 盖与机身的缝
            cx, cy = (x0 + x1) // 2, top + 4
            g.d.ellipse((cx - 6, cy - 4, cx + 6, cy + 4), fill=0)
            taiji(g, cx, cy, 3, 0.4)
        # 呼吸灯 + 几面上的光晕
        lx, ly = self.LED
        if b > 0.05:
            r = 1 + b * 9
            pix.checker(g, (lx - r, ly + 2, lx + r, ly + 4), 0.5 if b > 0.6 else 0.25)   # 几面上的光晕
            g.d.rectangle((lx - 1, ly - 1, lx, ly - 1), fill=1)
            if b > 0.45:
                g.px(lx - 3, ly - 1), g.px(lx + 2, ly - 1)
            if b > 0.8:
                g.px(lx - 5, ly - 1), g.px(lx + 4, ly - 1)
        else:
            g.d.rectangle((lx - 1, ly - 1, lx, ly - 1), fill=0)

    def room(self, g: Gfx, t: float):
        room_floor(g)
        night_window(g, 4, 3, t)
        pix.blit(g, spr("desk", _desk), *self.DESK)

    def event(self, t: float):
        """每 31 秒一个事件（第 9 秒起）：(种类, 事件内秒数)；种类 0 偷看 1 飞蛾 2 题字"""
        if t < 9:
            return None, 0.0
        n, k = cyc(t - 9, 31)
        kind = int(rand(n, self.s) * 3)
        if n == 0:
            kind = 0
        dur = (6.0, 9.0, 7.0)[kind]
        return (kind, k) if k < dur else (None, 0.0)

    def scene(self, g: Gfx, t: float, dt: float, c: float = 1.0, screen: float = 0.0, content: str = "",
              face: str = "sleep", head: str = "bow", zz: bool = True, b: float | None = None):
        self.room(g, t)
        kind, k = self.event(t)
        b = breath(t) if b is None else b
        peek, look = 0.0, 0
        if kind == 0:
            peek = ease_out(span(k, 0.0, 0.6)) * (1 - ease_out_bounce(span(k, 4.8, 5.6)))
            look = -1 if 1.4 < k < 2.4 else 1 if 2.4 < k < 3.4 else 0
            if 3.6 < k < 3.8:
                look = 9  # 眨眼（画到画面外）
        self.laptop(g, c, screen, content, peek, look, b)
        cushion(g, self.X)
        # 打盹：每 13 秒点一下头（猛一抬又垂下）
        nod = (t % 13) > 12.2 and head == "bow"
        if nod:
            sit(g, self.X, t, face="wow" if (t % 13) < 12.5 else "sleep", head="up")
        else:
            sit(g, self.X, t, face=face, head=head)
        hx, hy = head_box(self.X, FLOOR - 3)
        # z / Z：呼气时从头上飘起
        if zz and kind != 2:
            for i in range(3):
                q = ((t - 3) / 7 - i / 3) % 1
                if q < 0.85:
                    x = hx + 16 + q * 10 + math.sin(q * 8 + i) * 2
                    y = hy + 2 - q * 18
                    g.blit(ZZ[1 if q > 0.4 else 0], x, y)
        if kind == 1:  # 飞蛾：从右边飞来，绕灯两圈，飞走
            lx, ly = self.LED
            if k < 2:
                q = ease_out(k / 2)
                mx, my = lerp(132, lx + 15, q), lerp(14, ly - 5, q) + math.sin(k * 9) * 2
            elif k < 7:
                a = (k - 2) / 5 * 4 * math.pi
                mx, my = lx + 2 + math.cos(a) * 13, ly - 5 + math.sin(a) * 5
            else:
                q = ease_in((k - 7) / 2)
                mx, my = lerp(lx + 15, 70, q), lerp(ly - 5, -6, q) + math.sin(k * 9) * 2
            pix.blit(g, pix.anim(MOTH, t, 12), mx - 2, my - 2)
        self.puffs.step(dt)
        self.puffs.draw(g)
        if kind == 2 and k < 6.5:
            txt = "吐故纳新"
            n = min(4, int(k * 3) + 1)
            g.text(44, 4, txt[:n])
            if k > 5:
                g.fade(1 - span(k, 5, 6.5), (40, 0, 100, 18))
        self.mx_breath(g, b)

    def mx_breath(self, g: Gfx, b: float):
        r = 0.8 + b * 3.0
        for y in range(8):
            for x in range(8):
                d = math.hypot(x - 3.5, y - 3.5)
                if abs(d - r) < 0.55 or (b > 0.85 and d < 1):
                    g.mx[y, x] = True
        g.mx_level = 2 if b > 0.9 else 1

    def enter(self, g: Gfx, t: float):
        """屏上是刚才的法事名和“‖”，屏幕暗掉，盖子合上弹一下扬起两撮灰，他低头睡去，呼吸灯亮起"""
        dt = self.clock(t)
        c = ease_out_bounce(span(t, 1.5, 2.2))
        screen = 1 - span(t, 0.8, 1.4)
        head = "up" if t < 2.3 else "bow"
        face = "normal" if t < 1.5 else "sleep"
        if crossed(t, dt, 1.9):
            for s in (-1, 1):
                self.puffs.emit(81 + s * 23, 40, vx=s * 10, vy=-5, life=0.7, rmax=1.8, spread=1)
        self.scene(g, max(t - 3.0, 0.0), dt, c=c, screen=screen, content="pause", face=face,
                   head=head, zz=t > 2.4, b=span(t, 2.2, 3.0) * breath(0.0) if t > 2.2 else 0.0)
        if 0 <= c < 0.5 and screen > 0:
            name = (self.ctx.ritual_name or "法事")[:4]
            g.text(81, 30, name, size=8, align="center")

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        self.scene(g, t, dt)

    def exit(self, g: Gfx, t: float):
        """醒了：抬头，掀开盖子，屏幕亮起“▶”"""
        dt = self.clock(t)
        c = 1 - ease_out(span(t, 0.15, 0.7))
        self.scene(g, self.hold_t, dt, c=c, screen=span(t, 0.6, 0.9), content="play", face="wow" if t < 0.5 else
                   "normal", head="up", zz=False, b=0.0)
        g.fade(1 - span(t, 0.9, 1.3))
