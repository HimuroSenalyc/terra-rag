import os
os.environ["OMP_NUM_THREADS"] = "16"
os.environ["MKL_NUM_THREADS"] = "16"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import threading

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
print("loading model...", flush=True)
m = SentenceTransformer(MODEL_NAME, device="cpu")
DIM = m.get_sentence_embedding_dimension()
print(f"model loaded, dim={DIM}", flush=True)

# 预热
m.encode(["预热"], normalize_embeddings=True)
print("warmed up", flush=True)

app = FastAPI()
_lock = threading.Lock()

class Req(BaseModel):
    input: list[str] | str
    model: str | None = None

@app.post("/v1/embeddings")
def embeddings(req: Req):
    texts = [req.input] if isinstance(req.input, str) else req.input
    with _lock:
        vs = m.encode(texts, batch_size=64, normalize_embeddings=True)
    return {
        "object": "list",
        "model": MODEL_NAME,
        "data": [{"object": "embedding", "index": i, "embedding": v.tolist()}
                 for i, v in enumerate(vs)],
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }

@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": MODEL_NAME, "object": "model"}]}
