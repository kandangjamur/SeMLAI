from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import ccxt.async_support as ccxt
from utils.logger import log

app = FastAPI()
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    exchange = ccxt.binance({"enableRateLimit": True})
    try:
        markets = await exchange.load_markets()
        symbols = [s for s in markets.keys() if s.endswith("/USDT")][:10]
        return templates.TemplateResponse("dashboard.html", {"request": request, "symbols": symbols})
    except Exception as e:
        log(f"Error loading dashboard: {e}", level='ERROR')
        return templates.TemplateResponse("dashboard.html", {"request": request, "symbols": [], "error": str(e)})
    finally:
        await exchange.close()
