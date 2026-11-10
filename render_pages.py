# -*- coding: utf-8 -*-
"""把 PDF 每页导出成 PNG，方便肉眼检查排版。

    python render_pages.py out/xxx.pdf            # 默认 110 dpi
    python render_pages.py out/xxx.pdf --dpi 200
"""
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="PDF 逐页转 PNG")
    ap.add_argument("pdf")
    ap.add_argument("-o", "--outdir", help="输出目录，默认与 PDF 同级的 pages/")
    ap.add_argument("--dpi", type=int, default=110)
    args = ap.parse_args()

    try:
        import pymupdf
    except ImportError:
        raise SystemExit("[错误] 需要 pymupdf：pip install pymupdf")

    pdf = Path(args.pdf).resolve()
    outdir = Path(args.outdir) if args.outdir else pdf.parent / "pages"
    outdir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf) as doc:
        for page in doc:
            path = outdir / ("%s_p%d.png" % (pdf.stem, page.number + 1))
            page.get_pixmap(dpi=args.dpi).save(path)
            print(path)
        total = len(doc)
    print("共 %d 页" % total)


if __name__ == "__main__":
    main()
