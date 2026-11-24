"""tool.py —— 读取 jsonl，输出字段分布报告（markdown）   【参考实现版】

用法：
    python tool.py --input data/sample.jsonl --output reports/sample_report.md

四条验收：
1. python tool.py --help 能打印参数说明
2. 正常跑完，退出码 0
3. report.md 有真实内容：字段分布、缺失率、text 长度统计、唯一值个数
4. 输入文件不存在时不崩溃，打印人能看懂的错误并返回非零退出码
"""
import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# 用于统计唯一值个数的字段（短字段才有意义）
LOW_CARDINALITY_FIELDS = ("source", "lang", "doc_type")


def load_records(path: Path):
    """逐行流式读取 jsonl，坏行跳过并告警。"""
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                log.warning("第 %d 行不是合法 JSON，跳过", i)


def summarize(records):
    """统计字段分布。"""
    n = len(records)
    present = Counter()        # 字段出现且非空的次数
    types = defaultdict(Counter)   # 字段 -> 类型 -> 次数
    low_card = defaultdict(Counter)  # 短字段 -> 值 -> 次数
    lens = []

    for r in records:
        for k, v in r.items():
            if v not in (None, "", [], {}):
                present[k] += 1
            types[k][type(v).__name__] += 1
            if k in LOW_CARDINALITY_FIELDS and isinstance(v, (str, int)):
                low_card[k][str(v)] += 1
            if k == "text" and isinstance(v, str):
                lens.append(len(v))

    text_stat = None
    if lens:
        text_stat = {
            "count": len(lens),
            "min": min(lens),
            "avg": sum(lens) / len(lens),
            "max": max(lens),
        }

    return {
        "total": n,
        "fields": {
            k: {
                "present": present[k],
                "missing": n - present[k],
                "types": dict(types[k]),
                "unique": (
                    len(low_card[k]) if k in LOW_CARDINALITY_FIELDS else None
                ),
                "top": low_card[k].most_common(5) if k in LOW_CARDINALITY_FIELDS else None,
            }
            for k in types
        },
        "text": text_stat,
    }


def render_markdown(summary, src: Path) -> str:
    """把 summary 渲染成 markdown 字符串。"""
    total = summary["total"]
    lines = [f"# 数据概况：`{src.name}`", ""]
    lines.append(f"- 总条数：**{total}**")
    lines.append(f"- 字段数：**{len(summary['fields'])}**")
    lines.append("")

    lines.append("## 字段分布")
    lines.append("")
    lines.append("| 字段 | 出现次数 | 缺失数 | 缺失率 | 唯一值 | 类型 |")
    lines.append("|---|---|---|---|---|---|")
    for k, v in summary["fields"].items():
        rate = v["missing"] / total * 100 if total else 0
        types = ", ".join(f"{t}({c})" for t, c in v["types"].items())
        unique = v["unique"] if v["unique"] is not None else "-"
        lines.append(
            f"| {k} | {v['present']} | {v['missing']} | {rate:.1f}% | {unique} | {types} |"
        )
    lines.append("")

    tops = {k: v["top"] for k, v in summary["fields"].items() if v["top"]}
    if tops:
        lines.append("## 取值 Top 5")
        lines.append("")
        for k, pairs in tops.items():
            s = "、".join(f"{val}({c})" for val, c in pairs)
            lines.append(f"- **{k}**：{s}")
        lines.append("")

    text = summary["text"]
    if text:
        lines.append("## text 字段长度")
        lines.append("")
        lines.append(f"- 样本数：{text['count']}")
        lines.append(f"- 最小：{text['min']}")
        lines.append(f"- 平均：{text['avg']:.1f}")
        lines.append(f"- 最大：{text['max']}")
        lines.append("")

    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="统计 jsonl 字段分布，输出 markdown 报告")
    p.add_argument("--input", required=True, type=Path, help="输入 jsonl 文件")
    p.add_argument("--output", required=True, type=Path, help="输出 markdown 文件")
    args = p.parse_args(argv)

    if not args.input.exists():
        log.error("输入文件不存在：%s", args.input)
        return 1
    if not args.input.is_file():
        log.error("输入路径不是文件：%s", args.input)
        return 1

    log.info("读取 %s", args.input)
    records = list(load_records(args.input))
    if not records:
        log.error("没有读到任何有效记录：%s", args.input)
        return 1
    log.info("读到 %d 条记录", len(records))

    summary = summarize(records)
    md = render_markdown(summary, args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    log.info("报告已写入 %s", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
