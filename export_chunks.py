#!/usr/bin/env python3
# 用法: python3 export_chunks.py <chunks.jsonl> <输出目录>
import json, sys, os, re

src, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)

def safe(name):
    return re.sub(r'[\\/:*?"<>|\s]+', '_', name)[:80]

n = 0
for line in open(src, encoding='utf-8'):
    if line.startswith('#'):
        continue
    r = json.loads(line)
    meta = r["meta"]["source"]              # 如 【主线·13-18·结尾】
    body = r["text"].split('\n\n', 1)[-1]   # 去掉原来的元数据行，只留正文
    fn = safe(f"{r['meta']['file'][:-4]}_{r['meta']['chunk']:03d}_{meta}")
    with open(os.path.join(outdir, fn + '.txt'), 'w', encoding='utf-8') as f:
        f.write(f"{meta}\n\n{body}")
    n += 1

print(f"exported {n} files -> {outdir}", file=sys.stderr)
