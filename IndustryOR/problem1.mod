# Problem 1: Children Vacation Selection (IP)
# Minimizing travel costs for the Zhang family

set CHILDREN;

param cost{CHILDREN} >= 0;

# Decision variables: 1 if child c is selected, 0 otherwise
var take{CHILDREN} binary;

# Objective: Minimize total travel cost
minimize TotalCost:
    sum {c in CHILDREN} cost[c] * take[c];

# 1. At most 4 children
subject to MaxChildren:
    sum {c in CHILDREN} take[c] <= 4;

# 2. At least 3 children
subject to MinChildren:
    sum {c in CHILDREN} take[c] >= 3;

# 3. Ginny must be taken
subject to MustTakeGinny:
    take["Ginny"] = 1;

# 4. If Harry is taken, Fred is NOT taken
subject to ConflictHarryFred:
    take["Harry"] + take["Fred"] <= 1;

# 5. If Harry is taken, George is NOT taken
subject to ConflictHarryGeorge:
    take["Harry"] + take["George"] <= 1;

# 6. If George is taken, Fred must also be taken
subject to GeorgeRequiresFred:
    take["George"] <= take["Fred"];

# 7. If George is taken, Hermione must also be taken
subject to GeorgeRequiresHermione:
    take["George"] <= take["Hermione"];
