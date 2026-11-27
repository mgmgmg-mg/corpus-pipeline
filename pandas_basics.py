"""pandas_basics.py —— pandas 五个基础练习

数据：data/sample.jsonl（1000 条，字段 id / source / lang / text）
运行：python pandas_basics.py
前提：必须在 corpus-pipeline 目录下运行（相对路径依赖当前目录）
"""
import pandas as pd

# ============================================================
# 0. 读数据
# ============================================================
df = pd.read_json("data/sample.jsonl", lines=True)

print("=" * 62)
print("数据概况")
print("=" * 62)
print("形状:", df.shape)
print("列名:", df.columns.tolist())


# ============================================================
# 练习 1：每个 source 的条数与占比
# ============================================================
print("\n" + "=" * 62)
print("练习 1：每个 source 的条数与占比")
print("=" * 62)

col = df["source"]

print("次数:")
print(col.value_counts())

print("\n占比:")
print(col.value_counts(normalize=True).round(3))

print("\n唯一值个数:", col.nunique())

# 验证：normalize 就是 次数 / 总和
print("\n手算（次数 ÷ 总和），应与上面占比一致:")
c = col.value_counts()
print((c / c.sum()).round(3))


# ============================================================
# 练习 2：每个 source 的 text 平均长度与最大长度
# ============================================================
print("\n" + "=" * 62)
print("练习 2：每个 source 的 text 平均长度与最大长度")
print("=" * 62)

# ① 先加一列长度，打印出来人工核对
df2 = df.assign(text_len=df["text"].str.len())
print(df2[["source", "text", "text_len"]].head(3))

# ② 再分组聚合
result = df2.groupby("source").agg(
    n=("id", "size"),
    avg_len=("text_len", "mean"),
    max_len=("text_len", "max"),
)

print()
print(result.round(1))
print()
print("自查：n 列应等于练习 1 的次数（315 / 355 / 330）")
print("自查：max_len 应为 160（每个词 2 字，最多 80 个词）")


# ============================================================
# 练习 3：每列缺失率（降序）
# ============================================================
print("\n" + "=" * 62)
print("练习 3：每列缺失率（降序）")
print("=" * 62)

missing = df.isna().mean().sort_values(ascending=False)
print(missing.round(3))

# 加一版更像报告的表格
missing_table = pd.DataFrame(
    {
        "缺失条数": df.isna().sum(),
        "缺失率": df.isna().mean().round(3),
    }
).sort_values("缺失率", ascending=False)

print()
print(missing_table)
print()
print("自查：lang 应为 143 / 0.143，text 应为 91 / 0.091，与 tool.py 报告一致")


# ============================================================
# 练习 4：lang == 'zh' 且 text 长度 > 50 的条数
# ============================================================
print("\n" + "=" * 62)
print("练习 4：lang == 'zh' 且 text 长度 > 50 的条数")
print("=" * 62)

cond = (df["lang"] == "zh") & (df["text"].str.len() > 50)
sub = df[cond]

print("条数:", len(sub))
print("lang 取值:", sub["lang"].unique())
print("最短 text:", sub["text"].str.len().min())
print("最长 text:", sub["text"].str.len().max())

# 反向验证：子集不可能大于全集
total_zh = (df["lang"] == "zh").sum()
print("\nzh 总数:", total_zh, "（必须 ≥ 上面的条数）")


# ============================================================
# 练习 5：merge 映射表，把 lang 翻译成中文名
# ============================================================
print("\n" + "=" * 62)
print("练习 5：merge 映射表")
print("=" * 62)

mapping = pd.DataFrame(
    {
        "lang_code": ["zh", "en"],
        "lang_name": ["中文", "英文"],
    }
)

merged = df.merge(mapping, left_on="lang", right_on="lang_code", how="left")

print("行数变化:", len(df), "->", len(merged), "（how='left' 不丢行）")
print("列数变化:", df.shape[1], "->", merged.shape[1])
print("列名:", merged.columns.tolist())

print()
print(merged[["id", "lang", "lang_code", "lang_name"]].head(5))

print()
print("lang_name 缺失条数:", merged["lang_name"].isna().sum())
print("lang 本身缺失条数:", df["lang"].isna().sum())
print("两者应该相等（143）——匹配不上的填 NaN")


# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 62)
print("五个练习全部跑完")
print("=" * 62)
