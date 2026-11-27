#!/usr/bin/env bash
# 语料管线：清洗 -> 切块 -> 去重 -> 漏斗
#
# 用法：
#   bash run_pipeline.sh
#
# 前提：data/raw.jsonl 已存在（由 build_raw.py 生成）
set -euo pipefail
cd "$(dirname "$0")"

echo "========== 1/4 清洗 =========="
python clean.py --input data/raw.jsonl --output data/clean.jsonl

echo
echo "========== 2/4 切块 =========="
python split_chunks.py --input data/clean.jsonl --output data/chunks.jsonl

echo
echo "========== 3/4 去重 =========="
python dedup.py \
  --input data/chunks.jsonl \
  --output data/final.jsonl \
  --threshold 0.8 \
  --shingle-type char \
  --no-eval

echo
echo "========== 4/4 漏斗 =========="
python funnel.py \
  --stage 原始:data/raw.jsonl \
  --stage 清洗:data/clean.jsonl \
  --stage 切块:data/chunks.jsonl \
  --stage 去重:data/final.jsonl

echo
echo "管线完成。产出 data/final.jsonl"
