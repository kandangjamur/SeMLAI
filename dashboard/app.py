# dashboard/app.py
import os
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from data.tracker import update_signal_status

app = FastAPI()

# Setup templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(templates_dir))

# Mount static folder (if needed later)
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    update_signal_status()
    try:
        df = pd.read_csv("logs/signals_log.csv")
        df = df.sort_values(by="timestamp", ascending=False)
        html_table = df.to_html(index=False, classes="table table-striped", escape=False)
    except Exception as e:
        html_table = f"<p>Error loading log: {e}</p>"

    template = env.get_template("dashboard.html")
    return template.render(content=html_table)
