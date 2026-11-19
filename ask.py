#!/usr/bin/env python3
"""ask.py —— 人 → AI → 知识库的一次完整闭环

用法:
    python3 ask.py "霜星为什么放过罗德岛"
    MAX_MAIN=8 python3 ask.py "特蕾西娅的戒指"
    MODE=event python3 ask.py "某活动剧情"
    NO_LLM=1 python3 ask.py "只列原文，不让模型回答"

环境变量:
    MAX_MAIN    主线章节上限（默认 4，防剧透）
    MODE        main | event | all（默认 main）
    TOP_K       检索条数（默认 5）
    MIN_SCORE   相关度下限（默认 0.45）
    NO_LLM      设为 1 则只输出原文，不调模型
    LLM_URL     生成服务地址（默认 http://127.0.0.1:8081/v1/chat/completions）
    LLM_MODEL   模型名（默认从 /v1/models 里取第一个）
"""
import os, sys, json, re, urllib.request, urllib.error
import numpy as np

INDEX    = os.path.expanduser(os.environ.get("ARK_INDEX", "~/ark_index.npz"))
EMB_URL  = os.environ.get("EMB_URL", "http://127.0.0.1:8000/v1/embeddings")
LLM_BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8081/v1/chat/completions")
MAX_MAIN = int(os.environ.get("MAX_MAIN", "4"))
MODE     = os.environ.get("MODE", "main")
TOP_K    = int(os.environ.get("TOP_K", "5"))
MIN_SCORE= float(os.environ.get("MIN_SCORE", "0.45"))
NO_LLM   = os.environ.get("NO_LLM", "0") == "1"

# ---------- 嵌入 ----------
def embed(text):
    payload = json.dumps({"input": [text]}).encode("utf-8")
    req = urllib.request.Request(EMB_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    v = np.asarray(data["data"][0]["embedding"], dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v

# ---------- 过滤 ----------
def allowed(src):
    is_main = src.startswith("level_main_")
    if MODE == "all":
        return True
    if MODE == "event":
        return not is_main
    m = re.search(r'level_main_(\d+)-', src)
    if not is_main or not m:
        return False
    return int(m.group(1)) <= MAX_MAIN

def chapter_tag(src):
    if "【" in src and "】" in src:
        return src[src.index("【"):src.index("】")+1]
    return src

# ---------- LLM ----------
def llm_chat(messages, max_tokens=600):
    payload = json.dumps({
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(LLM_BASE, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def llm_available():
    if NO_LLM:
        return False
    try:
        base = LLM_BASE.rsplit("/chat/completions", 1)[0]
        with urllib.request.urlopen(base + "/models", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

# ---------- 主流程 ----------
def main():
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        q = input("问题 > ").strip()
    if not q:
        sys.exit("空问题")

    if not os.path.exists(INDEX):
        sys.exit(f"索引不存在: {INDEX}")

    d = np.load(INDEX, allow_pickle=True)
    vecs, texts, sources = d["vecs"], d["texts"], d["sources"]

    qv = embed(q)
    scores = vecs @ qv
    order = np.argsort(-scores)

    # 按分数阈值 + 范围过滤
    picked = []
    for i in order:
        if scores[i] < MIN_SCORE:
            break
        if allowed(str(sources[i])):
            picked.append(int(i))
        if len(picked) >= TOP_K:
            break

    scope = {"main": (f"主线 1~{MAX_MAIN} 章" if MAX_MAIN < 99 else "主线（全部）"),
             "event": "活动/密录", "all": "全量"}[MODE]

    # 没有结果
    if not picked:
        best = float(scores[order[0]])
        best_src = chapter_tag(str(sources[order[0]]))
        print(f"\n【未找到】当前范围：{scope}")
        if best >= MIN_SCORE:
            print(f"其他章节可能有相关内容（最高 {best:.3f}，来自 {best_src}）")
            print(f"试试：MAX_MAIN=8 或 MODE=all")
        else:
            print(f"全库最高相关度仅 {best:.3f}，基本无关。")
        return

    # 组装上下文
    ctx_blocks = []
    for i in picked:
        tag = chapter_tag(str(sources[i]))
        body = str(texts[i]).strip()
        ctx_blocks.append(f"[{tag}]\n{body}")
    contexts = "\n\n---\n\n".join(ctx_blocks)

    # 没有 LLM，就直接列原文
    if not llm_available():
        print(f"\n【原文检索】范围：{scope}   （生成服务未运行，仅列原文）\n")
        for n, i in enumerate(picked, 1):
            print(f"[{n}] {chapter_tag(str(sources[i]))}  score={scores[i]:.3f}")
            print("    " + str(texts[i]).strip().replace("\n", "\n    ")[:700])
            print()
        return

    # 有 LLM，走 RAG
    system = (
        "你是《明日方舟》剧情考据助手。你的唯一知识来源是下面提供的剧情原文。\n"
        "铁律：\n"
        "1. 只依据原文回答，原文没写的就说“剧情中未提及”，不要编。\n"
        "2. 每条结论必须标出处，格式：（出处：主线·4-1·开场）\n"
        "3. 区分“谁说的”和“事实”：角色的话可能是谎话或误解。\n"
        "4. 不抒情、不铺垫、不写散文。先给结论，再列依据。\n"
        "5. 原文与问题无关，就说“检索到的内容与问题不直接相关”。\n"
    )
    user = f"问题：{q}\n\n参考原文：\n{contexts}\n\n请根据以上原文回答。"

    try:
        ans = llm_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
    except Exception as e:
        print(f"\n【生成失败】{e}\n降级为原文列表：\n")
        for n, i in enumerate(picked, 1):
            print(f"[{n}] {chapter_tag(str(sources[i]))}  score={scores[i]:.3f}")
            print("    " + str(texts[i]).strip().replace("\n", "\n    ")[:700])
            print()
        return

    print(f"\n【回答】范围：{scope}\n")
    print(ans.strip())
    print("\n【依据原文】")
    for n, i in enumerate(picked, 1):
        print(f"  [{n}] {chapter_tag(str(sources[i]))}  score={scores[i]:.3f}")

if __name__ == "__main__":
    main()
