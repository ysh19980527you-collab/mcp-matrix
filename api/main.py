from fastapi import FastAPI
from pydantic import BaseModel
import os
from upstash_redis import Redis

# 1. 앱 생성 (Vercel 환경에 최적화된 경로 설정)
app = FastAPI()

# 2. Redis 금고 연결
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

# --- [주목] 주소 설계도 ---

# 1. 상태 확인 (https://mcp-matrix.vercel.app/)
@app.get("/")
async def root():
    return {"status": "Persistent Engine Online", "vault": "Connected" if redis else "Disconnected"}

# 2. 데이터 업데이트 (POST 요청)
@app.post("/update")
@app.post("/api/update") # 혹시 모를 경로 꼬임 방지용 중복 선언
async def update_data(data: StrategyData):
    if not redis: return {"status": "error", "msg": "Vault Offline"}
    symbol = data.symbol.upper()
    strat_key = data.strategy_name[-1].upper()
    db_key = f"{symbol}:{data.timeframe}:{strat_key}"
    redis.set(db_key, data.dict())
    return {"status": "success"}

# 3. 매트릭스 조회 (GET 요청)
@app.get("/matrix/{symbol}")
@app.get("/api/matrix/{symbol}") # 혹시 모를 경로 꼬임 방지용 중복 선언
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
