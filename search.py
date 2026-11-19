#!/usr/bin/env python3
"""向量检索：默认只搜主线 1~4 章，防止剧透。
用法:
    python3 search.py "戒指"              # 默认：主线 1~4 章
    MAX_MAIN=6 python3 search.py "霜星"   # 放宽到第 6 章
    MODE=event python3 search.py "戒指"   # 搜活动
    MODE=all python3 search.py "戒指"     # 全量（慎用）
"""
import os, sys, json, re, urllib.request
import numpy as np

INDEX   = os.path.expanduser("~/ark_index.npz")
EMB_URL = "http://127.0.0.1:8000/v1/embeddings"

MAX_MAIN = int(os.environ.get("MAX_MAIN", "4"))
MODE     = os.environ.get("MODE", "main")      # main | event | all
TOP_K    = int(os.environ.get("TOP_K", "5"))

def embed(text):
    payload = json.dumps({"input": [text]}).encode("utf-8")
    req = urllib.request.Request(EMB_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    v = np.asarray(data["data"][0]["embedding"], dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v

def chapter_num(src):
    """从 level_main_04-01_beg_003... 提取 4"""
    m = re.search(r'level_main_(\d+)-', src)
    return int(m.group(1)) if m else None

def allowed(src):
    is_main = src.startswith("level_main_")
    if MODE == "all":
        return True
    if MODE == "event":
        return not is_main          # 活动/密录等
    # MODE == main
    if not is_main:
        return False
    n = chapter_num(src)
    return n is not None and n <= MAX_MAIN

def main():
    if not os.path.exists(INDEX):
        sys.exit(f"索引不存在：{INDEX}")
    d = np.load(INDEX, allow_pickle=True)
    vecs, texts, sources = d["vecs"], d["texts"], d["sources"]

    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("查询 > ")
    qv = embed(q)
    scores = vecs @ qv

    # 先按分数排序，再过滤，取前 TOP_K
    order = np.argsort(-scores)
    picked = []
    for i in order:
        src = str(sources[i])
        if allowed(src):
            picked.append(i)
        if len(picked) >= TOP_K:
            break

    scope = {"main": f"主线 1~{MAX_MAIN} 章", "event": "活动/密录", "all": "全量"}[MODE]
    print(f"\n查询：{q}    [范围: {scope}]\n")
    if not picked:
        print("（该范围内没有匹配）")
        return

    for rank, i in enumerate(picked, 1):
        src = str(sources[i])
        chapter = src
        if "【" in src and "】" in src:
            chapter = src[src.index("【"):src.index("】")+1]
        body = str(texts[i])
        print(f"[{rank}] score={scores[i]:.4f}  {chapter}")
        print(f"    {src}")
        print("    " + body.replace("\n", "\n    ")[:800])
        print()

if __name__ == "__main__":
    main()
