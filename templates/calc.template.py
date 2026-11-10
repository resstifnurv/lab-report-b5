# -*- coding: utf-8 -*-
"""计算与出图模板

复制本文件到你的实验目录，改 DATA 与公式即可。
build.py 会以实验目录为工作目录运行它；
运行后必须写出 out/out.json，并生成 data.json 里引用的图片。
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

try:
    import figstyle          # build.py 会把模板根目录加进 PYTHONPATH
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import figstyle

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# ---------------- 原始数据（把照片里的数字录到这里） ----------------
x = np.array([1, 2, 3, 4], float)
y = np.array([1.02, 2.05, 2.97, 4.01], float)


def sup(n):
    return "<sup>%s</sup>" % str(n).replace("-", "&minus;")


def main():
    res = stats.linregress(x, y)
    k, b, r2 = res.slope, res.intercept, res.rvalue ** 2

    # ---- 图：宽度按版心 136 mm，16:9 ----
    fig, ax = figstyle.fig(136, "16:9")
    ax.plot(x, y, "o", ms=5, mfc="#1f4e9c", mec="white", mew=0.8)
    ax.plot(x, k * x + b, color="#c0392b", lw=1.2)
    ax.set_xlabel("x / 单位", fontsize=10)
    ax.set_ylabel("y / 单位", fontsize=10)
    ax.grid(ls="--", lw=0.45, color="#999999", alpha=0.45)
    figstyle.save(fig, OUT / "fig1.png")

    # ---- 报告里用到的所有数字 ----
    out = {
        "slope": "%.3f" % k,
        "intercept": "%.3f" % b,
        "r2": "%.4f" % r2,
        "note_value": "42",
    }
    (OUT / "out.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("calc ok: k=%.4f b=%.4f R2=%.4f" % (k, b, r2))


if __name__ == "__main__":
    main()
