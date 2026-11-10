# -*- coding: utf-8 -*-
"""lab-report-b5 · 出图样式

按 B5 版心宽度（136 mm）直接出图，页面里不再缩放，
这样图上的字号就是打印出来的字号。

用法::

    import figstyle
    fig, ax = figstyle.fig(width_mm=136, aspect="16:9")
    ax.plot(x, y)
    figstyle.save(fig, "out/fig1.png")
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

MM = 1 / 25.4          # 1 mm 对应的英寸数
CONTENT_MM = 136.0     # B5、左右 20 mm 页边距时的版心宽度


def _pick_font(*names):
    """按顺序挑一个系统里真实存在的字体，避免中文变方块。"""
    have = {f.name for f in font_manager.fontManager.ttflist}
    for n in names:
        if n in have:
            return n
    return "sans-serif"


def setup(size=10):
    """全局样式：中文字体、向内刻度、浅虚线网格、无 unicode 负号。"""
    plt.rcParams.update({
        "font.family": _pick_font("SimHei", "Microsoft YaHei", "Noto Sans CJK SC"),
        "font.size": size,
        # SimHei 没有 U+2212，必须用 ASCII 连字符，否则负号变方框
        "axes.unicode_minus": False,
        "axes.linewidth": 0.9,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "xtick.minor.size": 2,
        "ytick.minor.size": 2,
        "mathtext.fontset": "dejavusans",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })


def parse_aspect(aspect):
    """'16:9' 或 16/9 -> 1.777。"""
    if isinstance(aspect, str) and ":" in aspect:
        a, b = aspect.split(":")
        return float(a) / float(b)
    return float(aspect)


def fig(width_mm=CONTENT_MM, aspect="16:9", height_mm=None, margins=None):
    """建一张打印尺寸精确的图。

    margins=(left, right, top, bottom) 为 subplots 边距，默认给轴标签留足空间。
    """
    h_mm = height_mm if height_mm else width_mm / parse_aspect(aspect)
    f, ax = plt.subplots(figsize=(width_mm * MM, h_mm * MM))
    left, right, top, bottom = margins or (0.115, 0.975, 0.965, 0.175)
    f.subplots_adjust(left=left, right=right, top=top, bottom=bottom)
    return f, ax


def save(f, path, dpi=400):
    f.savefig(path, dpi=dpi)
    plt.close(f)


setup()
