import json
import math
from datetime import datetime
from amplpy import AMPL, modules

# Load amplpy solver modules (HiGHS / CBC)
modules.load()

def haversine_distance_meters(loc1, loc2):
    R = 6371000.0  # Earth radius in meters
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
    mod_path = "timefold/vrp/vrp.mod"

    print(f"Reading data from {json_path}...")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)["problem"]

    start_dt = datetime.fromisoformat(data["startDateTime"])
    vehicles = data["vehicles"]
    visits = data["visits"]

    visit_ids = [str(v["id"]) for v in visits]
    vehicle_ids = [str(v["id"]) for v in vehicles]
    depot_id = "0"
    all_nodes = [depot_id] + visit_ids

    print(f"Visits: {len(visit_ids)}, Vehicles: {len(vehicle_ids)}")

    # Map visit ID -> object
    visit_map = {str(v["id"]): v for v in visits}
    vehicle_map = {str(v["id"]): v for v in vehicles}

    # Initialize AMPL
    ampl = AMPL()
    ampl.read(mod_path)

    # 1. Set VISITS and VEHICLES
    ampl.get_set("VISITS").set_values(visit_ids)
    ampl.get_set("VEHICLES").set_values(vehicle_ids)

    # 2. Demand, service_duration, min_start_time, max_end_time
    demand_data = {vid: visit_map[vid]["demand"] for vid in visit_ids}
    service_dur_data = {vid: visit_map[vid]["serviceDuration"] for vid in visit_ids}
    
    min_st_data = {}
    max_et_data = {}
    for vid in visit_ids:
        v = visit_map[vid]
        min_st = (datetime.fromisoformat(v["minStartTime"]) - start_dt).total_seconds()
        max_et = (datetime.fromisoformat(v["maxEndTime"]) - start_dt).total_seconds()
        min_st_data[vid] = max(0, min_st)
        max_et_data[vid] = max_et

    ampl.get_parameter("demand").set_values(demand_data)
    ampl.get_parameter("service_duration").set_values(service_dur_data)
    ampl.get_parameter("min_start_time").set_values(min_st_data)
    ampl.get_parameter("max_end_time").set_values(max_et_data)

    # 3. Vehicle Capacity
    capacity_data = {vid: vehicle_map[vid]["capacity"] for vid in vehicle_ids}
    ampl.get_parameter("capacity").set_values(capacity_data)

    # 4. Travel Time Matrix: travel_time[i, j, k]
    travel_time_tuples = {}
    for k in vehicle_ids:
        veh_home = vehicle_map[k]["homeLocation"]
        for i in all_nodes:
            loc_i = veh_home if i == depot_id else visit_map[i]["location"]
            for j in all_nodes:
                if i == j:
                    travel_time_tuples[(i, j, k)] = 0
                else:
                    loc_j = veh_home if j == depot_id else visit_map[j]["location"]
                    travel_time_tuples[(i, j, k)] = compute_travel_time_seconds(loc_i, loc_j)

    ampl.get_parameter("travel_time").set_values(travel_time_tuples)

    # Configure Solver
    ampl.set_option("solver", "highs")
    ampl.set_option("highs_options", "outlev=1 timelimit=60")

    print("\nSolving VRPTW with HiGHS...")
    ampl.solve()

    print("\n--- Optimization Result ---")
    solve_result = ampl.get_value("solve_result")
    print(f"Solver Status: {solve_result}")
    
    obj_val = ampl.get_objective("Total_Cost").value()
    print(f"Total Objective Cost: {obj_val:.2f}")

    # Inspect decision variables
    u_var = ampl.get_variable("u").get_values().to_dict()
    unassigned_count = sum(1 for v, val in u_var.items() if val > 0.5)
    print(f"Unassigned Visits: {unassigned_count} / {len(visit_ids)}")

    x_var = ampl.get_variable("x").get_values().to_dict()
    S_var = ampl.get_variable("S").get_values().to_dict()

    total_driving_time = 0
    for k in vehicle_ids:
        route = []
        curr = depot_id
        while True:
            next_node = None
            for j in all_nodes:
                if curr != j and x_var.get((curr, j, k), 0) > 0.5:
                    next_node = j
                    break
            if not next_node or next_node == depot_id:
                break
            route.append(next_node)
            curr = next_node

        if route:
            veh_driving_time = 0
            prev = depot_id
            for node in route + [depot_id]:
                veh_driving_time += travel_time_tuples[(prev, node, k)]
                prev = node
            total_driving_time += veh_driving_time

            print(f"\nVehicle {k} (Capacity: {capacity_data[k]}):")
            print(f"  Route ({len(route)} visits): {' -> '.join(route)}")
            print(f"  Driving Time: {veh_driving_time} s ({veh_driving_time/3600:.2f} h)")

    print(f"\nTotal Travel Time across all vehicles: {total_driving_time} s")

if __name__ == "__main__":
    main()
