import json
import math
from datetime import datetime
from amplpy import AMPL, modules

modules.load()

def haversine_distance_meters(loc1, loc2):
    R = 6371000.0
    lat1, lon1 = math.radians(loc1[0]), math.radians(loc1[1])
    lat2, lon2 = math.radians(loc2[0]), math.radians(loc2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def compute_travel_time_seconds(loc1, loc2, speed_kmh=50.0):
    dist_m = haversine_distance_meters(loc1, loc2)
    speed_mps = (speed_kmh * 1000.0) / 3600.0
    return round(dist_m / speed_mps)

def main():
    json_path = "timefold/vrp/フィラデルフィア.json"

    print(f"Reading data from {json_path}...")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)["problem"]

    start_dt = datetime.fromisoformat(data["startDateTime"])
    vehicles = data["vehicles"]
    visits = data["visits"]

    visit_ids = [str(v["id"]) for v in visits]
    vehicle_ids = [str(v["id"]) for v in vehicles]
    depot_ids = [f"depot_{v['id']}" for v in vehicles]
    all_nodes = visit_ids + depot_ids

    visit_map = {str(v["id"]): v for v in visits}
    vehicle_map = {str(v["id"]): v for v in vehicles}
    home_depot_map = {str(v["id"]): f"depot_{v['id']}" for v in vehicles}

    node_loc_map = {}
    for vid in visit_ids:
        node_loc_map[vid] = visit_map[vid]["location"]
    for vk in vehicle_ids:
        node_loc_map[f"depot_{vk}"] = vehicle_map[vk]["homeLocation"]

    # Inline updated AMPL model for MDVRPTW
    model_str = """
    set VISITS;
    set DEPOTS;
    set NODES = VISITS union DEPOTS;
    set VEHICLES;

    param home_depot{VEHICLES} symbolic in DEPOTS;
    param demand{VISITS} >= 0;
    param capacity{VEHICLES} >= 0;
    param travel_time{NODES, NODES, VEHICLES} >= 0;
    param service_duration{VISITS} >= 0;
    param min_start_time{VISITS} >= 0;
    param max_end_time{VISITS} >= 0;
    param departure_time{VEHICLES} >= 0 default 0;

    param M_time{NODES} >= 0;
    param W_medium > 0 default 1000000;
    param W_soft > 0 default 1;

    var x{NODES, NODES, VEHICLES} binary;
    var S{NODES} >= 0;
    var u{VISITS} binary;

    minimize Total_Cost:
        W_medium * sum {i in VISITS} u[i]
      + W_soft * sum {k in VEHICLES, i in NODES, j in NODES: i != j} travel_time[i,j,k] * x[i,j,k];

    subject to Visit_Assignment {i in VISITS}:
        sum {k in VEHICLES, j in NODES: j != i} x[i,j,k] = 1 - u[i];

    subject to Flow_Conservation {i in VISITS, k in VEHICLES}:
        sum {j in NODES: j != i} x[i,j,k] - sum {j in NODES: j != i} x[j,i,k] = 0;

    subject to Depot_Departure {k in VEHICLES}:
        sum {j in VISITS} x[home_depot[k], j, k] <= 1;

    subject to No_Other_Depot_Departure {k in VEHICLES, d in DEPOTS: d != home_depot[k]}:
        sum {j in NODES: j != d} x[d, j, k] = 0;

    subject to Depot_Return {k in VEHICLES}:
        sum {i in VISITS} x[i, home_depot[k], k] = sum {j in VISITS} x[home_depot[k], j, k];

    subject to No_Other_Depot_Return {k in VEHICLES, d in DEPOTS: d != home_depot[k]}:
        sum {i in NODES: i != d} x[i, d, k] = 0;

    subject to Vehicle_Capacity {k in VEHICLES}:
        sum {i in VISITS} demand[i] * (sum {j in NODES: j != i} x[i,j,k]) <= capacity[k];

    subject to Time_Propagation {i in NODES, j in VISITS, k in VEHICLES: i != j}:
        (if i in VISITS then S[i] + service_duration[i] else departure_time[k]) + travel_time[i,j,k] 
        - M_time[i] * (1 - x[i,j,k]) <= S[j];

    subject to Min_Start_Time {i in VISITS}:
        S[i] >= min_start_time[i];

    subject to Max_End_Time {i in VISITS}:
        S[i] + service_duration[i] <= max_end_time[i];
    """

    ampl = AMPL()
    ampl.eval(model_str)

    ampl.get_set("VISITS").set_values(visit_ids)
    ampl.get_set("DEPOTS").set_values(depot_ids)
    ampl.get_set("VEHICLES").set_values(vehicle_ids)
    ampl.get_parameter("home_depot").set_values(home_depot_map)

    demand_data = {vid: visit_map[vid]["demand"] for vid in visit_ids}
    service_dur_data = {vid: visit_map[vid]["serviceDuration"] for vid in visit_ids}
    
    min_st_data = {}
    max_et_data = {}
    for vid in visit_ids:
        v = visit_map[vid]
        min_st = (datetime.fromisoformat(v["minStartTime"]) - start_dt).total_seconds()
        max_et = (datetime.fromisoformat(v["maxEndTime"]) - start_dt).total_seconds()
        min_st_data[vid] = max(0.0, min_st)
        max_et_data[vid] = max_et

    departure_time_data = {}
    for vk in vehicle_ids:
        v = vehicle_map[vk]
        dep_st = (datetime.fromisoformat(v["departureTime"]) - start_dt).total_seconds()
        departure_time_data[vk] = max(0.0, dep_st)

    ampl.get_parameter("demand").set_values(demand_data)
    ampl.get_parameter("service_duration").set_values(service_dur_data)
    ampl.get_parameter("min_start_time").set_values(min_st_data)
    ampl.get_parameter("max_end_time").set_values(max_et_data)
    ampl.get_parameter("departure_time").set_values(departure_time_data)

    capacity_data = {vid: vehicle_map[vid]["capacity"] for vid in vehicle_ids}
    ampl.get_parameter("capacity").set_values(capacity_data)

    travel_time_tuples = {}
    for k in vehicle_ids:
        for i in all_nodes:
            for j in all_nodes:
                if i == j:
                    travel_time_tuples[(i, j, k)] = 0
                else:
                    travel_time_tuples[(i, j, k)] = compute_travel_time_seconds(node_loc_map[i], node_loc_map[j])

    ampl.get_parameter("travel_time").set_values(travel_time_tuples)

    # Tight M_time for each node i
    M_time_data = {}
    for did in depot_ids:
        M_time_data[did] = 86400.0
    for vid in visit_ids:
        max_tt = max(travel_time_tuples[(vid, j, k)] for j in all_nodes for k in vehicle_ids)
        M_time_data[vid] = max_et_data[vid] + service_dur_data[vid] + max_tt

    ampl.get_parameter("M_time").set_values(M_time_data)

    ampl.set_option("solver", "highs")
    ampl.set_option("highs_options", "outlev=1 timelimit=60 mip_rel_gap=0.01")

    print("\nSolving Multi-Depot VRPTW with HiGHS (tight M & 60s limit)...")
    ampl.solve()

    print("\n--- Optimization Result ---")
    obj_val = ampl.get_objective("Total_Cost").value()
    print(f"Total Objective Cost: {obj_val:.2f}")

    u_var = ampl.get_variable("u").get_values().to_dict()
    unassigned_count = sum(1 for v, val in u_var.items() if val > 0.5)
    print(f"Assigned Visits: {len(visit_ids) - unassigned_count} / {len(visit_ids)} (Unassigned: {unassigned_count})")

    x_var = ampl.get_variable("x").get_values().to_dict()

    total_driving_time = 0
    for k in vehicle_ids:
        h_depot = home_depot_map[k]
        route = []
        curr = h_depot
        visited_set = set()
        
        while True:
            next_node = None
            for j in all_nodes:
                if curr != j and x_var.get((curr, j, k), 0) > 0.5:
                    next_node = j
                    break
            if not next_node or next_node in visited_set or next_node == h_depot:
                if next_node == h_depot:
                    route.append(h_depot)
                break
            route.append(next_node)
            visited_set.add(next_node)
            curr = next_node

        if route and len(route) > 1:
            veh_driving_time = 0
            prev = h_depot
            route_nodes = route if route[-1] == h_depot else route + [h_depot]
            for node in route_nodes:
                veh_driving_time += travel_time_tuples[(prev, node, k)]
                prev = node
            total_driving_time += veh_driving_time

            visit_nodes = [node for node in route_nodes if node in visit_ids]
            print(f"\nVehicle {k} (Depot: {h_depot}, Capacity: {capacity_data[k]}):")
            print(f"  Route ({len(visit_nodes)} visits): {h_depot} -> {' -> '.join(visit_nodes)} -> {h_depot}")
            print(f"  Driving Time: {veh_driving_time} s ({veh_driving_time/3600:.2f} h)")

    print(f"\nTotal Travel Time across assigned vehicles: {total_driving_time} s ({total_driving_time/3600:.2f} h)")

if __name__ == "__main__":
    main()

