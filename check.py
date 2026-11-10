# -*- coding: utf-8 -*-
"""lab-report-b5 · 版面检查

原理：往 HTML 里注入一段脚本，用无头浏览器把 DOM 渲染出来，
再把每个表/图的实际毫米尺寸、每页内容底部位置读回来，
与 data.json 里声明的约束比对。

单独运行：python check.py <实验目录>
"""
import html as htmllib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PX_PER_MM = 96 / 25.4

METRICS_SCRIPT = """<script>
window.addEventListener('load', function () {
  var rows = [];
  document.querySelectorAll('[data-id]').forEach(function (el) {
    var r = el.getBoundingClientRect();
    rows.push(el.getAttribute('data-id') + ' w=' + (r.width / 3.7795275591).toFixed(1) +
              ' h=' + (r.height / 3.7795275591).toFixed(1));
  });
  document.querySelectorAll('.page').forEach(function (pg, i) {
    var pr = pg.getBoundingClientRect(), bottom = 0;
    Array.prototype.forEach.call(pg.children, function (el) {
      if (el.classList.contains('foot')) return;
      var r = el.getBoundingClientRect();
      if (r.height > 0 && r.bottom - pr.top > bottom) bottom = r.bottom - pr.top;
    });
    rows.push('PAGE' + (i + 1) + ' bottom=' + (bottom / 3.7795275591).toFixed(1));
  });
  var pre = document.createElement('pre');
  pre.id = 'metrics';
  pre.textContent = 'METRICS\\n' + rows.join('\\n');
  document.body.appendChild(pre);
});
</script>
"""


def find_browser(explicit=None):
    """按 显式参数 → 环境变量 → 常见安装路径 → PATH 的顺序找 Chrome/Edge。"""
    cands = []
    if explicit:
        cands.append(explicit)
    env = os.environ.get("LAB_REPORT_BROWSER")
    if env:
        cands.append(env)
    bases = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
             os.environ.get("LOCALAPPDATA")]
    for base in bases:
        if not base:
            continue
        cands.append(Path(base) / "Google/Chrome/Application/chrome.exe")
        cands.append(Path(base) / "Microsoft/Edge/Application/msedge.exe")
    for name in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        p = shutil.which(name)
        if p:
            cands.append(p)
    for c in cands:
        if c and Path(c).exists():
            return str(c)
    return None


def stage(out_dir, html_name):
    """把 HTML 和图片复制到无空格的临时目录（浏览器对含空格/中文的路径不友好）。"""
    tmp = Path(tempfile.mkdtemp(prefix="labreport_"))
    shutil.copy(out_dir / html_name, tmp / html_name)
    for png in Path(out_dir).glob("*.png"):
        shutil.copy(png, tmp / png.name)
    return tmp


def dump_dom(html_path, browser, timeout=120):
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--virtual-time-budget=6000", "--dump-dom", Path(html_path).as_uri()]
    if not Path(html_path).exists():
        raise FileNotFoundError(html_path)
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return proc.stdout


def measure(html_path, browser):
    """返回 ({id: (w_mm, h_mm)}, [(page_no, bottom_mm)])。"""
    dom = dump_dom(html_path, browser)
    m = re.search(r'<pre id="metrics">(.*?)</pre>', dom, re.S)
    if not m:
        raise RuntimeError("页面里没有找到 metrics 结果——检查 HTML 是否注入了测量脚本")
    text = htmllib.unescape(m.group(1))
    els, pages = {}, []
    for line in text.splitlines():
        line = line.strip()
        mm = re.match(r"^PAGE(\d+)\s+bottom=([\d.]+)$", line)
        if mm:
            pages.append((int(mm.group(1)), float(mm.group(2))))
            continue
        mm = re.match(r"^(\S+)\s+w=([\d.]+)\s+h=([\d.]+)$", line)
        if mm:
            els[mm.group(1)] = (float(mm.group(2)), float(mm.group(3)))
    return els, pages


def collect_expectations(data):
    """从 data.json 收集每个表/图应有的尺寸或宽高比。"""
    exp = {}
    for pi, page in enumerate(data["pages"]):
        for bi, b in enumerate(page.get("blocks", [])):
            bid = b.get("id") or "p%db%d" % (pi + 1, bi + 1)
            if b["type"] == "table":
                exp[bid] = {"kind": "table", "min": b.get("minAspect"),
                            "max": b.get("maxAspect"), "page": pi + 1}
            elif b["type"] == "figure":
                w = b.get("widthMm", 136.0)
                h = b.get("heightMm") or w / parse_aspect(b.get("aspect", 16 / 9))
                exp[bid] = {"kind": "figure", "w": w, "h": h, "page": pi + 1}
    return exp


def parse_aspect(a):
    if isinstance(a, str) and ":" in a:
        x, y = a.split(":")
        return float(x) / float(y)
    return float(a)


def verify(expectations, els, pages, page_count, page_h, bottom_limit):
    """返回 (ok, 文本行列表)。"""
    lines, ok = [], True
    for bid, spec in expectations.items():
        if bid not in els:
            lines.append("[!!] %-6s 未在页面上找到（是否被裁掉？）" % bid)
            ok = False
            continue
        w, h = els[bid]
        if spec["kind"] == "table":
            ratio = w / h if h else 0
            lo, hi = spec["min"], spec["max"]
            if lo is None and hi is None:
                lines.append("[ok] %-6s %.1f x %.1f mm（宽高比 %.2f）" % (bid, w, h, ratio))
            elif lo is not None and (ratio < lo - 0.02 or (hi and ratio > hi + 0.02)):
                lines.append("[!!] %-6s %.1f x %.1f mm，宽高比 %.2f，不在 %s~%s 内"
                             % (bid, w, h, ratio, lo, hi))
                ok = False
            else:
                lines.append("[ok] %-6s %.1f x %.1f mm，宽高比 %.2f（需 %s~%s）"
                             % (bid, w, h, ratio, lo, hi))
        else:
            dw, dh = abs(w - spec["w"]), abs(h - spec["h"])
            if dw > 1.0 or dh > 1.0:
                lines.append("[!!] %-6s %.1f x %.1f mm，应为 %.1f x %.1f mm"
                             % (bid, w, h, spec["w"], spec["h"]))
                ok = False
            else:
                lines.append("[ok] %-6s %.1f x %.1f mm（目标 %.1f x %.1f）"
                             % (bid, w, h, spec["w"], spec["h"]))
    if len(pages) != page_count:
        lines.append("[!!] 实际 %d 页，应为 %d 页" % (len(pages), page_count))
        ok = False
    for no, bottom in pages:
        if bottom > bottom_limit + 0.5:
            lines.append("[!!] 第 %d 页内容底部 %.1f mm，超出可用高度 %.1f mm（溢出会被裁掉）"
                         % (no, bottom, bottom_limit))
            ok = False
        else:
            lines.append("[ok] 第 %d 页内容底部 %.1f mm（上限 %.1f）" % (no, bottom, bottom_limit))
    return ok, lines


def paper_geometry(data):
    paper = data.get("paper", {})
    w = float(paper.get("widthMm", 176))
    h = float(paper.get("heightMm", 250))
    margin = paper.get("marginMm", 20)
    if isinstance(margin, dict):
        bottom = float(margin.get("bottom", 20))
    else:
        bottom = float(margin)
    return w, h, bottom


def main():
    exp = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    data = json.loads((exp / "data.json").read_text(encoding="utf-8"))
    html = exp / "out" / "report.html"
    browser = find_browser()
    if not browser:
        raise SystemExit("[错误] 找不到 Chrome / Edge，可用 --browser 指定")
    tmp = stage(html.parent, html.name)
    try:
        els, pages = measure(tmp / html.name, browser)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    pw, ph, mb = paper_geometry(data)
    ok, lines = verify(collect_expectations(data), els, pages,
                       len(data["pages"]), ph, ph - mb)
    print("\n".join(lines))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
