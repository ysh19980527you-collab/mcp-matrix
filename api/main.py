from fastapi import FastAPI
from pydantic import BaseModel
import os
from upstash_redis import Redis

app = FastAPI()

# Vercel-Upstash 연결 금고 자동 호출
redis = Redis.from_env()

TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "60m", "2h", "3h", "4h", "8h", "1d", "3d"]
STRATEGIES = ["A", "B", "C"]

class StrategyData(BaseModel):
    symbol: str
    strategy_name: str
    timeframe: str
    net_profit_pct: float
    mdd_pct: float
    total_trades: int
    win_rate: float

@app.get("/")
async def root():
    return {"status": "Persistent Engine Online", "storage": "Upstash Redis Active"}

@app.post("/update")
async def update_data(data: StrategyData):
    symbol = data.symbol.upper()
    strat_key = data.strategy_name[-1].upper()
    db_key = f"{symbol}:{data.timeframe}:{strat_key}"
    
    # 데이터를 금고에 영구 저장
    redis.set(db_key, data.dict())
    return {"status": "success"}

@app.get("/matrix/{symbol}")
async def get_matrix(symbol: str):
    symbol = symbol.upper()
    matrix_data = []
    best_score = -999999
    best_info = "N/A"

    for tf in TIMEFRAMES:
        row = {"Timeframe": tf}
        for strat in STRATEGIES:
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
                    best_info = f"{tf} - Strategy {strat}"
            else:
                row[f"Strat_{strat}_Profit"] = 0
                row[f"Strat_{strat}_MDD"] = 0
                row[f"Strat_{strat}_WinRate"] = 0
        matrix_data.append(row)

    return {
        "BEST_STRATEGY_FOUND": best_info,
        "MATRIX": matrix_data
    }
