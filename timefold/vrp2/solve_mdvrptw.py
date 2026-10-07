"""Multi-depot VRPTW (Timefold vehicle-routing quickstart) solved with AMPL/amplpy.

Reads フィラデルフィア.json (a Timefold quickstart problem + its solution),
solves the same problem as a MIP (mdvrptw.mod) and compares the routes.

Usage:
    python timefold/vrp2/solve_mdvrptw.py [--timelimit 600] [--solvers highs,gurobi]

Set AMPL_PATH to an AMPL installation with a full license (the pip
ampl_module_base ships a size-limited demo license that cannot hold this model).
"""

import argparse
import json
import math
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import networkx as nx
import pandas as pd
from amplpy import AMPL, Environment

HERE = Path(__file__).resolve().parent
JSON_PATH = HERE.parent / "vrp" / "フィラデルフィア.json"
MOD_PATH = HERE / "mdvrptw.mod"
OUT_DIR = HERE / "results"
DEFAULT_AMPL_PATH = Path.home() / "Documents/ampl/ampl.macos64"

EARTH_RADIUS_M = 6371000.0
AVERAGE_SPEED_KMPH = 50.0


# -----------------------------------------------------------------------------
# Data (driving time identical to Timefold's HaversineDrivingTimeCalculator)
# -----------------------------------------------------------------------------
def java_round(v):
    return math.floor(v + 0.5)


def driving_seconds(p, q):
    if p == q:
        return 0
    lat1, lon1, lat2, lon2 = map(math.radians, (*p, *q))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    meters = java_round(2 * EARTH_RADIUS_M * math.asin(math.sqrt(h)))
    return java_round(meters / AVERAGE_SPEED_KMPH * 3.6)


def load_problem(path=JSON_PATH):
    raw = json.loads(path.read_text(encoding="utf-8"))
    prob = raw["problem"]
    t0 = datetime.fromisoformat(prob["startDateTime"])
    sec = lambda s: (datetime.fromisoformat(s) - t0).total_seconds()

    visits = {
        v["id"]: dict(name=v["name"], loc=v["location"], demand=v["demand"],
                      service=v["serviceDuration"], ready=sec(v["minStartTime"]), due=sec(v["maxEndTime"]))
        for v in prob["visits"]
    }
    vehicles = {
        k["id"]: dict(loc=k["homeLocation"], capacity=k["capacity"], depart=sec(k["departureTime"]))
        for k in prob["vehicles"]
    }
    routes = {k["id"]: list(k["visits"]) for k in prob["vehicles"]}  # Timefold solution
    return dict(raw=raw, t0=t0, visits=visits, vehicles=vehicles, timefold_routes=routes,
                timefold_score=raw["summary"])


# -----------------------------------------------------------------------------
# Route evaluation (Timefold score semantics)
# -----------------------------------------------------------------------------
def evaluate(P, routes):
    V, K = P["visits"], P["vehicles"]
    rows, hard, total = [], 0, 0
    for k, route in routes.items():
        t, loc, drive, load, late = K[k]["depart"], K[k]["loc"], 0, 0, 0
        for i in route:
            d = driving_seconds(loc, V[i]["loc"])
            drive += d
            t = max(t + d, V[i]["ready"]) + V[i]["service"]
            late += max(0, t - V[i]["due"])
            load += V[i]["demand"]
            loc = V[i]["loc"]
        drive += driving_seconds(loc, K[k]["loc"])
        back = t + driving_seconds(loc, K[k]["loc"]) if route else K[k]["depart"]
        over = max(0, load - K[k]["capacity"])
        hard -= over + late / 60  # Timefold: capacity overflow + late minutes
        total += drive
        rows.append(dict(vehicle=k, visits=len(route), demand=load, capacity=K[k]["capacity"],
                         driving_s=drive, return_time=str(P["t0"] + timedelta(seconds=back))[11:19],
                         late_s=late, over_capacity=over))
    assigned = sum(len(r) for r in routes.values())
    return dict(driving=total, hard=hard, assigned=assigned, per_vehicle=pd.DataFrame(rows))


# -----------------------------------------------------------------------------
# AMPL model
# -----------------------------------------------------------------------------
def make_ampl():
    ampl_path = Path(os.environ.get("AMPL_PATH", DEFAULT_AMPL_PATH))
    return AMPL(Environment(str(ampl_path))) if ampl_path.exists() else AMPL()


def build_model(P):
    V, K = P["visits"], P["vehicles"]
    ampl = make_ampl()
    ampl.read(str(MOD_PATH))

    ampl.set_data(pd.DataFrame.from_dict(
        {i: dict(demand=v["demand"], service=v["service"], ready=v["ready"], due=v["due"]) for i, v in V.items()},
        orient="index"), "VISITS")
    ampl.set_data(pd.DataFrame.from_dict(
        {k: dict(capacity=v["capacity"], depart=v["depart"]) for k, v in K.items()}, orient="index"), "VEHICLES")

    ampl.param["t_vv"] = {(i, j): driving_seconds(V[i]["loc"], V[j]["loc"]) for i in V for j in V}
    ampl.param["t_dv"] = {(k, j): driving_seconds(K[k]["loc"], V[j]["loc"]) for k in K for j in V}
    ampl.param["t_vd"] = {(i, k): driving_seconds(V[i]["loc"], K[k]["loc"]) for i in V for k in K}
    return ampl


def set_start(ampl, routes, fix=False):
    """Load a set of routes as initial values (MIP start) or fix them."""
    arcs = {tuple(a) for a in ampl.get_set("ARCS").get_values().to_list()}
    starts = {tuple(a) for a in ampl.get_set("START").get_values().to_list()}
    x = {a: 0 for a in arcs}
    y = {a: 0 for a in starts}
    z, a_ = {}, {}
    visits = ampl.get_set("VISITS").get_values().to_list()
    for i in visits:
        for k in routes:
            z[i, k] = a_[i, k] = 0
    for k, r in routes.items():
        if not r:
            continue
        y[k, r[0]] = 1
        z[r[-1], k] = 1
        for i in r:
            a_[i, k] = 1
        for i, j in zip(r, r[1:]):
            x[i, j] = 1
    for name, vals in (("x", x), ("y", y), ("z", z), ("a", a_)):
        var = ampl.get_variable(name)
        var.set_values(vals)
        if fix:
            for idx, v in vals.items():
                var[idx].fix(v)


def extract_routes(ampl, P):
    x = {k: v for k, v in ampl.get_variable("x").get_values().to_dict().items() if v > 0.5}
    y = {k: v for k, v in ampl.get_variable("y").get_values().to_dict().items() if v > 0.5}
    succ = {i: j for (i, j) in x}
    routes = {k: [] for k in P["vehicles"]}
    for (k, j) in y:
        while j is not None:
            routes[k].append(j)
            j = succ.get(j)
    return routes


def load_cuts(ampl, cuts):
    ampl.set["CUTS"] = list(range(len(cuts)))
    for c, members in enumerate(cuts):
        ampl.set["CUT_SET"][c] = members


def separate_sec(P, max_rounds=50):
    """Cutting-plane loop on the LP relaxation: add violated subtour elimination
    constraints found by max-flow/min-cut from a super depot to every visit."""
    ampl = build_model(P)
    ampl.option["solver"] = "highs"
    ampl.option["relax_integrality"] = 1
    cuts, history = [], []
    for _ in range(max_rounds):
        ampl.solve(verbose=False)
        history.append(ampl.get_objective("Total_Driving_Time").value())
        G = nx.DiGraph()
        G.add_nodes_from(["D", *P["visits"]])
        for (i, j), v in ampl.get_variable("x").get_values().to_dict().items():
            if v > 1e-6:
                G.add_edge(i, j, capacity=v)
        for (k, j), v in ampl.get_variable("y").get_values().to_dict().items():
            if v > 1e-6:
                G.add_edge("D", j, capacity=G.get_edge_data("D", j, {"capacity": 0})["capacity"] + v)
        known = {frozenset(c) for c in cuts}
        new = set()
        for t in P["visits"]:
            value, (_, sink_side) = nx.minimum_cut(G, "D", t)
            if value < 1 - 1e-4 and frozenset(sink_side) not in known:
                new.add(frozenset(sink_side))
        if not new:
            break
        cuts += [sorted(c) for c in new]
        load_cuts(ampl, cuts)
    return cuts, history


def solve(P, solver, timelimit, warm=None, fix=None, cuts=()):
    ampl = build_model(P)
    load_cuts(ampl, cuts)
    if warm:
        set_start(ampl, warm)
    if fix:
        set_start(ampl, fix, fix=True)
    ampl.option["solver"] = solver
    opts = f"outlev=1 timelimit={timelimit} mip:gap=0 mip:bestbound=1 threads=8"
    if warm:
        opts += " mip:start=1"  # Gurobi only; the HiGHS driver has no MIP start option
    ampl.option[f"{solver}_options"] = opts
    t = time.time()
    ampl.solve()
    elapsed = time.time() - t
    status = ampl.solve_result
    routes = extract_routes(ampl, P)
    if status not in ("solved", "limit") or sum(map(len, routes.values())) != len(P["visits"]):
        status, routes = "no solution", None
    obj = ampl.get_objective("Total_Driving_Time").value() if routes else float("nan")
    try:
        bound = ampl.get_value("Total_Driving_Time.bestbound")
    except Exception:
        bound = float("nan")
    n_bin = ampl.get_value("_nvars")
    n_con = ampl.get_value("_ncons")
    return dict(status=status, obj=obj, bound=bound, time=elapsed, routes=routes,
                nvars=n_bin, ncons=n_con)


# -----------------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------------
def to_timefold_json(P, routes, name):
    raw = json.loads(json.dumps(P["raw"]))
    raw["name"] = name
    for veh in raw["problem"]["vehicles"]:
        veh["visits"] = routes[veh["id"]]
    ev = evaluate(P, routes)
    raw["summary"] = f"訪問先 {ev['assigned']} 件・車両 {len(routes)} 台・総走行時間 {ev['driving']} 秒 (AMPL)"
    return raw


def plot_routes(P, results, path):
    import matplotlib.pyplot as plt

    V, K = P["visits"], P["vehicles"]
    cmap = plt.get_cmap("tab10")
    fig, axes = plt.subplots(1, len(results), figsize=(7 * len(results), 6.5), squeeze=False)
    for ax, (label, routes) in zip(axes[0], results.items()):
        for c, (k, r) in enumerate(routes.items()):
            pts = [K[k]["loc"]] + [V[i]["loc"] for i in r] + [K[k]["loc"]]
            ax.plot([p[1] for p in pts], [p[0] for p in pts], "-o", ms=3, lw=1.3, color=cmap(c), label=f"vehicle {k}")
            ax.plot(K[k]["loc"][1], K[k]["loc"][0], "s", ms=10, color=cmap(c), mec="black")
        am = [v["loc"] for v in V.values() if v["ready"] < 5 * 3600]
        ax.scatter([p[1] for p in am], [p[0] for p in am], s=40, facecolors="none", edgecolors="gray",
                   label="AM window")
        ax.set_title(f"{label}: {evaluate(P, routes)['driving']} s")
        ax.set_xlabel("longitude")
        ax.set_ylabel("latitude")
        ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)


# -----------------------------------------------------------------------------
# Experiment
# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timelimit", type=int, default=600)
    ap.add_argument("--solvers", default="highs,gurobi")
    args = ap.parse_args()
    OUT_DIR.mkdir(exist_ok=True)

    P = load_problem()
    tf = P["timefold_routes"]
    ev_tf = evaluate(P, tf)
    print(f"Timefold JSON: {P['timefold_score']}")
    print(f"  re-evaluated: hard={ev_tf['hard']}, driving={ev_tf['driving']} s")
    print(ev_tf["per_vehicle"].to_string(index=False))

    # Sanity check: the Timefold routes must be feasible in the AMPL model with the same objective
    chk = solve(P, "highs", 60, fix=tf)
    print(f"\nTimefold routes fixed in AMPL model: {chk['status']}, obj={chk['obj']:.0f}")
    assert abs(chk["obj"] - ev_tf["driving"]) < 0.5

    t = time.time()
    cuts, lp_hist = separate_sec(P)
    print(f"\nLP relaxation: {lp_hist[0]:.1f} -> {lp_hist[-1]:.1f} with {len(cuts)} subtour cuts "
          f"({len(lp_hist)} rounds, {time.time() - t:.1f}s)")

    rows = [dict(method="Timefold (JSON)", status="-", driving_s=ev_tf["driving"], bound_s=None,
                 gap_pct=None, time_s=None, hard=ev_tf["hard"], assigned=ev_tf["assigned"]),
            dict(method="LP relaxation", status="-", driving_s=None, bound_s=lp_hist[0]),
            dict(method=f"LP relaxation + {len(cuts)} SECs", status="-", driving_s=None, bound_s=lp_hist[-1])]
    route_sets = {"Timefold": tf}
    solvers = args.solvers.split(",")
    runs = [(s, None) for s in solvers] + [("gurobi", tf)] * ("gurobi" in solvers)
    for solver, warm in runs:
        label = f"AMPL+{solver}" + (" (warm start)" if warm else "")
        print(f"\n=== {label}, timelimit={args.timelimit}s ===")
        r = solve(P, solver, args.timelimit, warm=warm, cuts=cuts)
        if r["routes"] is None:
            print(f"{label}: no feasible solution, bound={r['bound']:.1f} time={r['time']:.1f}s")
            rows.append(dict(method=label, status=r["status"], driving_s=None, bound_s=r["bound"],
                             gap_pct=None, time_s=r["time"], hard=None, assigned=None))
            continue
        ev = evaluate(P, r["routes"])
        assert abs(ev["driving"] - r["obj"]) < 0.5 and ev["hard"] == 0 and ev["assigned"] == len(P["visits"])
        gap = 100 * (r["obj"] - r["bound"]) / r["obj"] if r["bound"] == r["bound"] else None
        rows.append(dict(method=label, status=r["status"], driving_s=ev["driving"], bound_s=r["bound"],
                         gap_pct=gap, time_s=r["time"], hard=ev["hard"], assigned=ev["assigned"]))
        route_sets[label] = r["routes"]
        print(f"{label}: {r['status']} obj={r['obj']:.0f} bound={r['bound']:.1f} time={r['time']:.1f}s "
              f"(vars={r['nvars']:.0f}, cons={r['ncons']:.0f})")

    table = pd.DataFrame(rows)
    table["vs_timefold_pct"] = 100 * (table["driving_s"] - ev_tf["driving"]) / ev_tf["driving"]
    table["timefold_gap_pct"] = 100 * (ev_tf["driving"] - table["bound_s"]) / ev_tf["driving"]
    table.to_csv(OUT_DIR / "comparison.csv", index=False)
    print("\n" + table.to_string(index=False))

    best_label = min((l for l in route_sets if l != "Timefold"),
                     key=lambda l: evaluate(P, route_sets[l])["driving"])
    best = route_sets[best_label]
    for k in P["vehicles"]:
        print(f"vehicle {k}\n  Timefold: {tf[k]}\n  {best_label}: {best[k]}")
    evaluate(P, best)["per_vehicle"].to_csv(OUT_DIR / "best_per_vehicle.csv", index=False)
    (OUT_DIR / "routes.json").write_text(json.dumps(route_sets, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "フィラデルフィア_ampl.json").write_text(
        json.dumps(to_timefold_json(P, best, "フィラデルフィア (AMPL)"), ensure_ascii=False, indent=1), encoding="utf-8")
    plot_routes(P, {"Timefold": tf, best_label: best}, OUT_DIR / "routes_comparison.png")
    print(f"\nResults written to {OUT_DIR}")


if __name__ == "__main__":
    main()
