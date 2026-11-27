"""dedup.py —— 两级去重

第一级：精确去重（md5 哈希，完全相同）
第二级：近重复去重（MinHash + LSH，相似度 >= 阈值）

shingle 默认用「字符级 5-gram」：对插入、改动更稳健。
词级 shingle 对位置极敏感，插入一个词会让后面所有 shingle 全变。

用法：
    python dedup.py --input data/dedup_test.jsonl --output data/dedup_out.jsonl

    # 消融实验
    python dedup.py --input data/dedup_test.jsonl --output /tmp/o.jsonl --threshold 0.9
    python dedup.py --input data/dedup_test.jsonl --output /tmp/o.jsonl --shingle-type word
"""
import argparse
import hashlib
import json
from pathlib import Path

from datasketch import MinHash, MinHashLSH


# ---------------------------------------------------------------- 切 shingle

def shingles(text: str, k: int = 5, kind: str = "char") -> set:
    """把文本切成 shingle 集合。

    kind="char": 字符级 k-gram（默认，对插入稳健）
    kind="word": 词级 k-gram（对插入敏感）
    """
    if kind == "word":
        words = text.split()
        if len(words) < k:
            return {" ".join(words)} if words else set()
        return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}

    t = "".join(text.split())          # 去掉所有空白，避免空格差异
    if len(t) <= k:
        return {t} if t else set()
    return {t[i:i + k] for i in range(len(t) - k + 1)}


# ---------------------------------------------------------------- 第一级

def exact_dedup(docs):
    seen = {}
    kept, removed = [], []

    for d in docs:
        h = hashlib.md5(d["text"].encode("utf-8")).hexdigest()
        if h in seen:
            removed.append({"id": d["id"], "reason": "exact", "dup_of": seen[h]})
        else:
            seen[h] = d["id"]
            kept.append(d)

    return kept, removed


# ---------------------------------------------------------------- 第二级

def near_dedup(docs, threshold, shingle_size, shingle_type, num_perm=128):
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes = {}
    kept, removed = [], []

    for d in docs:
        m = MinHash(num_perm=num_perm)
        for sh in shingles(d["text"], shingle_size, shingle_type):
            m.update(sh.encode("utf-8"))

        # LSH 只给「候选」，再用真实 Jaccard 确认
        dup_of = None
        for cand in lsh.query(m):
            if m.jaccard(minhashes[cand]) >= threshold:
                dup_of = cand
                break

        if dup_of:
            removed.append({"id": d["id"], "reason": "near", "dup_of": dup_of})
        else:
            lsh.insert(d["id"], m)
            minhashes[d["id"]] = m
            kept.append(d)

    return kept, removed


# ---------------------------------------------------------------- 评测（按对算）

def evaluate(removed, truth_path: Path):
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    removed_ids = {r["id"] for r in removed}

    def pair_hits(pairs):
        """一对里删掉任意一条就算命中。"""
        return sum(1 for x in pairs if x["dup"] in removed_ids or x["orig"] in removed_ids)

    # 真值里出现过的所有 id（dup 和 orig 都算"应该被考虑"的）
    truth_ids = set()
    for key in ("exact", "near"):
        for x in truth[key]:
            truth_ids.add(x["dup"])
            truth_ids.add(x["orig"])

    exact_hit = pair_hits(truth["exact"])
    near_hit = pair_hits(truth["near"])
    n_exact = len(truth["exact"])
    n_near = len(truth["near"])
    total = n_exact + n_near

    fp = removed_ids - truth_ids          # 删了不该删的
    tp = removed_ids & truth_ids

    def pct(a, b):
        return f"{a / b * 100:.1f}%" if b else "n/a"

    print("\n=== 评测（按对算）===")
    print(f"精确复制命中: {exact_hit}/{n_exact}  ({pct(exact_hit, n_exact)})")
    print(f"扰动复制命中: {near_hit}/{n_near}  ({pct(near_hit, n_near)})")
    print(f"整体召回:     {exact_hit + near_hit}/{total}  ({pct(exact_hit + near_hit, total)})")
    print(f"精确率:       {len(tp)}/{len(removed_ids)}  ({pct(len(tp), len(removed_ids))})")
    print(f"误删（与真值无关）: {len(fp)} 条")


# ---------------------------------------------------------------- 主流程

def main():
    p = argparse.ArgumentParser(description="两级去重")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--truth", type=Path, default=Path("data/dedup_truth.json"))
    p.add_argument("--threshold", type=float, default=0.8)
    p.add_argument("--shingle-size", type=int, default=5)
    p.add_argument("--shingle-type", choices=["char", "word"], default="char")
    args = p.parse_args()

    if not args.input.exists():
        print(f"文件不存在：{args.input}")
        return 1

    docs = [json.loads(l) for l in args.input.open(encoding="utf-8") if l.strip()]
    total = len(docs)
    print(f"输入 {total} 条")

    kept, removed_exact = exact_dedup(docs)
    print(f"\n=== 精确去重 ===")
    print(f"{total} -> {len(kept)}   删除 {len(removed_exact)}")

    kept2, removed_near = near_dedup(
        kept, args.threshold, args.shingle_size, args.shingle_type
    )
    print(f"\n=== 近重复去重（阈值 {args.threshold}，{args.shingle_type} {args.shingle_size}-gram）===")
    print(f"{len(kept)} -> {len(kept2)}   删除 {len(removed_near)}")

    if args.truth.exists():
        evaluate(removed_exact + removed_near, args.truth)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for d in kept2:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\n写入 {len(kept2)} 条 -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
