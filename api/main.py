from fastapi import FastAPI
from pydantic import BaseModel
import os
from upstash_redis import Redis

app = FastAPI()

# 스크린샷에서 확인된 정확한 환경 변수 이름으로 금고 연결
# Vercel이 제공한 KV_REST_API_URL과 KV_REST_API_TOKEN을 사용합니다.
try:
    redis = Redis(
        url=os.environ.get("KV_REST_API_URL"), 
        token=os.environ.get("KV_REST_API_TOKEN")
    )
except Exception:
    redis = None

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
    # 금고 연결 상태를 체크합니다.
    status = "Connected" if redis else "Disconnected"
    return {"status": "Engine Live", "vault_connection": status}

@app.get("/matrix/{symbol}")
async def get_matrix(symbol: str):
    if not redis:
        return {"error": "Vault keys not found in Environment Variables."}
    
    symbol = symbol.upper()
    timeframes = ["1m", "3m", "5m", "15m", "30m", "60m", "2h", "3h", "4h", "8h", "1d", "3d"]
    strategies = ["A", "B", "C"]
    
    matrix_data = []
    for tf in timeframes:
        row = {"Timeframe": tf}
        for strat in strategies:
            # 금고에서 데이터 꺼내기 (예: BTC:5m:A)
            db_key = f"{symbol}:{tf}:{strat}"
            d = redis.get(db_key)
            if d:
                row[f"Strat_{strat}_Profit"] = d.get('net_profit_pct', 0)
                row[f"Strat_{strat}_MDD"] = d.get('mdd_pct', 0)
                row[f"Strat_{strat}_WinRate"] = d.get('win_rate', 0)
            else:
                row[f"Strat_{strat}_Profit"] = 0
                row[f"Strat_{strat}_MDD"] = 0
                row[f"Strat_{strat}_WinRate"] = 0
        matrix_data.append(row)
    
    return {"MATRIX": matrix_data}

@app.post("/update")
async def update_data(data: StrategyData):
    if not redis: return {"status": "error", "msg": "Vault Offline"}
    # 전략명에서 마지막 알파벳(A, B, C) 추출
    strat_key = data.strategy_name[-1].upper()
    db_key = f"{data.symbol.upper()}:{data.timeframe}:{strat_key}"
    # 금고에 영구 저장
    redis.set(db_key, data.dict())
    return {"status": "success"}
