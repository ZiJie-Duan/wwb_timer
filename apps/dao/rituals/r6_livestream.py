"""直播祈福（像素风）：小道士举着自拍杆在供桌前开直播，弹幕刷“福生无量天尊”，爱心往上飘。

依据：近年宫观开“云祈福”“线上法会”直播；“福生无量天尊”是道门的礼语（道门称“无量天尊”），
与佛门“阿弥陀佛”相对，所以弹幕刷的是它。LIVE、在线人数、点赞爱心、“送出火箭”、“主播暂时离开”都是直播间的标准元素。

入场：补光灯没开，屏中间大字倒数 3、2、1；“开播”——补光灯一闪亮起（闪白、一震），底栏 LIVE 弹出，
      小道士举着自拍杆向镜头作揖，第一条弹幕“福生无量天尊”飘过，手机上冒出爱心。
持续：弹幕从右往左飘（两条轨道，按计时推进，暂停就定格）；小道士对着手机说话（嘴一张一合），自拍杆跟着晃，
      每 9 秒对镜头低头一揖；左边供桌上香炉冒烟、烛火跳；爱心从手机往上飘；底栏在线人数慢慢涨、点赞数跳、香火条一轮 10 分钟涨满；
      每 53 秒有人“送出火箭”：一枚像素火箭拖着火星飞过，左边弹出礼物卡，小道士先惊后喜、作揖道谢。
      一轮满：香火条一闪，爱心从手机炸开，一震，“香火已满”，小道士深深一揖，“第几场”加一。
中断：小道士挥别、垂下自拍杆转身，补光灯熄，画面压暗（网点），弹幕定格消失，LIVE 变空心，“主播暂时离开”。
恢复：“主播回来了”，小道士转回来举起自拍杆，补光灯一闪亮起，画面亮回，弹幕接着飘。
圆满：两条轨道一起刷屏“福生无量天尊”，闪白、爱心炸开，小道士深深一揖，收成“直播已结束”卡片（点赞数、香火 100%）。
点阵：一颗跟着节拍跳动的心；暂停时是暂停符号；香火满 / 圆满时心炸开成一圈。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx, text_width
from ..engine.scene import register
from .r6_common import R6, badge, banner, dao, nth, pixsmoke, tiny

FLOOR = 57
DX = 50                        # 小道士
TABLE = (2, 34, 45)            # 供桌
CENSER_X = 18
RING = (112, 31)               # 补光灯中心
CLIP = 36                      # 弹幕左边界（左上角留给计数牌）
LANES = (1, 13)
SPEED = 26.0
SLOT = 5.5
T0 = 3.2                       # 第一条弹幕在入场的这一刻进来
RENEW = 6.0
ROCKET = 53.0
MSGS = ["福生无量天尊", "无量天尊", "道法自然", "求平安", "考研上岸", "福生无量天尊", "身体健康", "上上签",
        "心想事成", "道长好", "风调雨顺", "福生无量天尊"]


# ---------------------------------------------------------------- 道具

def _censer():
    """小香炉 15×10：立耳、口沿、鼓腹回纹、三足"""
    p = Part(15, 10)
    p.shape("rectangle", (1, 0, 2, 2), fill=1)
    p.shape("rectangle", (12, 0, 13, 2), fill=1)
    p.shape("rectangle", (0, 2, 14, 3), fill=1)
    p.shape("polygon", [(1, 4), (13, 4), (14, 5), (12, 7), (2, 7), (0, 5)], fill=1)
    p.d.line((1, 3, 13, 3), fill=0)
    for x in range(3, 12, 3):
        p.px(x, 5, 0), p.px(x + 1, 6, 0)
    p.dither([(9, 5), (14, 5), (12, 7), (9, 7)], 0.5, 0)
    for x in (2, 7, 12):
        p.shape("rectangle", (x, 7, x, 9), fill=1)
    return p.sprite()


def _candle():
    """烛台 5×11：蜡烛（高光一线）、托盘、细柄、底座"""
    p = Part(5, 11)
    p.shape("rectangle", (1, 0, 3, 4), fill=1)
    p.px(3, 1, 0), p.px(3, 3, 0)
    p.shape("rectangle", (0, 5, 4, 5), fill=1)
    p.shape("rectangle", (2, 6, 2, 8), fill=1)
    p.shape("rectangle", (1, 9, 3, 10), fill=1)
    p.px(0, 10)
    p.px(4, 10)
    return p.sprite()


def _phone():
    """自拍杆上的手机 6×9：背面摄像头（圆圈）、闪光灯"""
    p = Part(6, 9)
    p.shape("rectangle", (0, 0, 5, 8), fill=1)
    p.d.rectangle((1, 1, 3, 3), fill=0)
    p.px(2, 2)
    p.px(4, 1, 0)
    p.d.line((1, 7, 4, 7), fill=0)
    return p.sprite()


def _ring(on=True):
    """环形补光灯 17×17：双圈灯环（亮时一圈 LED 点、灭时网点），中间夹手机的支架"""
    p = Part(17, 17)
    p.shape("ellipse", (0, 0, 16, 16), fill=1)
    p.d.ellipse((4, 4, 12, 12), fill=0)
    p.m.ellipse((4, 4, 12, 12), fill=0)
    p.d.ellipse((1, 1, 15, 15), outline=0 if not on else 1)
    if on:
        for i in range(12):
            a = i / 12 * 2 * math.pi
            p.px(round(8 + math.cos(a) * 6), round(8 + math.sin(a) * 6), 0)
    else:
        p.dither((0, 0, 16, 16), 0.5, 0)
    p.shape("rectangle", (8, 12, 8, 16), fill=1)
    return p.sprite()


def _rocket():
    """火箭 16×9（朝左飞）：尖头、舷窗（高光）、机身环线、上下尾翼、尾喷口"""
    p = Part(16, 9)
    p.shape("polygon", [(0, 4), (4, 1), (13, 1), (13, 7), (4, 7)], fill=1)
    p.d.ellipse((5, 2, 9, 6), fill=0)
    p.px(6, 3)
    p.d.line((11, 2, 11, 6), fill=0)
    p.shape("polygon", [(10, 1), (14, 0), (15, 0), (13, 2)], fill=1)
    p.shape("polygon", [(10, 7), (14, 8), (15, 8), (13, 6)], fill=1)
    p.shape("rectangle", (14, 3, 15, 5), fill=1)
    p.dither([(4, 5), (13, 5), (13, 7), (4, 7)], 0.5, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"censer": _censer, "candle": _candle, "phone": _phone, "ring": _ring,
                        "ring_off": lambda: _ring(False), "rocket": _rocket}[name]()
    return _PROPS[name]


FLAME = pix.frames("""
 #
 #
###
---
  #
 #
###
---
 #
##
###
""")
JET = pix.frames("""
###
 ####
###
---
####
  ####
####
""")
HEART = pix.sprite("""
.#.#.
#####
#####
.###.
..#..
""")
HEART_S = pix.sprite("""
#.#
###
.#.
""")


# ---------------------------------------------------------------- 画面

def stage_bg(g: Gfx, t: float, light: bool):
    """舞台：地板线、踢脚、左边供桌（香炉 + 两支烛台），右边环形补光灯（三脚架）"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    for x in range(4, 128, 10):
        g.px(x, FLOOR - 1)
    x0, x1, ty = TABLE
    g.d.rectangle((x0, ty, x1, ty + 2), fill=1)
    g.d.line((x0 + 1, ty + 1, x1 - 1, ty + 1), fill=0)
    g.d.rectangle((x0 + 2, ty + 3, x1 - 2, FLOOR - 1), outline=1, fill=0)
    pix.checker(g, (x0 + 3, ty + 4, x1 - 2, FLOOR - 1), 0.125)
    g.d.rectangle((x0 + 12, ty + 5, x0 + 20, FLOOR - 2), fill=0)
    g.d.rectangle((x0 + 13, ty + 6, x0 + 19, FLOOR - 3), outline=1)
    g.px(x0 + 16, ty + 8)
    pix.blit(g, prop("censer"), CENSER_X - 7, ty - 10)
    for k, x in enumerate((6, 30)):
        pix.blit(g, prop("candle"), x - 2, ty - 11)
        pix.blit(g, pix.anim(FLAME, t + k * 0.37, 7), x - 1, ty - 14, outline=False)
    rx, ry = RING                                    # 补光灯三脚架
    g.d.line((rx, ry + 8, rx, FLOOR - 6), fill=1)
    g.d.line((rx, FLOOR - 6, rx - 6, FLOOR), fill=1)
    g.d.line((rx, FLOOR - 6, rx + 6, FLOOR), fill=1)
    g.d.line((rx, FLOOR - 6, rx, FLOOR), fill=1)
    g.d.rectangle((rx - 1, ry + 14, rx + 1, ry + 15), fill=1)
    pix.blit(g, prop("ring" if light else "ring_off"), rx - 8, ry - 8)
    if light:
        for i in range(3):                           # 补光朝小道士打过去
            y = ry - 6 + i * 6
            ph = int(t * 8 + i) % 4
            pix.dotted(g, rx - 12 - ph, y + (i - 1) * 1, rx - 18 - ph, y + (i - 1) * 2, 2)


def incense_smoke(g: Gfx, t: float, amount: float = 1.0):
    for i, dx in enumerate((-3, 0, 3)):
        pixsmoke(g, CENSER_X + dx, TABLE[2] - 12, t + i * 0.9, seed=11 + i, height=20, amount=amount,
                 sway=2, drift=math.sin(t * 0.4) * 3, bits=False, n=5, rate=0.35)
    for dx in (-3, 0, 3):
        g.d.line((CENSER_X + dx, TABLE[2] - 11, CENSER_X + dx, TABLE[2] - 15), fill=1)


def selfie(g: Gfx, t: float, angle: float = 25, stick: float = 40, head: str = "up", face: str = "normal",
           flip: bool = False, x: float = DX, legs: str = "stand", rec: bool = True):
    """小道士举自拍杆：手臂 angle，杆子朝 stick 度伸出 14 像素，杆头手机。返回手机中心"""
    h = dao(g, x, FLOOR, t, angle=angle, head=head, face=face, flip=flip, legs=legs)
    hx, hy = h["hand"]
    s = -1 if flip else 1
    a = math.radians(stick)
    ex, ey = hx + s * math.cos(a) * 14, hy - math.sin(a) * 14
    g.d.line((hx, hy, ex, ey), fill=1)
    g.d.line((hx + s, hy, hx + s * 4, hy - 3 * math.tan(a)), fill=1)       # 握把
    pix.blit(g, prop("phone"), ex - 3, ey - 5, flip=flip)
    if rec and int(t * 2) % 2 == 0:
        g.px(ex + s * 2, ey - 6)
    return ex, ey


def strip(g: Gfx, e: float, t: float, live: bool = True, p: float = 0.0, slide: float = 1.0):
    """底栏：LIVE 牌、在线人数、点赞数、香火条"""
    off = int((1 - slide) * 30)
    x = 1 - off
    if live:
        g.d.rectangle((x, 58, x + 18, 63), fill=1)
        tiny(g, x + 2, 59, "LIVE", fill=0)
        if int(t * 2) % 2 == 0:
            g.px(x + 17, 59, 0)
    else:
        g.d.rectangle((x, 58, x + 18, 63), outline=1)
        tiny(g, x + 2, 59, "LIVE")
    viewers = 1200 + int(e * 1.9) + int(rand(int(t * 2), 3) * 9)
    vs = f"{viewers / 10000:.1f}W" if viewers >= 10000 else str(viewers)
    g.d.ellipse((22 - off, 59, 28 - off, 63), outline=1)           # 眼睛
    g.px(25 - off, 61)
    tiny(g, 30 - off, 59, vs)
    likes = 300 + int(e * 4.3)
    ls = f"{likes / 10000:.1f}W" if likes >= 10000 else str(likes)
    pix.blit(g, HEART_S, 52 - off, 60, outline=False)
    tiny(g, 57 - off, 59, ls)
    for i in range(3):                                            # 香火条：三根小香
        g.d.line((82 + i * 2 + off, 59, 82 + i * 2 + off, 63), fill=1)
    g.d.rectangle((89 + off, 58, 126 + off, 63), outline=1)
    w = int(round(35 * clamp(p)))
    if w > 0:
        g.d.rectangle((90 + off, 60, 90 + off + w - 1, 61), fill=1)


def hearts(g: Gfx, t: float, x: float, y: float, rate: float = 1.0, n: int = 5):
    """爱心从手机往上飘（无状态）"""
    if rate <= 0:
        return
    for j in range(n):
        u = t * 0.6 * rate + j / n
        ph = u % 1
        cyc = int(u)
        if rand(cyc * 5 + j, 21) > 0.8:
            continue
        hx = x + 4 + math.sin(ph * 6 + j * 2 + cyc) * 3 + ph * 8
        hy = y - 4 - ph * 26
        spr = HEART if rand(cyc * 3 + j, 22) < 0.4 and ph < 0.7 else HEART_S
        if ph > 0.8 and int(t * 12) % 2:
            continue
        pix.blit(g, spr, hx - spr.w // 2, hy - spr.h // 2)


def danmaku_list(tau: float, skip_lane2: bool = False):
    """τ 时刻屏上的弹幕：[(lane_y, x, s)]（按计时推进，同一轨道里互不重叠）"""
    out = []
    for li, ly in enumerate(LANES):
        if li == 1 and skip_lane2:
            continue
        off = T0 + li * SLOT / 2
        n0 = int(math.floor((tau - off) / SLOT))
        for n in (n0 - 1, n0):
            if n < 0:
                continue
            if not (li == 0 and n == 0) and rand(n * 7 + li, 31) > 0.72:
                continue
            start = off + n * SLOT
            s = MSGS[0] if (li == 0 and n == 0) else MSGS[int(rand(n * 11 + li, 32) * len(MSGS))]
            x = 128 - (tau - start) * SPEED
            out.append((ly, x, s))
    return out


def draw_danmaku(g: Gfx, items):
    """先画全部黑底板，再写字；左边进了计数牌区域的字一个个“吃掉”"""
    vis = []
    for ly, x, s in items:
        i = 0
        while i < len(s) and x + text_width(s[:i], 12) < CLIP:
            i += 1
        if i >= len(s) or x >= 128:
            continue
        xs = x + text_width(s[:i], 12)
        sub = s[i:]
        w = text_width(sub, 12)
        if xs + w > 128:                       # 右边还没进来的字先不写
            k = len(sub)
            while k > 0 and xs + text_width(sub[:k], 12) > 128:
                k -= 1
            sub = sub[:k]
            w = text_width(sub, 12)
        if not sub:
            continue
        vis.append((ly, int(round(xs)), sub, w))
    for ly, xs, sub, w in vis:
        g.d.rectangle((xs - 1, ly - 1, xs + w, ly + 11), fill=0)
    for ly, xs, sub, w in vis:
        g.text(xs, ly, sub)


def mx_heart(g: Gfx, t: float, big: bool | None = None):
    beat = (t * 1.3) % 1 < 0.3 if big is None else big
    if beat:
        g.mx_rows([0b01100110, 0b11111111, 0b11111111, 0b11111111, 0b01111110, 0b00111100, 0b00011000, 0])
    else:
        g.mx_rows([0, 0b00100100, 0b01111110, 0b01111110, 0b00111100, 0b00011000, 0, 0])


def mx_pause(g: Gfx):
    g.mx_rows([0, 0b01100110, 0b01100110, 0b01100110, 0b01100110, 0b01100110, 0b01100110, 0])


def mx_burst(g: Gfx, r: float):
    for y in range(8):
        for x in range(8):
            if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.7:
                g.mx[y, x] = True


@register
class LiveStream(R6):
    id = "r6.livestream"
    name = "直播祈福"
    desc = "小道士举着自拍杆在供桌前开直播，弹幕刷“福生无量天尊”，爱心往上飘，有人送火箭，香火条涨满"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 2.0, "complete": 5.5}
    CYCLE = 600.0

    def pct(self, e: float) -> float:
        return (e % self.CYCLE) / self.CYCLE

    def tau(self, e: float) -> float:
        return e + self.T["enter"]

    def talk(self, g: Gfx, t: float, e: float, face_override: str | None = None):
        """说话、晃杆、每 9 秒一揖"""
        ph = t % 9
        if 7.4 < ph < 8.8:
            return selfie(g, t, angle=18, stick=30, head="bow")
        face = face_override or ("happy" if ph < 5 and int(t * 3) % 2 == 0 else "normal")
        wob = math.sin(t * 1.7) * 3
        return selfie(g, t, angle=25 + wob, stick=40 + wob, face=face)

    def counter(self, g: Gfx, e: float):
        badge(g, nth(int(e // self.CYCLE) + 1, "场"))

    def rocket(self, g: Gfx, e: float, t: float, dt: float):
        """送火箭：火箭飞过 + 左边礼物卡。返回 (礼物卡进度 0..1 或 None, 惊喜表情)"""
        if e < 20:
            return None, None
        r = e % ROCKET
        if r > 4.2:
            return None, None
        q = span(r, 0, 1.8)
        if 0 < q < 1:
            x = lerp(132, -22, q)
            y = 40 - q * 14 + math.sin(q * 9) * 2
            pix.blit(g, prop("rocket"), x, y)
            pix.blit(g, pix.anim(JET, t, 12), x + 16, y + 2, outline=False)
            if int(t * 30) % 2 == 0:
                self.sparks.burst(x + 18, y + 4, 2, 14, life=0.4, gravity=20)
        card = span(r, 1.4, 1.8) if r < 3.8 else 1 - span(r, 3.8, 4.2)
        face = "wow" if r < 1.6 else "happy"
        return card, face

    def gift_card(self, g: Gfx, k: float):
        """礼物卡：左边滑进来（黑底、白框、小火箭图标、“送出火箭”）"""
        if k <= 0:
            return
        x = -66 + 68 * ease_out_back(k)
        g.d.rectangle((x - 1, 12, x + 66, 26), fill=0)
        g.d.rectangle((x, 13, x + 65, 25), outline=1)
        spr = prop("rocket")
        pix.blit(g, spr, x + 2, 15)
        g.text(x + 19, 14, "送出火箭")

    # ------------------------------------------------------------ 入场：倒数开播

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        on = t >= 2.4
        stage_bg(g, t, on)
        incense_smoke(g, t)
        if t < 2.4:
            px, py = selfie(g, t, angle=-20 if t < 0.8 else 25, stick=-30 if t < 0.8 else 40, rec=False,
                            face="normal")
        elif t < 4.0:
            px, py = selfie(g, t, angle=18, stick=30, head="bow" if 2.9 < t < 3.8 else "up", face="happy")
        else:
            px, py = self.talk(g, t, 0)
        if abs(t - 2.4) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(RING[0], RING[1], 16, 34, life=0.5, gravity=20)
        if 2.4 < t < 2.7:
            pix.shake(g, t, 1.5)
        if t < 2.4:
            pix.checker(g, (0, 0, 128, FLOOR), 0.5, fill=0)
        hearts(g, t - 3.0, px, py, rate=span(t, 3.0, 3.6))
        self.fx(g, dt)
        if on:
            strip(g, 0, t, True, 0, slide=ease_out_back(span(t, 2.4, 2.9)))
            mx_heart(g, t)
        else:
            g.mx_rows([0, 0b00111100, 0b01000010, 0b01011010, 0b01011010, 0b01000010, 0b00111100, 0]) \
                if int(t * 4) % 2 else g.mx_rows([0, 0, 0b00011000, 0b00111100, 0b00111100, 0b00011000, 0, 0])
        if t < 2.4:                                    # 倒数 3、2、1（大字，最后画）
            n = 3 - int(t / 0.8)
            k = (t % 0.8) / 0.8
            sc = 3 if k > 0.15 else 4
            w = text_width(str(n), 12) * sc
            x0, y0 = 88, 6
            g.d.rectangle((x0 - w / 2 - 3, y0 - 2, x0 + w / 2 + 3, y0 + 11 * sc + 2), fill=0)
            g.text(x0, y0, str(n), scale=sc, align="center")
        else:
            if t > 2.8:
                self.counter(g, 0)
            draw_danmaku(g, danmaku_list(t, skip_lane2=True))

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self.renew(g, t, e, k, dt)
            return
        stage_bg(g, t, True)
        incense_smoke(g, t)
        card, rface = self.rocket(g, e, t, dt)
        if card is not None and (e % ROCKET) > 2.2 and (e % ROCKET) < 3.4:   # 作揖道谢
            px, py = selfie(g, t, angle=18, stick=30, head="bow", face="happy")
        else:
            px, py = self.talk(g, t, e, rface)
        hearts(g, t, px, py, rate=1.6 if card else 1.0)
        self.fx(g, dt)
        strip(g, e, t, True, self.pct(e))
        mx_heart(g, t)
        show_badge = t < 5 or (e % 60) < 4
        if card:
            self.gift_card(g, card)
            draw_danmaku(g, danmaku_list(self.tau(e), skip_lane2=True))
        else:
            if show_badge:
                self.counter(g, e)
            draw_danmaku(g, danmaku_list(self.tau(e), skip_lane2=show_badge))

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """香火满：心炸开，“香火已满”，深深一揖，新的一场"""
        stage_bg(g, t, True)
        incense_smoke(g, t, 1.5)
        if k < 1.0:
            px, py = selfie(g, t, angle=25, stick=40, face="wow")
        elif k < 3.6:
            px, py = selfie(g, t, angle=14, stick=26, head="bow")
        else:
            px, py = self.talk(g, t, e, "happy")
        if k < dt * 1.5:
            pix.flash(g)
        if abs(k - 0.3) < dt * 0.6:
            for j in range(10):
                a = j / 10 * 2 * math.pi
                self.sparks.burst(px + math.cos(a) * 4, py + math.sin(a) * 4, 2, 30, life=0.8, gravity=10)
        if k < 0.6:
            pix.shake(g, t, 1.5)
        if 0.3 < k < 1.6:                              # 心一圈圈炸开
            r = (k - 0.3) * 30
            for j in range(10):
                a = j / 10 * 2 * math.pi + k
                pix.blit(g, HEART_S, px + math.cos(a) * r - 1, py + math.sin(a) * r * 0.7 - 1)
        hearts(g, t, px, py, rate=2.0)
        self.fx(g, dt)
        full = k < 3.6
        strip(g, e, t, True, 1.0 if full and int(k * 6) % 2 == 0 else (0 if full else self.pct(e)))
        mx_heart(g, t)
        if 0.3 < k < 2.0:
            g.mx[:] = False
            mx_burst(g, (k - 0.3) * 4)
            g.mx_level = 6
        if k < 3.6:
            banner(g, 64, 8, "香火已满", span(k, 0.4, 0.8), t=t)
        else:
            self.counter(g, e)
            draw_danmaku(g, danmaku_list(self.tau(e), skip_lane2=True))

    # ------------------------------------------------------------ 中断 / 恢复

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        light = t < 0.6
        stage_bg(g, t, light)
        incense_smoke(g, t)
        if t < 0.6:
            selfie(g, t, angle=18, stick=30, head="bow", face="happy")
        else:
            q = span(t, 0.6, 1.0)
            selfie(g, t, angle=lerp(25, -30, q), stick=lerp(40, -40, q), flip=t > 1.0, rec=False)
        if abs(t - 0.6) < dt * 0.6:
            self.puffs.emit(RING[0], RING[1], vy=-4, life=0.6, rmax=2.5, spread=0)
        if t > 0.6:
            pix.checker(g, (0, 0, 128, FLOOR + 1), 0.25 if t < 0.9 else 0.5, fill=0)
        self.fx(g, dt)
        strip(g, e, t, t < 0.6, self.pct(e))
        if t < 0.6:
            mx_heart(g, t)
            draw_danmaku(g, danmaku_list(self.tau(e)))
        else:
            mx_pause(g)
            banner(g, 64, 8, "主播暂时离开", span(t, 0.7, 1.05), stars=False, t=t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        light = t >= 0.9
        stage_bg(g, t, light)
        incense_smoke(g, t)
        if t < 0.5:
            selfie(g, t, angle=-30, stick=-40, flip=True, rec=False)
        elif t < 0.9:
            q = span(t, 0.5, 0.9)
            selfie(g, t, angle=lerp(-30, 25, q), stick=lerp(-40, 40, q), face="happy")
        else:
            px, py = self.talk(g, t, e, "happy" if t < 1.5 else None)
            hearts(g, t - 0.9, px, py, rate=span(t, 0.9, 1.4))
        if abs(t - 0.9) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(RING[0], RING[1], 14, 30, life=0.5, gravity=20)
        if 0.9 < t < 1.15:
            pix.shake(g, t, 1)
        if t < 0.9:
            pix.checker(g, (0, 0, 128, FLOOR + 1), 0.5 if t < 0.6 else 0.25, fill=0)
        self.fx(g, dt)
        strip(g, e, t, t >= 0.9, self.pct(e))
        if t < 0.9:
            mx_pause(g) if int(t * 4) % 2 == 0 else mx_heart(g, t, big=False)
        else:
            mx_heart(g, t)
        if t < 1.3:
            banner(g, 64, 8, "主播回来了", span(t, 0.0, 0.35), t=t)
        else:
            self.counter(g, e)
            draw_danmaku(g, danmaku_list(self.tau(e), skip_lane2=True))

    # ------------------------------------------------------------ 圆满：刷屏、深揖、直播已结束

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        stage_bg(g, t, t < 3.2)
        incense_smoke(g, t)
        if t < 1.6:
            px, py = self.talk(g, t, e, "happy")
        elif t < 3.4:
            px, py = selfie(g, t, angle=12, stick=22, head="bow")
        else:
            px, py = selfie(g, t, angle=25, stick=40, face="happy", rec=False)
        hearts(g, t, px, py, rate=2.5 if t < 3.2 else 0)
        if abs(t - 1.6) < dt * 0.6:
            pix.flash(g)
            for j in range(12):
                a = j / 12 * 2 * math.pi
                self.sparks.burst(px + math.cos(a) * 4, py + math.sin(a) * 4, 2, 36, life=1.0, gravity=10)
        if 1.6 < t < 2.0:
            pix.shake(g, t, 1.8)
        if 1.6 < t < 2.8:
            r = (t - 1.6) * 40
            for j in range(12):
                a = j / 12 * 2 * math.pi + t
                pix.blit(g, HEART_S, px + math.cos(a) * r - 1, py + math.sin(a) * r * 0.6 - 1)
        self.fx(g, dt)
        strip(g, e, t, t < 3.2, 1.0)
        if t < 1.6:
            mx_heart(g, t * 2)
        else:
            mx_burst(g, (t - 1.6) * 4 % 6)
            if t > 3.2:
                mx_heart(g, t, big=True)
            g.mx_level = 1 + int(6 * (1 - span(t, 1.6, 3.0)))
        if t < 3.2:                                    # 两条轨道一起刷屏
            tau = t * 2.2
            items = []
            for li, ly in enumerate(LANES):
                s = "福生无量天尊福生无量天尊"
                x = 128 - ((tau * 30 + li * 40) % 400)
                items.append((ly, x if x > -150 else x + 400, s))
            draw_danmaku(g, items)
        else:                                          # 直播已结束卡片
            k = ease_out_back(span(t, 3.2, 3.6))
            y0 = 8 + (1 - k) * 20
            g.d.rectangle((18, y0, 109, y0 + 37), fill=0)
            g.d.rectangle((19, y0 + 1, 108, y0 + 36), outline=1)
            g.d.line((21, y0 + 17, 106, y0 + 17), fill=1)
            pix.blit(g, HEART, 26, y0 + 23)
            likes = 300 + int(e * 4.3)
            tiny(g, 33, y0 + 23, f"{likes / 10000:.1f}W" if likes >= 10000 else str(likes))
            for i in range(3):
                g.d.line((66 + i * 2, y0 + 22, 66 + i * 2, y0 + 28), fill=1)
            tiny(g, 74, y0 + 23, "100%")
            g.text(64, y0 + 4, "直播已结束", align="center")
