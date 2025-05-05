from fastapi import FastAPI, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import polars as pl
import asyncio
import os

app = FastAPI()
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/")
async def dashboard(request: Request):
    try:
        df = pl.read_csv("logs/signals_log.csv")
        signals = df.to_dicts()[-10:]  # Last 10 signals
        return templates.TemplateResponse("dashboard.html", {"request": request, "signals": signals})
    except:
        return templates.TemplateResponse("dashboard.html", {"request": None, "signals": []})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            df = pl.read_csv("logs/signals_log.csv")
            signals = df.to_dicts()[-10:]
            await websocket.send_json(signals)
            await asyncio.sleep(10)  # Update every 10 seconds
    except:
        await websocket.close()
