"""x6 赛博歇的公用零件：打坐的道士、窗口、鼠标、进度条（本文件不登记场景）"""
from __future__ import annotations

from ..engine.anim import clamp
from ..engine.gfx import Gfx, Sprite

# 盘坐的道士（正面，Q 版）：发髻横插一根簪、宽袖道袍（抖动纹）、双手在腹前结印。左右对称，用半幅镜像生成
_SAGE_HALF = [
    "                .##",
    "               .###",
    "             ######",
    "               .###",
    "            .######",
    "          .##......",
    "         .#........",
    "         #.........",
    "         #.........",
    "         #.........",
    "         #.........",
    "         .#........",
    "          .#.......",
    "           .##.....",
    "            ..#####",
    "        #####......",
    "      ##.#...#.....",
    "     #.#.#....#....",
    "    #.#.#.#....#...",
    "   #.#.#.#.#....#..",
    "   ##.#.#.#.#....#.",
    "  #.#.#.#.#.#.....#",
    "  ##.#.#.#.#.#.....",
    "  #.#.#.#.#.#.#....",
    " #.#.#.#.#.#.#.#...",
    " ##.#.#.#.#.#.#.###",
    " #.#.#.#.#.#.##...#",
    "#.#.#.#.#.#.##.....",
    "##.#.#.#.#.#.#.....",
    "#.#.#.#.#.#..##...#",
    "#..............####",
    " ##...............#",
    "#..###.........##..",
    "#.....#######......",
    "#..................",
    " ##################",
]
SAGE = Sprite("\n".join(h.ljust(19) + h.ljust(19)[:-1][::-1] for h in _SAGE_HALF))
SAGE_W, SAGE_H = SAGE.w, SAGE.h      # 37 × 36
SAGE_EYES = (13, 9)                  # 左眼左端（相对左上角）；右眼 +8
SAGE_HEAD = (9, 0, 28, 15)           # 头部范围（含发髻），坐忘时用
SAGE_CX = 18                         # 中线


def sage(g: Gfx, x: float, y: float, eyes: str = "closed", spr: Sprite = SAGE):
    """在 (x, y)（左上角）画道士。eyes: closed 闭目 / open 睁眼 / one 睁一只 / x 晕 / up 翻白眼看上 / none"""
    g.blit(spr, x, y)
    ex, ey = int(round(x)) + SAGE_EYES[0], int(round(y)) + SAGE_EYES[1]
    for i, kind in enumerate(_eye_kinds(eyes)):
        xx = ex + i * 8
        if kind == "c":
            g.d.line((xx, ey + 1, xx + 2, ey + 1), fill=1)
        elif kind == "o":
            g.d.rectangle((xx, ey, xx + 2, ey + 1), fill=1)
        elif kind == "u":
            g.d.rectangle((xx + 1, ey - 1, xx + 2, ey), fill=1)
        elif kind == "x":
            g.d.line((xx, ey - 1, xx + 2, ey + 1), fill=1)
            g.d.line((xx, ey + 1, xx + 2, ey - 1), fill=1)


def _eye_kinds(eyes: str):
    return {"closed": "cc", "open": "oo", "one": "co", "x": "xx", "up": "uu", "none": "  "}.get(eyes, "cc")


def window(g: Gfx, x0: float, y0: float, x1: float, y1: float, title: str = "", close: bool = True, size: int = 8):
    """像素风窗口：标题栏反白（size=8 高 10，size=12 高 13），右上角一个 ×。返回标题栏底边 y"""
    bh = 10 if size == 8 else 13
    g.d.rectangle((x0, y0, x1, y1), fill=0, outline=1)
    g.d.rectangle((x0, y0, x1, y0 + bh - 1), fill=1)
    if title:
        g.text(x0 + 3, y0 + (1 if size == 8 else 1), title, size=size, fill=0)
    if close:
        cx, cy = x1 - 7, y0 + (bh - 6) // 2
        g.d.rectangle((cx - 1, cy, cx + 5, cy + 5), fill=0)
        g.d.line((cx, cy + 1, cx + 4, cy + 4), fill=1)
        g.d.line((cx, cy + 4, cx + 4, cy + 1), fill=1)
    return y0 + bh


def progress(g: Gfx, x0: int, y0: int, x1: int, y1: int, p: float, stripes: float | None = None):
    """进度条：外框 + 实心填充；stripes = 时间时画流动斜纹（填充部分里挖暗线）"""
    p = clamp(p)
    g.d.rectangle((x0, y0, x1, y1), outline=1, fill=0)
    xf = x0 + 2 + (x1 - x0 - 4) * p
    if xf >= x0 + 2:
        g.d.rectangle((x0 + 2, y0 + 2, xf, y1 - 2), fill=1)
        if stripes is not None:
            h = y1 - y0 - 4
            off = int(stripes * 8) % 6
            for sx in range(int(x0 + 2) - 6 + off, int(xf) + 1, 6):
                for k in range(h + 1):
                    px = sx + k
                    if x0 + 2 <= px <= xf:
                        g.px(px, y1 - 2 - k, 0)


CURSOR = Sprite("""
#
##
#.#
#..#
#...#
#....#
#.....#
#..####
#.#
##
#
""")
HAND = Sprite("""
  ##
 #..#
 #..#
 #..###
 #..#..##
##..#..#.#
#.#....#.#
#..#.....#
 #.......#
 #......#
  ######
""")
