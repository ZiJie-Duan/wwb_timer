"""燃香（示范法事，新画风的质量标杆）。

夜里供桌的特写：左后方木格窗透进月光，一道光柱斜照，浮尘在光里飘；中间一尊三足立耳铜炉（回纹带、铜锈），
炉口是有颗粒的香灰；右边一盏烛台，烛火跳动。全部是灰度渲染（3D 光照、透视、材质）后抖动成黑白。

入场：宽袖的手握三炷香从右上伸来，到烛火上引燃，抖手扇灭明火，移到炉上插进香灰（扬起一点灰），手指松开收回。
持续：香随计时变短（一轮 10 分钟），香头火星明灭，香灰卷曲渐长、不时断落；三缕烟在气流里扭动、合拢、散开，
      穿过月光时更亮。一炷烧完：残香暗去，手再引燃三炷新香插上（“再加一根香”），左下角“第几炷”加一。
中断：手指依次捏灭香头，烟断。  恢复：手拿火折子吹亮，逐一点回。
圆满：香一齐烧尽，最后的火星大亮，烟聚成一团盘旋上升，烛火一涨，“功德圆满”。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import art, rig
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, span
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register

PITCH = 0.42
CX, RIM_Y = 54, 36          # 炉口中心（屏幕）
ASH_DY = 2.6                # 香灰面比口沿低多少（世界单位）
STICK_DX = (-6.5, 0.0, 6.5)  # 三炷香在炉里的横向位置
STICK_DZ = (-1.5, 1.5, -0.5)
FULL = 22.0                 # 新香露出香灰的长度（像素）
STUB = 2.5
CANDLE = (110, 27)          # 烛芯（火焰底部）
RENEW = 7.0


def _censer_sprite():
    """三足立耳铜炉：炉身（旋转体）+ 香灰面 + 两只立耳（竖直圆环）+ 三足，合成一个点云一次渲染（遮挡正确）"""
    prof = [(-0.6, 23.0), (0.0, 24.6), (1.1, 24.8), (2.0, 23.6), (3.2, 22.2), (5.5, 22.8), (9.0, 24.6),
            (13.0, 24.4), (17.0, 21.5), (20.0, 16.5), (21.6, 11.0), (22.0, 6.0)]
    P, N, U, V = art.lathe_mesh(prof, nu=300)
    band = (V > 0.30) & (V < 0.50)
    meander = ((np.floor(U * 48) + np.floor(V * 30)) % 2 == 0) & band          # 回纹带
    patina = art.fbm(U * 260, V * 70)
    alb = 0.95 - 0.55 * band + 0.45 * meander + 0.35 * (patina - 0.5)
    alb[V < 0.08] += 0.15                                                       # 口沿打磨得亮
    parts = [(P.reshape(-1, 3), N.reshape(-1, 3), alb.ravel())]
    # 香灰面：口沿内的圆盘，颗粒
    r = np.sqrt(np.linspace(0, 1, 70))[:, None] * 22.4
    th = np.linspace(0, 2 * np.pi, 280, endpoint=False)[None, :]
    AP = np.stack([r * np.sin(th), np.full(r.shape, ASH_DY) + 0 * th, r * np.cos(th)], -1).reshape(-1, 3)
    AN = np.tile(np.array([0, -1, 0], np.float32), (AP.shape[0], 1))
    grain = art.fbm(AP[:, 0] * 6 + 40, AP[:, 2] * 6 + 9)
    parts.append((AP, AN, 0.05 + 0.30 * (grain > 0.62)))
    # 立耳：竖直的圆环，立在口沿左右
    TP, TN, _, _ = art.torus_mesh(4.2, 1.25, 120, 30)
    rot = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], np.float32)            # 绕 x 轴转 90°：环立起来
    TP, TN = TP.reshape(-1, 3) @ rot.T, TN.reshape(-1, 3) @ rot.T
    for sx in (-1, 1):
        off = np.array([sx * 22.5, -4.6, 0], np.float32)
        parts.append((TP + off, TN, 0.85))
    # 三足：一前两后，略外撇
    leg = [(0, 3.2), (3, 2.6), (6.5, 2.1), (7.5, 2.4)]
    LP, LN, _, _ = art.lathe_mesh(leg, nu=60)
    for ang in (0.0, 2.25, -2.25):
        off = np.array([math.sin(ang) * 13, 19.5, math.cos(ang) * 13], np.float32)
        parts.append((LP.reshape(-1, 3) + off, LN.reshape(-1, 3), 0.7))
    P = np.concatenate([p for p, _, _ in parts])
    N = np.concatenate([n for _, n, _ in parts])
    A = np.concatenate([np.broadcast_to(np.asarray(a, np.float32), (len(p),)) for p, _, a in parts])
    return art.render_surface(P, N, A, 0.0, PITCH, amb=0.04, spec=0.9, shine=26)


def _censer():
    return art.cached(("r.incense.censer",), _censer_sprite)


def _world(x, y, z):
    """炉子坐标 → 屏幕（与炉子同一个视角）"""
    sx, sy, _ = art.view(np.array([x, y, z], np.float32), 0.0, PITCH)
    return CX + float(sx), RIM_Y + float(sy)


def _room(g: Gfx):
    """静态背景：暗墙、木格窗（月光）、供桌桌面"""
    art.vgrad(g, (0, 0, 128, 64), 0.035, 0.0)
    # 窗：透光的窗纸 + 深色窗棂（月光从外面照在纸上，上亮下暗）
    x0, y0, x1, y1 = 4, 2, 34, 34
    art.vgrad(g, (x0, y0, x1, y1), 0.95, 0.55)
    art.noise_tex(g, (x0, y0, x1, y1), scale=2.2, lo=0.85, hi=1.0)
    for x in range(x0, x1 + 1, 6):
        art.line(g, x, y0, x, y1, 1.6, 0.0)
    for y in range(y0, y1 + 1, 8):
        art.line(g, x0, y, x1, y, 1.6, 0.0)
    art.line(g, x0 - 1, y0 - 1, x1 + 1, y0 - 1, 2, 0.16)
    art.line(g, x0 - 1, y1 + 1, x1 + 1, y1 + 1, 2, 0.16)
    # 桌面：透视木纹，近处暗
    art.poly(g, [(0, 47), (128, 47), (128, 64), (0, 64)], grad=(0.16, 0.03, math.pi / 2))
    art.noise_tex(g, (0, 47, 128, 64), scale=1.0, lo=0.4, hi=1.0, sx=0.08, oy=3)
    art.line(g, 0, 47, 128, 47, 1, 0.5)
    # 炉与烛台的接触阴影
    art.shadow(g, CX, 61, 30, 4, 0.85)
    art.shadow(g, CANDLE[0], 57.5, 9, 2.2, 0.8)


def _candlestick():
    holder = [(0, 1.4), (1, 3.0), (2, 3.2), (3, 1.4), (11, 1.2), (12, 3.0), (14.5, 5.8), (16, 6.2), (17, 4.0)]
    return art.lathe(holder, pitch=0.3, albedo=0.8, key="r.incense.holder", spec=0.9, shine=30, amb=0.08)


def _candle():
    return art.lathe([(0, 2.6), (12, 2.6)], pitch=0.3, albedo=0.92, key="r.incense.candle", spec=0.3, amb=0.25)


@register
class IncenseRitual(Ritual):
    id = "r.incense"
    name = "燃香"
    desc = "月夜供桌：手执三香就烛引火、甩灭明火插入铜炉；香随计时燃短，火星明灭、香灰断落，烟穿月光；烧完再续一炷"
    T = {"enter": 5.2, "interrupt": 2.0, "resume": 2.4, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.room = art.Layer(_room)

    def _look(self, g: Gfx):
        g.sharpen = 0.6

    # ------------------------------------------------------------ 共用画面

    def length(self, e: float) -> float:
        return lerp(FULL, STUB, (e % self.CYCLE) / self.CYCLE)

    def base(self, g: Gfx, t: float, flare: float = 0.0):
        """背景、月光、烛台、铜炉（每帧都画）"""
        self._look(g)
        self.room.draw(g)
        # 月光光柱：从窗斜照到右下，缓慢变化，浮尘在光里飘
        L = g.L()
        k = (art.XX - art.YY * 0.85 - 18) / 13
        beam = np.exp(-k * k) * np.clip(1 - art.YY / 70, 0, 1) * (0.07 + 0.02 * math.sin(t * 0.4))
        L += beam
        for i in range(9):
            ph = (t * 0.05 + i * 0.137) % 1
            dx = 14 + ph * 40 + math.sin(t * 0.7 + i) * 3
            dy = 4 + ph * 34 + math.cos(t * 0.5 + i * 2) * 3
            art.fill(g, (dx, dy, dx + 1, dy + 1), 0.55, 0.8, "max")
        # 烛台与烛火
        _candlestick().draw(g, CANDLE[0], 40)
        _candle().draw(g, CANDLE[0], 28)
        fx, fy = CANDLE
        fl = 1 + 0.15 * math.sin(t * 13) + 0.1 * noise(t * 6, 3) + flare
        art.glow(g, fx, fy - 4, 4 * fl, 0.25)
        art.fire(g, fx, fy, 4.2 * fl, 10 * fl, t, seed=5)
        art.disc(g, fx, fy - 2.5, 0.9, 1.6, v=0.15)   # 焰心
        art.line(g, fx, fy, fx, fy - 1.5, 1, 0.1)     # 烛芯
        _censer().draw(g, CX, RIM_Y)

    def stick_tip(self, i: int, length: float, sway: float = 0.0):
        bx, by = _world(STICK_DX[i], ASH_DY, STICK_DZ[i])
        lean = (i - 1) * 0.08 + sway
        return bx, by, bx + math.sin(lean) * length, by - math.cos(lean) * length

    def sticks(self, g: Gfx, length: float, lit, t: float, e: float, smoke: float = 1.0, glow: float = 1.0,
               ash: bool = True):
        tips = []
        for i in range(3):
            bx, by, tx, ty = self.stick_tip(i, length)
            # 香脚（竹签）露在香灰外一小段，上面是香身
            art.capsule(g, bx, by, lerp(bx, tx, 0.18), lerp(by, ty, 0.18), 0.75, base=0.45, amb=0.1, spec=0.2)
            art.capsule(g, lerp(bx, tx, 0.18), lerp(by, ty, 0.18), tx, ty, 0.85, 0.8, base=0.62, amb=0.1, spec=0.3)
            if lit[i]:
                f = 0.75 + 0.25 * noise(t * 2.5 + i * 3.1, self.seed + i)
                if ash and length > STUB + 2:  # 香灰：烧过的一截卷着挂在火星上，渐长、到点断落（按 e）
                    period = 37 + i * 11
                    k = ((e + i * 13.7) % period) / period
                    al = 0.5 + 3.2 * k
                    curl = (i - 1) * 0.6 + 0.4
                    art.line(g, tx, ty - 0.5, tx + curl * al * 0.4, ty - al, 1.3, 0.5, 1.0, v1=0.35)
                    if k < 0.06:  # 刚断落的一截往下掉
                        fy = ty + ease_in(k / 0.06) * (by - ty)
                        art.fill(g, (tx - 1, fy, tx + 1, fy + 1), 0.55)
                art.glow(g, tx, ty, 1.3, 0.8 * f * glow)
                art.disc(g, tx, ty, 1.0, v=1.0, alpha=min(glow, 1.0))
                tips.append((tx, ty, i))
        if smoke > 0 and tips:
            wind = (noise(t * 0.15, self.seed) - 0.5) * 22
            for tx, ty, i in tips:
                art.smoke(g, tx, ty - 1.5, (ty - 1.5) * smoke + 6, t + i * 3.3, width=3.5, spread=12 + i * 2,
                          density=3.5 * smoke, wind=wind + (i - 1) * 5, seed=self.seed + i, curl=4.5, speed=7.5)
        return tips

    def mx(self, g: Gfx, length: float, lit, t: float):
        g.mx[7, 1:7] = True
        g.mx[6, 2:6] = True
        h = 1 + int(round((length - STUB) / (FULL - STUB) * 4))
        for i, col in enumerate((2, 4, 5)):
            for r in range(5, 5 - h, -1):
                g.mx[r, col] = True
            tip = 5 - h
            if lit[i] and tip >= 0:
                g.mx[tip, col] = (t * 1.3 + i * 0.37) % 1 < 0.7
                sy = tip - 1 - int((t * 2 + i * 0.6) % max(tip, 1))
                if 0 <= sy < tip:
                    g.mx_set(col + (1 if int(t + i) % 2 else -1), sy)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        """左下角一方小印：第几炷"""
        n = int(e // self.CYCLE) + 1
        s = label or (f"第{cn_num(n)}炷" if n < 100 else f"{n}炷")
        from ..engine.gfx import text_width
        w = text_width(s, 8)
        g.k.rectangle((2, 52, 6 + w, 62), fill=1)
        g.text(4, 54, s, size=8)
        g.d.rectangle((2, 52, 6 + w, 62), outline=1)

    # ------------------------------------------------------------ 手的动作

    def _holding(self, g: Gfx, hx, hy, length, lit, t, flames=0.0, ang=math.pi * 0.62, fanned=0.0):
        """握着三炷香的手：香从拳心穿过，香头在下方。返回三个香头位置"""
        tips = []

        def under(hg):
            for i in range(3):
                spread = (i - 1) * (2.2 + fanned * 3)
                ax, ay = hx + math.cos(ang) * 8 + spread * 0.6, hy + math.sin(ang) * 8
                txx = ax + math.cos(ang) * length * 0.75 + spread
                tyy = ay + math.sin(ang) * length * 0.75
                art.capsule(hg, ax - math.cos(ang) * 6, ay - math.sin(ang) * 6, txx, tyy, 0.8, base=0.6, amb=0.1)
                tips.append((txx, tyy))
        rig.hand(g, hx, hy, ang, s=2.3, curl=0.92, thumb=0.9, sleeve=1.0, sleeve_ang=-0.45, under=under,
                 flare=1.0, sleeve_tone=0.3)
        for i, (tx, ty) in enumerate(tips):
            if lit[i]:
                art.glow(g, tx, ty, 2.0, 0.9)
                art.disc(g, tx, ty, 1.0, v=1.0)
                if flames > 0:
                    art.fire(g, tx, ty, 2.6 * flames, 6 * flames, t + i, seed=i)
        return tips

    def _plant(self, g: Gfx, t: float, e: float, renewing: bool = False):
        """引火 → 甩灭 → 插香 → 松手（入场与续香共用），t ∈ [0, 5.2]"""
        self.base(g, t)
        if t < 3.7:
            # 0–1.2 伸到烛火上；1.2–2.1 引燃（香头冒明火）；2.1–2.8 甩手扇灭；2.8–3.7 移到炉上插下
            p = ease_out(span(t, 0, 1.2))
            hx, hy = lerp(150, 92, p), lerp(-12, 6, p)
            lit = tuple(t > 1.35 + i * 0.12 for i in range(3))
            flames = clamp((t - 1.35) / 0.3) * (1 - span(t, 2.1, 2.6))
            if 2.1 <= t < 2.8:  # 抖手：快速小幅左右摆
                k = (t - 2.1) / 0.7
                hx += math.sin(k * math.pi * 6) * 4 * (1 - k)
                hy += math.cos(k * math.pi * 6) * 1.5 * (1 - k)
            if t >= 2.8:
                q = ease_in_out(span(t, 2.8, 3.55))
                hx, hy = lerp(92, CX + 13, q), lerp(6, -1, q)
                hy += span(t, 3.4, 3.7) * 4
            ang = lerp(math.pi * 0.62, math.pi * 0.5, span(t, 2.8, 3.4))
            fan = 1 - span(t, 2.8, 3.4)
            tips = self._holding(g, hx, hy, FULL + 6, lit, t, flames, ang, fan * 0.5)
            if t > 2.2:  # 扇灭明火冒出的一股烟
                for (tx, ty), i in zip(tips, range(3)):
                    art.smoke(g, tx, ty - 1, 16 * span(t, 2.2, 3.0), t + i, width=2, spread=7, density=0.7,
                              seed=i + 20)
            self.mx(g, FULL, (0, 0, 0), t)
        else:
            # 插好了：香在炉里；手指松开、手收回
            self.sticks(g, FULL, (1, 1, 1), t, e, smoke=ease_out(span(t, 3.7, 5.2)), ash=False)
            if t < 3.9:  # 插进香灰时扬起一点灰
                k = span(t, 3.7, 3.9)
                bx, by = _world(0, ASH_DY, 0)
                for j in range(10):
                    a = j / 10 * math.pi
                    art.fill(g, (bx + math.cos(a) * 9 * k, by - math.sin(a) * 4 * k - 1,
                                 bx + math.cos(a) * 9 * k + 1, by - math.sin(a) * 4 * k), 0.6, 1 - k)
            q = ease_in(span(t, 3.9, 5.0))
            if q < 1:
                rig.hand(g, lerp(CX + 13, 150, q), lerp(3, -20, q), math.pi * 0.5, s=1.55,
                         curl=lerp(0.92, 0.25, span(t, 3.7, 4.0)), thumb=lerp(0.9, 0.2, span(t, 3.7, 4.0)),
                         sleeve=1.3, sleeve_ang=-0.55, flare=1.2)
            self.mx(g, FULL, (1, 1, 1), t)
        if not renewing:
            g.L()[:] *= ease_out(span(t, 0, 0.8))  # 入场：从黑暗里亮起

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self._plant(g, t, 0.0)
        if t > 3.0:
            self.counter(g, 0.0)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            if k < 1.6:  # 残香的火星暗去
                self.base(g, t)
                self.sticks(g, STUB, (1, 1, 1), t, e, smoke=1 - k / 1.6, glow=1 - k / 1.6, ash=False)
                self.mx(g, STUB, (k < 0.8,) * 3, t)
            else:
                self._plant(g, (k - 1.6) * 5.2 / (RENEW - 1.6), e, renewing=True)
                for i in range(3):  # 旧香根留在炉里
                    bx, by = _world(STICK_DX[i] + 2.5, ASH_DY, STICK_DZ[i] + 1)
                    art.capsule(g, bx, by, bx, by - STUB, 0.7, base=0.3, amb=0.1)
            self.counter(g, e)
            return
        length = self.length(e)
        self.base(g, t)
        self.sticks(g, length, (1, 1, 1), t, e)
        self.counter(g, e)
        self.mx(g, length, (1, 1, 1), t)

    def interrupt(self, g: Gfx, t: float, e: float):
        length = self.length(e)
        self.base(g, t)
        lit = tuple(t < 0.55 + i * 0.4 for i in range(3))
        smoke = 1 - ease_out(span(t, 0.3, 1.9))
        self.sticks(g, length, lit, t, e, smoke=smoke)
        if t < 1.7:  # 手从右上伸来，拇指食指依次捏灭香头
            j = min(2, int(max(t - 0.15, 0) / 0.4))
            bx, by, tx, ty = self.stick_tip(j, length)
            pinch = (t - 0.15) % 0.4 / 0.4
            come = ease_out(span(t, 0, 0.35))
            hx = lerp(150, tx + 9, come)
            hy = lerp(-15, ty - 11, come) + math.sin(pinch * math.pi) * 2
            rig.hand(g, hx, hy, math.pi * 0.72, s=1.45, curl=[0.15 + 0.5 * pinch, 0.85, 0.95, 1.0],
                     thumb=0.3 + 0.6 * pinch, sleeve=1.3, sleeve_ang=-0.6, flare=1.2)
        else:
            q = ease_in(span(t, 1.7, 2.0))
            _, _, tx, ty = self.stick_tip(2, length)
            rig.hand(g, lerp(tx + 9, 150, q), lerp(ty - 11, -20, q), math.pi * 0.72, s=1.45,
                     curl=[0.4, 0.85, 0.95, 1.0], thumb=0.6, sleeve=1.3, sleeve_ang=-0.6, flare=1.2)
        self.counter(g, e, "暂熄")
        self.mx(g, length, lit, t)

    def resume(self, g: Gfx, t: float, e: float):
        """火折子：手拿一截竹筒，吹一口气冒出火苗，逐一点亮香头"""
        length = self.length(e)
        self.base(g, t)
        lit = tuple(t > 1.05 + i * 0.35 for i in range(3))
        self.sticks(g, length, lit, t, e, smoke=ease_out(span(t, 1.2, 2.4)))
        if t < 2.15:
            j = min(2, max(0, int((t - 0.9) / 0.35)))
            bx, by, tx, ty = self.stick_tip(j, length)
            come = ease_out(span(t, 0, 0.6))
            hx = lerp(150, tx + 8, come) if t < 0.9 else tx + 8
            hy = lerp(-10, ty - 3, come) if t < 0.9 else ty - 3
            out = ease_in(span(t, 1.85, 2.15))
            hx, hy = lerp(hx, 150, out), lerp(hy, -10, out)
            fold = (hx - 8, hy + 1)

            def under(hg):  # 火折子竹筒
                art.capsule(hg, fold[0] + 6, fold[1] - 2, fold[0] - 1, fold[1] + 1, 1.3, base=0.55, amb=0.15)
            rig.hand(g, hx + 4, hy - 6, math.pi * 0.85, s=1.35, curl=0.95, thumb=0.9, sleeve=1.2,
                     sleeve_ang=-0.5, under=under, flare=1.2)
            fl = span(t, 0.5, 0.8)  # 吹一下，火苗腾起
            art.fire(g, fold[0] - 1, fold[1] + 1, 2.5 * fl, 5 * fl, t, seed=9)
            art.glow(g, fold[0] - 1, fold[1] - 1, 3, 0.5 * fl)
        self.counter(g, e)
        self.mx(g, length, lit, t)

    def complete(self, g: Gfx, t: float, e: float):
        length0 = self.length(e)
        burn = ease_in(span(t, 0, 1.6))
        length = lerp(length0, STUB, burn)
        flare = 0.6 * span(t, 1.6, 2.2) * (1 - span(t, 3.5, 5.0))
        self.base(g, t, flare=flare)
        glow = 1 + 1.5 * math.sin(math.pi * span(t, 1.2, 2.4))
        alive = t < 2.6
        self.sticks(g, length, (alive,) * 3, t, e, smoke=1 - span(t, 2.0, 3.0), glow=glow, ash=False)
        if t > 1.4:  # 烟聚成一团，盘旋上升
            k = span(t, 1.4, 5.5)
            cx, cy = CX + math.sin(t * 1.3) * 3, 26 - k * 30
            for j in range(5):
                a = t * 2.2 + j * 1.256
                art.smoke(g, cx + math.cos(a) * 5 * (1 + k), cy + math.sin(a) * 3, 12, t + j, width=3,
                          spread=7 + k * 6, density=0.7 * (1 - k), seed=40 + j)
        if t > 2.6:
            from ..engine.fx import typewriter
            typewriter(g, 72, 4, "功德圆满", t - 2.6, cps=4, align="center")
        self.counter(g, e)
        g.mx[7, 1:7] = True
        g.mx[6, 2:6] = True
        if t > 1.6:
            r = (t - 1.6) * 3
            for y in range(6):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, (y - 6) * 1.2) - r) < 0.7:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(4 * (1 - span(t, 1.6, 3.5)))
