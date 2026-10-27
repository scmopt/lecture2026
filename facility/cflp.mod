# Single-source Capacitated Facility Location Problem (SSCFLP)
# Timefold facility-location quickstart の HardSoftScore を再現:
#   hard : 施設容量制約（違反ゼロを制約として課す）
#   soft : w_setup * 開設費用合計 + w_dist * 顧客-施設距離合計 を最小化

set FAC;                      # 施設候補
set CUS;                      # 顧客

param setup {FAC} >= 0;       # 開設費用
param cap   {FAC} >= 0;       # 容量
param dem   {CUS} >= 0;       # 需要
param dist  {CUS, FAC} >= 0;  # 距離 [m]（Timefold と同じ切り上げ整数）

param w_setup default 2;      # "facility setup cost"    の重み
param w_dist  default 6;      # "distance from facility" の重み

var y {FAC} binary;           # 施設 j を開設するなら 1
var x {CUS, FAC} binary;      # 顧客 i を施設 j に割り当てるなら 1

minimize SoftCost:
    w_setup * sum {j in FAC} setup[j] * y[j]
  + w_dist  * sum {i in CUS, j in FAC} dist[i,j] * x[i,j];

subject to Assign {i in CUS}:
    sum {j in FAC} x[i,j] = 1;

subject to Capacity {j in FAC}:
    sum {i in CUS} dem[i] * x[i,j] <= cap[j] * y[j];

# 強い定式化（LP 緩和を引き締める変数上界）
subject to Link {i in CUS, j in FAC}:
    x[i,j] <= y[j];
