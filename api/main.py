from fastapi import FastAPI
from pydantic import BaseModel
import os
from upstash_redis import Redis

app = FastAPI()

# 금고 연결 (환경변수 이름이 무엇이든 다 찾아냅니다)
try:
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    redis = Redis(url=url, token=token)
except:
    redis = None

class StrategyData(BaseModel):
    symbol: str
    strategy_name: str
    timeframe: str
    net_profit_pct: float
    mdd_pct: float
    total_trades: int
    win_rate: float

# [핵심] 어떤 주소로 들어와도 다 받아주는 무적 경로
@app.get("/")
@app.get("/matrix/{symbol}")
@app.get("/api/matrix/{symbol}")
async def get_matrix(symbol: str = "BTC"):
    if not redis: return {"error": "DB 연결 실패"}
    symbol = symbol.upper()
    timeframes = ["1m", "3m", "5m", "15m", "30m", "60m", "2h", "3h", "4h", "8h", "1d", "3d"]
    strategies = ["A", "B", "C"]
    matrix_data = []
    for tf in timeframes:
        row = {"Timeframe": tf}
        for strat in strategies:
            db_key = f"{symbol}:{tf}:{strat}"
            d = redis.get(db_key)
            if d:
                row[f"Strat_{strat}_Profit"] = d.get('net_profit_pct', 0)
                row[f"Strat_{strat}_MDD"] = d.get('mdd_pct', 0)
                row[f"Strat_{strat}_WinRate"] = d.get('win_rate', 0)
            else:
                row[f"Strat_{strat}_Profit"] = 0; row[f"Strat_{strat}_MDD"] = 0; row[f"Strat_{strat}_WinRate"] = 0
        matrix_data.append(row)
    return {"MATRIX": matrix_data}

@app.post("/update")
@app.post("/api/update")
async def update_data(data: StrategyData):
    if not redis: return {"status": "error"}
    db_key = f"{data.symbol.upper()}:{data.timeframe}:{data.strategy_name[-1].upper()}"
    redis.set(db_key, data.dict())
    return {"status": "success"}
