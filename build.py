# -*- coding: utf-8 -*-
"""lab-report-b5 · 构建器

    python build.py <实验目录>

流程：跑 calc.py -> 读 out/out.json -> data.json 渲染成 HTML ->
Chrome/Edge 无头打印 B5 PDF -> 回读渲染尺寸做版面检查。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
CSS_SRC = (ROOT / "styles" / "page.css").read_text(encoding="utf-8")
sys.path.insert(0, str(ROOT))
import check  # noqa: E402


# ---------------------------------------------------------------- 文本与尺寸
def fmt(text, out):
    """把 {key} 换成 out.json 里的值；缺 key 时明确报错，不静默留空。"""
    if text is None:
        return ""
    text = str(text)
    try:
        return text.format_map(out)
    except KeyError as e:
        raise SystemExit("[错误] 文本里的占位符 %s 在 out.json 中不存在：%s" % (e, text[:60]))
    except ValueError as e:
        raise SystemExit("[错误] 文本里有不成对的花括号：%s (%s)" % (text[:60], e))


def paper_geometry(paper):
    w = float(paper.get("widthMm", 176))
    h = float(paper.get("heightMm", 250))
    m = paper.get("marginMm", 20)
    if isinstance(m, dict):
        return w, h, float(m.get("top", 20)), float(m.get("right", 20)), \
            float(m.get("bottom", 20)), float(m.get("left", 20))
    return w, h, float(m), float(m), float(m), float(m)


def aspect_of(b):
    a = b.get("aspect", 16 / 9)
    if isinstance(a, str) and ":" in a:
        x, y = a.split(":")
        return float(x) / float(y)
    return float(a)


# ---------------------------------------------------------------- 块渲染
def cell_html(c, tag, idx, row_h, divider, out):
    style = []
    if row_h:
        style.append("height:%smm" % row_h)
    if divider is not None and idx == divider:
        style.append("border-left:0.25mm solid #000")
    if isinstance(c, dict):
        body = fmt(c.get("t", ""), out)
        if c.get("sub"):
            body += '<br><span class="small">%s</span>' % fmt(c["sub"], out)
    else:
        body = fmt(c, out)
    st = ' style="%s"' % ";".join(style) if style else ""
    return "<%s%s>%s</%s>" % (tag, st, body, tag)


def render_table(b, out, bid):
    cap = b.get("caption")
    # rows 可以直接写死在 data.json，也可以由 out.json 提供（rowsFrom: "rows_t2"）
    rows = out[b["rowsFrom"]] if b.get("rowsFrom") else b.get("rows", [])
    row_h = b.get("rowHeightMm")
    divider = b.get("dividerAfter")
    parts = []
    if cap:
        parts.append('<div class="cap">%s</div>' % fmt(cap, out))
    attrs = ' data-id="%s"' % bid
    if b.get("minAspect") is not None:
        attrs += ' data-min-aspect="%s"' % b["minAspect"]
    if b.get("maxAspect") is not None:
        attrs += ' data-max-aspect="%s"' % b["maxAspect"]
    cols = b.get("colWidthsMm")
    colgroup = ""
    if cols:
        colgroup = "<colgroup>" + "".join('<col style="width:%smm">' % c for c in cols) + "</colgroup>"
    parts.append("<table class=\"three\"%s>%s" % (attrs, colgroup))
    if b.get("layout", "normal") == "quantities":
        # 首行是“量名 + 各列值”，整张表按行读
        body = []
        for ri, r in enumerate(rows):
            cls = ' class="sep"' if ri == 0 else ""
            body.append("<tr%s>%s</tr>" % (
                cls, "".join(cell_html(c, "td", i, row_h, divider, out) for i, c in enumerate(r))))
        parts.append("<tbody>%s</tbody>" % "".join(body))
    else:
        head = b.get("header", [])
        parts.append("<thead><tr>%s</tr></thead>" % "".join(
            cell_html(c, "th", i, None, divider, out) for i, c in enumerate(head)))
        body = []
        for r in rows:
            body.append("<tr>%s</tr>" % "".join(
                cell_html(c, "td", i, row_h, divider, out) for i, c in enumerate(r)))
        parts.append("<tbody>%s</tbody>" % "".join(body))
    parts.append("</table>")
    return "\n".join(parts)


def render_figure(b, out, bid):
    w = b.get("widthMm", 136)
    h = b.get("heightMm") or w / aspect_of(b)
    parts = []
    if b.get("caption"):
        parts.append('<div class="cap">%s</div>' % fmt(b["caption"], out))
    parts.append('<img src="%s" data-id="%s" data-aspect="%.4f" style="width:%smm;height:%smm">'
                 % (b["src"], bid, aspect_of(b), w, round(h, 2)))
    return "\n".join(parts)


def render_note(b, out, bid):
    style = ' style="%s"' % b["style"] if b.get("style") else ""
    return '<div class="note"%s>%s</div>' % (style, fmt(b.get("text", ""), out))


def render_result(b, out, bid):
    style = ' style="%s"' % b["style"] if b.get("style") else ""
    lines = "".join('<div class="line">%s</div>' % fmt(t, out) for t in b.get("lines", []))
    return '<div class="res"%s>%s</div>' % (style, lines)


def render_spacer(b, out, bid):
    return '<div style="height:%smm"></div>' % b.get("heightMm", 2)


RENDERERS = {
    "table": render_table,
    "figure": render_figure,
    "note": render_note,
    "result": render_result,
    "spacer": render_spacer,
}


# ---------------------------------------------------------------- 页面
def render_page(page, no, total, out, footer_left):
    blocks = []
    for bi, b in enumerate(page.get("blocks", [])):
        kind = b["type"]
        if kind not in RENDERERS:
            raise SystemExit("[错误] 未知块类型：%s（第 %d 页）" % (kind, no))
        bid = b.get("id") or "p%db%d" % (no, bi + 1)
        blocks.append(RENDERERS[kind](b, out, bid))
    head = page.get("header", ["", ""])
    return """
<div class="page">
  <div class="ph"><span>%s</span><span>%s</span></div>
  <h2>%s</h2>
%s
  <div class="foot"><span>%s</span><span>第 %d 页 / 共 %d 页</span></div>
</div>""" % (
        fmt(head[0], out), fmt(head[1], out), fmt(page.get("title", ""), out),
        "\n".join(blocks), fmt(footer_left, out), no, total)


def build_html(data, out, paper):
    pw, ph, mt, mr, mb, ml = paper_geometry(paper)
    css = Template(CSS_SRC).substitute(PW=pw, PH=ph, MT=mt, MR=mr, MB=mb, ML=ml)
    total = len(data["pages"])
    footer_left = data.get("footerLeft", "B5（176 × 250 mm）　页边距 20 mm　图文宽 136 mm")
    body = "".join(render_page(p, i + 1, total, out, footer_left)
                   for i, p in enumerate(data["pages"]))
    title = data.get("name", "实验数据")
    return """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>%s</title>
<style>%s</style></head>
<body>%s</body></html>""" % (title, css, body)


# ---------------------------------------------------------------- 打印
def print_pdf(browser, html_path, pdf_path):
    base = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--virtual-time-budget=8000", "--no-pdf-header-footer",
            "--print-to-pdf=%s" % pdf_path, Path(html_path).as_uri()]
    subprocess.run(base, capture_output=True, timeout=180)
    if not pdf_path.exists():
        # 旧版 Chrome 的另一种写法
        base[base.index("--no-pdf-header-footer")] = "--print-to-pdf-no-header"
        subprocess.run(base, capture_output=True, timeout=180)
    return pdf_path.exists()


def pdf_page_count(pdf_path):
    try:
        import pymupdf
    except ImportError:
        return None
    with pymupdf.open(pdf_path) as doc:
        return len(doc)


# ---------------------------------------------------------------- 主流程
def main(argv=None):
    ap = argparse.ArgumentParser(description="把 data.json + calc.py 排成 B5 PDF")
    ap.add_argument("exp", nargs="?", default=".", help="实验目录（含 data.json、calc.py）")
    ap.add_argument("--no-calc", action="store_true", help="跳过 calc.py（沿用上次 out/）")
    ap.add_argument("--no-check", action="store_true", help="跳过版面检查")
    ap.add_argument("--browser", help="Chrome/Edge 路径，默认自动查找")
    args = ap.parse_args(argv)

    exp = Path(args.exp).resolve()
    data_path = exp / "data.json"
    if not data_path.exists():
        raise SystemExit("[错误] 找不到 %s" % data_path)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    out_dir = exp / "out"
    out_dir.mkdir(exist_ok=True)

    if not args.no_calc:
        print("[1/5] 运行 calc.py …")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), str(exp), env.get("PYTHONPATH", "")])
        p = subprocess.run([sys.executable, "calc.py"], cwd=exp, env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if p.returncode != 0:
            sys.stderr.write(p.stdout or "")
            sys.stderr.write(p.stderr or "")
            raise SystemExit("[错误] calc.py 运行失败（见上面的报错）")

    out_json = out_dir / "out.json"
    if not out_json.exists():
        raise SystemExit("[错误] 没有 %s，calc.py 需要输出它" % out_json)
    out = json.loads(out_json.read_text(encoding="utf-8"))

    print("[2/5] 生成 HTML …")
    html = build_html(data, out, data.get("paper", {}))
    (out_dir / "report.html").write_text(
        html.replace("</body>", check.METRICS_SCRIPT + "</body>"), encoding="utf-8")
    (out_dir / "report_print.html").write_text(html, encoding="utf-8")
    print("      %d 页 -> out/report.html" % len(data["pages"]))

    browser = check.find_browser(args.browser)
    if not browser:
        raise SystemExit("[错误] 找不到 Chrome / Edge，请用 --browser 指定路径，"
                         "或设置环境变量 LAB_REPORT_BROWSER")
    name = (data.get("name") or exp.name).replace("/", "_").replace("\\", "_")
    pdf_path = out_dir / (name + ".pdf")

    print("[3/5] 打印 PDF …")
    tmp = check.stage(out_dir, "report_print.html")
    try:
        ok = print_pdf(browser, tmp / "report_print.html", pdf_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not ok:
        raise SystemExit("[错误] 打印失败：浏览器没有生成 PDF")
    pages = pdf_page_count(pdf_path)
    print("      %s（%s）" % (pdf_path.name, "%d 页" % pages if pages else "页数未知"))

    rc = 0
    if not args.no_check:
        print("[4/5] 版面检查 …")
        tmp = check.stage(out_dir, "report.html")
        try:
            els, pgs = check.measure(tmp / "report.html", browser)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        pw, ph, mt, mr, mb, ml = paper_geometry(data.get("paper", {}))
        ok, lines = check.verify(check.collect_expectations(data), els, pgs,
                                 len(data["pages"]), ph, ph - mb)
        print("\n".join("      " + s for s in lines))
        if not ok:
            rc = 1
            print("      -> 版面不合格，请调整 rowHeightMm / heightMm 后重跑")
    else:
        print("[4/5] 版面检查 … 已跳过")

    print("[5/5] 完成：%s" % pdf_path)
    return rc


if __name__ == "__main__":
    sys.exit(main())
