"""積換問題 Web アプリの FastAPI バックエンド

起動方法（transshipment_app/backend で実行）::

    uvicorn main:app --reload
"""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import transshipment_core as core

app = FastAPI(title="Transshipment Problem")

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


class Warehouse(BaseModel):
    """倉庫（Warehouse）"""

    ID: str
    name: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    capacity: float = Field(ge=0)


class SolveRequest(BaseModel):
    """求解リクエスト"""

    customers: list[Customer]
    suppliers: list[Supplier]
    warehouses: list[Warehouse]
    cost_per_unit_distance_sw: float = Field(15.0, ge=0)
    cost_per_unit_distance_wc: float = Field(20.0, ge=0)
    unit: Literal["km", "mi"] = "km"
    solver: str = "highs"
    enforce_capacity: bool = True
    allow_shortage: bool = False
    penalty: float = Field(100000.0, ge=0)


@app.get("/api/solvers")
def get_solvers():
    """利用可能なソルバーの一覧"""
    return core.available_solvers()


@app.get("/api/sample")
def get_sample():
    """サンプルデータ"""
    customers, suppliers, warehouses = core.load_sample()
    return {"customers": customers, "suppliers": suppliers, "warehouses": warehouses}


@app.post("/api/solve")
def solve(req: SolveRequest):
    """積換問題を解く"""
    if not req.customers or not req.suppliers or not req.warehouses:
        raise HTTPException(400, "顧客・サプライヤー・倉庫がそれぞれ1件以上必要です")
    for node in [*req.customers, *req.suppliers, *req.warehouses]:
        node.ID = node.ID.strip()
        if not node.ID:
            raise HTTPException(400, "空の ID は指定できません")
    ids = (
        [c.ID for c in req.customers]
        + [s.ID for s in req.suppliers]
        + [w.ID for w in req.warehouses]
    )
    if len(ids) != len(set(ids)):
        raise HTTPException(400, "ID が重複しています")
    if req.solver not in core.available_solvers():
        raise HTTPException(400, f"ソルバー {req.solver} はインストールされていません")

    try:
        return core.solve_transshipment(
            customers=[c.model_dump() for c in req.customers],
            suppliers=[s.model_dump() for s in req.suppliers],
            warehouses=[w.model_dump() for w in req.warehouses],
            cost_per_unit_distance_sw=req.cost_per_unit_distance_sw,
            cost_per_unit_distance_wc=req.cost_per_unit_distance_wc,
            unit=req.unit,
            solver=req.solver,
            enforce_capacity=req.enforce_capacity,
            allow_shortage=req.allow_shortage,
            penalty=req.penalty,
        )
    except Exception as e:
        raise HTTPException(500, f"求解に失敗しました: {e}")


# ビルド済みのフロントエンド (npm run build) があれば配信する
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
