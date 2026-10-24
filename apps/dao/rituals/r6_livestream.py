"""直播祈福：道长开了直播间“云上祈福”，供桌前上香、作揖，满屏弹幕刷“福生无量天尊”，
右边点赞爱心往上冒，底部“香火值”随计时涨满。

依据：近年不少宫观开“云祈福”“线上法会”直播；“福生无量天尊”是道教信众与道士相见的礼语（道门称“无量天尊”），
与佛门“阿弥陀佛”相对，所以弹幕刷的是它。
入场：手机开播倒计时 3、2、1，LIVE 亮起，补光灯打开，道长入画，第一条弹幕“福生无量天尊”飘过。
持续：弹幕四条轨道从右往左飘（随计时推进，暂停时会定格），道长每隔几秒作一个揖，香炉三缕烟，
      右边点赞爱心一颗颗往上飘，偶尔有人“送出火箭”；在线人数慢慢涨；底部香火值一轮 10 分钟涨满。
      一轮满：屏幕中间大横幅“香火已满”，爱心炸开，香火值清零，“第几场”加一。
中断：画面变暗定格，弹幕停住，中间“主播暂时离开”。
恢复：“主播回来了”，画面亮回，弹幕继续飘。
圆满：弹幕刷屏“福生无量天尊”，道长深深一揖，画面收成“直播已结束”卡片，香火 100%，点赞数。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import smoke_wisp, typewriter
from ..engine.gfx import Gfx, Sprite, text_width
from ..engine.scene import Ritual, register
from .r6_common import ctext, num, tiny

TOP, BOT = 9, 55             # 视频区上下边界（顶栏、底栏之间）
PX = 72                      # 道长中心 x
LANES = (11, 20, 29, 38)
SAY = ["福生无量天尊", "无量天尊", "道长好", "666", "求平安", "考研上岸", "暴富暴富", "已三连", "好运+1",
       "道法自然", "求脱单", "前排", "福生无量天尊", "上上签", "稳了", "心诚则灵"]
DM_EVERY = 1.35
HEART_EVERY = 0.8
GIFT_EVERY = 53.0
RENEW = 5.0

HEART = Sprite("""
  .##.##.
  #######
  #######
  .#####.
  ..###..
  ...#...
""")
HEART_O = Sprite("""
  .##.##.
  #..#..#
  #.....#
  .#...#.
  ..#.#..
  ...#...
""")
ROCKET = Sprite("""
  ..###.....
  .#...##...
  #.......##
  .#...##...
  ..###.....
""")
MX_HEART = [0b01100110, 0b11111111, 0b11111111, 0b11111111, 0b01111110, 0b00111100, 0b00011000, 0]
MX_HEART_S = [0, 0b00100100, 0b01111110, 0b01111110, 0b00111100, 0b00011000, 0, 0]


def ring_light(g: Gfx, on: float = 1.0):
    """网红补光灯：环形灯 + 三脚架"""
    cx, cy = 17, 24
    g.d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), outline=1)
    g.d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), outline=1)
    if on > 0:
        for i in range(16):
            a = i / 16 * 2 * math.pi
            if i % 2 == 0 or on >= 1:
                g.px(cx + math.cos(a) * 6.5, cy + math.sin(a) * 6.5)
    g.d.line((cx, cy + 8, cx, 50), fill=1)
    g.d.line((cx, 50, cx - 6, 54), fill=1)
    g.d.line((cx, 50, cx + 6, 54), fill=1)


def altar(g: Gfx):
    """供桌 + 小香炉"""
    g.d.rectangle((34, 47, 102, 54), outline=1, fill=0)
    for x in range(38, 100, 4):
        g.px(x, 50)
        g.px(x + 2, 52)
    # 香炉
    g.d.rectangle((40, 42, 52, 46), outline=1, fill=0)
    g.d.line((39, 42, 53, 42), fill=1)


def priest(g: Gfx, bow: float = 0.0, dy: float = 0.0):
    """道长：道冠、长须、宽袍大袖拱手。bow 0..1 作揖（头低下去、手举到额前）"""
    cx = PX
    b = bow * 4
    sy = 28 + dy                      # 肩
    robe = [(cx - 9, sy), (cx + 9, sy), (cx + 17, 47), (cx - 17, 47)]
    g.d.polygon(robe, fill=0, outline=1)
    g.d.line((cx - 4, sy, cx, sy + 7, cx + 4, sy), fill=1)          # 交领
    g.d.line((cx, sy + 7, cx, 47), fill=1)
    # 宽袖：两袖在胸前合拢
    hy = sy + 9 - bow * 9                                           # 手的高度
    for sg in (-1, 1):
        sl = [(cx + sg * 9, sy + 1), (cx + sg * 17, sy + 15), (cx + sg * 12, sy + 18), (cx + sg * 3, hy + 4)]
        g.d.polygon(sl, fill=0, outline=1)
        g.d.line((cx + sg * 13, sy + 9, cx + sg * 15, sy + 15), fill=1)  # 袖褶
    g.d.rectangle((cx - 3, hy, cx + 3, hy + 4), fill=0, outline=1)   # 拱手
    g.px(cx, hy + 2)
    # 头
    hy0 = 15 + dy + b
    g.d.ellipse((cx - 6, hy0, cx + 6, hy0 + 12), fill=0, outline=1)
    if bow < 0.5:
        g.d.line((cx - 4, hy0 + 5, cx - 2, hy0 + 6), fill=1)        # 闭目
        g.d.line((cx + 2, hy0 + 6, cx + 4, hy0 + 5), fill=1)
        g.d.line((cx - 1, hy0 + 12, cx - 2, hy0 + 16), fill=1)      # 长须
        g.d.line((cx, hy0 + 12, cx, hy0 + 17), fill=1)
        g.d.line((cx + 1, hy0 + 12, cx + 2, hy0 + 16), fill=1)
    else:
        for x in range(cx - 4, cx + 5, 2):                           # 低头：头顶发丝
            g.px(x, hy0 + 3)
    # 道冠：发髻 + 簪
    g.d.polygon([(cx - 3, hy0 + 1), (cx + 3, hy0 + 1), (cx + 2, hy0 - 4), (cx - 2, hy0 - 4)], fill=1)
    g.d.line((cx - 6, hy0 - 2, cx + 6, hy0 - 2), fill=1)


@register
class LiveStream(Ritual):
    id = "r6.livestream"
    name = "直播祈福"
    desc = "道长开直播“云上祈福”，上香作揖，满屏弹幕刷福生无量天尊，爱心上飘，香火值随计时涨满"
    T = {"enter": 4.2, "interrupt": 1.5, "resume": 1.8, "complete": 5.2}
    CYCLE = 600.0

    def setup(self):
        self.s = self.rng.randrange(10000)
        self.base = 800 + self.rng.randrange(3000)

    # ------------------------------------------------------------ 弹幕、爱心、礼物（都是 e 的函数）

    def dm(self, i: int):
        st = i * DM_EVERY + rand(i, self.s) * 0.6
        lane = i % 4
        v = 21 + lane * 2.5 + rand(i, self.s + 1) * 3
        txt = SAY[int(rand(i, self.s + 2) * len(SAY))]
        if i % 7 == 0:
            txt = "福生无量天尊"
        return st, lane, v, txt

    def danmaku(self, g: Gfx, e: float, extra: float = 0.0):
        for i in range(max(0, int((e - 9) / DM_EVERY)), int(e / DM_EVERY) + 1):
            st, lane, v, txt = self.dm(i)
            if e < st:
                continue
            x = 128 - (e - st) * (v + extra)
            w = text_width(txt, 8)
            if x < -w - 2:
                continue
            y = LANES[lane]
            g.d.rectangle((x - 1, y - 1, x + w, y + 7), fill=0)
            ctext(g, x, y, txt, size=8)

    def hearts(self, g: Gfx, e: float, burst: float = 0.0):
        for i in range(max(0, int((e - 3) / HEART_EVERY)), int(e / HEART_EVERY) + 1):
            st = i * HEART_EVERY + rand(i, self.s + 5) * 0.4
            k = (e - st) / 2.8
            if k < 0 or k > 1:
                continue
            x = 113 + math.sin(k * 5 + i) * 4 + (rand(i, self.s + 6) - 0.5) * 6
            y = BOT - 7 - k * 40
            if k > 0.75 and rand(int(e * 10) + i, 3) < (k - 0.75) * 3:
                continue
            g.blit(HEART if i % 3 else HEART_O, x - 3, y)

    def gift(self, g: Gfx, e: float):
        k = e % GIFT_EVERY
        if e < GIFT_EVERY or k > 3.2:
            return
        s = ease_out_back(span(k, 0.0, 0.4)) * (1 - span(k, 2.8, 3.2))
        x = lerp(-40, 2, s)
        g.d.rectangle((x, 41, x + 44, 49), fill=1)
        ctext(g, x + 2, 42, "送出火箭", size=8, fill=0)
        rx = 50 + (k - 0.3) * 30
        if k > 0.3:
            g.blit(ROCKET, rx, 40)
            for j in range(4):
                g.px(rx - 2 - j * 3, 42 + (j % 2))

    def viewers(self, e: float) -> str:
        v = self.base + int(e * 9 + noise(e * 0.3, self.s) * 200)
        return f"{v / 10000:.1f}W" if v >= 10000 else str(v)

    def likes(self, e: float) -> int:
        return int(e / HEART_EVERY) * 3

    # ------------------------------------------------------------ 界面

    def topbar(self, g: Gfx, e: float, live: bool = True):
        g.d.ellipse((0, 0, 8, 8), outline=1)                 # 头像
        g.d.pieslice((2, 2, 6, 6), 90, 270, fill=1)
        ctext(g, 11, 1, "云上祈福", size=8)
        if live:
            g.d.rectangle((83, 0, 101, 8), fill=1)
            tiny(g, 85, 2, "LIVE", fill=0)
        else:
            g.d.rectangle((83, 0, 101, 8), outline=1)
            tiny(g, 85, 2, "LIVE")
        tiny(g, 127, 2, self.viewers(e), align="right")
        g.d.line((0, TOP, 127, TOP), fill=1)

    def botbar(self, g: Gfx, p: float, n: int):
        g.d.rectangle((0, BOT, 127, 63), fill=0)
        g.d.line((0, BOT, 127, BOT), fill=1)
        ctext(g, 1, 57, "香火", size=8)
        g.d.rectangle((19, 57, 89, 62), outline=1)
        w = int(68 * clamp(p))
        if w > 0:
            g.d.rectangle((20, 58, 20 + w, 61), fill=1)
        ctext(g, 127, 57, f"第{num(n)}场", size=8, align="right")

    def smoke(self, g: Gfx, t: float, amt: float = 1.0):
        for i, x in enumerate((43, 46, 49)):
            g.d.line((x, 41, x, 36), fill=1)
            if amt > 0:
                smoke_wisp(g, x, 34, 20 * amt, t, self.s + i, sway=2.5, speed=5, drift=(i - 1) * 3)

    def bow(self, e: float) -> float:
        k = (e + rand(0, self.s) * 5) % 9.0
        return math.sin(math.pi * span(k, 0.0, 2.2)) if k < 2.2 else 0.0

    def mx(self, g: Gfx, e: float, t: float):
        k = (e % HEART_EVERY) / HEART_EVERY
        g.mx_rows(MX_HEART if k < 0.35 else MX_HEART_S)

    # ------------------------------------------------------------ 阶段

    def stage(self, g: Gfx, t: float, e: float, bow: float | None = None, smoke: float = 1.0, light: float = 1.0):
        ring_light(g, light)
        priest(g, self.bow(e) if bow is None else bow)
        altar(g)
        self.smoke(g, t, smoke)

    def frame(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n = int(e // self.CYCLE) + 1
        self.stage(g, t, e)
        self.danmaku(g, e)
        self.hearts(g, e)
        self.gift(g, e)
        self.topbar(g, e)
        self.botbar(g, k / self.CYCLE, n)
        self.mx(g, e, t)

    def enter(self, g: Gfx, t: float):
        if t < 1.8:  # 倒计时 3 2 1
            k = int(t / 0.6)
            s = 3 - k
            f = (t % 0.6) / 0.6
            r = 14 + 4 * (1 - ease_out(f))
            g.d.ellipse((64 - r, 32 - r, 64 + r, 32 + r), outline=1)
            ctext(g, 64, 26, str(s), align="center")
            g.d.arc((64 - r - 3, 32 - r - 3, 64 + r + 3, 32 + r + 3), -90, -90 + 360 * f, fill=1)
            g.mx_rows([0, 0x3C, 0x42, 0x02, 0x1C, 0x02, 0x42, 0x3C] if s == 3 else
                      [0, 0x3C, 0x42, 0x04, 0x18, 0x20, 0x7E, 0] if s == 2 else
                      [0, 0x18, 0x38, 0x18, 0x18, 0x18, 0x3C, 0])
            return
        u = t - 1.8
        ring_light(g, on=1.0 if u > 0.3 else (1.0 if blink(u, 0.1, 0.5) else 0.0))
        pdy = (1 - ease_out_back(span(u, 0.2, 1.0))) * 40
        priest(g, 0.0, dy=pdy)
        altar(g)
        self.smoke(g, t, ease_out(span(u, 0.8, 2.2)))
        self.topbar(g, 0, live=u > 0.1)
        if u < 0.4:  # LIVE 弹出
            s = ease_out_back(span(u, 0.0, 0.4))
            g.d.rectangle((92 - 10 * s, 4 - 4 * s, 92 + 10 * s, 4 + 4 * s), outline=1)
        self.botbar(g, 0, 1)
        if u > 1.0:  # 第一条弹幕
            x = 128 - (u - 1.0) * 30
            w = text_width("福生无量天尊", 8)
            g.d.rectangle((x - 1, LANES[0] - 1, x + w, LANES[0] + 7), fill=0)
            ctext(g, x, LANES[0], "福生无量天尊", size=8)
        self.mx(g, u, u)
        g.mx_level = 4 if u < 0.3 else 1

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e, t)
            return
        self.frame(g, t, e)

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        n = int(e // self.CYCLE) + 1
        self.stage(g, t, e)
        self.danmaku(g, e)
        self.hearts(g, e)
        # 爱心炸开
        if k < 2.0:
            for j in range(14):
                a = j / 14 * 2 * math.pi + 0.2
                r = 8 + ease_out(k / 2.0) * 50
                x, y = 64 + math.cos(a) * r, 32 + math.sin(a) * r * 0.6
                if rand(j + int(k * 8), 4) > k / 2.0:
                    g.blit(HEART if j % 2 else HEART_O, x - 3, y - 3)
        self.topbar(g, e)
        self.botbar(g, 1.0 if k < 3.0 else span(k, 3.0, 5.0) * 0.0, n - 1 if k < 3.0 else n)
        if k < 3.4:
            s = ease_out_back(span(k, 0.2, 0.6)) * (1 - ease_in(span(k, 3.0, 3.4)))
            h = 8 * s
            if h > 1:
                g.d.rectangle((14, 30 - h, 114, 30 + h), fill=1)
                if s > 0.9:
                    ctext(g, 64, 25, "香火已满", fill=0, align="center")
        self.mx(g, e, t)
        if k < 2.0:
            g.mx_level = 5 if blink(k, 0.2, 0.5) else 2

    def interrupt(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n = int(e // self.CYCLE) + 1
        self.stage(g, 0.0, e, smoke=1 - span(t, 0.0, 0.8))
        self.danmaku(g, e)
        self.hearts(g, e)
        self.topbar(g, e, live=t < 0.6)
        self.botbar(g, k / self.CYCLE, n)
        dim = 1 - 0.7 * ease_out(span(t, 0.2, 0.9))
        g.fade(dim, (0, TOP + 1, 128, BOT))
        if t > 0.5:
            s = ease_out_back(span(t, 0.5, 0.9))
            w = 42 * s
            g.d.rectangle((64 - w, 26, 64 + w, 39), fill=0, outline=1)
            if s > 0.9:
                ctext(g, 64, 27, "主播暂时离开", align="center")
        self.mx(g, e, 0.0)
        if t > 0.5:
            g.mx_rows([0, 0b01100110, 0b01100110, 0b01100110, 0b01100110, 0b01100110, 0b01100110, 0])

    def resume(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n = int(e // self.CYCLE) + 1
        self.stage(g, t, e, smoke=ease_out(span(t, 0.8, 1.8)))
        self.danmaku(g, e)
        self.hearts(g, e)
        self.topbar(g, e, live=t > 0.4)
        self.botbar(g, k / self.CYCLE, n)
        dim = 0.3 + 0.7 * ease_in(span(t, 0.6, 1.4))
        g.fade(dim, (0, TOP + 1, 128, BOT))
        if t < 1.3:
            s = ease_out_back(span(t, 0.0, 0.3)) * (1 - ease_in(span(t, 1.0, 1.3)))
            w = 36 * s
            if w > 2:
                g.d.rectangle((64 - w, 26, 64 + w, 39), fill=0, outline=1)
                if s > 0.9:
                    ctext(g, 64, 27, "主播回来了", align="center")
        self.mx(g, e, t)

    def complete(self, g: Gfx, t: float, e: float):
        k0 = e % self.CYCLE
        n = int(e // self.CYCLE) + 1
        p = lerp(k0 / self.CYCLE, 1.0, ease_in_out(span(t, 0.0, 1.2)))
        card = ease_out_back(span(t, 2.8, 3.4))
        if t < 3.0:
            self.stage(g, t, e, bow=math.sin(math.pi * span(t, 0.6, 2.6)))
            # 刷屏：四条轨道全是“福生无量天尊”
            w = text_width("福生无量天尊", 8)
            for j in range(10):
                lane = j % 4
                x = 128 - (t * (60 + lane * 8)) + j * 34 - lane * 9
                if -w < x < 128:
                    y = LANES[lane]
                    g.d.rectangle((x - 1, y - 1, x + w, y + 7), fill=0)
                    ctext(g, x, y, "福生无量天尊", size=8)
            self.hearts(g, e + t * 3)
            self.topbar(g, e)
            self.botbar(g, p, n)
        if t >= 2.8:  # 直播已结束卡片
            h = 26 * card
            g.d.rectangle((10, 32 - h, 117, 32 + h), fill=0, outline=1)
            if card > 0.9:
                g.d.rectangle((12, 32 - h + 2, 115, 32 + h - 2), outline=1)
                ctext(g, 64, 10, "直播已结束", align="center")
                g.d.line((24, 24, 104, 24), fill=1)
                ctext(g, 20, 28, "香火", size=8)
                tiny(g, 40, 29, "100%")
                ctext(g, 66, 28, "点赞", size=8)
                tiny(g, 84, 29, str(self.likes(e)))
                typewriter(g, 64, 40, "福生无量天尊", t - 3.3, cps=6, size=8, align="center")
        self.mx(g, e + t * 3, t)
        if t > 2.8:
            g.mx_rows(MX_HEART)
            g.mx_level = 1 + int(4 * (1 - span(t, 2.8, 4.2)))
