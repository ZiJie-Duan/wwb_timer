"""画布：OLED 128×64 单色 + 点阵 8×8。场景每帧在清空的画布上重画（立即模式）。

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

# 4×4 Bayer 有序抖动阈值（0..15）
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.uint8)
BAYER = np.tile(BAYER4, (H // 4, W // 4))
BAYER8 = np.tile(BAYER4, (2, 2))


def font(size: int = 12) -> ImageFont.FreeTypeFont:
    if size not in _fonts:
        name = _FONT_FILES[size][0]
        _fonts[size] = ImageFont.truetype(str(FONT_DIR / name), size)
    return _fonts[size]


def text_width(s: str, size: int = 12) -> int:
    return int(font(size).getlength(s))


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


class Gfx:
    def __init__(self):
        self.img = Image.new("1", (W, H))
        self.d = ImageDraw.Draw(self.img)
        self.d.fontmode = "1"
        self.mx = np.zeros((8, 8), dtype=bool)
        self.mx_level = 1
        self.texts: list[tuple[str, int]] = []  # 本帧画过的文字（检查缺字用）

    def clear(self):
        self.d.rectangle((0, 0, W - 1, H - 1), fill=0)
        self.mx[:] = False
        self.mx_level = 1
        self.texts.clear()

    # ------------------------------------------------------------ 文字

    def text(self, x: float, y: float, s: str, size: int = 12, fill: int = 1, align: str = "left",
             scale: int = 1) -> int:
        """y 为汉字顶端（12px 字高 11，8px 字高 7）。align: left / center / right（相对 x）。
        scale>1 时放大成粗像素。返回宽度"""
        self.texts.append((s, size))
        f = font(size)
        off = _FONT_FILES[size][1]
        w = int(f.getlength(s))
        if align == "center":
            x -= w * scale / 2
        elif align == "right":
            x -= w * scale
        x, y = int(round(x)), int(round(y))
        if scale == 1:
            self.d.text((x, y - off), s, font=f, fill=fill)
        else:
            hh = size + 4
            tmp = Image.new("1", (max(w, 1), hh))
            td = ImageDraw.Draw(tmp)
            td.fontmode = "1"
            td.text((0, -off), s, font=f, fill=1)
            tmp = tmp.resize((max(w, 1) * scale, hh * scale), Image.NEAREST)
            self.img.paste(fill, (x, y), tmp)
        return w * scale

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

    def fade(self, level: float, box=None):
        """有序抖动淡出：box=(x0,y0,x1,y1)（不含 x1、y1）内只保留 level 比例的亮点"""
        if level >= 1:
            return
        x0, y0, x1, y1 = self._box(box)
        if x1 <= x0 or y1 <= y0:
            return
        a = self.array()
        keep = BAYER[y0:y1, x0:x1] < int(round(max(level, 0) * 16))
        a[y0:y1, x0:x1] &= keep
        self.put(a)

    def shade(self, box, level: float, fill: int = 1):
        """box 内按 level（0..1）画抖动灰度（只画亮点，不清除）"""
        x0, y0, x1, y1 = self._box(box)
        if x1 <= x0 or y1 <= y0:
            return
        a = self.array()
        pat = BAYER[y0:y1, x0:x1] < int(round(max(min(level, 1), 0) * 16))
        if fill:
            a[y0:y1, x0:x1] |= pat
        else:
            a[y0:y1, x0:x1] &= ~pat
        self.put(a)

    def shade_poly(self, pts, level: float, outline: int | None = 1):
        """多边形内画抖动灰度（衣袖、山、云的明暗），可带轮廓"""
        m = Image.new("1", (W, H))
        ImageDraw.Draw(m).polygon(pts, fill=1)
        a = self.array()
        mask = np.array(m, dtype=bool)
        a[mask] = BAYER[mask] < int(round(max(min(level, 1), 0) * 16))
        self.put(a)
        if outline is not None:
            self.d.polygon(pts, outline=outline)

    def invert(self, box=None):
        x0, y0, x1, y1 = self._box(box)
        a = self.array()
        a[y0:y1, x0:x1] = ~a[y0:y1, x0:x1]
        self.put(a)

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
