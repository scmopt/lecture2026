"""積換問題 (Transshipment Problem) のコアロジック

02Transshipment_Problem_Python_Exercise_ja.py の距離計算・コスト計算・AMPLモデルを
Web API から使えるように切り出したもの。
"""

import csv
from pathlib import Path

from amplpy import AMPL, modules
from geopy.distance import geodesic

DATA_DIR = Path(__file__).parent / "data"

# LP を解けるソルバーのうち、画面に表示する候補
KNOWN_SOLVERS = ["highs", "cbc", "gurobi", "cplex", "xpress", "copt", "mosek"]

# 積換問題の AMPL モデル
#   enforce_capacity = 1 のときは倉庫の容量制約を有効にする（Task 1）
#   allow_shortage = 1 のときは需要の未充足を許し、1単位あたり penalty のコストを課す
TRANSSHIPMENT_MODEL = r"""
set SUPPLIERS;                                              # サプライヤーの集合
set WAREHOUSES;                                             # 倉庫の集合
set CUSTOMERS;                                              # 顧客の集合

param supply {SUPPLIERS} >= 0;                              # サプライヤーの供給可能量
param capacity {WAREHOUSES} >= 0;                           # 倉庫の容量
param demand {CUSTOMERS} >= 0;                              # 顧客の需要量
param unit_cost_sw {SUPPLIERS, WAREHOUSES} >= 0;            # サプライヤー・倉庫間の単位輸送コスト
param unit_cost_wc {WAREHOUSES, CUSTOMERS} >= 0;            # 倉庫・顧客間の単位輸送コスト
param enforce_capacity binary;                              # 倉庫容量制約を有効にするか
param allow_shortage binary;                                # 需要の未充足を許すか
param penalty >= 0;                                         # 未充足1単位あたりのペナルティ

# サプライヤー・倉庫間および倉庫・顧客間のフローを表す決定変数
var flow_sw {SUPPLIERS, WAREHOUSES} >= 0;
var flow_wc {WAREHOUSES, CUSTOMERS} >= 0;

# 顧客ごとの需要の未充足量
var shortage {c in CUSTOMERS} >= 0, <= allow_shortage * demand[c];

# 目的関数：総輸送コスト（＋未充足ペナルティ）の最小化
minimize TotalCost:
    sum {s in SUPPLIERS, w in WAREHOUSES} unit_cost_sw[s, w] * flow_sw[s, w]
    + sum {w in WAREHOUSES, c in CUSTOMERS} unit_cost_wc[w, c] * flow_wc[w, c]
    + sum {c in CUSTOMERS} penalty * shortage[c];

# 需要制約
subject to Demand {c in CUSTOMERS}:
    sum {w in WAREHOUSES} flow_wc[w, c] + shortage[c] = demand[c];

# 供給制約
subject to Supply {s in SUPPLIERS}:
    sum {w in WAREHOUSES} flow_sw[s, w] <= supply[s];

# フロー保存制約（倉庫への流入量と流出量が等しい）
subject to FlowBalance {w in WAREHOUSES}:
    sum {s in SUPPLIERS} flow_sw[s, w] = sum {c in CUSTOMERS} flow_wc[w, c];

# 倉庫の容量制約（enforce_capacity = 1 のとき有効）
subject to WarehouseCapacity {w in WAREHOUSES: enforce_capacity = 1}:
    sum {s in SUPPLIERS} flow_sw[s, w] <= capacity[w];
"""


def _read_csv(path, numeric_cols):
    """CSV を辞書のリストとして読み込み、数値列を float に変換する。"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for col in numeric_cols:
            row[col] = float(row[col])
    return rows


def load_sample():
    """サンプルの顧客・サプライヤー・倉庫データを読み込む。"""
    customers = _read_csv(DATA_DIR / "customers.csv", ["lat", "lon", "demand"])
    suppliers = _read_csv(DATA_DIR / "suppliers.csv", ["lat", "lon", "supply"])
    warehouses = _read_csv(DATA_DIR / "warehouses.csv", ["lat", "lon", "capacity"])
    return customers, suppliers, warehouses


def available_solvers():
    """この環境に amplpy モジュールとしてインストールされているソルバーを返す。"""
    installed = set(modules.installed())
    return [s for s in KNOWN_SOLVERS if s in installed]


def compute_geodesic_distance(origin, destination, unit="km"):
    """2地点間の測地線距離を計算する。"""
    d = geodesic((origin["lat"], origin["lon"]), (destination["lat"], destination["lon"]))
    return d.km if unit == "km" else d.mi


def compute_arc_costs(
    suppliers,
    warehouses,
    customers,
    cost_per_unit_distance_sw,
    cost_per_unit_distance_wc,
    unit="km",
):
    """サプライヤー→倉庫、倉庫→顧客の距離と単位輸送コストを計算する。"""
    distances_sw = {}
    unit_cost_sw = {}
    for s in suppliers:
        for w in warehouses:
            d = compute_geodesic_distance(s, w, unit)
            distances_sw[(s["ID"], w["ID"])] = d
            unit_cost_sw[(s["ID"], w["ID"])] = d * cost_per_unit_distance_sw

    distances_wc = {}
    unit_cost_wc = {}
    for w in warehouses:
        for c in customers:
            d = compute_geodesic_distance(w, c, unit)
            distances_wc[(w["ID"], c["ID"])] = d
            unit_cost_wc[(w["ID"], c["ID"])] = d * cost_per_unit_distance_wc

    return distances_sw, unit_cost_sw, distances_wc, unit_cost_wc


def solve_transshipment(
    customers,
    suppliers,
    warehouses,
    cost_per_unit_distance_sw=15.0,
    cost_per_unit_distance_wc=20.0,
    unit="km",
    solver="highs",
    enforce_capacity=True,
    allow_shortage=False,
    penalty=0.0,
):
    """AMPL で積換問題のモデルを作成し、amplpy で求解する。"""
    distances_sw, unit_cost_sw, distances_wc, unit_cost_wc = compute_arc_costs(
        suppliers,
        warehouses,
        customers,
        cost_per_unit_distance_sw,
        cost_per_unit_distance_wc,
        unit,
    )

    modules.load()

    ampl = AMPL()
    ampl.eval(TRANSSHIPMENT_MODEL)

    ampl.set["SUPPLIERS"] = [s["ID"] for s in suppliers]
    ampl.set["WAREHOUSES"] = [w["ID"] for w in warehouses]
    ampl.set["CUSTOMERS"] = [c["ID"] for c in customers]
    ampl.param["supply"] = {s["ID"]: s["supply"] for s in suppliers}
    ampl.param["capacity"] = {w["ID"]: w["capacity"] for w in warehouses}
    ampl.param["demand"] = {c["ID"]: c["demand"] for c in customers}
    ampl.param["unit_cost_sw"] = unit_cost_sw
    ampl.param["unit_cost_wc"] = unit_cost_wc
    ampl.param["enforce_capacity"] = 1 if enforce_capacity else 0
    ampl.param["allow_shortage"] = 1 if allow_shortage else 0
    ampl.param["penalty"] = penalty

    ampl.option["solver"] = solver
    output = ampl.get_output("solve;")
    status = ampl.solve_result

    result = {"status": status, "solver_output": output.replace("\b", "").strip()}
    if status != "solved":
        return result

    flow_sw = ampl.var["flow_sw"].get_values().to_dict()
    flow_wc = ampl.var["flow_wc"].get_values().to_dict()
    shortage = ampl.var["shortage"].get_values().to_dict()

    flows = []
    for (s, w), v in flow_sw.items():
        if v > 1e-6:
            flows.append(
                {
                    "stage": "S→W",
                    "from_id": s,
                    "to_id": w,
                    "flow": v,
                    "distance": distances_sw[s, w],
                    "unit_cost": unit_cost_sw[s, w],
                    "cost": v * unit_cost_sw[s, w],
                }
            )
    for (w, c), v in flow_wc.items():
        if v > 1e-6:
            flows.append(
                {
                    "stage": "W→C",
                    "from_id": w,
                    "to_id": c,
                    "flow": v,
                    "distance": distances_wc[w, c],
                    "unit_cost": unit_cost_wc[w, c],
                    "cost": v * unit_cost_wc[w, c],
                }
            )

    warehouse_throughputs = {}
    for w in warehouses:
        wid = w["ID"]
        warehouse_throughputs[wid] = sum(
            v for (s, w_id), v in flow_sw.items() if w_id == wid and v > 1e-6
        )

    transport_cost = sum(f["cost"] for f in flows)
    result.update(
        objective=ampl.obj["TotalCost"].value(),
        transport_cost=transport_cost,
        flows=flows,
        shortages={c: v for c, v in shortage.items() if v > 1e-6},
        warehouse_throughputs=warehouse_throughputs,
    )
    return result
