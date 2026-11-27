"""clean.py —— 语料清洗

规则按顺序作用在 doc["text"] 上，后面加规则只改 clean_text()。

用法：
    python clean.py --input data/raw.jsonl --output data/clean.jsonl
"""
import argparse
import json
from pathlib import Path

# 句子结束符：遇到这些结尾，说明上一行是完整句子，不该和下一行合并
SENT_END = (".", "?", "!", ":", ";", "。", "？", "！", "：", "；")

def is_fragment(line:str) -> bool:
    s = line.strip()
    if len(s) < 6:
        return True
    tokens = s.split()
    if len(tokens) >= 3 and len(set(tokens)) <=2:
        return True
    alnum = sum(1 for ch in s if ch.isalnum())
    return alnum / len(s) < 0.5

def remove_fragment(text:str) -> str:
    lines = text.split("\n")
    kept = [ln for ln in lines if not is_fragment(ln)]
    removed = len(lines) - len(kept)
    return "\n".join(kept)


def should_join(prev: str, cur: str) -> bool:
    """判断 cur 是否应该拼到 prev 后面。"""
    if not prev:
        return False
    if prev.endswith(SENT_END):
        return False          # 上一行已经是完整句子
    if cur[:1].isupper():
        return False          # 下一行是新句子开头
    return True


def merge_broken_lines(text: str) -> str:
    """把被 PDF 硬换行切断的句子拼回去。"""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    out = []
    for ln in lines:
        if out and should_join(out[-1], ln):
            out[-1] = out[-1] + " " + ln      # 合并，不是新建行
        else:
            out.append(ln)
    return "\n".join(out)


def clean_text(text: str) -> str:
    """所有清洗规则按顺序作用。新规则加在这里。"""
    text = remove_fragment(text)
    text = merge_broken_lines(text)
    return text


def main():
    p = argparse.ArgumentParser(description="语料清洗")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    if not args.input.exists():
        print(f"文件不存在：{args.input}")
        return 1

    docs = []
    lines_before = lines_after = 0

    for line in args.input.open("r", encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)

        old = d.get("text", "")
        new = clean_text(old)

        lines_before += old.count("\n") + 1
        lines_after += new.count("\n") + 1

        d["text"] = new
        docs.append(d)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"总行数: {lines_before} -> {lines_after}  (减少 {lines_before - lines_after})")
    print(f"写入 {len(docs)} 条 -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
