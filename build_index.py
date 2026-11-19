#!/usr/bin/env python3
"""把 ark_story_chunks 下的 txt 全部嵌入，存成 npz 索引。"""
import os, sys, json, glob, time, urllib.request
import numpy as np

CHUNK_DIR = os.path.expanduser("~/ark_story_chunks")
OUT_NPY   = os.path.expanduser("~/ark_index.npz")
EMB_URL   = "http://127.0.0.1:8000/v1/embeddings"
BATCH     = 32

def embed_batch(texts):
    payload = json.dumps({"input": texts}).encode("utf-8")
    req = urllib.request.Request(EMB_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [d["embedding"] for d in data["data"]]

def main():
    files = sorted(glob.glob(os.path.join(CHUNK_DIR, "*.txt")))
    print(f"找到 {len(files)} 个文件", flush=True)
    if not files:
        sys.exit("目录为空，检查路径")

    all_vecs, all_texts, all_sources = [], [], []
    t0 = time.time()
    for i in range(0, len(files), BATCH):
        batch_files = files[i:i+BATCH]
        batch_texts = []
        for f in batch_files:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                batch_texts.append(fh.read().strip())
        vecs = embed_batch(batch_texts)
        all_vecs.extend(vecs)
        all_texts.extend(batch_texts)
        all_sources.extend([os.path.basename(f) for f in batch_files])
        done = min(i+BATCH, len(files))
        if done % 320 == 0 or done == len(files):
            el = time.time() - t0
            speed = done / el if el > 0 else 0
            eta = (len(files) - done) / speed if speed > 0 else 0
            print(f"{done}/{len(files)}  {speed:.1f} files/s  ETA {eta/60:.1f} min", flush=True)

    mat = np.asarray(all_vecs, dtype=np.float32)
    # 归一化，检索时直接点积即余弦
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms

    np.savez_compressed(OUT_NPY,
                        vecs=mat,
                        texts=np.array(all_texts, dtype=object),
                        sources=np.array(all_sources, dtype=object))
    print(f"\n完成：{mat.shape[0]} 条，维度 {mat.shape[1]}")
    print(f"已保存 {OUT_NPY}  ({os.path.getsize(OUT_NPY)/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
