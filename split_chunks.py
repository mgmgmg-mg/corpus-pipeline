"""split_chunks.py —— 把清洗后的文档切成块（正式管线的第 3 步）

用法：
    python split_chunks.py --input data/clean.jsonl --output data/chunks.jsonl
"""
import argparse
import json
from pathlib import Path

from chunking import chunk_docs


def main():
    p = argparse.ArgumentParser(description="文档切块")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--chunk-min", type=int, default=400)
    args = p.parse_args()

    if not args.input.exists():
        print(f"文件不存在：{args.input}")
        return 1

    docs = [json.loads(l) for l in args.input.open(encoding="utf-8") if l.strip()]
    chunks = chunk_docs(docs, args.chunk_min)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    avg = sum(len(c["text"]) for c in chunks) / len(chunks) if chunks else 0
    print(f"{len(docs)} 篇文档 -> {len(chunks)} 块（平均 {avg:.0f} 字符）")
    print(f"写入 -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
