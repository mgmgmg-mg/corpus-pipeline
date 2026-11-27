"""text_quality.py —— 文本质量诊断

用法：
    python text_quality.py --input data/raw.jsonl

指标含义：
    short_ratio   短行（<20 字）占比  → 断行严重程度
    cn_ratio      中文字符占比        → 编码是否正常
    symbol_ratio  符号占比            → 公式/乱码多少
    dup_ratio     重复行占比          → 页眉页脚嫌疑
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

CN_RE = re.compile(r"[\u4e00-\u9fff]")      # 中文
WORD_RE = re.compile(r"[A-Za-z0-9]")        # 字母数字


def load_records(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"第 {i} 行不是合法 JSON，跳过")


def analyze(text: str) -> dict:
    lines = text.split("\n")
    non_empty = [ln.strip() for ln in lines if ln.strip()]
    n_lines = len(non_empty) or 1
    chars = len(text)

    # 断行信号：短行占比
    short = sum(1 for ln in non_empty if len(ln) < 20)

    # 编码信号：中文字符占比
    cn = len(CN_RE.findall(text))

    # 乱码/公式信号：既非中文也非字母数字的字符占比
    symbol = sum(
        1
        for ch in text
        if not CN_RE.match(ch) and not WORD_RE.match(ch) and not ch.isspace()
    )

    # 页眉页脚信号：重复行
    counter = Counter(non_empty)
    dup = sum(c - 1 for c in counter.values() if c > 1)

    return {
        "chars": chars,
        "lines": len(lines),
        "avg_line_len": round(chars / n_lines, 1),
        "short_ratio": round(short / n_lines, 3),
        "cn_ratio": round(cn / chars, 3) if chars else 0,
        "symbol_ratio": round(symbol / chars, 3) if chars else 0,
        "dup_ratio": round(dup / n_lines, 3),
        "top_lines": [(ln[:40], c) for ln, c in counter.most_common(3)],
    }


def main():
    p = argparse.ArgumentParser(description="文本质量诊断")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--min-chars", type=int,default=0)
    args = p.parse_args()

    if not args.input.exists():
        print(f"文件不存在：{args.input}")
        return 1

    print("| 文档 | chars | lines | avg_line_len | short_ratio | cn_ratio | symbol_ratio | dup_ratio |")
    print("|---|---|---|---|---|---|---|---|")

    details = []
    for d in load_records(args.input):
        s = analyze(d.get("text", ""))
        if s["chars"]<args.min_chars:
            continue
        details.append((d.get("id", "?"), s))
        print(
            f"| {d.get('id', '?')} | {s['chars']} | {s['lines']} | "
            f"{s['avg_line_len']} | {s['short_ratio']} | {s['cn_ratio']} | "
            f"{s['symbol_ratio']} | {s['dup_ratio']} |"
        )

    print("\n## 重复最多的行（页眉页脚嫌疑）")
    for doc_id, s in details:
        print(f"\n**{doc_id}**")
        for line, c in s["top_lines"]:
            print(f"- ({c} 次) {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
