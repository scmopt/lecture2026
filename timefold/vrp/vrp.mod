# AMPL Model for Timefold Vehicle Routing Problem with Time Windows (VRPTW)

# -----------------------------------------------------------------------------
# Sets
# -----------------------------------------------------------------------------
set VISITS;                                   # Set of customer visits V = {1..n}
param depot_id symbolic default "0";          # Depot identifier
set NODES = VISITS union {depot_id};          # All nodes N = V union {0}
set VEHICLES;                                 # Set of available vehicles K = {1..m}

# -----------------------------------------------------------------------------
# Parameters
# -----------------------------------------------------------------------------
param demand{VISITS} >= 0;                    # Demand d_i at visit i
param capacity{VEHICLES} >= 0;                # Capacity C_k of vehicle k
param travel_time{NODES, NODES, VEHICLES} >= 0; # Travel time t_{i,j,k} from node i to node j for vehicle k
param service_duration{VISITS} >= 0;          # Service duration s_i at visit i
param min_start_time{VISITS} >= 0;            # Earliest service start time a_i
param max_end_time{VISITS} >= 0;              # Maximum service completion time b_i

param M > 0 default 100000;                   # Big-M parameter
param W_medium > 0 default 10000;             # Weight for unassigned visit penalty (Medium)
param W_soft > 0 default 1;                   # Weight for total travel time (Soft)

# -----------------------------------------------------------------------------
# Decision Variables
# -----------------------------------------------------------------------------
var x{NODES, NODES, VEHICLES} binary;         # x[i,j,k] = 1 if vehicle k travels from i to j
var S{NODES} >= 0;                            # Service start time at node i
var u{VISITS} binary;                         # u[i] = 1 if visit i is unassigned

# -----------------------------------------------------------------------------
# Objective Function
# Minimize unassigned visit penalty (Medium level) + total travel time (Soft level)
# -----------------------------------------------------------------------------
minimize Total_Cost:
    W_medium * sum {i in VISITS} u[i]
  + W_soft * sum {k in VEHICLES, i in NODES, j in NODES: i != j} travel_time[i,j,k] * x[i,j,k];

# -----------------------------------------------------------------------------
# Constraints
# -----------------------------------------------------------------------------

# 1. Visit Assignment Constraint: Each visit is served at most once
subject to Visit_Assignment {i in VISITS}:
    sum {k in VEHICLES, j in NODES: j != i} x[i,j,k] = 1 - u[i];

# 2. Flow Conservation Constraint: Vehicles entering node i must leave node i
subject to Flow_Conservation {i in VISITS, k in VEHICLES}:
    sum {j in NODES: j != i} x[i,j,k] - sum {j in NODES: j != i} x[j,i,k] = 0;

# 3. Depot Departure Constraint: Each vehicle departs from depot at most once
subject to Depot_Departure {k in VEHICLES}:
    sum {j in VISITS} x[depot_id, j, k] <= 1;

# 4. Depot Return Constraint: Each vehicle returning to depot must match departure
subject to Depot_Return {k in VEHICLES}:
    sum {i in VISITS} x[i, depot_id, k] = sum {j in VISITS} x[depot_id, j, k];

# 5. Vehicle Capacity Constraint (Hard)
subject to Vehicle_Capacity {k in VEHICLES}:
    sum {i in VISITS} demand[i] * (sum {j in NODES: j != i} x[i,j,k]) <= capacity[k];

# 6. Service Start Time Propagation & Subtour Elimination (Hard)
subject to Time_Propagation {i in NODES, j in VISITS, k in VEHICLES: i != j}:
    S[i] + (if i in VISITS then service_duration[i] else 0) + travel_time[i,j,k] 
    - M * (1 - x[i,j,k]) <= S[j];

# 7. Minimum Start Time Constraint (Earliest Arrival)
subject to Min_Start_Time {i in VISITS}:
    S[i] >= min_start_time[i];

# 8. Maximum End Time Constraint (Hard: Service completed before max_end_time)
subject to Max_End_Time {i in VISITS}:
    S[i] + service_duration[i] <= max_end_time[i];
