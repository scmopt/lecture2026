"""輸送問題 Web アプリの FastAPI バックエンド

起動方法（transport_app/backend で実行）::

    uvicorn main:app --reload
"""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import transport_core as core

app = FastAPI(title="Transportation Problem")

# Vite の開発サーバー (npm run dev) からのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Customer(BaseModel):
    """顧客（Customer）"""
    ID: str
    name: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    demand: float = Field(ge=0)


class Supplier(BaseModel):
    """サプライヤー（Supplier）"""
    ID: str
    name: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    supply: float = Field(ge=0)


class SolveRequest(BaseModel):
    """求解リクエスト"""
    customers: list[Customer]
    suppliers: list[Supplier]
    cost_per_unit_distance: float = Field(1.2, ge=0)
    unit: Literal["km", "mi"] = "km"
    solver: str = "highs"
    allow_shortage: bool = False
    penalty: float = Field(10000.0, ge=0)


@app.get("/api/solvers")
def get_solvers():
    """利用可能なソルバーの一覧"""
    return core.available_solvers()


@app.get("/api/sample")
def get_sample():
    """サンプルデータ"""
    customers, suppliers = core.load_sample()
    return {"customers": customers, "suppliers": suppliers}


@app.post("/api/solve")
def solve(req: SolveRequest):
    """輸送問題を解く"""
    if not req.customers or not req.suppliers:
        raise HTTPException(400, "顧客とサプライヤーが1件以上必要です")
    ids = [c.ID for c in req.customers] + [s.ID for s in req.suppliers]
    if len(ids) != len(set(ids)):
        raise HTTPException(400, "ID が重複しています")
    if req.solver not in core.available_solvers():
        raise HTTPException(400, f"ソルバー {req.solver} はインストールされていません")

    try:
        return core.solve_transportation(
            customers=[c.model_dump() for c in req.customers],
            suppliers=[s.model_dump() for s in req.suppliers],
            cost_per_unit_distance=req.cost_per_unit_distance,
            unit=req.unit,
            solver=req.solver,
            allow_shortage=req.allow_shortage,
            penalty=req.penalty,
        )
    except Exception as e:  # ライセンスエラーなどをそのまま画面に返す
        raise HTTPException(500, f"求解に失敗しました: {e}")


# ビルド済みのフロントエンド (npm run build) があれば配信する
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
