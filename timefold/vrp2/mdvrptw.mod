# =============================================================================
# Multi-Depot VRP with Time Windows (Timefold vehicle-routing quickstart)
#
# 2-index arc formulation with vehicle-specific depot arcs:
#   x[i,j]  visit  -> visit arcs
#   y[k,j]  depot of vehicle k -> visit j   (first visit of vehicle k)
#   z[i,k]  visit i -> depot of vehicle k   (last visit of vehicle k)
#   a[i,k]  visit i is served by vehicle k  (carries the vehicle identity
#           along a route so that each route returns to its own depot and
#           respects that vehicle's capacity)
#
# Timefold constraints reproduced:
#   hard : vehicleCapacity, serviceFinishedAfterMaxEndTime
#   soft : minimizeTravelTime (total driving time incl. return to depot)
# All visits must be assigned (Timefold list variable without unassigned values).
# Times are in seconds measured from problem startDateTime.
# =============================================================================

set VISITS;
set VEHICLES;

param demand   {VISITS} >= 0;
param service  {VISITS} >= 0;                       # service duration
param ready    {VISITS} >= 0;                       # minStartTime
param due      {i in VISITS} >= ready[i] + service[i];  # maxEndTime

param capacity {VEHICLES} >= 0;
param depart   {VEHICLES} >= 0;                     # departureTime

param t_vv {VISITS, VISITS} >= 0;                   # visit  -> visit
param t_dv {VEHICLES, VISITS} >= 0;                 # depot  -> visit
param t_vd {VISITS, VEHICLES} >= 0;                 # visit  -> depot

# Arc pre-processing: drop arcs that cannot respect time windows / start times
set ARCS  = {i in VISITS, j in VISITS:
             i != j and ready[i] + service[i] + t_vv[i,j] + service[j] <= due[j]};
set START = {k in VEHICLES, j in VISITS:
             depart[k] + t_dv[k,j] + service[j] <= due[j]};

var x {ARCS}  binary;
var y {START} binary;
var z {VISITS, VEHICLES} binary;
var a {VISITS, VEHICLES} binary;
var T {i in VISITS} >= ready[i], <= due[i] - service[i];   # service start time

minimize Total_Driving_Time:
    sum {(i,j) in ARCS}  t_vv[i,j] * x[i,j]
  + sum {(k,j) in START} t_dv[k,j] * y[k,j]
  + sum {i in VISITS, k in VEHICLES} t_vd[i,k] * z[i,k];

# Every visit has exactly one predecessor and one successor
subject to In_Degree {j in VISITS}:
    sum {(i,j) in ARCS} x[i,j] + sum {(k,j) in START} y[k,j] = 1;

subject to Out_Degree {i in VISITS}:
    sum {(i,j) in ARCS} x[i,j] + sum {k in VEHICLES} z[i,k] = 1;

# Each vehicle leaves its depot at most once and comes back to the same depot
subject to Leave_Depot {k in VEHICLES}:
    sum {(k,j) in START} y[k,j] <= 1;

subject to Return_Depot {k in VEHICLES}:
    sum {i in VISITS} z[i,k] = sum {(k,j) in START} y[k,j];

# Vehicle identity propagation
subject to Assign {i in VISITS}:
    sum {k in VEHICLES} a[i,k] = 1;

subject to Start_Identity {(k,j) in START}:
    y[k,j] <= a[j,k];

subject to End_Identity {i in VISITS, k in VEHICLES}:
    z[i,k] <= a[i,k];

subject to Arc_Identity {(i,j) in ARCS, k in VEHICLES}:
    x[i,j] + a[i,k] - a[j,k] <= 1;

# Hard: vehicle capacity
subject to Capacity {k in VEHICLES}:
    sum {i in VISITS} demand[i] * a[i,k] <= capacity[k];

# Hard: time propagation (waiting allowed; also eliminates subtours).
# Written with arc-specific tight big-M coefficients derived from the time
# windows.  The indicator form  x[i,j] = 1 ==> T[j] >= T[i] + ...  is also
# valid, but AMPL MP's reformulation grew the model from 3,255 to 10,020
# variables with no gain (same incumbent and a similar bound with Gurobi), so
# the linear form is used here.
subject to Time_From_Depot {(k,j) in START}:
    T[j] >= depart[k] + t_dv[k,j] - (depart[k] + t_dv[k,j] - ready[j]) * (1 - y[k,j]);

subject to Time_Between_Visits {(i,j) in ARCS}:
    T[j] >= T[i] + service[i] + t_vv[i,j] - (due[i] + t_vv[i,j] - ready[j]) * (1 - x[i,j]);

# Subtour elimination cuts.  Not needed for correctness (time propagation
# already forbids cycles) but they strengthen the LP relaxation; the sets are
# filled by a min-cut separation loop in solve_mdvrptw.py.
set CUTS default {};
set CUT_SET {CUTS} within VISITS;

subject to SEC {c in CUTS}:
    sum {(i,j) in ARCS: i in CUT_SET[c] and j in CUT_SET[c]} x[i,j] <= card(CUT_SET[c]) - 1;
