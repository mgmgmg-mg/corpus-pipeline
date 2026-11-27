"""make_dedup_test.py —— 构造带已知重复的去重测试集

做法：
  1. 读 data/clean.jsonl，切成约 400 字符的块（复用 chunking.py）
  2. 注入 100 条「完全复制」+ 200 条「轻微扰动复制」
  3. 输出：
       data/dedup_test.jsonl   待去重的语料（含重复）
       data/dedup_truth.json   真值：哪些 id 是重复的

用法：
    python make_dedup_test.py
"""
import json
import random
from pathlib import Path

from chunking import CHUNK_MIN, chunk_docs

N_EXACT = 100          # 完全复制的条数
N_NEAR = 200           # 扰动复制的条数
SEED = 42              # 固定种子，结果可复现


def perturb(text, rng):
    """对文本做轻微扰动，相似度保持 95% 以上。"""
    kind = rng.choice(["prefix", "suffix", "insert", "truncate", "punct"])

    if kind == "prefix":
        return "[DUP] " + text
    if kind == "suffix":
        return text + " (source: arxiv)"
    if kind == "insert":
        i = rng.randrange(len(text)) if text else 0
        return text[:i] + " however" + text[i:]
    if kind == "truncate":
        return text[: max(10, int(len(text) * 0.95))]
    return text.replace(".", "。", 1)


def main():
    random.seed(SEED)

    src = Path("data/clean.jsonl")
    if not src.exists():
        print(f"找不到 {src}，先把 clean.py 跑一遍")
        return 1

    docs = [json.loads(l) for l in src.open(encoding="utf-8") if l.strip()]
    chunks = chunk_docs(docs)
    print(f"切成 {len(chunks)} 块，平均 {sum(len(c['text']) for c in chunks)/len(chunks):.0f} 字符/块")

    pool = [c for c in chunks if len(c["text"]) >= CHUNK_MIN]
    random.shuffle(pool)

    truth = {"exact": [], "near": []}
    out = list(chunks)

    for i, c in enumerate(pool[:N_EXACT]):
        new_id = f'{c["id"]}-exact{i}'
        out.append({"id": new_id, "source": c["source"], "text": c["text"]})
        truth["exact"].append({"dup": new_id, "orig": c["id"]})

    for i, c in enumerate(pool[N_EXACT: N_EXACT + N_NEAR]):
        new_id = f'{c["id"]}-near{i}'
        out.append({
            "id": new_id,
            "source": c["source"],
            "text": perturb(c["text"], random),
        })
        truth["near"].append({"dup": new_id, "orig": c["id"]})

    random.shuffle(out)

    out_path = Path("data/dedup_test.jsonl")
    with out_path.open("w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    truth_path = Path("data/dedup_truth.json")
    truth_path.write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"写入 {len(out)} 条 -> {out_path}")
    print(f"  其中 精确复制 {len(truth['exact'])} 条，扰动复制 {len(truth['near'])} 条")
    print(f"真值 -> {truth_path}")
    print(f"\n去重的理论上限：{len(out)} 条里应识别出 {N_EXACT + N_NEAR} 条重复")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
