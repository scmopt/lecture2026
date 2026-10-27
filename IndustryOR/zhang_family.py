"""Zhang Family Trip Optimization using AMPL and amplpy."""

from amplpy import AMPL, modules

# Load AMPL modules (HiGHS solver)
modules.load()

# Initialize AMPL
ampl = AMPL()
ampl.set_option("solver", "highs")

# Define model in AMPL syntax
model_str = """
set CHILDREN;

param cost{CHILDREN} >= 0;

var x{CHILDREN} binary;

# 目的関数: 総費用の最小化
minimize TotalCost:
    sum{c in CHILDREN} cost[c] * x[c];

# 制約条件 1: 最低3人の子供を連れて行く
subject to MinChildren:
    sum{c in CHILDREN} x[c] >= 3;

# 制約条件 2: 連れて行ける子供は最大4人
subject to MaxChildren:
    sum{c in CHILDREN} x[c] <= 4;

# 制約条件 3: 末っ子のジニーは必ず連れて行く
subject to TakeGinny:
    x['Ginny'] = 1;

# 制約条件 4: ハリーを連れて行く場合、フレッドは連れて行かない
subject to HarryNoFred:
    x['Harry'] + x['Fred'] <= 1;

# 制約条件 5: ハリーを連れて行く場合、ジョージは連れて行かない
subject to HarryNoGeorge:
    x['Harry'] + x['George'] <= 1;

# 制約条件 6: ジョージを連れて行くなら、フレッドも連れて行く
subject to GeorgeRequiresFred:
    x['George'] <= x['Fred'];

# 制約条件 7: ジョージを連れて行くなら、ハーマイオニーも連れて行く
subject to GeorgeRequiresHermione:
    x['George'] <= x['Hermione'];
"""

ampl.eval(model_str)

# データの設定
children = ["Harry", "Hermione", "Ron", "Fred", "George", "Ginny"]
costs = {
    "Harry": 1200,
    "Hermione": 1650,
    "Ron": 750,
    "Fred": 800,
    "George": 800,
    "Ginny": 1500,
}

ampl.set["CHILDREN"] = children
ampl.param["cost"] = costs

# 最適化の実行
ampl.solve()

# 結果の表示
total_cost = ampl.obj["TotalCost"].value()
print("=" * 40)
print(f"Optimal Total Cost: ${total_cost:.2f}")
print("=" * 40)
print("Selected Children:")
for c in children:
    val = ampl.var["x"][c].value()
    status = "連れて行く (選出)" if val > 0.5 else "連れて行かない"
    print(f"  - {c:<10}: {status} (費用: ${costs[c]})")
