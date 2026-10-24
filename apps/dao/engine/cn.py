"""中文数字、干支、时辰"""
from __future__ import annotations

DIGITS = "〇一二三四五六七八九"
TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
SHICHEN = [f"{z}时" for z in DIZHI]  # 子时 23-1 点，丑时 1-3 点……
WUXING = "木火土金水"


def cn_num(n: int) -> str:
    """1 → 一，12 → 十二，105 → 一百零五（0-9999）"""
    if n < 0:
        return "负" + cn_num(-n)
    if n < 10:
        return DIGITS[n] if n else "零"
    units = ["", "十", "百", "千"]
    s = str(n)
    out = []
    zero = False
    for i, ch in enumerate(s):
        d = int(ch)
        u = units[len(s) - 1 - i]
        if d == 0:
            zero = True
            continue
        if zero and out:
            out.append("零")
        zero = False
        out.append(("" if (d == 1 and u == "十" and i == 0) else DIGITS[d]) + u)
    return "".join(out)


def shichen(hour: int) -> str:
    """0-23 点 → 时辰名"""
    return SHICHEN[((hour + 1) // 2) % 12]


def ganzhi(n: int) -> str:
    """六十甲子第 n 个（0 = 甲子）"""
    return TIANGAN[n % 10] + DIZHI[n % 12]
