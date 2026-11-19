#!/usr/bin/env python3
import os, re, sys, json, glob

STORY_DIR = sys.argv[1]
CHUNK_MAX = 550
SPEAKER_RE = re.compile(r'^([^\s：:]{1,20})[：:]\s*(.*)$')

def meta_from_filename(fn):
    base = os.path.basename(fn).rsplit('.', 1)[0]
    m = re.match(r'level_main_(\d+)-(\d+)_(beg|end|st\d+)?', base)
    if m:
        seg = {'beg':'开场','end':'结尾'}.get(m.group(3), m.group(3) or '')
        return f"【主线·{int(m.group(1))}-{int(m.group(2))}{'·'+seg if seg else ''}】"
    m = re.match(r'level_(act\d+\w*?)_(\d+|\w+)_?(beg|end)?', base)
    if m:
        seg = {'beg':'开场','end':'结尾'}.get(m.group(3), m.group(3) or '')
        return f"【活动{m.group(1)}·第{m.group(2)}段{'·'+seg if seg else ''}】"
    m = re.match(r'story_(\w+?)_(\d+)_(\d+)', base)
    if m:
        return f"【干员密录·{m.group(1)}·{m.group(2)}-{m.group(3)}】"
    return f"【{base}】"

def parse_lines(text):
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append((None, ''))
            continue
        m = SPEAKER_RE.match(line)
        if m and not line.startswith('——'):
            out.append((m.group(1), m.group(2)))
        else:
            out.append(('旁白', line))
    return out

def chunk_lines(lines):
    blocks, buf, cur = [], [], 0
    for sp, line in lines:
        if line == '':
            if buf and cur >= CHUNK_MAX * 0.6:
                blocks.append(buf); buf, cur = [], 0
            elif buf:
                buf.append('')
            continue
        txt = f"{sp}：{line}"
        if cur + len(txt) > CHUNK_MAX and buf:
            blocks.append(buf); buf, cur = [], 0
        buf.append(txt); cur += len(txt)
    if buf: blocks.append(buf)
    return blocks

total = 0
for path in sorted(glob.glob(os.path.join(STORY_DIR, '*.txt'))):
    meta = meta_from_filename(path)
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = parse_lines(f.read())
    for i, block in enumerate(chunk_lines(lines)):
        body = '\n'.join(block).strip()
        if not body:
            continue
        text = f"{meta}\n\n{body}"
        print(json.dumps({
            "text": text,
            "meta": {"file": os.path.basename(path), "chunk": i, "source": meta}
        }, ensure_ascii=False))
        total += 1
print(f"# total chunks: {total}", file=sys.stderr)
