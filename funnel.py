"""funnel.py —— 生成数据管线漏斗表

用法：
    python funnel.py \
        --stage 原始:data/raw.jsonl \
        --stage 清洗:data/clean.jsonl \
        --stage 去重:data/final.jsonl

    # 输出 markdown 表格（贴进 README）
    python funnel.py --stage 原始:data/raw.jsonl --stage 清洗:data/clean.jsonl --markdown
"""
import argparse
import json
from pathlib import Path


def stats(path: Path):
    """返回 (条数, 总字符数)。"""
    n = 0
    chars = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            n += 1
            chars += len(d.get("text", ""))
    return n, chars


def main():
    p = argparse.ArgumentParser(description="生成管线漏斗表")
    p.add_argument(
        "--stage", action="append", required=True, metavar="名称:路径",
        help="可重复，按顺序给出管线各阶段",
    )
    p.add_argument("--markdown", action="store_true", help="输出 markdown 表格")
    args = p.parse_args()

    rows = []
    for s in args.stage:
        if ":" not in s:
            print(f"格式错误（应为 名称:路径）：{s}")
            return 1
        name, path_str = s.split(":", 1)
        path = Path(path_str)
        if not path.exists():
            print(f"文件不存在：{path}")
            return 1
        n, chars = stats(path)
        rows.append((name, n, chars))

    base_n, base_c = rows[0][1], rows[0][2]

    if args.markdown:
        print("| 阶段 | 条数 | 条数保留率 | 字符数 | 字符保留率 |")
        print("|---|---|---|---|---|")
        for name, n, chars in rows:
            rn = n / base_n * 100 if base_n else 0
            rc = chars / base_c * 100 if base_c else 0
            print(f"| {name} | {n} | {rn:.1f}% | {chars} | {rc:.1f}% |")
    else:
        print(f"{'阶段':<10}{'条数':>8}{'条数保留':>10}{'字符数':>12}{'字符保留':>10}")
        print("-" * 52)
        for name, n, chars in rows:
            rn = n / base_n * 100 if base_n else 0
            rc = chars / base_c * 100 if base_c else 0
            print(f"{name:<10}{n:>8}{rn:>9.1f}%{chars:>12}{rc:>9.1f}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
