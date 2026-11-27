# corpus-pipeline

大模型训练语料处理管线：从非结构化文档（PDF）到可去重的语料块，附质量诊断与去重评测。

## 数据流

```
arXiv PDF ×3
   │  build_raw.py      pdfplumber 解析
   ▼
raw.jsonl         3 条 · 310,864 字符
   │  clean.py          删图表碎片 → 合并硬换行
   ▼
clean.jsonl       3 条 · 306,358 字符（保留 98.6%）
   │  split_chunks.py   按 400 字符切块
   ▼
chunks.jsonl    533 块 · 305,828 字符（平均 574 字符/块）
   │  dedup.py          精确哈希 → MinHash + LSH
   ▼
final.jsonl     533 块（真实数据无重复）
```

## 关键结果

### 清洗效果（文本质量诊断，`text_quality.py`）

| 文档 | 行数 | 短行占比 | 平均行长 | 重复行占比 |
|---|---|---|---|---|
| attention 原始 | 871 | 0.467 | 40.8 | 0.297 |
| attention 清洗后 | 211 | **0.066** | **162.6** | **0.014** |
| bert 原始 | 1170 | 0.116 | 52.6 | 0.038 |
| bert 清洗后 | 428 | 0.056 | 141.3 | 0.000 |
| gpt3 原始 | 2895 | 0.095 | 73.9 | 0.024 |
| gpt3 清洗后 | 1341 | 0.051 | 157.8 | 0.018 |

行数减少 60%（4936 → 1980），字符仅减少 1.4%——删除的是占行数但字符极少的图表碎片。

### 去重效果

构造 833 条测试集（533 条原始块 + 100 条完全复制 + 200 条扰动复制）：

| 配置 | 精确复制召回 | 扰动复制召回 | 整体召回 | 精确率 | 误删 |
|---|---|---|---|---|---|
| word 5-gram, θ=0.8 | 100/100 | 139/200 (69.5%) | 79.7% | 100% | 0 |
| char 5-gram, θ=0.7 | 100/100 | 200/200 (100%) | 100% | 100% | 0 |
| **char 5-gram, θ=0.8** | **100/100** | **200/200 (100%)** | **100%** | **100%** | **0** |
| char 5-gram, θ=0.9 | 100/100 | 182/200 (91%) | 94% | 100% | 0 |

**结论**：字符级 5-gram 显著优于词级（召回 100% vs 69.5%），因为词级 shingle 对插入操作位置敏感——插入一个词会让其后所有 shingle 错位。

阈值 0.9 时漏抓 18 条，原因是 LSH 分桶的概率性（阈值附近的 S 曲线），而非相似度不足；选 0.8 留出余量。

## 复现

```bash
# 环境：Python 3.14 + pandas / pyarrow / pdfplumber / beautifulsoup4 / datasketch
pip install pandas pyarrow tqdm pdfplumber beautifulsoup4 requests datasets datasketch

# 1. 下载 PDF
mkdir -p data/pdf
curl -L -o data/pdf/attention.pdf https://arxiv.org/pdf/1706.03762
curl -L -o data/pdf/bert.pdf      https://arxiv.org/pdf/1810.04805
curl -L -o data/pdf/gpt3.pdf      https://arxiv.org/pdf/2005.14165

# 2. 解析
python build_raw.py

# 3. 整条管线
bash run_pipeline.sh

# 4. 质量诊断
python text_quality.py --input data/raw.jsonl
python text_quality.py --input data/clean.jsonl

# 5. 去重评测
python make_dedup_test.py
python dedup.py --input data/dedup_test.jsonl --output data/dedup_out.jsonl
```

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_raw.py` | PDF/网页解析，统一 schema |
| `tool.py` | jsonl 字段分布统计，生成 markdown 报告 |
| `text_quality.py` | 文本质量诊断（断行/乱码/重复行） |
| `clean.py` | 清洗规则：删碎片 → 合并断行 |
| `chunking.py` | 切块逻辑（共用模块） |
| `split_chunks.py` | 文档切块 |
| `dedup.py` | 两级去重 + 评测 |
| `make_dedup_test.py` | 构造带已知重复的测试集 |
| `funnel.py` | 生成管线漏斗表 |
| `run_pipeline.sh` | 串联整条管线 |

## 已知限制

- 仅 3 篇**英文**论文，未在中文语料上验证（`cn_ratio` 指标尚无效）
- 网页源未接入：arXiv 可访问，但 wikipedia 在本地网络不可达
- attention 论文仍有图表碎片残留（如 `Input-Input Layer5 tcefrep tcefrep noita`，为图中文字倒序抽取），规则无法识别
- PDF 抽取存在词间空格丢失（`Providedproperattributionisprovided`），未处理
- 无断点续跑机制，处理上千个 PDF 需补上
- 单进程，未做并行
