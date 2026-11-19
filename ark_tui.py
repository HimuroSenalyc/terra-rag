#!/usr/bin/env python3
"""方舟剧情检索 TUI"""
import os, json, re, urllib.request
import numpy as np
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, ListView, ListItem, Label, Static
from textual.binding import Binding

INDEX   = os.path.expanduser(os.environ.get("ARK_INDEX", "~/ark_index.npz"))
TITLE   = os.environ.get("ARK_TITLE", "方舟剧情检索")
IS_DOC  = os.environ.get("ARK_MODE", "story") == "doc"
EMB_URL = "http://127.0.0.1:8000/v1/embeddings"

def embed(text):
    payload = json.dumps({"input": [text]}).encode("utf-8")
    req = urllib.request.Request(EMB_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    v = np.asarray(data["data"][0]["embedding"], dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v

class ResultItem(ListItem):
    def __init__(self, idx, score, src, chapter, body):
        super().__init__()
        self.idx, self.score, self.src, self.chapter, self.body = idx, score, src, chapter, body
    def compose(self):
        yield Label(f"[{self.chapter}]  {self.score:.3f}", markup=False)

class ArkApp(App):
    CSS = """
    Screen { background: $surface; }
    #search { dock: top; height: 3; }
    #scope { dock: top; height: 1; padding-left: 1; color: $text-muted; }
    #results { height: 35%; border: round $primary; }
    #detail { height: 1fr; border: round $accent; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+c", "quit", "退出"),
        Binding("/", "focus_search", "搜索"),
        Binding("f2", "toggle_scope", "切换范围"),
    ]

    def __init__(self):
        super().__init__()
        d = np.load(INDEX, allow_pickle=True)
        self.vecs, self.texts, self.sources = d["vecs"], d["texts"], d["sources"]
        self.modes = ["main4", "main8", "event", "all"]
        self.mode_i = 0

    def compose(self) -> ComposeResult:
        self.title = TITLE
        self.sub_title = "本地向量检索"
        yield Input(placeholder="输入关键词，回车检索…（/ 聚焦，F2 切范围）", id="search")
        yield Static("", id="scope")
        yield ListView(id="results")
        yield Static("↑↓ 选择，回车查看全文", id="detail")

    def on_mount(self):
        self.update_scope()

    def mode_desc(self):
        return {"main4": "主线 1~4 章", "main8": "主线 1~8 章",
                "event": "活动 / 密录", "all": "全部（剧透警告）"}[self.modes[self.mode_i]]

    def update_scope(self):
        self.query_one("#scope", Static).update(f"范围: {self.mode_desc()}    [F2] 切换")

    def allowed(self, src):
        if IS_DOC: return True
        m = self.modes[self.mode_i]
        is_main = src.startswith("level_main_")
        if m == "all": return True
        if m == "event": return not is_main
        mm = re.search(r'level_main_(\d+)-', src)
        if not is_main or not mm: return False
        return int(mm.group(1)) <= (4 if m == "main4" else 8)

    def action_toggle_scope(self):
        self.mode_i = (self.mode_i + 1) % len(self.modes)
        self.update_scope()
        q = self.query_one("#search", Input).value
        if q: self.do_search(q)

    def action_focus_search(self):
        self.query_one("#search", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        self.do_search(event.value)

    def do_search(self, q):
        if not q.strip(): return
        try:
            qv = embed(q)
        except Exception as e:
            self.query_one("#detail", Static).update(f"嵌入失败: {e}")
            return
        scores = self.vecs @ qv
        order = np.argsort(-scores)
        picked = []
        for i in order:
            if self.allowed(str(self.sources[i])):
                picked.append(int(i))
            if len(picked) >= 20: break

        lv = self.query_one("#results", ListView)
        lv.clear()
        for i in picked:
            src = str(self.sources[i])
            chap = src[src.index("【"):src.index("】")+1] if "【" in src else src
            lv.append(ResultItem(i, float(scores[i]), src, chap, str(self.texts[i])))
        self.query_one("#detail", Static).update(
            "↑↓ 选择，回车查看全文" if picked else "（该范围无结果）")

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        self.query_one("#detail", Static).update(f"{item.chapter}\n{item.src}\n\n{item.body}")

if __name__ == "__main__":
    ArkApp().run()
