"""chunking.py —— 把长文档切成固定规模的块（共用模块）

split_chunks.py 和 make_dedup_test.py 都 import 这里的函数，
保证"真实管线"和"测试集"用的是同一套切块逻辑。
"""

CHUNK_MIN = 400        # 每块最少字符数


def chunk_docs(docs, chunk_min: int = CHUNK_MIN):
    """把每篇文档按行累积切成约 chunk_min 字符的块。

    返回列表，每条是 {"id", "source", "text"}。
    """
    chunks = []
    for d in docs:
        buf, size, idx = [], 0, 0

        def flush():
            nonlocal buf, size, idx
            if buf:
                chunks.append({
                    "id": f'{d["id"]}-c{idx}',
                    "source": d.get("source", ""),
                    "text": " ".join(buf),
                })
                idx += 1
                buf, size = [], 0

        for line in d.get("text", "").split("\n"):
            line = line.strip()
            if not line:
                continue
            buf.append(line)
            size += len(line)
            if size >= chunk_min:
                flush()
        flush()

    return chunks
