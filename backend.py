import os
import queue

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Shared queue — launcher polls this for persona selection
launch_queue: queue.Queue = queue.Queue()

app = FastAPI()

_static = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(_static, "index.html"), encoding="utf-8") as f:
        return f.read()


class StartRequest(BaseModel):
    voice_id: str


@app.post("/start")
def start(req: StartRequest):
    launch_queue.put(req.voice_id)
    return {"status": "launched"}
