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
    depot_ids = [f"depot_{v['id']}" for v in vehicles]
    all_nodes = visit_ids + depot_ids

    print(f"Visits: {len(visit_ids)}, Vehicles: {len(vehicle_ids)}, Depots: {len(depot_ids)}")

    visit_map = {str(v["id"]): v for v in visits}
    vehicle_map = {str(v["id"]): v for v in vehicles}
    home_depot_map = {str(v["id"]): f"depot_{v['id']}" for v in vehicles}

    node_loc_map = {}
    for vid in visit_ids:
        node_loc_map[vid] = visit_map[vid]["location"]
    for vk in vehicle_ids:
        node_loc_map[f"depot_{vk}"] = vehicle_map[vk]["homeLocation"]

    # 1. Evaluate Initial Solution in JSON
    print("\n--- 1. Evaluating Solution in フィラデルフィア.json ---")
    json_total_driving = 0
    json_assigned_count = 0

    for k in vehicle_ids:
        v_list = vehicle_map[k]["visits"]
        h_depot = home_depot_map[k]
        cap = vehicle_map[k]["capacity"]
        json_assigned_count += len(v_list)
        
        veh_driving = 0
        curr_loc = vehicle_map[k]["homeLocation"]
        for vid in v_list:
            v_loc = visit_map[vid]["location"]
            veh_driving += compute_travel_time_seconds(curr_loc, v_loc)
            curr_loc = v_loc
        veh_driving += compute_travel_time_seconds(curr_loc, vehicle_map[k]["homeLocation"])
        
        json_total_driving += veh_driving
        print(f"Vehicle {k} (Depot: {h_depot}, Capacity: {cap}):")
        print(f"  Route ({len(v_list)} visits): {h_depot} -> {' -> '.join(v_list)} -> {h_depot}")
        print(f"  Driving Time: {veh_driving} s ({veh_driving/3600:.2f} h)")

    print(f"JSON Solution Summary:")
    print(f"  Assigned Visits: {json_assigned_count} / {len(visit_ids)}")
    print(f"  Total Driving Time: {json_total_driving} s ({json_total_driving/3600:.2f} h / ~{json_total_driving*50/3600:.1f} km at 50km/h)")

    # 2. Setup AMPL MDVRPTW Model
    print("\n--- 2. Setting up AMPL MDVRPTW Model ---")
    ampl = AMPL()
    ampl.read(mod_path)

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

    departure_time_data = {vk: 0.0 for vk in vehicle_ids}

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

    # Configure Solver
    ampl.set_option("solver", "highs")
    ampl.set_option("highs_options", "outlev=1 timelimit=60 mip_rel_gap=0.01")

    print("\nSolving Multi-Depot VRPTW (MDVRPTW) with HiGHS...")
    ampl.solve()

    print("\n--- 3. MIP Optimization Result ---")
    solve_result = ampl.get_value("solve_result")
    print(f"Solver Status: {solve_result}")
    
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


