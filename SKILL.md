---
name: lab-report-b5
description: 把实验原始数据排成 B5 可打印剪贴的图表页（三线表 + 定尺寸图 + 拟合结果），自动校验版面并输出 PDF
whenToUse: 用户给出实验原始数据（照片或数字），要求按 B5 页宽排版表格与图像、给出拟合结果并输出可打印 PDF
---

# lab-report-b5 使用流程

工具根目录 = 本文件所在目录（下称 `$ROOT`）。所有命令在 `$ROOT` 下执行。

## 0. 开始前

1. 读 `$ROOT/references/page-geometry.md`：B5 几何、字号、宽高比与 237 mm 上限。
2. 若用户要复现既有版式，先看 `$ROOT/examples/1105-photoelectric/`
   （`data.json` + `calc.py` + `out/` 成品），这是唯一的样式基准。
3. 确认有 Python 与 Chrome/Edge；`python -c "import numpy, scipy, matplotlib"` 不报错即可。

## 1. 建实验目录

```
<实验目录>/
├─ data.json     ← 复制 $ROOT/templates/data.template.json
├─ calc.py       ← 复制 $ROOT/templates/calc.template.py
└─ 原始数据*.jpg
```

## 2. 录入数据

用 `read_image` 读原始数据，**逐项核对后**写成 `calc.py` 顶部的 numpy 数组。
核对手段：单位、量级、单调性、与已知公式（如 c/λ）是否吻合。
照片上的涂改、被划掉的数字、表头单位是主要错误来源；不确定就问用户。

## 3. 写 calc.py

- 用 `scipy.stats.linregress` 等做拟合，算出 R²、斜率和截距标准误、相对误差。
- 图一律 `figstyle.fig(width_mm=136, aspect="16:9")`（或 `height_mm=`），
  字号 9~10 pt，`figstyle.save(fig, OUT/"figN.png")`。
- 所有要出现在报告里的数字写进 `out/out.json`，值为**可直接插入 HTML 的字符串**
  （上标用 `<sup>`，减号用 `&minus;`，乘号 `&times;`）。
- 禁止把数字手写进 `data.json`；正文用 `{key}` 占位。

## 4. 写 data.json

只描述结构，不写样式：
- 纸：`{"widthMm":176,"heightMm":250,"marginMm":{"top":17,"right":20,"bottom":13,"left":20}}`
- 每页：`header`、`title`、`blocks`（`table` / `figure` / `result` / `note` / `spacer`）。
- 表：`colWidthsMm` 之和建议 = 136（满宽）或 ≤136；`rowHeightMm` 先给 4~12。
  行数很多（>10 行）时用 `"rowsFrom": "rows_tN"`，行数据由 `calc.py` 写入 `out.json`。
- 声明约束：小表给 `minAspect:3, maxAspect:5`，数据表给 `minAspect:2.5`；
  图给 `widthMm` + `aspect`（或 `heightMm`）。

## 5. 构建

```bash
python build.py <实验目录>
```

脚本依次：运行 `calc.py` → 生成 `out/report.html` 与 `out/report_print.html` →
Chrome 打印 `out/<name>.pdf` → 回读渲染尺寸做检查。

## 6. 迭代直到全绿（必须）

检查项（任一 `[!!]` 都不算完成）：

| 检查 | 门槛 | 不通过怎么办 |
|---|---|---|
| 表格宽高比 | 声明区间内（容差 0.02） | 调 `rowHeightMm`，或加/减列宽 |
| 图尺寸 | 与声明偏差 ≤ 1 mm | `calc.py` 出图尺寸与 `aspect` 对齐 |
| 页面内容底部 | ≤ 页高 − 下边距（默认 237 mm） | 减行高、删 spacer、缩短说明 |
| PDF 页数 | 等于 `pages` 数 | 检查打印版是否混入调试元素 |

通过后再用 `python render_pages.py out/<name>.pdf` 出 PNG，逐页目检：
表线是否齐全、图例是否遮挡、文字是否被裁、题注编号连续。

## 7. 交付

- 交付 PDF 路径；保留 `out/` 与源码，方便用户改数据重跑。
- 在回复里给出关键结果：拟合表达式、R²、目标物理量、相对误差、特征值估计。
- 若用户原始要求与数据规模冲突（例如要求 12 行但数据有 44 组），
  按数据实际排布并在回复中说明，不要删数据。

## 关键约束

- 页面固定 250 mm 高且 `overflow:hidden`：溢出不会报错，只会被裁掉——必须看检查结果。
- 图不能在 HTML 里缩放：出图即最终尺寸。
- 打印用 `report_print.html`（不含测量脚本），调试用 `report.html`。
- 中文负号：matplotlib 保持 `axes.unicode_minus=False`；HTML 用 `&minus;`。
- 缺占位符会直接报错并指出 key，按提示补 `out.json`。

## 资源

- `references/page-geometry.md` — 尺寸/字号/线宽/一页容量速查
- `references/pitfalls.md` — 已知坑（Chrome 路径、字体、溢出、多页）
- `references/prompt-example.md` — 给用户的指令模板
- `examples/1105-photoelectric/` — 三页成品（表 1~4、图 1~3）
