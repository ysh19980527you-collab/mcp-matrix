from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd

app = FastAPI()

# 12개 타임프레임 정의
TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "60m", "2h", "3h", "4h", "8h", "1d", "3d"]
STRATEGIES = ["A", "B", "C"]

# 인메모리 데이터 저장소 (MVP 단계)
# 구조: { "BTC": { "5m": { "A": {data}, "B": {data} } } }
db = {}

class StrategyData(BaseModel):
    symbol: str
    strategy_name: str
    timeframe: str
    net_profit_pct: float
    mdd_pct: float
    total_trades: int
    win_rate: float

@app.get("/")
async def health_check():
    return {"status": "operational", "engine": "Quant-Backtest-Decipherer"}

@app.post("/update")
async def update_data(data: StrategyData):
    if data.symbol not in db:
        db[data.symbol] = {tf: {strat: None for strat in STRATEGIES} for tf in TIMEFRAMES}
    
    # 전략명에서 A, B, C 추출 (예: 4중BB-A -> A)
    strat_key = data.strategy_name[-1].upper()
    if strat_key in STRATEGIES:
        db[data.symbol][data.timeframe][strat_key] = data.dict()
    
    return {"status": "success"}

@app.get("/matrix/{symbol}")
async def get_matrix(symbol: str):
    if symbol not in db:
        return {"error": "Symbol not found"}

    matrix_data = []
    best_score = -float('inf')
    best_strat_info = "N/A"

    for tf in TIMEFRAMES:
        row = {"Timeframe": tf}
        for strat in STRATEGIES:
            d = db[symbol][tf][strat]
            if d:
                row[f"Strat_{strat}_Profit"] = d['net_profit_pct']
                row[f"Strat_{strat}_MDD"] = d['mdd_pct']
                row[f"Strat_{strat}_WinRate"] = d['win_rate']
                
                # 최적 전략 판독 로직: 수익률 / MDD (Risk-Adjusted Return)
                score = d['net_profit_pct'] / (abs(d['mdd_pct']) + 0.001)
                if score > best_score:
                    best_score = score
                    best_strat_info = f"{tf} - Strategy {strat}"
            else:
                row[f"Strat_{strat}_Profit"] = 0
                row[f"Strat_{strat}_MDD"] = 0
                row[f"Strat_{strat}_WinRate"] = 0
        
        matrix_data.append(row)

    return {
        "BEST_STRATEGY_FOUND": best_strat_info,
        "MATRIX": matrix_data
    }