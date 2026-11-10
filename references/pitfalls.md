# 已知坑与处理方式

按出现频率排序。模板已经内置了大部分处理，改模板时注意别破坏它们。

## 1. 打印失败：`Multiple targets are not supported`

**原因**：Chrome 把含空格/中文的 `file:///...` 路径拆成了多个参数。
**处理**：`check.stage()` 会把 HTML 和图片复制到 `%TEMP%` 下的纯 ASCII 临时目录再打印。
自己写脚本时不要直接把工作目录的路径拼进命令行。

## 2. 图里负号变方框

**原因**：SimHei 没有 U+2212（真正的减号）。
**处理**：`figstyle.py` 已设 `axes.unicode_minus = False`（用 ASCII 连字符）。
HTML 正文里可以用 `&minus;`，因为西文走 Times New Roman，它有该字形。

## 3. 内容被静默裁掉

**原因**：`.page{height:250mm; overflow:hidden}`，超出的部分不会报错、直接消失。
**处理**：每次构建都跑 `check.py`，看“第 N 页内容底部”是否 ≤ 237 mm。
不要靠目测——预览渲染和打印可能略有差异。

## 4. 表格行高设了不生效

**原因**：CSS 的 `height` 在表格单元格上是“最小高度”，内容更高时会撑开；反之不会压缩。
**处理**：行高只能调大不能调小到低于文字高度；要更矮就减字号或减 padding。

## 5. 图在页面里被拉伸变形

**原因**：`img` 只给宽度，高度由图片自身比例决定。
**处理**：`calc.py` 出图时必须用 `figstyle.fig()` 的精确尺寸；`data.json` 里的
`widthMm`/`aspect`/`heightMm` 只是给检查用的“声明值”，不能代替真实出图尺寸。

## 6. PDF 多出一页空白

**原因**：调试用的 `metrics` 脚本在 `</body>` 后插了一个 `<pre>`，正文被它顶到下一页。
**处理**：`build.py` 分成 `report.html`（带脚本，用于测量）和 `report_print.html`（不带，用于打印）。
自己写页面时，任何调试元素都不能留在打印版里。

## 7. 中文字体缺失（macOS / Linux）

**原因**：样式栈写死了 SimSun / SimHei。
**处理**：`figstyle._pick_font()` 会依次尝试 SimHei → Microsoft YaHei → Noto Sans CJK SC；
HTML 侧把 `font-family` 里的 SimSun 换成 `"Songti SC", "Noto Serif CJK SC", serif` 即可。

## 8. `calc.py` 报 `ModuleNotFoundError: figstyle`

**原因**：直接 `python calc.py` 时没有模板根目录的搜索路径。
**处理**：用 `python build.py <实验目录>` 运行（它会设 `PYTHONPATH`）；
或在 `calc.py` 顶部加 `sys.path.insert(0, "<lab-report-b5 路径>")`。

## 9. 数字写死导致对不上

**原因**：把拟合结果手抄进 `data.json`。
**处理**：`data.json` 只放 `{占位符}`，真实数字由 `calc.py` 写进 `out.json`；
`build.py` 遇到缺失的占位符会直接报错并指出是哪个 key。

## 10. 旧版 Chrome 没有 `--no-pdf-header-footer`

**处理**：`build.py` 失败后会改用 `--print-to-pdf-no-header` 重试一次。
两个都失败时，用 `--browser` 指定 Edge 也能打印。
