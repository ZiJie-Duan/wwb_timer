"""飞符：夜里的小坛前，小道士从一叠黄符里抽一道，扬手掷出，符翻飞着入阵，绕符胆盘旋。

依据：飞符召将——以符上达、召请神将；符命“符到奉行”（汉典引宋赵彦卫，“急急如律令”犹言“符到奉行”）。

舞台（侧视）：左边小坛（供案、烛台、一叠黄符），中间小道士，右上方符阵：中心一颗符胆（圆里一道螺旋、四道光芒），
九个符位排在一个椭圆轨道上转，前面的符大、后面的小（被符胆挡住），每张符绕自身竖轴翻转。
入场：坛上烛火点亮，一点灵光从坛上升起，展开成符胆，轨道虚线闪现；小道士走来站定，拱手。
持续：一轮 540 秒飞九道符，每 58 秒一道：转身抽符 → 回身举符过头（蓄力）→ 扬手掷出（速度线）→
      符翻飞着划弧入阵（火星尾迹），入阵时符胆一闪、震一下。其间小道士剑指一点（全阵符一齐翻面）、
      作揖、抬头看流星。九符齐了：符胆一明一暗，环上光点流转。
      续：九道符依次拉成竖直的流光直上九霄，天上回应一道光柱落在符胆上，“召将”；坛上又弹出一叠新符。
中断：小道士往下一按，符阵散落、符胆缩成小圈，“落符”。恢复：一指，符胆复明，符从地上升回阵里。
圆满：坛上剩下的符一齐飞起入阵，九符收拢合入符胆，闪白，一道光柱冲天、两侧光点上流，“符到奉行”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.fx import stars
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import act, boxed, candle, fist, floor, fu_spr, ring, star4, table_spr

FLOOR = 58
DAO_X = 44
TABLE_X, TABLE_Y = 4, 44
STACK = (17, TABLE_Y)            # 符叠左下角
CX, CY = 90, 25                  # 符胆
RX, RY = 25, 8
NF = 9
LEAD = 4.0
SLOT = 58.0
RENEW = 6.0
FLY = 1.6                        # 掷出到入阵


def _slot_time(i):
    return LEAD + i * SLOT


def _core():
    """符胆 11×11：外圈、里面一道螺旋（像一个“炁”团）"""
    p = Part(11, 11)
    p.shape("ellipse", (0, 0, 10, 10), fill=1)
    p.d.ellipse((1, 1, 9, 9), fill=0)
    pts = []
    for k in range(22):
        q = k / 21
        a = -math.pi / 2 + q * 2 * math.pi * 1.6
        r = 3.6 * (1 - q * 0.8)
        pts.append((5 + math.cos(a) * r, 5 + math.sin(a) * r))
    p.d.line(pts, fill=1)
    p.px(5, 5)
    return p.sprite()


def _stack(n: int):
    """坛上的一叠符 11×(n+2)：每张一道亮边，最上面一张露出符头三勾"""
    key = ("stack", n)
    if key not in _P:
        h = max(n, 1) + 2
        p = Part(11, h)
        p.shape("rectangle", (0, h - 2, 10, h - 1), fill=1)          # 托盘
        p.d.line((1, h - 1, 9, h - 1), fill=0)
        for j in range(n):
            y = h - 3 - j
            p.shape("line", (1 + (j % 2), y, 9 + (j % 2) - 1, y), fill=1)
        _P[key] = p.sprite()
    return _P[key]


_P: dict = {}


def core_spr():
    if "core" not in _P:
        _P["core"] = _core()
    return _P["core"]


def fu_side(big: bool, sx: float):
    """阵里的一张符：big = 前排大张；sx = 翻转的宽度比例"""
    spr = fu_spr(7, 13, 0) if big else fu_spr(5, 9, 1)
    return pix.stretch(spr, max(0.2, round(sx, 1)), 1.0)


@register
class FeiFu(Ritual):
    id = "r2.feifu"
    name = "飞符"
    desc = "小道士从坛上抽符、扬手掷出，符翻飞着入阵绕符胆盘旋；九符齐了化作流光直上九霄，天上回应一道光"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 540.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 3)
        self.last_t = None
        self.star_seed = self.rng.randrange(100)

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    # ------------------------------------------------------------ 布景

    def sky(self, g: Gfx, t: float):
        stars(g, t, self.star_seed, n=26, box=(0, 0, 128, 40))
        g.d.ellipse((6, 4, 14, 12), fill=1)       # 月牙
        g.d.ellipse((9, 3, 17, 11), fill=0)
        floor(g, FLOOR)
        # 远处的山门剪影：两根柱子 + 横梁
        for x in (117, 126):           # 右边山门的一角
            g.d.line((x, 40, x, FLOOR - 1), fill=1)
            g.px(x - 1, FLOOR - 1), g.px(x + 1, FLOOR - 1)
        g.d.line((113, 40, 127, 40), fill=1)
        g.d.line((114, 42, 127, 42), fill=1)
        g.px(113, 39), g.px(112, 38)

    def altar(self, g: Gfx, t: float, n_stack: int, lit: bool = True, pop: float = 1.0):
        pix.blit(g, table_spr(28, 14), TABLE_X, TABLE_Y)
        candle(g, TABLE_X + 4, TABLE_Y, t, lit)
        if n_stack > 0:
            spr = _stack(n_stack)
            if pop < 1:
                spr = pix.stretch(spr, 1.0, max(0.2, ease_out_back(pop)))
            pix.blit(g, spr, STACK[0], STACK[1] - spr.h)

    def slot_pos(self, i: int, t: float, rmul: float = 1.0):
        a = t * 0.55 + i * 2 * math.pi / NF
        return CX + math.cos(a) * RX * rmul, CY + math.sin(a) * RY * rmul + math.sin(t * 2.2 + i) * 1.0, math.sin(a)

    def formation(self, g: Gfx, t: float, joined, core: float = 1.0, flipall: float = 0.0, rmul: float = 1.0,
                  extra=None, pulse: float = 0.0):
        """符阵：轨道虚线、后排符、符胆、前排符。joined = 已入阵的符位集合"""
        ph = int(t * 6)
        n = 40
        for k in range(n):  # 转动的点线轨道
            if (k + ph) % 3 == 0:
                a = k / n * 2 * math.pi
                g.px(CX + math.cos(a) * RX * rmul, CY + math.sin(a) * RY * rmul)
        items = []
        for i in joined:
            x, y, depth = self.slot_pos(i, t, rmul)
            sx = abs(math.cos(t * 1.7 + i * 0.9 + flipall * math.pi))
            items.append((depth, x, y, i, sx))
        if extra:
            items += extra
        items.sort()
        for depth, x, y, i, sx in items:
            if depth < 0:
                s = fu_side(False, sx)
                pix.blit(g, s, x - s.w / 2, y - s.h / 2)
        if core > 0:
            spr = core_spr() if core >= 1 else pix.stretch(core_spr(), max(0.2, core), max(0.2, core))
            pix.blit(g, spr, CX - spr.w / 2, CY - spr.h / 2)
            if core >= 1:
                ln = 3 + int(pulse * 3) + (int(t * 4) % 2)
                for a in range(4):
                    aa = a * math.pi / 2 + t * 0.8
                    ca, sa = math.cos(aa), math.sin(aa)
                    g.d.line((CX + ca * 7, CY + sa * 7, CX + ca * (7 + ln), CY + sa * (7 + ln)), fill=1)
        for depth, x, y, i, sx in items:
            if depth >= 0:
                s = fu_side(True, sx)
                pix.blit(g, s, x - s.w / 2, y - s.h / 2)

    def thrown(self, u: float):
        """一轮内第 u 秒：已入阵的符位、正在飞的那张（进度）、小道士的动作"""
        if u < LEAD:
            return set(), None, None, 0.0
        i = min(int((u - LEAD) // SLOT), NF - 1)
        k = u - _slot_time(i)
        joined = set(range(i)) | ({i} if k >= 1.4 + FLY else set())
        fly = span(k, 1.4, 1.4 + FLY) if 1.4 <= k < 1.4 + FLY else None
        return joined, (i, fly) if fly is not None else None, (i, k), k

    def dao_throw(self, g: Gfx, t: float, i: int, k: float, n_stack: int):
        """抽符 → 举过头 → 掷出 → 余韵 → 静候里的小动作。返回出手点"""
        x = DAO_X
        if k < 0.25:
            daoshi(g, x, FLOOR, "idle", t)
        elif k < 0.75:  # 转身抽符
            h = act(g, x, FLOOR, t, hand_to=(STACK[0] + 7, STACK[1] - 4 - n_stack), flip=True)["hand"]
            if k > 0.5:
                pix.blit(g, fu_spr(5, 9, 1), h[0] - 2, h[1] - 8)
                fist(g, *h)
        elif k < 1.2:  # 回身、举符过头（蓄力：身子一沉）
            h = daoshi(g, x, FLOOR + (1 if k > 0.95 else 0), "raise", t)["hand"]
            pix.blit(g, fu_spr(5, 9, 1), h[0] - 2 - (1 if k > 0.95 else 0), h[1] - 9)
            fist(g, h[0], h[1] + 1)
        elif k < 1.4:  # 掷出：手臂甩到前上方，速度线
            q = span(k, 1.2, 1.32)
            ang = lerp(-1.5, -0.35, ease_out(q))
            h = act(g, x + 1, FLOOR, t, ang=ang, L=12, face="wow")["hand"]
            for j in range(3):
                yy = h[1] - 4 + j * 3
                g.d.line((h[0] - 10 + j * 2, yy + 6, h[0] - 3 + j * 2, yy), fill=1)
        elif k < 2.2:  # 余韵：手伸着，看符飞
            act(g, x + 1, FLOOR, t, ang=-0.4, L=12)
        elif 8.0 < k < 9.4:  # 剑指一点
            daoshi(g, x, FLOOR, "point", t)
        elif 25.0 < k < 27.0:
            daoshi(g, x, FLOOR, "bow" if k > 25.6 else "gongshou", t)
        elif 40.0 < k < 42.0:
            daoshi(g, x, FLOOR, "idle", t, face="wow")
        else:
            daoshi(g, x, FLOOR, "idle", t)

    def flying(self, g: Gfx, t: float, i: int, q: float, dt: float, src=(DAO_X + 10, 30)):
        """正在飞的符：从出手点划一道弧、绕着转进它的符位，快速翻面，带火星尾迹"""
        tx, ty, depth = self.slot_pos(i, t)
        a = ease_in_out(q)
        x = lerp(src[0], tx, a) + math.sin(a * math.pi * 2) * 6 * (1 - a)
        y = lerp(src[1], ty, a) - math.sin(a * math.pi) * 18
        sx = abs(math.cos(q * 14))
        for m in range(1, 6):  # 尾迹
            qq = max(q - m * 0.04, 0)
            aa = ease_in_out(qq)
            px = lerp(src[0], tx, aa) + math.sin(aa * math.pi * 2) * 6 * (1 - aa)
            py = lerp(src[1], ty, aa) - math.sin(aa * math.pi) * 18
            if m % 2 == 1 or m < 3:
                g.px(px, py)
        s = fu_side(True, sx)
        pix.blit(g, s, x - s.w / 2, y - s.h / 2)
        if int(t * 30) % 3 == 0:
            self.sparks.burst(x, y + 4, 1, 6, life=0.45, gravity=20)
        return x, y

    def mx(self, g: Gfx, t: float, joined, core: bool = True, level: int = 1):
        if core:
            g.mx[3:5, 3:5] = True
        for i in joined:
            a = t * 0.55 + i * 2 * math.pi / NF
            g.mx_set(int(round(3.5 + math.cos(a) * 3.4)), int(round(3.5 + math.sin(a) * 3.4)))
        g.mx_level = level

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        self.sky(g, t)
        self.altar(g, t, NF, lit=t > 0.5)
        if 0.5 <= t < 0.5 + dt:
            self.sparks.burst(TABLE_X + 4, TABLE_Y - 16, 6, 14, up=6, life=0.4)
        q = span(t, 1.0, 2.4)  # 灵光从坛上升起 → 展开成符胆
        if 0 < q < 1:
            x, y = lerp(STACK[0] + 5, CX, ease_in_out(q)), lerp(STACK[1] - 12, CY, ease_in_out(q)) - math.sin(q * math.pi) * 14
            star4(g, x, y, big=int(t * 10) % 2 == 0)
            self.sparks.burst(x, y, 1, 6, life=0.4, gravity=10)
        core = ease_out_back(span(t, 2.4, 2.9))
        if t >= 2.4:
            self.formation(g, t, set(), core=core, rmul=ease_out(span(t, 2.6, 3.4)))
            if t < 2.4 + dt * 1.5:
                self.sparks.burst(CX, CY, 14, 30, life=0.6, gravity=0)
                pix.shake(g, t, 1)
        if t < 2.6:
            daoshi(g, lerp(-12, DAO_X, ease_out(span(t, 0, 2.6))), FLOOR, "walk", t)
        else:
            daoshi(g, DAO_X, FLOOR, "gongshou" if 3.0 < t < 4.4 else "idle", t, face="wow" if t < 3.0 else "normal")
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 3.0:
            boxed(g, 24, 4, "请符")
        self.mx(g, t, set(), core=t > 2.4)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            return self.renew(g, t, e, u, dt)
        joined, fly, act_ik, k = self.thrown(u)
        n_stack = NF - len(joined) - (1 if fly else 0) - (1 if act_ik and 0.6 < act_ik[1] < 1.4 else 0)
        self.sky(g, t)
        self.altar(g, t, n_stack)
        all9 = len(joined) == NF
        flipall = span(k, 8.6, 9.2) if act_ik and 8.0 < k < 10 else 0.0
        pulse = (0.5 + 0.5 * math.sin(t * 3)) if all9 else 0.0
        self.formation(g, t, joined, flipall=flipall, pulse=pulse)
        if all9:  # 环上光点流转
            for j in range(6):
                a = t * 1.8 + j * math.pi / 3
                g.px(CX + math.cos(a) * (RX + 3), CY + math.sin(a) * (RY + 2))
        if fly:
            i, q = fly
            self.flying(g, t, i, q, dt)
            if q > 0.97:
                self.sparks.burst(CX, CY, 10, 24, life=0.5, gravity=0)
                pix.shake(g, t, 0.8)
                ring(g, CX, CY, 8, step=2)
        if act_ik:
            self.dao_throw(g, t, act_ik[0], act_ik[1], n_stack)
            if 8.6 < k < 8.8:
                ring(g, CX, CY, 9 + (k - 8.6) * 30, step=2, sy=0.5)
            if 40.0 < k < 41.4:  # 流星
                q = span(k, 40.0, 41.0)
                x, y = lerp(30, 70, q), lerp(2, 14, q)
                g.d.line((x - 6, y - 2, x, y), fill=1) if q < 1 else None
        else:  # 开头：拱手凝神
            daoshi(g, DAO_X, FLOOR, "gongshou" if u > 1.0 else "idle", t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        n = len(joined)
        boxed(g, 24, 4, (cn_num(n) + "符") if n else "请符")
        self.mx(g, t, joined, level=4 if fly and fly[1] > 0.95 else 1)

    def renew(self, g: Gfx, t: float, e: float, u: float, dt: float):
        """续：九符依次化作流光直上九霄 → 天上回应一道光 → 坛上弹出一叠新符"""
        self.sky(g, t)
        pop = span(u, 3.0, 3.6)
        self.altar(g, t, NF if u >= 3.0 else 0, pop=pop)
        left = [i for i in range(NF) if u < 0.3 + i * 0.22]
        self.formation(g, t, left, pulse=1.0)
        for i in range(NF):  # 流光
            q = span(u, 0.3 + i * 0.22, 0.3 + i * 0.22 + 0.5)
            if 0 < q < 1:
                x, y, _ = self.slot_pos(i, 0.3 + i * 0.22 + t * 0)
                top = y - ease_in(q) * 70
                g.d.line((x, top, x, top + 10 * (1 - q) + 3), fill=1)
                star4(g, x, top)
        beam = span(u, 2.4, 3.2)
        if 0 < beam < 1:
            w = 3 * (1 - abs(beam * 2 - 1)) + 1
            g.d.rectangle((CX - w, 0, CX + w, CY - 6), fill=1)
            if u < 2.4 + dt * 1.5:
                pix.flash(g)
                self.sparks.burst(CX, CY, 20, 34, life=0.7, gravity=10)
            if beam < 0.3:
                pix.shake(g, t, 1.2)
        if u < 3.0:
            daoshi(g, DAO_X, FLOOR, "raise", t, face="wow" if u > 2.2 else "normal")
        else:
            daoshi(g, DAO_X, FLOOR, "bow" if 3.8 < u < 5.0 else "gongshou", t, face="happy")
        self.sparks.step(dt)
        self.sparks.draw(g)
        boxed(g, 24, 4, "召将" if u > 2.4 else "九符")
        self.mx(g, t, left, level=6 if 2.4 < u < 3.0 else 1)
        if 0 < beam < 1:
            g.mx[0:4, 3:5] = True

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        joined, fly, act_ik, k = self.thrown(u)
        n_stack = NF - len(joined) - (1 if fly else 0)
        self.sky(g, t)
        self.altar(g, t, n_stack, lit=t < 1.0)
        fall = ease_in(span(t, 0.3, 1.3))
        core = 1 - span(t, 0.3, 1.0) * 0.6
        self.formation(g, t, [] if fall > 0 else joined, core=core)
        if fall > 0:
            for i in joined:  # 散落：一张张翻着落地
                x, y, _ = self.slot_pos(i, t)
                yy = lerp(y, FLOOR - 4, fall)
                s = fu_side(True, abs(math.cos(t * 9 + i)))
                if yy < FLOOR - 4:
                    pix.blit(g, s, x - s.w / 2, yy - s.h / 2)
                else:
                    g.d.line((x - 3, FLOOR - 1, x + 3, FLOOR - 1), fill=1)
        if 1.0 <= t < 1.0 + dt:
            self.puffs.emit(TABLE_X + 4, TABLE_Y - 16, vy=-6, life=1.0, rmax=1.6, spread=0)
        h = act(g, DAO_X, FLOOR, t, ang=lerp(-1.2, 0.5, ease_out(span(t, 0.0, 0.4))), L=11)["hand"]
        self.puffs.step(dt)
        self.puffs.draw(g)
        boxed(g, 24, 4, "落符")
        self.mx(g, t, [] if fall > 0.5 else joined, core=True)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        joined, fly, act_ik, k = self.thrown(u)
        n_stack = NF - len(joined) - (1 if fly else 0) - (1 if act_ik and 0.6 < act_ik[1] < 1.4 else 0)
        self.sky(g, t)
        self.altar(g, t, n_stack, lit=t > 0.3)
        rise = ease_out(span(t, 0.5, 1.5))
        core = 0.4 + 0.6 * ease_out_back(span(t, 0.2, 0.6))
        self.formation(g, t, joined if rise >= 1 else [], core=core)
        if rise < 1:
            for i in joined:
                x, y, _ = self.slot_pos(i, t)
                yy = lerp(FLOOR - 4, y, rise)
                if rise > 0:
                    s = fu_side(True, abs(math.cos(t * 9 + i)))
                    pix.blit(g, s, x - s.w / 2, yy - s.h / 2)
                else:
                    g.d.line((x - 3, FLOOR - 1, x + 3, FLOOR - 1), fill=1)
        if 0.2 <= t < 0.2 + dt:
            self.sparks.burst(CX, CY, 12, 26, life=0.5, gravity=0)
            pix.flash(g)
        daoshi(g, DAO_X, FLOOR, "point" if t < 1.5 else "idle", t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        n = len(joined)
        boxed(g, 24, 4, (cn_num(n) + "符") if n else "请符")
        self.mx(g, t, joined if rise > 0.5 else [], core=True)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        joined, fly, act_ik, k = self.thrown(u)
        rest = [i for i in range(NF) if i not in joined]
        self.sky(g, t)
        self.altar(g, t, len(rest) if t < 0.3 else 0)
        conv = ease_in(span(t, 1.4, 2.4))
        rmul = 1 - conv
        q = ease_out(span(t, 0.3, 1.4))
        extra = []
        for j, i in enumerate(rest):  # 剩下的符一齐飞起入阵
            if q < 1:
                tx, ty, depth = self.slot_pos(i, t)
                x = lerp(STACK[0] + 5, tx, q)
                y = lerp(STACK[1] - 6, ty, q) - math.sin(q * math.pi) * 20
                extra.append((1.0, x, y, i, abs(math.cos(t * 12 + j))))
        shown = joined if q < 1 else set(range(NF))
        if t < 2.4:
            self.formation(g, t * (1 + conv * 3), shown, rmul=rmul, extra=extra, pulse=1.0)
        if 2.4 <= t < 2.4 + dt:
            pix.flash(g)
            self.sparks.burst(CX, CY, 30, 44, life=1.0, gravity=20)
        if t >= 2.4:  # 光柱冲天、两侧光点上流
            w = 2 + (1 if int(t * 10) % 2 else 0)
            g.d.rectangle((CX - w, 0, CX + w, CY + 4), fill=1)
            pix.blit(g, core_spr(), CX - 5, CY - 5)
            for j in range(8):
                yy = (CY - ((t * 40 + j * 9) % 40))
                g.px(CX - 7 - (j % 2) * 2, yy)
                g.px(CX + 7 + (j % 2) * 2, yy - 4)
            for r in range(2):
                rr = (t - 2.4) * 26 - r * 10
                if 0 < rr < 34:
                    ring(g, CX, CY, rr, step=2, sy=0.6)
        if 2.4 < t < 2.8:
            pix.shake(g, t, 1.5)
        if t < 2.4:
            daoshi(g, DAO_X, FLOOR, "raise", t)
        else:
            daoshi(g, DAO_X, FLOOR, "kneel" if t > 2.8 else "raise", t, face="happy")
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 2.8:
            boxed(g, 24, 4, "符到奉行", size=12, pop=ease_out_back(span(t, 2.8, 3.2)))
        else:
            boxed(g, 24, 4, "九符")
        self.mx(g, t, shown if t < 2.4 else [], core=True)
        if t > 2.4:
            g.mx[:, 3:5] = True
            g.mx_level = 1 + int(6 * (1 - span(t, 2.4, 4.0)))
