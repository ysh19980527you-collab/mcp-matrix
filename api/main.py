from fastapi import FastAPI
from pydantic import BaseModel
import os
from upstash_redis import Redis

app = FastAPI()

# 금고 연결
try:
    redis = Redis(
        url=os.environ.get("KV_REST_API_URL"), 
        token=os.environ.get("KV_REST_API_TOKEN")
    )
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

# --- 경로 에러를 원천 차단하는 트리플 라우팅 ---

# 1. 메인 (https://mcp-matrix.vercel.app/ 및 /api)
@app.get("/")
@app.get("/api")
async def root():
    return {"status": "Persistent Engine Online", "vault": "Connected" if redis else "Disconnected"}

# 2. 업데이트 (https://mcp-matrix.vercel.app/update 및 /api/update)
@app.post("/update")
@app.post("/api/update")
async def update_data(data: StrategyData):
    if not redis: return {"status": "error", "msg": "Vault Offline"}
    db_key = f"{data.symbol.upper()}:{data.timeframe}:{data.strategy_name[-1].upper()}"
    redis.set(db_key, data.dict())
    return {"status": "success"}

# 3. 매트릭스 (https://mcp-matrix.vercel.app/matrix/BTC 및 /api/matrix/BTC)
@app.get("/matrix/{symbol}")
@app.get("/api/matrix/{symbol}")
async def get_matrix(symbol: str):
    if not redis: return {"error": "Vault keys not found."}
    symbol = symbol.upper()
    timeframes = ["1m", "3m", "5m", "15m", "30m", "60m", "2h", "3h", "4h", "8h", "1d", "3d"]
    strategies = ["A", "B", "C"]
    matrix_data = []
    best_score = -999999
    best_info = "N/A"
    for tf in timeframes:
        row = {"Timeframe": tf}
        for strat in strategies:
            db_key = f"{symbol}:{tf}:{strat}"
            d = redis.get(db_key)
            if d:
                profit = d.get('net_profit_pct', 0)
                mdd = d.get('mdd_pct', 0)
                row[f"Strat_{strat}_Profit"] = profit
                row[f"Strat_{strat}_MDD"] = mdd
                row[f"Strat_{strat}_WinRate"] = d.get('win_rate', 0)
                score = profit / (abs(mdd) + 0.001)
                if score > best_score:
                    best_score = score
                    best_info = f"{tf} - Strat {strat}"
            else:
                row[f"Strat_{strat}_Profit"] = 0
                row[f"Strat_{strat}_MDD"] = 0
                row[f"Strat_{strat}_WinRate"] = 0
        matrix_data.append(row)
    return {"BEST_STRATEGY_FOUND": best_info, "MATRIX": matrix_data}
