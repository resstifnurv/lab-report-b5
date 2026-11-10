# -*- coding: utf-8 -*-
"""1105 光电效应 · 计算与出图

build.py 会以本目录为工作目录运行本文件；
运行后要产出 out/out.json（所有报告数字）和 out/fig*.png（图）。
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

try:
    import figstyle
except ImportError:  # 单独运行本文件时
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import figstyle

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

E_CHARGE = 1.602176634e-19
H_TRUE = 6.62607015e-34

# ---------------- 原始数据 ----------------
lam = np.array([365, 405, 436, 546, 577], float)
nu = np.array([8.214, 7.408, 6.879, 5.490, 5.196], float)      # 1e14 Hz
Uc = np.array([-1.804, -1.466, -1.208, -0.642, -0.500], float)

U_a = np.array([-1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0,
                3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5,
                8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 12.0, 13.0,
                14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 24.0,
                26.0, 28.0, 30.0, 34.0, 38.0, 42.0, 46.0, 50.0])
I_435 = np.array([1, 6, 13, 23, 35, 49, 65, 80, 90,
                  98, 105, 112, 120, 127, 134, 141, 146, 150,
                  154, 158, 162, 165, 168, 172, 177, 185, 192,
                  198, 205, 210, 215, 220, 225, 229, 238, 244,
                  251, 255, 260, 269, 277, 284, 292, 298], float)
I_546 = np.array([0, 0, 2, 7, 14, 24, 34, 44, 52,
                  58, 63, 69, 73, 76, 78, 80, 82, 84,
                  87, 89, 92, 93, 95, 98, 100, 104, 107,
                  110, 113, 115, 117, 119, 121, 123, 127, 130,
                  133, 135, 138, 142, 146, 149, 152, 155], float)

phi = np.array([2, 4, 8], float)
Ia1 = np.array([90, 333, 1297], float)
Ia2 = np.array([43, 164, 648], float)

L = np.array([400, 380, 360, 340, 320, 300], float)
I_L = np.array([164, 188, 217, 256, 295, 352], float)


def sat(U, I, u_min=20.0):
    """高压段 I = Is - a/U 外推饱和电流。"""
    m = U >= u_min
    X = np.column_stack([np.ones(m.sum()), -1.0 / U[m]])
    coef, *_ = np.linalg.lstsq(X, I[m], rcond=None)
    pred = X @ coef
    r2 = 1 - ((I[m] - pred) ** 2).sum() / ((I[m] - I[m].mean()) ** 2).sum()
    return coef[0], coef[1], r2


def sup(n):
    return "<sup>%s</sup>" % str(n).replace("-", "&minus;")


def p10(mant, exp):
    return "%s&times;10%s" % (mant, sup(exp))


def main():
    # ---------- 一、普朗克常数 ----------
    res = stats.linregress(nu, Uc)
    k, b, r2 = res.slope, res.intercept, res.rvalue ** 2
    k_si = abs(k) * 1e-14
    h = k_si * E_CHARGE
    err = abs(h - H_TRUE) / H_TRUE * 100
    u_h = res.stderr * 1e-14 * E_CHARGE

    fig, ax = figstyle.fig(136, "16:9")
    ax.plot(nu, k * nu + b, color="#c0392b", lw=1.2, zorder=2)
    ax.plot(nu, Uc, "o", ms=5.2, mfc="#1f4e9c", mec="white", mew=0.8, zorder=3)
    ax.set_xlabel(r"频率 $\nu$ / ($10^{14}$ Hz)", fontsize=10)
    ax.set_ylabel(r"截止电压 $U_{\mathrm{c}}$ / V", fontsize=10)
    ax.set_xlim(4.85, 8.55)
    ax.set_ylim(-2.02, -0.30)
    ax.grid(ls="--", lw=0.45, color="#999999", alpha=0.45)
    ax.text(0.965, 0.95,
            r"$U_{\mathrm{c}}=%.3f-%.3f\times10^{-15}\nu$" % (b, k_si / 1e-15) + "\n"
            + r"$R^{2}=%.4f$" % r2,
            transform=ax.transAxes, va="top", ha="right", fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.75", lw=0.5))
    figstyle.save(fig, OUT / "fig1.png")

    # ---------- 二、伏安特性 ----------
    Is1, _, _ = sat(U_a, I_435)
    Is2, _, _ = sat(U_a, I_546)
    s_end1 = (I_435[-1] - I_435[-2]) / (U_a[-1] - U_a[-2])
    s_end2 = (I_546[-1] - I_546[-2]) / (U_a[-1] - U_a[-2])

    fig, ax = figstyle.fig(136, height_mm=66, margins=(0.115, 0.975, 0.965, 0.185))
    ax.plot(U_a, I_435, "-o", ms=2.9, lw=1.0, color="#c0392b",
            label=r"$\lambda=435.8$ nm")
    ax.plot(U_a, I_546, "-s", ms=2.7, lw=1.0, color="#1f4e9c", mfc="none",
            label=r"$\lambda=546.1$ nm")
    ax.set_xlabel(r"$U_{\mathrm{AC}}$ / V", fontsize=10)
    ax.set_ylabel(r"光电流 $I$ / ($10^{-11}$ A)", fontsize=10)
    ax.set_xlim(-2.5, 52.5)
    ax.set_ylim(0, 320)
    ax.grid(ls="--", lw=0.45, color="#999999", alpha=0.45)
    ax.legend(loc="upper left", frameon=True, framealpha=1, edgecolor="0.7",
              fontsize=9.5, handlelength=1.6, borderpad=0.4)
    figstyle.save(fig, OUT / "fig2.png")

    # ---------- 三、I - L^-2 ----------
    x3 = 1e6 / L ** 2                      # 10^-6 mm^-2
    res3 = stats.linregress(x3, I_L)
    k3, b3, r23 = res3.slope, res3.intercept, res3.rvalue ** 2

    fig, ax = figstyle.fig(136, "16:9", margins=(0.125, 0.975, 0.965, 0.175))
    xx = np.linspace(5.85, 11.55, 50)
    ax.plot(xx, k3 * xx + b3, color="#c0392b", lw=1.2, zorder=2)
    ax.plot(x3, I_L, "o", ms=5.2, mfc="#1f4e9c", mec="white", mew=0.8, zorder=3)
    ax.set_xlabel(r"$L^{-2}$ / ($10^{-6}$ mm$^{-2}$)", fontsize=10)
    ax.set_ylabel(r"饱和光电流 $I$ / ($10^{-11}$ A)", fontsize=10)
    ax.set_xlim(5.85, 11.55)
    ax.set_ylim(120, 390)
    ax.grid(ls="--", lw=0.45, color="#999999", alpha=0.45)
    ax.text(0.035, 0.95,
            r"$I=%.1f\,L^{-2}-%.1f$" % (k3, abs(b3)) + "\n" + r"$R^{2}=%.4f$" % r23,
            transform=ax.transAxes, va="top", ha="left", fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.75", lw=0.5))
    figstyle.save(fig, OUT / "fig3.png")

    # ---------- 报告数字 ----------
    def us(v):
        return ("%.1f" % v).replace("-", "&minus;")

    # 大表（44 组数据）不写进 data.json，避免和这里重复
    rows_t2 = [[us(U_a[i]), "%d" % I_435[i], "%d" % I_546[i],
                us(U_a[i + 22]), "%d" % I_435[i + 22], "%d" % I_546[i + 22]]
               for i in range(22)]

    out = {
        "rows_t2": rows_t2,
        "eq": "%.3f &minus; %.3f&times;10<sup>&minus;15</sup><i>ν</i>" % (b, k_si / 1e-15),
        "r2": "%.4f" % r2,
        "k": "&minus;%.3f&times;10<sup>&minus;15</sup> V&middot;s" % (k_si / 1e-15),
        "h": p10("%.3f" % (h / 1e-34), -34),
        "err": "%.2f%%" % err,
        "uk": p10("%.1f" % (res.stderr * 1e-14 / 1e-17), -17),
        "uh": p10("%.2f" % (u_h / 1e-34), -34),
        "hpm": "(%.2f &plusmn; %.2f)&times;10<sup>&minus;34</sup> J&middot;s" % (h / 1e-34, u_h / 1e-34),
        "b": "%.3f" % b,
        "w0": "%.2f" % b,
        # Is 的单位是 10^-11 A，换成 10^-9 A 要除以 100
        "is1": p10("%.1f" % (Is1 / 100), -9),
        "is2": p10("%.1f" % (Is2 / 100), -9),
        "ratio": "%.1f" % (Is1 / Is2),
        "s435": "%.1f" % s_end1,
        "s546": "%.1f" % s_end2,
        "r1": "%.1f" % (Ia1[-1] / Ia1[0]),
        "r2x": "%.1f" % (Ia2[-1] / Ia2[0]),
        "k3": "%.1f" % k3,
        "b3": "%.1f" % abs(b3),
        "r23": "%.4f" % r23,
        "il": "%.2f" % ((I_L * L ** 2).min() / 1e7),
        "ih": "%.2f" % ((I_L * L ** 2).max() / 1e7),
    }
    (OUT / "out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    print("calc ok: h=%.4e  R2=%.4f  Is1=%.1f Is2=%.1f" % (h, r2, Is1, Is2))


if __name__ == "__main__":
    main()
