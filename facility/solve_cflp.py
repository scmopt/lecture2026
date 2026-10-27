"""Timefold facility-location quickstart solved as an SSCFLP with AMPL/amplpy.

Usage:
    python solve_cflp.py [--data london.json] [--solvers gurobi,highs] [--timelimit 300]

The JSON is a solution saved from the Timefold quickstart UI. Its score is
recomputed here with the same rules as FacilityLocationConstraintProvider, then
the same instance is solved to optimality and both are compared.
"""

import argparse
import json
import math
import os
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from amplpy import AMPL, Environment

HERE = Path(__file__).resolve().parent
MOD_PATH = HERE / "cflp.mod"
RESULTS = HERE / "results"
DEFAULT_AMPL_PATH = Path.home() / "Documents/ampl/ampl.macos64"
METERS_PER_DEGREE = 111_000


def distance(a, b):
    # Location.getDistanceTo: ceil(euclid(deg) * 111000)
    return math.ceil(math.hypot(a[0] - b[0], a[1] - b[1]) * METERS_PER_DEGREE)


def load(path):
    P = json.load(open(path))["problem"]
    F = {f["id"]: f for f in P["facilities"]}
    C = {c["id"]: c for c in P["consumers"]}
    D = {(i, j): distance(C[i]["location"], F[j]["location"]) for i in C for j in F}
    w = {o["id"]: o["weight"] for o in P["weights"]}
    return P, F, C, D, w


def score(F, C, D, w, assign):
    """HardSoftScore of an assignment {consumer: facility} as Timefold computes it."""
    load_ = {}
    for i, j in assign.items():
        load_[j] = load_.get(j, 0) + C[i]["demand"]
    hard = -sum(max(0, d - F[j]["capacity"]) for j, d in load_.items())
    setup = sum(F[j]["setupCost"] for j in load_)
    dist = sum(D[i, j] for i, j in assign.items())
    soft = -(w["facility setup cost"] * setup + w["distance from facility"] * dist)
    return {"hard": hard, "soft": soft, "setup": setup, "distance_m": dist,
            "open": sorted(load_, key=int), "load": load_}


def make_ampl():
    ampl_path = Path(os.environ.get("AMPL_PATH", DEFAULT_AMPL_PATH))
    return AMPL(Environment(str(ampl_path))) if ampl_path.exists() else AMPL()


def build(F, C, D, w):
    ampl = make_ampl()
    ampl.read(str(MOD_PATH))
    ampl.set["FAC"] = list(F)
    ampl.set["CUS"] = list(C)
    ampl.param["setup"] = {j: F[j]["setupCost"] for j in F}
    ampl.param["cap"] = {j: F[j]["capacity"] for j in F}
    ampl.param["dem"] = {i: C[i]["demand"] for i in C}
    ampl.param["dist"] = D
    ampl.param["w_setup"] = w["facility setup cost"]
    ampl.param["w_dist"] = w["distance from facility"]
    return ampl


def solve(F, C, D, w, solver, timelimit, relax=False, strong=True):
    ampl = build(F, C, D, w)
    if not strong:
        ampl.eval("drop Link;")
    ampl.option["solver"] = solver
    ampl.option["relax_integrality"] = int(relax)
    opts = {"gurobi": f"outlev=0 timelim={timelimit}",
            "highs": f"outlev=0 timelim={timelimit}"}
    ampl.option[f"{solver}_options"] = opts[solver]
    t0 = time.perf_counter()
    ampl.solve()
    elapsed = time.perf_counter() - t0
    obj = ampl.get_objective("SoftCost").value()
    res = {"solver": solver, "relax": relax, "strong": strong, "time": elapsed,
           "obj": obj, "status": ampl.solve_result}
    if not relax:
        x = ampl.get_variable("x").get_values().to_dict()
        res["assign"] = {i: j for (i, j), v in x.items() if v > 0.5}
    return res


def plot(F, C, assign, title, path):
    fig, ax = plt.subplots(figsize=(5.0, 5.6))
    opened = set(assign.values())
    for i, j in assign.items():
        (a, b), (c, d) = C[i]["location"], F[j]["location"]
        ax.plot([b, d], [a, c], color="#9aa5b1", lw=0.8, zorder=1)
    ax.scatter([C[i]["location"][1] for i in C], [C[i]["location"][0] for i in C],
               s=14, color="#2b6cb0", label="顧客", zorder=2)
    closed = [j for j in F if j not in opened]
    ax.scatter([F[j]["location"][1] for j in closed], [F[j]["location"][0] for j in closed],
               s=40, marker="s", facecolor="white", edgecolor="#718096", label="施設（閉鎖）", zorder=3)
    ax.scatter([F[j]["location"][1] for j in opened], [F[j]["location"][0] for j in opened],
               s=70, marker="s", color="#c53030", label="施設（開設）", zorder=4)
    for j in opened:
        ax.annotate(j, (F[j]["location"][1], F[j]["location"][0]), xytext=(4, 4),
                    textcoords="offset points", fontsize=9, color="#c53030", weight="bold")
    ax.set_xlabel("経度")
    ax.set_ylabel("緯度")
    ax.set_title(title)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8, frameon=False)
    ax.set_aspect(1 / math.cos(math.radians(51.5)))
    ax.xaxis.set_major_locator(plt.MaxNLocator(4))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "london.json"))
    ap.add_argument("--solvers", default="gurobi,highs")
    ap.add_argument("--timelimit", type=float, default=300)
    args = ap.parse_args()

    plt.rcParams["font.family"] = ["Hiragino Sans", "sans-serif"]
    plt.rcParams["pdf.fonttype"] = 42
    RESULTS.mkdir(exist_ok=True)
    P, F, C, D, w = load(args.data)

    tf_assign = {c["id"]: c["facility"] for c in P["consumers"]}
    tf = score(F, C, D, w, tf_assign)
    print(f"Timefold  saved={P['score']}  recomputed={tf['hard']}hard/{tf['soft']}soft"
          f"  open={tf['open']}  setup={tf['setup']}  dist={tf['distance_m']} m")

    out = {"timefold": {**tf, "saved_score": P["score"]}, "runs": []}
    best = None
    for s in args.solvers.split(","):
        for strong in (True, False):
            lp = solve(F, C, D, w, s, args.timelimit, relax=True, strong=strong)
            ip = solve(F, C, D, w, s, args.timelimit, strong=strong)
            sc = score(F, C, D, w, ip["assign"])
            run = {"solver": s, "strong": strong, "lp": lp["obj"], "obj": ip["obj"],
                   "time": ip["time"], "status": ip["status"], **sc}
            out["runs"].append(run)
            print(f"{s:7s} {'strong' if strong else 'weak  '}  LP={lp['obj']:.1f}  IP={ip['obj']:.0f}"
                  f"  ({ip['status']}, {ip['time']:.2f}s)  open={sc['open']}")
            if best is None or ip["obj"] < best[0]["obj"] - 1e-6:
                best = (ip, sc)

    ip, sc = best
    gap = (-tf["soft"] - ip["obj"]) / ip["obj"]
    out["optimal"] = {**sc, "obj": ip["obj"], "assign": ip["assign"]}
    out["timefold_gap"] = gap
    changed = sorted((i for i in C if tf_assign[i] != ip["assign"][i]), key=int)
    out["changed_consumers"] = changed
    print(f"Optimal soft = -{ip['obj']:.0f}, Timefold gap = {100 * gap:.3f}%,"
          f" reassigned consumers = {len(changed)}")

    for d in (out["timefold"], out["optimal"]):
        d["load"] = {j: d["load"][j] for j in sorted(d["load"], key=int)}
    json.dump(out, open(RESULTS / "comparison.json", "w"), ensure_ascii=False, indent=2)

    plot(F, C, tf_assign, f"Timefold 解（{tf['hard']}hard/{tf['soft']}soft）", RESULTS / "timefold_map.pdf")
    plot(F, C, ip["assign"], f"AMPL 最適解（0hard/-{ip['obj']:.0f}soft）", RESULTS / "ampl_map.pdf")


if __name__ == "__main__":
    main()
