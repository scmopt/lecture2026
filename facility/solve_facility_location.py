"""
Timefold facility-location quickstart CFLP Solver using AMPL (amplpy)
"""

import json
import math
from amplpy import AMPL


def calculate_distance(loc1, loc2):
    """
    Timefold quickstart distance formula (meters):
    ceil(sqrt((lat1 - lat2)^2 + (lon1 - lon2)^2) * 111000)
    """
    dlat = loc1[0] - loc2[0]
    dlon = loc1[1] - loc2[1]
    return int(math.ceil(math.sqrt(dlat * dlat + dlon * dlon) * 111000))


def solve_facility_location(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    problem = data.get("problem", data)
    facilities = problem["facilities"]
    consumers = problem["consumers"]

    # Read weights
    weights = {w["id"]: w["weight"] for w in problem.get("weights", [])}
    w_setup = weights.get("facility setup cost", 2)
    w_dist = weights.get("distance from facility", 6)

    # 1. Evaluate JSON solution (Timefold)
    fac_map = {f["id"]: f for f in facilities}
    json_assignment = {c["id"]: c.get("facility") for c in consumers}
    json_open_facs = sorted(set(f for f in json_assignment.values() if f), key=int)
    json_setup_cost = sum(fac_map[fid]["setupCost"] for fid in json_open_facs)
    json_dist = sum(
        calculate_distance(c["location"], fac_map[c["facility"]]["location"])
        for c in consumers
        if c.get("facility")
    )
    json_soft_score = -(w_setup * json_setup_cost + w_dist * json_dist)

    # 2. Build and solve AMPL model
    ampl = AMPL()
    ampl.eval(
        """
    set CUSTOMERS;
    set FACILITIES;

    param demand{CUSTOMERS};
    param capacity{FACILITIES};
    param setup_cost{FACILITIES};
    param dist{CUSTOMERS, FACILITIES};
    param w_setup;
    param w_dist;

    # Decision variables
    var y{FACILITIES} binary;            # 1 if facility is opened
    var x{CUSTOMERS, FACILITIES} binary; # 1 if customer i is served by facility j

    # Objective: Minimize total weighted penalty (setup cost + distance)
    minimize TotalCost:
        sum{j in FACILITIES} w_setup * setup_cost[j] * y[j]
        + sum{i in CUSTOMERS, j in FACILITIES} w_dist * dist[i, j] * x[i, j];

    # Each customer must be assigned to exactly one facility
    s.t. AssignOnce{i in CUSTOMERS}:
        sum{j in FACILITIES} x[i, j] = 1;

    # Capacity constraint for each facility
    s.t. Capacity{j in FACILITIES}:
        sum{i in CUSTOMERS} demand[i] * x[i, j] <= capacity[j] * y[j];

    # Strengthening constraint (tightens LP relaxation)
    s.t. Linking{i in CUSTOMERS, j in FACILITIES}:
        x[i, j] <= y[j];
    """
    )

    c_ids = [c["id"] for c in consumers]
    f_ids = [f["id"] for f in facilities]

    ampl.set["CUSTOMERS"] = c_ids
    ampl.set["FACILITIES"] = f_ids
    ampl.param["w_setup"] = w_setup
    ampl.param["w_dist"] = w_dist
    ampl.param["demand"] = {c["id"]: c["demand"] for c in consumers}
    ampl.param["capacity"] = {f["id"]: f["capacity"] for f in facilities}
    ampl.param["setup_cost"] = {f["id"]: f["setupCost"] for f in facilities}

    dist_matrix = {
        (c["id"], f["id"]): calculate_distance(c["location"], f["location"])
        for c in consumers
        for f in facilities
    }
    ampl.param["dist"] = dist_matrix

    ampl.option["solver"] = "highs"
    ampl.solve()

    # 3. Retrieve AMPL solution
    obj_val = ampl.get_objective("TotalCost").value()
    ampl_soft_score = -int(round(obj_val))

    y_sol = ampl.get_variable("y").get_values().to_dict()
    ampl_open_facs = sorted([j for j, val in y_sol.items() if val > 0.5], key=int)

    x_sol = ampl.get_variable("x").get_values().to_dict()
    ampl_assignment = {i: j for (i, j), val in x_sol.items() if val > 0.5}

    ampl_setup_cost = sum(fac_map[fid]["setupCost"] for fid in ampl_open_facs)
    ampl_dist = sum(
        dist_matrix[(i, ampl_assignment[i])] for i in c_ids
    )

    # 4. Print Comparison Report
    print("=" * 65)
    print("  Facility Location Problem (CFLP) Comparison Report")
    print("=" * 65)
    print(f"{'Metric':<25} | {'JSON (Timefold)':<18} | {'AMPL (Optimal)':<18}")
    print("-" * 65)
    print(f"{'Status':<25} | {'Heuristic':<18} | {'Global Optimal':<18}")
    print(f"{'Soft Score':<25} | {json_soft_score:<18} | {ampl_soft_score:<18}")
    print(f"{'Total Cost (Objective)':<25} | {-json_soft_score:<18} | {-ampl_soft_score:<18}")
    print(f"{'Opened Facilities Count':<25} | {len(json_open_facs):<18} | {len(ampl_open_facs):<18}")
    print(f"{'Total Setup Cost':<25} | {json_setup_cost:<18} | {ampl_setup_cost:<18}")
    print(f"{'Total Distance (m)':<25} | {json_dist:<18} | {ampl_dist:<18}")
    print(f"{'Setup Cost Contribution':<25} | {w_setup * json_setup_cost:<18} | {w_setup * ampl_setup_cost:<18}")
    print(f"{'Distance Contribution':<25} | {w_dist * json_dist:<18} | {w_dist * ampl_dist:<18}")
    improvement = (-json_soft_score) - (-ampl_soft_score)
    improvement_pct = (improvement / (-json_soft_score)) * 100
    print("-" * 65)
    print(f"Improvement: {improvement:,} points ({improvement_pct:.2f}% cost reduction)")
    print("=" * 65)

    print("\n[Opened Facilities]")
    print(f"  - JSON (Timefold): {json_open_facs}")
    print(f"  - AMPL (Optimal) : {ampl_open_facs}")
    common_facs = sorted(set(json_open_facs) & set(ampl_open_facs), key=int)
    only_json = sorted(set(json_open_facs) - set(ampl_open_facs), key=int)
    only_ampl = sorted(set(ampl_open_facs) - set(json_open_facs), key=int)
    print(f"  - Shared facilities: {common_facs}")
    print(f"  - Closed by AMPL   : {only_json}")
    print(f"  - Newly opened     : {only_ampl}")

    diff_customers = [i for i in c_ids if json_assignment[i] != ampl_assignment[i]]
    print(f"\n[Customer Assignments]")
    print(f"  - Customers reassigned: {len(diff_customers)} / {len(c_ids)}")

    print("\n[Facility Utilization Comparison]")
    print(f"{'Facility':<10} | {'Capacity':<10} | {'SetupCost':<10} | {'JSON Demand':<12} | {'AMPL Demand':<12}")
    print("-" * 65)
    all_facs = sorted(set(json_open_facs + ampl_open_facs), key=int)
    for fid in all_facs:
        j_dem = sum(c["demand"] for c in consumers if json_assignment[c["id"]] == fid)
        a_dem = sum(c["demand"] for c in consumers if ampl_assignment[c["id"]] == fid)
        print(
            f"{fid:<10} | {fac_map[fid]['capacity']:<10} | {fac_map[fid]['setupCost']:<10} | {j_dem:<12} | {a_dem:<12}"
        )
    print("=" * 65)


if __name__ == "__main__":
    solve_facility_location("ロンドン（施設 30・顧客 60）.json")
