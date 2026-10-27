"""輸送問題 (Transportation Problem) のコアロジック

01Transportation_Problem_ja.py の距離計算・コスト計算・AMPLモデルを
Web API から使えるように切り出したもの。
"""

from pathlib import Path

import pandas as pd
from amplpy import AMPL, modules
from geopy.distance import geodesic

DATA_DIR = Path(__file__).parent / "data"

# LP を解けるソルバーのうち、画面に表示する候補
KNOWN_SOLVERS = ["highs", "cbc", "gurobi", "cplex", "xpress", "copt", "mosek"]

# 輸送問題のAMPLモデル
#   allow_shortage = 0 のときは通常の輸送問題（需要を必ず満たす）
#   allow_shortage = 1 のときは需要の未充足を許し、1単位あたり penalty のコストを課す
TRANSPORTATION_MODEL = r"""
set SUPPLIERS;                                  # サプライヤーの集合
set CUSTOMERS;                                  # 顧客の集合

param supply {SUPPLIERS} >= 0;                  # サプライヤーの供給可能量
param demand {CUSTOMERS} >= 0;                  # 顧客の需要量
param unit_cost {SUPPLIERS, CUSTOMERS} >= 0;    # 単位輸送コスト
param allow_shortage binary;                    # 需要の未充足を許すかどうか
param penalty >= 0;                             # 未充足1単位あたりのペナルティ

# サプライヤーと顧客間のフローを表す決定変数
var flow {SUPPLIERS, CUSTOMERS} >= 0;

# 顧客ごとの需要の未充足量
var shortage {c in CUSTOMERS} >= 0, <= allow_shortage * demand[c];

# 目的関数：総輸送コスト（＋未充足ペナルティ）の最小化
minimize TotalCost:
    sum {s in SUPPLIERS, c in CUSTOMERS} unit_cost[s, c] * flow[s, c]
    + sum {c in CUSTOMERS} penalty * shortage[c];

# 需要制約
subject to Demand {c in CUSTOMERS}:
    sum {s in SUPPLIERS} flow[s, c] + shortage[c] = demand[c];

# 供給制約
subject to Supply {s in SUPPLIERS}:
    sum {c in CUSTOMERS} flow[s, c] <= supply[s];
"""


def load_sample():
    """サンプルの顧客・サプライヤーデータを読み込む。"""
    customers = pd.read_csv(DATA_DIR / "customers.csv", encoding="utf-8-sig")
    suppliers = pd.read_csv(DATA_DIR / "suppliers.csv", encoding="utf-8-sig")
    return customers.to_dict("records"), suppliers.to_dict("records")


def available_solvers():
    """この環境に amplpy モジュールとしてインストールされているソルバーを返す。"""
    installed = set(modules.installed())
    return [s for s in KNOWN_SOLVERS if s in installed]


def compute_geodesic_distance(origin, destination, unit="km"):
    """測地線距離の計算

    2地点間の測地線距離を計算する関数。
    """
    d = geodesic((origin["lat"], origin["lon"]), (destination["lat"], destination["lon"]))
    return d.km if unit == "km" else d.mi


def compute_unit_costs(customers, suppliers, cost_per_unit_distance, unit="km"):
    """アークの距離とコスト

    顧客とサプライヤー間の距離と単位輸送コストの辞書を作成する。
    """
    distances = {}
    unit_cost = {}
    for s in suppliers:
        for c in customers:
            key = (s["ID"], c["ID"])
            distances[key] = compute_geodesic_distance(c, s, unit)
            unit_cost[key] = distances[key] * cost_per_unit_distance
    return distances, unit_cost


def solve_transportation(customers, suppliers, cost_per_unit_distance=1.2, unit="km",
                         solver="highs", allow_shortage=False, penalty=0.0):
    """最適化モデルの作成と求解

    AMPLで輸送問題のモデルを作成し、データをamplpyで渡して求解する。
    """
    distances, unit_cost = compute_unit_costs(customers, suppliers, cost_per_unit_distance, unit)

    # amplpyでインストールしたソルバーモジュールを読み込み
    modules.load()

    ampl = AMPL()
    ampl.eval(TRANSPORTATION_MODEL)

    # 集合とパラメータのデータを設定
    ampl.set["SUPPLIERS"] = [s["ID"] for s in suppliers]
    ampl.set["CUSTOMERS"] = [c["ID"] for c in customers]
    ampl.param["supply"] = {s["ID"]: s["supply"] for s in suppliers}
    ampl.param["demand"] = {c["ID"]: c["demand"] for c in customers}
    ampl.param["unit_cost"] = unit_cost
    ampl.param["allow_shortage"] = 1 if allow_shortage else 0
    ampl.param["penalty"] = penalty

    # モデルの求解
    ampl.option["solver"] = solver
    output = ampl.get_output("solve;")
    status = ampl.solve_result

    result = {"status": status, "solver_output": output.replace("\b", "").strip()}
    if status != "solved":
        return result

    flow = ampl.var["flow"].get_values().to_dict()
    shortage = ampl.var["shortage"].get_values().to_dict()
    flows = [
        {
            "supplier": s,
            "customer": c,
            "flow": v,
            "distance": distances[s, c],
            "unit_cost": unit_cost[s, c],
            "cost": v * unit_cost[s, c],
        }
        for (s, c), v in flow.items()
        if v > 1e-6
    ]
    transport_cost = sum(f["cost"] for f in flows)
    result.update(
        objective=ampl.obj["TotalCost"].value(),
        transport_cost=transport_cost,
        flows=flows,
        shortages={c: v for c, v in shortage.items() if v > 1e-6},
    )
    return result
