"""画布：OLED 128×64 单色 + 点阵 8×8。场景每帧在清空的画布上重画（立即模式）。

三层，最后合成为黑白（g.finish()，引擎在每个阶段方法之后调用）：
    g.lum   灰度层 numpy float32 [64,128]，0 黑 … 1 白：光影、渐变、材质、烟雾都画在这里，
            合成时用蓝噪声抖动成点（engine/art.py 有大量工具）
    g.k     黑墨层 ImageDraw：画上的地方强制为黑（灰度之上的暗线、描边、剪影）
    g.d     白墨层 ImageDraw：画上的地方强制为亮（最上层：细线、文字、高光点）

    g.d                 PIL ImageDraw（fontmode="1"），直线、圆、多边形等直接用它
    g.text(x, y, s)     中文像素字（12px 或 8px），y 为字形顶端；返回宽度
    g.vtext(x, y, s)    竖排
    g.blit(sprite, x, y)  像素画（见 Sprite）
    g.fade(level, box)  有序抖动淡出：只保留 level（0..1）比例的亮点
    g.shade(box, level) 用抖动图案填充灰度
    g.invert(box)
    g.mx                点阵 8×8 numpy bool，mx[y, x]，y=0 在上
    g.mx_level          点阵亮度 0-15（默认 1）
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 128, 64
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
# 字号 → (文件, 顶端偏移, 汉字高度)：fusion-pixel 的汉字在字框里从第 3 行开始
_FONT_FILES = {12: ("fusion-pixel-12px-zh_hans-gbk.ttf", 3, 11), 8: ("fusion-pixel-8px-zh_hans-gbk.ttf", 3, 7)}
_fonts: dict[int, ImageFont.FreeTypeFont] = {}

_BN = np.load(Path(__file__).resolve().parent.parent / "assets" / "bluenoise64.npy")
BLUE = (np.tile(_BN, (1, 2)).astype(np.float32) + 0.5) / 256.0  # 蓝噪声阈值 [64,128]，0..1

# 4×4 Bayer 有序抖动阈值（0..15）
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.uint8)
BAYER = np.tile(BAYER4, (H // 4, W // 4))
BAYER8 = np.tile(BAYER4, (2, 2))
BAYER_F = (BAYER.astype(np.float32) + 0.5) / 16  # Bayer 阈值 0..1


def font(size: int = 12) -> ImageFont.FreeTypeFont:
    if size not in _fonts:
        name = _FONT_FILES[size][0]
        _fonts[size] = ImageFont.truetype(str(FONT_DIR / name), size)
    return _fonts[size]


def text_width(s: str, size: int = 12) -> int:
    return int(font(size).getlength(s))


_TEXT_CACHE: dict = {}


_HALO_CACHE: dict = {}


def _halo_img(s: str, size: int, scale: int) -> Image.Image:
    """字形向外扩 1 像素的遮罩（比字形大 2 像素，左上角对齐到字形 -1, -1）"""
    key = (s, size, scale)
    im = _HALO_CACHE.get(key)
    if im is None:
        a = np.pad(np.array(_text_img(s, size, scale), dtype=bool), 1)
        g = a.copy()
        g[1:, :] |= a[:-1, :]
        g[:-1, :] |= a[1:, :]
        g[:, 1:] |= a[:, :-1]
        g[:, :-1] |= a[:, 1:]
        g[1:, 1:] |= a[:-1, :-1]
        g[:-1, :-1] |= a[1:, 1:]
        g[1:, :-1] |= a[:-1, 1:]
        g[:-1, 1:] |= a[1:, :-1]
        if len(_HALO_CACHE) > 4000:
            _HALO_CACHE.clear()
        im = _HALO_CACHE[key] = Image.fromarray(g)
    return im


def _text_img(s: str, size: int, scale: int) -> Image.Image:
    """字串的遮罩图（缓存；字顶对齐到第 0 行）"""
    key = (s, size, scale)
    img = _TEXT_CACHE.get(key)
    if img is None:
        off = _FONT_FILES[size][1]
        w = max(1, int(font(size).getlength(s)))
        hh = size + 4
        img = Image.new("1", (w, hh))
        d = ImageDraw.Draw(img)
        d.fontmode = "1"
        d.text((0, -off), s, font=font(size), fill=1)
        if scale > 1:
            img = img.resize((w * scale, hh * scale), Image.NEAREST)
        if len(_TEXT_CACHE) > 4000:
            _TEXT_CACHE.clear()
        _TEXT_CACHE[key] = img
    return img


class Sprite:
    """像素画。'#' = 亮，'.' = 暗（不透明，会盖住底下），空格 = 透明。

        HAND = Sprite('''
          .##.
          #..#
        ''')
    """

    def __init__(self, art: str | None = None, on: np.ndarray | None = None, mask: np.ndarray | None = None):
        if art is not None:
            lines = [ln for ln in art.strip("\n").split("\n")]
            # 去掉公共缩进
            indent = min((len(ln) - len(ln.lstrip(" ")) for ln in lines if ln.strip()), default=0)
            lines = [ln[indent:] for ln in lines]
            w = max(len(ln) for ln in lines)
            on = np.zeros((len(lines), w), dtype=bool)
            mask = np.zeros((len(lines), w), dtype=bool)
            for y, ln in enumerate(lines):
                for x, ch in enumerate(ln):
                    if ch == "#":
                        on[y, x] = mask[y, x] = True
                    elif ch == ".":
                        mask[y, x] = True
        self.on = on
        self.mask = mask
        self.h, self.w = on.shape
        self._on_img = Image.fromarray(on)
        self._off_img = Image.fromarray(mask & ~on)

    def flip(self) -> "Sprite":
        """左右翻转"""
        return Sprite(on=self.on[:, ::-1].copy(), mask=self.mask[:, ::-1].copy())

    def flipv(self) -> "Sprite":
        return Sprite(on=self.on[::-1].copy(), mask=self.mask[::-1].copy())

    def rot90(self, k: int = 1) -> "Sprite":
        """逆时针旋转 k×90°"""
        return Sprite(on=np.rot90(self.on, k).copy(), mask=np.rot90(self.mask, k).copy())

    def scale(self, n: int) -> "Sprite":
        return Sprite(on=self.on.repeat(n, 0).repeat(n, 1), mask=self.mask.repeat(n, 0).repeat(n, 1))


def _norm(xy):
    """(x0,y0,x1,y1) 或 ((x0,y0),(x1,y1)) → 保证 x0≤x1、y0≤y1"""
    if len(xy) == 2:
        (x0, y0), (x1, y1) = xy
    else:
        x0, y0, x1, y1 = xy
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


class SafeDraw(ImageDraw.ImageDraw):
    """坐标反了不抛异常（缩放动画里常见）"""

    def rectangle(self, xy, *a, **k):
        return super().rectangle(_norm(xy), *a, **k)

    def ellipse(self, xy, *a, **k):
        return super().ellipse(_norm(xy), *a, **k)

    def rounded_rectangle(self, xy, *a, **k):
        return super().rounded_rectangle(_norm(xy), *a, **k)

    def arc(self, xy, *a, **k):
        return super().arc(_norm(xy), *a, **k)

    def chord(self, xy, *a, **k):
        return super().chord(_norm(xy), *a, **k)

    def pieslice(self, xy, *a, **k):
        return super().pieslice(_norm(xy), *a, **k)


class Gfx:
    def __init__(self):
        self.img = Image.new("1", (W, H))
        self.d = SafeDraw(self.img)
        self.d.fontmode = "1"
        self.mx = np.zeros((8, 8), dtype=bool)
        self.mx_level = 1
        self.texts: list[tuple[str, int]] = []  # 本帧画过的文字（检查缺字用）
        self.text_boxes: list[tuple] = []        # 本帧文字的范围（检查文字堆叠用）
        self.lum = np.zeros((H, W), np.float32)
        self.lum_used = False
        self.cut = Image.new("1", (W, H))
        self.k = SafeDraw(self.cut)
        self.threshold = BAYER_F  # 抖动阈值图：默认 Bayer（规则网点，在这个分辨率下最清楚）；BLUE 为蓝噪声
        self.offset = (0, 0)     # 整帧平移（屏幕震动）
        self.invert_all = False  # 整帧反色（闪白）
        self.tone = (0.06, 0.9)  # 色调：lum 在 lo 以下全黑、hi 以上全白，中间线性
        self.sharpen = 1.2       # 抖动前锐化（unsharp mask），小尺寸下保住边缘与形体；0 关闭

    def clear(self):
        self.d.rectangle((0, 0, W - 1, H - 1), fill=0)
        self.k.rectangle((0, 0, W - 1, H - 1), fill=0)
        self.mx[:] = False
        self.mx_level = 1
        self.texts.clear()
        self.text_boxes.clear()
        if self.lum_used:
            self.lum.fill(0)
            self.lum_used = False
        self.tone = (0.06, 0.9)
        self.sharpen = 1.2
        self.threshold = BAYER_F
        self.offset = (0, 0)
        self.invert_all = False

    def L(self) -> np.ndarray:
        """取灰度层来画（标记本帧用到了灰度）"""
        self.lum_used = True
        return self.lum

    def finish(self):
        """合成：灰度抖动 → 黑墨 → 白墨。引擎在场景画完一帧后调用"""
        if not self.lum_used and not self.cut.getbbox():
            self._post()
            return
        ink = np.array(self.img, dtype=bool)
        if self.lum_used:
            lum = self.lum
            if self.sharpen:
                p = np.pad(lum, 1, mode="edge")
                blur = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) * 0.125 + lum * 0.5
                lum = lum + self.sharpen * (lum - blur)
            if self.tone:
                lo, hi = self.tone
                lum = (lum - lo) / (hi - lo)
            out = lum > self.threshold
        else:
            out = np.zeros((H, W), bool)
        if self.cut.getbbox():
            out &= ~np.array(self.cut, dtype=bool)
        out |= ink
        self.img.paste(Image.fromarray(out))
        self._post()

    def _post(self):
        """屏幕震动与闪白"""
        dx, dy = self.offset
        if dx or dy or self.invert_all:
            a = np.array(self.img, dtype=bool)
            if dx or dy:
                a = np.roll(a, (dy, dx), (0, 1))
                if dy > 0:
                    a[:dy] = False
                elif dy < 0:
                    a[dy:] = False
                if dx > 0:
                    a[:, :dx] = False
                elif dx < 0:
                    a[:, dx:] = False
            if self.invert_all:
                a = ~a
            self.img.paste(Image.fromarray(a))

    # ------------------------------------------------------------ 文字

    def text(self, x: float, y: float, s: str, size: int = 12, fill: int = 1, align: str = "left",
             scale: int = 1, outline: bool = True) -> int:
        """y 为汉字顶端（12px 字高 11，8px 字高 7）。align: left / center / right（相对 x）。
        outline：字外描一圈黑边（默认开），压在任何画面上都清楚。scale>1 放大成粗像素。返回宽度。
        画过的字记在 g.text_boxes（检查文字堆叠用）"""
        self.texts.append((s, size))
        img = _text_img(s, size, scale)
        w = img.width if s else 0
        if align == "center":
            x -= w / 2
        elif align == "right":
            x -= w
        ix, iy = int(round(x)), int(round(y))
        if outline and fill:
            self.img.paste(0, (ix - 1, iy - 1), _halo_img(s, size, scale))
        self.img.paste(fill, (ix, iy), img)
        bb = img.getbbox()
        if bb and fill:
            self.text_boxes.append((s, ix + bb[0], iy + bb[1], ix + bb[2], iy + bb[3], ix, iy, size, scale))
        return w

    def vtext(self, x: float, y: float, s: str, size: int = 12, fill: int = 1, gap: int = 1) -> int:
        """竖排（从上到下），x 为列左边；返回总高度"""
        step = _FONT_FILES[size][2] + gap
        for i, ch in enumerate(s):
            cw = text_width(ch, size)
            self.text(x + (size - cw) / 2, y + i * step, ch, size, fill)
        return len(s) * step - gap

    # ------------------------------------------------------------ 像素

    def px(self, x: float, y: float, v: int = 1):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H:
            self.img.putpixel((x, y), v)

    def blit(self, spr: Sprite, x: float, y: float, invert: bool = False):
        """贴像素画：'#' 画亮（invert 时画暗），'.' 画暗（invert 时画亮），空格透明"""
        x, y = int(round(x)), int(round(y))
        self.img.paste(0 if invert else 1, (x, y), spr._on_img)
        self.img.paste(1 if invert else 0, (x, y), spr._off_img)

    def array(self) -> np.ndarray:
        """当前画面的 numpy 副本（bool，[y, x]）"""
        return np.array(self.img, dtype=bool)

    def put(self, a: np.ndarray):
        """用 numpy 数组（bool [64,128]）替换画面"""
        self.img.paste(Image.fromarray(a))

    def _box(self, box):
        if box is None:
            return 0, 0, W, H
        x0, y0, x1, y1 = (int(v) for v in box)
        return max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)

    def _region(self, x0, y0, x1, y1) -> np.ndarray:
        return np.array(self.img.crop((x0, y0, x1, y1)), dtype=bool)

    def _put_region(self, a: np.ndarray, x0, y0):
        self.img.paste(Image.fromarray(a), (x0, y0))

    def fade(self, level: float, box=None):
        """有序抖动淡出：box=(x0,y0,x1,y1)（不含 x1、y1）内只保留 level 比例的亮点"""
        if level >= 1:
            return
        x0, y0, x1, y1 = self._box(box)
        if x1 <= x0 or y1 <= y0:
            return
        a = self._region(x0, y0, x1, y1)
        a &= BAYER[y0:y1, x0:x1] < int(round(max(level, 0) * 16))
        self._put_region(a, x0, y0)

    def shade(self, box, level: float, fill: int = 1):
        """box 内按 level（0..1）画抖动灰度（fill=1 只加亮点，fill=0 按图案挖暗）"""
        x0, y0, x1, y1 = self._box(box)
        if x1 <= x0 or y1 <= y0:
            return
        a = self._region(x0, y0, x1, y1)
        pat = BAYER[y0:y1, x0:x1] < int(round(max(min(level, 1), 0) * 16))
        if fill:
            a |= pat
        else:
            a &= ~pat
        self._put_region(a, x0, y0)

    def shade_poly(self, pts, level: float, outline: int | None = 1):
        """多边形内画抖动灰度（衣袖、山、云的明暗），可带轮廓"""
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, y0, x1, y1 = self._box((min(xs), min(ys), max(xs) + 1, max(ys) + 1))
        if x1 > x0 and y1 > y0:
            m = Image.new("1", (x1 - x0, y1 - y0))
            ImageDraw.Draw(m).polygon([(px - x0, py - y0) for px, py in pts], fill=1)
            mask = np.array(m, dtype=bool)
            a = self._region(x0, y0, x1, y1)
            a[mask] = (BAYER[y0:y1, x0:x1] < int(round(max(min(level, 1), 0) * 16)))[mask]
            self._put_region(a, x0, y0)
        if outline is not None:
            self.d.polygon(pts, outline=outline)

    def invert(self, box=None):
        x0, y0, x1, y1 = self._box(box)
        if x1 <= x0 or y1 <= y0:
            return
        self._put_region(~self._region(x0, y0, x1, y1), x0, y0)

    # ------------------------------------------------------------ 点阵

    def mx_set(self, x: int, y: int, v: bool = True):
        if 0 <= x < 8 and 0 <= y < 8:
            self.mx[int(y), int(x)] = v

    def mx_rows(self, rows):
        """8 个整数，bit7 在左"""
        for y, r in enumerate(rows):
            for x in range(8):
                self.mx[y, x] = bool(r & (0x80 >> x))

    def mx_blit(self, spr: Sprite | str, x: int = 0, y: int = 0):
        if isinstance(spr, str):
            spr = Sprite(spr)
        for sy in range(spr.h):
            for sx in range(spr.w):
                if spr.mask[sy, sx]:
                    self.mx_set(x + sx, y + sy, bool(spr.on[sy, sx]))

    def mx_bytes(self) -> bytes:
        return bytes(int(sum(1 << (7 - x) for x in range(8) if self.mx[y, x])) for y in range(8))


def dissolve(a: np.ndarray, b: np.ndarray, p: float) -> np.ndarray:
    """从画面 a 抖动溶解到 b（p 0..1）"""
    return np.where(BAYER < int(round(p * 16)), b, a)


text_image = _text_img  # 公开：字串 → PIL '1' 遮罩（字顶对齐第 0 行），印进道具精灵用
