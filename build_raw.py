"""build_raw.py —— 把网页和 PDF 解析成统一格式的 data/raw.jsonl

运行前准备：
    mkdir -p data/pdf
    curl -L -o data/pdf/attention.pdf https://arxiv.org/pdf/1706.03762
    curl -L -o data/pdf/bert.pdf      https://arxiv.org/pdf/1810.04805
    curl -L -o data/pdf/gpt3.pdf      https://arxiv.org/pdf/2005.14165

运行：
    python build_raw.py

产出：
    data/raw.jsonl   每条含 id / source / doc_type / title / url / text / meta
"""
import json
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "corpus-pipeline/0.1 (learning project)"}

WebDoc = ("https://zh.wikipedia.org/wiki/机器学习", "wiki-机器学习", "机器学习")

PDF_DOCS = [
    ("attention.pdf", "arxiv-1706.03762", "Attention Is All You Need",
     "https://arxiv.org/abs/1706.03762"),
    ("bert.pdf", "arxiv-1810.04805", "BERT",
     "https://arxiv.org/abs/1810.04805"),
    ("gpt3.pdf", "arxiv-2005.14165", "Language Models are Few-Shot Learners",
     "https://arxiv.org/abs/2005.14165"),
]


def fetch_web(url, doc_id, title):
    """抓网页正文，去掉脚本/样式/导航等噪音。"""
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding          # 中文站必须，否则乱码

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "sup"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return {
        "id": doc_id,
        "source": "wikipedia",
        "doc_type": "html",
        "title": title,
        "url": url,
        "text": text,
        "meta": {"chars": len(text)},
    }


def parse_pdf(path, doc_id, title, url):
    """逐页抽取文本，页与页之间用换行拼接。"""
    with pdfplumber.open(path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
        n_pages = len(pdf.pages)

    text = "\n".join(pages)
    n_lines = max(len(text.split("\n")),1)
    return {
        "id": doc_id,
        "source": "arxiv",
        "doc_type": "pdf",
        "title": title,
        "url": url,
        "text": text,
        "meta": {"pages": n_pages, "chars": len(text),"avg_line_len": round(len(text)/n_lines,1)},
    }


def main():
    docs = []

    # ① 网页
    url, doc_id, title = WebDoc
    try:
        docs.append(fetch_web(url, doc_id, title))
        print("网页 OK")
    except Exception as e:  # noqa: BLE001
        print("网页失败:", type(e).__name__, e)

    # ② PDF
    for fn, doc_id, title, url in PDF_DOCS:
        p = Path("data/pdf") / fn
        if not p.exists():
            print(f"跳过（文件不存在）: {p}")
            continue
        try:
            docs.append(parse_pdf(p, doc_id, title, url))
            print(f"PDF OK: {fn}")
        except Exception as e:  # noqa: BLE001
            print(f"PDF 失败: {fn}", type(e).__name__, e)

    if not docs:
        print("什么都没解析出来，检查网络和 data/pdf/")
        return 1

    # ③ 写 jsonl
    out = Path("data/raw.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\n写入 {len(docs)} 条 -> {out}")
    for d in docs:
        print(f"  {d['id']:<22} {d['doc_type']:<5} {len(d['text']):>8} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
