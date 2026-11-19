# Ark RAG · 泰拉剧情检索栈

本地剧情向量检索 + 本地 LLM 问答。

## 组件

| 文件 | 作用 |
|---|---|
| `emb_server.py` | 本地嵌入服务（bge-small-zh-v1.5，512 维，8000 端口） |
| `story_ingest.py` | 剧情 txt → 带章节标记的 chunk |
| `export_chunks.py` | chunk JSONL → 独立 txt 文件（给 Cherry Studio 用） |
| `build_index.py` | 全量嵌入 → `ark_index.npz` |
| `search.py` | 命令行检索（带防剧透过滤） |
| `ark_tui.py` | 交互式 TUI |
| `ask.py` | RAG 问答（检索 + 本地 LLM 生成） |
| `ask_gui.sh` | zenity 图形封装 |

## 快速开始

```bash
# 1. 嵌入服务
python3 -m uvicorn emb_server:app --host 127.0.0.1 --port 8000

# 2. 建索引（一次性）
python3 build_index.py

# 3. 检索
python3 search.py "阿米娅的戒指"
MAX_MAIN=8 python3 search.py "霜星"      # 放宽章节
MODE=event python3 search.py "活动"      # 搜活动

# 4. 问答（需要 llama-server 在 8081）
python3 ask.py "阿米娅的戒指有什么特别"
NO_LLM=1 python3 ask.py "只列原文"

环境变量
变量	默认	说明
ARK_INDEX	~/ark_index.npz	索引路径
MAX_MAIN	4	主线章节上限（防剧透）
MODE	main	main / event / all
TOP_K	5	检索条数
MIN_SCORE	0.45	相关度下限
NO_LLM	0	设为 1 则只列原文
LLM_URL	http://127.0.0.1:8081/v1/chat/completions	

依赖
Python 3.13，numpy
bge-small-zh-v1.5（通过 emb_server 加载）
llama.cpp + Qwen2.5-3B GGUF（可选，用于生成）

注意
索引文件 ark_index.npz（约 54MB）不随仓库分发，需自行构建。
剧情文本版权归鹰角网络，仅本地学习研究使用。 EOF
