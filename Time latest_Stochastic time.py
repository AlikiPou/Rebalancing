import sys
import math
import random
from itertools import permutations
import numpy as np
import gurobipy as grb
import pandas as pd
import itertools
from collections import defaultdict
from pathlib import Path

# ============================================================
# 1. General settings
# ============================================================

# Folder with the original optimization instance files
foldername = Path(r"C:\Users\aliki\PycharmProjects\Latest version 18.09\Instances\ZeroDemand")

# Folder for solution files
solution_folder = Path("SolutionsTimeStochastic/ZeroDemand")
solution_folder.mkdir(parents=True, exist_ok=True)

# Stochastic travel-time / cost scenario file
# scenario_id, from_node, to_node, stochastic_time
time_scenario_file = Path(
    r"C:\Users\aliki\OneDrive\Jobs - Companies\NTUA\5. Papers\7. Rebalancing 2\dott data\Net bike change\stochastic_time_scenarios.csv"
)

# Number of scenarios to use
# This is |S| in the mathematical formulation
number_of_scenarios_to_use = 100

# Random seed for selecting a subset of scenarios
run_seed = 123

# Lognormal dispersion parameter
# Suggested initial value: 0.20
travel_time_sigma = 0.20

# Penalty for unmet demand
p = 1500

# Big M
M = 100000

# Number of vehicles
K = 2

# Percentage 𝛽 that needs to be reached or exceeded out of the total number of uncertain scenarios |S|
beta = 0.90

# ============================================================
# 2. Data files
# ============================================================

datafiles = []
'''
datafiles.append("Coordinates_7_Athens.txt")

datafiles.append("Coordinates_12_RC_NYC.txt")
datafiles.append("Coordinates_12_Cluster_NYC.txt")
'''
datafiles.append("Coordinates_12_Random_Ber.txt")
'''
datafiles.append("Coordinates_12_RC_Ber.txt")
datafiles.append("Coordinates_12_Cluster_Ber.txt")
datafiles.append("Coordinates_12_RC_Bar.txt")
datafiles.append("Coordinates_12_Random_Bar.txt")
datafiles.append("Coordinates_12_Cluster_Bar.txt")
datafiles.append("Coordinates_12_RC_PoA.txt")
datafiles.append("Coordinates_12_Random_PoA.txt")
datafiles.append("Coordinates_12_Cluster_PoA.txt")
datafiles.append("Coordinates_12_Random_NYC.txt")

datafiles.append("Coordinates_15_Cluster_NYC.txt")
datafiles.append("Coordinates_15_RC_NYC.txt")
datafiles.append("Coordinates_15_Random_NYC.txt")
datafiles.append("Coordinates_15_Cluster_Ber.txt")
datafiles.append("Coordinates_15_RC_Ber.txt")
datafiles.append("Coordinates_15_Random_Ber.txt")
datafiles.append("Coordinates_15_Cluster_Bar.txt")
datafiles.append("Coordinates_15_RC_Bar.txt")
datafiles.append("Coordinates_15_Random_Bar.txt")
datafiles.append("Coordinates_15_Cluster_PoA.txt")
datafiles.append("Coordinates_15_RC_PoA.txt")
datafiles.append("Coordinates_15_Random_PoA.txt")

datafiles.append("Coordinates_20_RC_NYC.txt")
datafiles.append("Coordinates_20_Random_NYC.txt")
datafiles.append("Coordinates_20_Cluster_NYC.txt")
datafiles.append("Coordinates_20_RC_Ber.txt")
datafiles.append("Coordinates_20_Random_PoA.txt")
datafiles.append("Coordinates_20_Random_Ber.txt")
datafiles.append("Coordinates_20_Cluster_Ber.txt")
datafiles.append("Coordinates_20_RC_Bar.txt")
datafiles.append("Coordinates_20_Random_Bar.txt")
datafiles.append("Coordinates_20_Cluster_Bar.txt")
datafiles.append("Coordinates_20_RC_PoA.txt")
datafiles.append("Coordinates_20_Cluster_PoA.txt")

datafiles.append("Coordinates_5_Random_PoA.txt")
datafiles.append("Coordinates_5_Random_NYC.txt")
datafiles.append("Coordinates_5_Random_Bar.txt")
datafiles.append("Coordinates_5_Random_Ber.txt")

datafiles.append("Coordinates_8_Random_PoA.txt")
datafiles.append("Coordinates_8_Random_NYC.txt")
datafiles.append("Coordinates_8_Random_Bar.txt")
datafiles.append("Coordinates_8_Random_Ber.txt")

datafiles.append("Coordinates_10_Random_PoA.txt")
datafiles.append("Coordinates_10_Random_NYC.txt")
datafiles.append("Coordinates_10_Random_Bar.txt")
datafiles.append("Coordinates_10_Random_Ber.txt")
'''
path = datafiles[0]

print("\nOptimization instance selected:")
print(path)

# ============================================================
# 3. Read deterministic optimization instance
# ============================================================

instance_file = foldername / path

print("\nReading optimization instance from:")
print(instance_file)

if not instance_file.exists():
    raise FileNotFoundError(f"Instance file not found: {instance_file}")

data_header = np.loadtxt(instance_file, max_rows=1, dtype=int)

numberOfNodes = int(data_header[0])
vehicleCapacity = int(data_header[2])

end = numberOfNodes + 1

data_main_body = np.loadtxt(instance_file, skiprows=1, dtype=float)

nodes = tuple(range(0, numberOfNodes + 2))
locations = tuple(range(1, numberOfNodes + 2))

print("\nNumber of optimization nodes:", numberOfNodes)
print("Vehicle capacity:", vehicleCapacity)
print("End depot:", end)

# ============================================================
# 4. Read deterministic optimization instance data
# ============================================================
# - Demand remains deterministic and is read from the original input file.
# - Parking capacity P and station status are read from the original input file.
# - Deterministic travel time / cost is read from the original input file.
# - Stochastic travel times tau[s,i,j] are generated from the deterministic
#   travel times using a mean-preserving lognormal distribution.

actual_demand = {}
forecast_node = {}
P = {}
status_node = {}

for i in nodes:

    if i != end:

        actual_demand[i] = int(data_main_body[i, numberOfNodes + 2])
        P[i] = int(data_main_body[i, numberOfNodes + 3])
        status_node[i] = int(data_main_body[i, numberOfNodes + 4])
        forecast_node[i] = status_node[i] - actual_demand[i]

    else:

        actual_demand[i] = int(data_main_body[0, numberOfNodes + 2])
        P[i] = int(data_main_body[0, numberOfNodes + 3])
        status_node[i] = int(data_main_body[0, numberOfNodes + 4])
        forecast_node[i] = status_node[0] - actual_demand[0]

# Depot and artificial end depot
P[0] = 0
P[end] = 0
status_node[0] = 0
status_node[end] = 0
actual_demand[0] = 0
actual_demand[end] = 0
forecast_node[0] = 0
forecast_node[end] = 0

initial_load = {i: 0 for i in nodes}

print("\nInitial load:")
print(initial_load)

print("\nDeterministic demand data:")
for i in nodes:
    if i != 0 and i != end:
        print(
            "node", i,
            "actual_demand:", actual_demand[i],
            "P:", P[i],
            "status_node:", status_node[i],
            "forecast_node:", forecast_node[i]
        )

# ============================================================
# 5. Generate stochastic travel-time scenarios tau[s,i,j]
# ============================================================

# Arcs used in the objective and chance-time constraints.
# Included: 0 -> real nodes - real node -> real node - real node -> end depot
# Excluded: i -> i, any node -> 0, 0 -> end, end -> anything

model_arcs = [
    (i, j)
    for i in nodes
    for j in nodes
    if i != j
    and i < end
    and j != 0
    and not (i == 0 and j == end)
]

# Scenario identifiers
S = tuple(range(number_of_scenarios_to_use))

# ------------------------------------------------------------
# 5.1 Read deterministic travel time / cost
# ------------------------------------------------------------

cost = {}

for i, j in model_arcs:

    if j != end:
        # Ordinary destination node
        deterministic_time = float(data_main_body[i, j + 1])
    else:
        # Artificial end depot represents the return to depot 0
        deterministic_time = float(data_main_body[i, 1])

    if not np.isfinite(deterministic_time):
        raise ValueError(
            f"Non-finite deterministic travel time "
            f"for arc {(i, j)}: {deterministic_time}"
        )

    if deterministic_time < 0:
        raise ValueError(
            f"Negative deterministic travel time "
            f"for arc {(i, j)}: {deterministic_time}"
        )

    cost[(i, j)] = deterministic_time

print("\nDeterministic travel-time dictionary created.")
print("Number of model arcs:", len(model_arcs))

print("\nReturn-to-depot travel-time check")
print("===================================")

for i in range(1, end):
    print(
        f"model arc ({i}, {end}) "
        f"represents physical arc ({i}, 0): "
        f"raw data_main_body[{i}, 0] = {data_main_body[i, 0]}, "
        f"cost[{i}, {end}] = {cost[(i, end)]}"
    )

# ------------------------------------------------------------
# 5.2 Generate mean-preserving log-normal travel times
# ------------------------------------------------------------
# tau[s,i,j] = cost[i,j] * exp(
#     -0.5 * travel_time_sigma^2
#     + travel_time_sigma * Z[s,i,j]
# )
# where Z[s,i,j] follows a standard normal distribution.
# The -0.5 * sigma^2 correction ensures that
# E[tau[s,i,j]] = cost[i,j].

if travel_time_sigma < 0:
    raise ValueError("travel_time_sigma must be non-negative.")

rng = np.random.default_rng(run_seed)

tau = {}
scenario_rows = []

for s in S:
    for i, j in model_arcs:

        deterministic_time = cost[(i, j)]

        if deterministic_time == 0:
            standard_normal_value = 0.0
            multiplier = 1.0
            stochastic_time = 0.0
        else:
            standard_normal_value = float(rng.standard_normal())

            multiplier = float(
                np.exp(
                    -0.5 * travel_time_sigma ** 2
                    + travel_time_sigma * standard_normal_value
                )
            )

            stochastic_time = deterministic_time * multiplier

        tau[(s, i, j)] = float(stochastic_time)

        scenario_rows.append({
            "scenario_id": s,
            "from_node": i,
            "to_node": j,
            "deterministic_time": deterministic_time,
            "standard_normal_value": standard_normal_value,
            "lognormal_multiplier": multiplier,
            "stochastic_time": stochastic_time
        })

print("\nStochastic travel-time dictionary created.")
print("Number of scenarios:", len(S))
print("Number of model arcs per scenario:", len(model_arcs))
print("Number of generated scenario-arc values:", len(tau))
print("Expected number of values:", len(S) * len(model_arcs))

# ------------------------------------------------------------
# 5.3 Save generated scenarios to CSV
# ------------------------------------------------------------

time_scenario_df = pd.DataFrame(scenario_rows)

time_scenario_file.parent.mkdir(parents=True, exist_ok=True)
time_scenario_df.to_csv(time_scenario_file, index=False)

print("\nGenerated stochastic travel-time scenarios saved to:")
print(time_scenario_file)

# ------------------------------------------------------------
# 5.4 Validate the generated scenarios
# ------------------------------------------------------------

validation_rows = []

for i, j in model_arcs:

    arc_scenario_times = np.array([
        tau[(s, i, j)]
        for s in S
    ])

    deterministic_time = cost[(i, j)]
    sample_mean = float(arc_scenario_times.mean())

    if deterministic_time > 0:
        relative_mean_error = (
            sample_mean - deterministic_time
        ) / deterministic_time
    else:
        relative_mean_error = 0.0

    validation_rows.append({
        "from_node": i,
        "to_node": j,
        "deterministic_time": deterministic_time,
        "sample_mean": sample_mean,
        "sample_standard_deviation": float(
            arc_scenario_times.std(ddof=1)
        ),
        "sample_minimum": float(arc_scenario_times.min()),
        "sample_maximum": float(arc_scenario_times.max()),
        "relative_mean_error": relative_mean_error
    })

travel_time_validation_df = pd.DataFrame(validation_rows)

validation_file = (
    time_scenario_file.parent
    / f"{time_scenario_file.stem}_validation.csv"
)

travel_time_validation_df.to_csv(validation_file, index=False)

print("\nTravel-time scenario validation saved to:")
print(validation_file)

print("\nFirst generated travel-time scenarios:")
print(time_scenario_df.head())

print("\nFirst travel-time validation rows:")
print(travel_time_validation_df.head())

# ============================================================
# 6. Create optimization model
# ============================================================

Rebalancing = grb.Model(name="Stochastic_Time_SAA_Rebalancing")

# ============================================================
# 7. Decision variables
# ============================================================

# x[i,j] = 1 if arc i,j is traversed
x = {(i, j): Rebalancing.addVar(vtype=grb.GRB.BINARY,name=f"x_{i}_{j}") for i in nodes for j in nodes if i != end}

# Load of vehicle after serving node i
l = {i: Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=0, name=f"l_{i}") for i in nodes}

# eta_i: station status after rebalancing
st = {i: Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=0, name=f"st_{i}") for i in nodes}

# y[i] > 0 means bikes loaded from station i onto vehicle. y[i] < 0 means bikes unloaded from vehicle to station i
y = {i: Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"y_{i}") for i in nodes}

# Scenario-dependent auxiliary variables
b = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"b_{i}") for i in nodes}

r = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=0, name=f"r_{i}") for i in nodes}

theta = {(i): Rebalancing.addVar(vtype=grb.GRB.BINARY,name=f"theta_{i}") for i in nodes}

# Scenario-dependent time variable
# t[s,i] is the arrival/sequence time at node i under scenario s
t = {(s, i): Rebalancing.addVar(vtype=grb.GRB.CONTINUOUS,lb=0,name=f"t_{s}_{i}") for s in S for i in nodes}
# C[s,i,j] expression variable used in the chance constraint
C = {(s, i, j): Rebalancing.addVar(vtype=grb.GRB.CONTINUOUS,lb=-grb.GRB.INFINITY,name=f"C_{s}_{i}_{j}") for s in S for i, j in model_arcs}

# z[s,i,j] = 1 if the time-sequencing condition is satisfied in scenario s
z = {(s, i, j): Rebalancing.addVar(vtype=grb.GRB.BINARY,name=f"z_{s}_{i}_{j}") for s in S for i, j in model_arcs}

Rebalancing.update()

# ============================================================
# 8. Initial constraints
# ============================================================

for i in nodes:
    Rebalancing.addConstr(l[i] >= 0)
    Rebalancing.addConstr(st[i] >= 0)
    Rebalancing.addConstr(y[i] >= -40)

Rebalancing.addConstr(y[0] == 0)
Rebalancing.addConstr(y[end] == 0)

for s in S:
    Rebalancing.addConstr(t[(s, 0)] == 0)

Rebalancing.addConstr(theta[0] == 0)
Rebalancing.addConstr(r[0] == 0)
Rebalancing.addConstr(b[0] == 0)

Rebalancing.addConstr(theta[end] == 0)
Rebalancing.addConstr(r[end] == 0)
Rebalancing.addConstr(b[end] == 0)

for i in nodes:
    for j in nodes:
        if i == j and i < end:
            Rebalancing.addConstr(x[(i, j)] == 0)

# Depot status
Rebalancing.addConstr(st[0] == 0)
Rebalancing.addConstr(st[end] == 0)

# ============================================================
# 9. Objective function: Sample Average Approximation
# ============================================================
expected_routing_cost = (1 / len(S)) * grb.quicksum(tau[(s, i, j)] * x[(i, j)] for s in S for i, j in model_arcs)

shortage_penalty = p * grb.quicksum(r[i] for i in nodes if i != 0 and i != end)

Rebalancing.setObjective(expected_routing_cost + shortage_penalty, grb.GRB.MINIMIZE)

# ============================================================
# 10. Routing constraints
# ============================================================

# Everything leaves from the depot
Rebalancing.addConstr(grb.quicksum(x[(0, j)] for j in nodes if j != 0 and j != end) == K)

# Everything returns to the artificial end depot
Rebalancing.addConstr(grb.quicksum(x[(j, end)] for j in nodes if j != 0 and j != end) == K)

# Every node is served at most once
for i in nodes:
    if i != 0 and i < end:
        Rebalancing.addConstr(grb.quicksum(x[(i, j)] for j in nodes if j != i and j != 0) <= 1)

# Flow conservation
for j in nodes:
    if j != 0 and j != end:
        Rebalancing.addConstr(grb.quicksum(x[(i, j)] for i in nodes if j != i and i < end) - grb.quicksum(x[(j, i)] for i in nodes if j != i and i != 0) == 0)

# Do not allow direct 0 -> end
Rebalancing.addConstr(x[(0, end)] == 0)

# No node returns to initial depot 0
for i in nodes:
    if i != 0 and i < end:
        Rebalancing.addConstr(x[(i, 0)] == 0)

# ============================================================
# 11. Chance-constrained time sequencing
# ============================================================
# C[s,i,j] = t[s,j] - t[s,i] - tau[s,i,j] + M(1 - x[i,j])
# If z[s,i,j] = 1, then C[s,i,j] >= 0 must hold.
# The chance constraint requires this to hold in at least beta * |S| scenarios.

for s in S:
    for i, j in model_arcs:

        Rebalancing.addConstr(C[(s, i, j)] == t[(s, j)] - t[(s, i)] - tau[(s, i, j)] + M * (1 - x[(i, j)]))

        Rebalancing.addConstr(C[(s, i, j)] >= -M * (1 - z[(s, i, j)]))

for i, j in model_arcs:
    Rebalancing.addConstr(grb.quicksum(z[(s, i, j)] for s in S) >= beta * len(S))

# ============================================================
# 12. Vehicle load constraints
# ============================================================

for i in nodes:
    for j in nodes:
        if i != j and j != 0 and j != end and i < end:
            Rebalancing.addConstr(l[j] >= l[i] + y[j] - vehicleCapacity * (1 - x[(i, j)]))
            Rebalancing.addConstr(l[j] <= l[i] + y[j] + vehicleCapacity * (1 - x[(i, j)]))

# Vehicle load cannot exceed capacity
for i in nodes:
    Rebalancing.addConstr(l[i] <= vehicleCapacity)

# Available bikes to load cannot exceed current station status
for i in nodes:
    Rebalancing.addConstr(y[i] <= status_node[i])

# If y[j] > 0, cannot load more than remaining vehicle capacity
for i in nodes:
    for j in nodes:
        if i != j and j != 0 and j != end and i < end:
            Rebalancing.addConstr(y[j] <= vehicleCapacity - l[i] + M * (1 - x[(i, j)]))

# If y[j] < 0, cannot unload more than current vehicle load
for i in nodes:
    for j in nodes:
        if i != j and j != 0 and j != end and i < end:
            Rebalancing.addConstr(-y[j] <= l[i] + M * (1 - x[(i, j)]))

# If a station is not visited, y[i] must be zero
for j in nodes:
    Rebalancing.addConstr(y[j] >= -M * grb.quicksum(x[(i, j)] for i in nodes if i != j and i < end))

    Rebalancing.addConstr(y[j] <= M * grb.quicksum(x[(i, j)] for i in nodes if i != j and i < end))

# Initial and final vehicle load
Rebalancing.addConstr(l[0] == initial_load[0])
Rebalancing.addConstr(l[end] == initial_load[0])

# ============================================================
# 13. Station inventory constraints
# ============================================================

# eta_i = station inventory after rebalancing, before demand/inflow
for i in nodes:
    Rebalancing.addConstr(st[i] == status_node[i] - y[i])

# Capacity immediately after rebalancing - parking station capacity cannot be exceeded
for i in nodes:
    if i != 0 and i != end:
        Rebalancing.addConstr(st[i] <= P[i])

# ============================================================
# 14. Deterministic unmet-demand constraints
# ============================================================
 # the penalty is charged if only there is a shortage of bikes in node i (17), (18), (19), (20), (21)
for i in nodes:
    if (i != 0  and i!= (numberOfNodes +1)):
        Rebalancing.addConstr(b[i] == forecast_node[i] - st[i])

for i in nodes:
    if (i != 0  and i!= (numberOfNodes +1)):
        Rebalancing.addConstr(r[i] >= b[i])

for i in nodes:
    if (i != 0  and i!=(numberOfNodes +1)):
        Rebalancing.addConstr(r[i] <= M * theta[i])

for i in nodes:
    if (i != 0  and i!= (numberOfNodes +1)):
        Rebalancing.addConstr(r[i] <= b[i] + M * (1 - theta[i]))

for i in nodes:
    if (i != 0  and i!= (numberOfNodes +1)):
        Rebalancing.addConstr(r[i] >= 0)

# ============================================================
# 15. Optimize
# ============================================================

Rebalancing.setParam("TimeLimit", 7200)
Rebalancing.setParam("MIPGap", 0.00)

Rebalancing.optimize()

# ============================================================
# 16. Save results
# ============================================================

if Rebalancing.status not in [
    grb.GRB.OPTIMAL,
    grb.GRB.TIME_LIMIT
]:
    print("Model ended with status:", Rebalancing.status)

else:

    runtime = "%.2f" % Rebalancing.Runtime

    try:
        gap = Rebalancing.MIPGap
    except Exception:
        gap = None

    # --------------------------------------------------
    # Expected stochastic travel-time cost
    # --------------------------------------------------
    expected_time_cost_value = sum(tau[(s, i, j)] * x[(i, j)].X for s in S for i, j in model_arcs) / len(S)

    # --------------------------------------------------
    # Deterministic shortage penalty
    # --------------------------------------------------
    total_shortage = sum(r[i].X for i in nodes if i != 0 and i != end)
    penalty_cost = p * total_shortage

    obj = Rebalancing.ObjVal

    print("\nExpected stochastic travel-time cost:", expected_time_cost_value)
    print("Total deterministic shortage:", total_shortage)
    print("Penalty cost:", penalty_cost)
    print("Objective value:", obj)
    print("Runtime:", runtime)
    print("MIP gap:", gap)

    # --------------------------------------------------
    # Selected arcs
    # --------------------------------------------------

    selected_arcs = []

    for i, j in model_arcs:
        if x[(i, j)].X > 0.1:
            selected_arcs.append((i, j))

    # --------------------------------------------------
    # Save solution file
    # --------------------------------------------------

    solution_path = solution_folder / f"solution_{path}"

    with open(solution_path, "w") as f:

        # --------------------------------------------------
        # Main solution summary
        # --------------------------------------------------

        f.write("Solution summary\n")
        f.write("================\n")
        f.write(f"Input instance: {path}\n")
        f.write(f"Number of time scenarios used: {len(S)}\n")
        f.write(f"Scenario IDs used: {', '.join(str(s) for s in S)}\n")
        f.write(f"Beta: {beta}\n")
        f.write(f"Expected stochastic travel-time cost: {expected_time_cost_value}\n")
        f.write(f"Total deterministic shortage: {total_shortage}\n")
        f.write(f"Penalty cost: {penalty_cost}\n")
        f.write(f"Objective value: {obj}\n")
        f.write(f"Runtime: {runtime}\n")
        f.write(f"MIP gap: {gap}\n")

        # --------------------------------------------------
        # Selected routing arcs
        # --------------------------------------------------

        f.write("\nSelected routing arcs x[i,j]\n")
        f.write("============================\n")

        for i, j in selected_arcs:
            f.write(f"x_{i}_{j} {x[(i, j)].X}\n")

        # --------------------------------------------------
        # Loading / unloading decisions
        # --------------------------------------------------

        f.write("\nLoading/unloading variables y[i]\n")
        f.write("=================================\n")
        f.write("Positive y[i] = bikes loaded from station onto vehicle\n")
        f.write("Negative y[i] = bikes unloaded from vehicle to station\n\n")

        for i in nodes:
            if abs(y[i].X) > 1e-6:
                f.write(f"y_{i} {y[i].X}\n")

        # --------------------------------------------------
        # Station status and deterministic demand
        # --------------------------------------------------

        f.write("\nStation status and deterministic demand\n")
        f.write("=======================================\n")
        f.write(
            "node,"
            "actual_demand,"
            "status_node,"
            "forecast_node,"
            "status_after_rebalancing,"
            "b,"
            "shortage_r\n"
        )

        for i in nodes:
            if i != 0 and i != end:
                f.write(
                    f"{i},"
                    f"{actual_demand[i]},"
                    f"{status_node[i]},"
                    f"{forecast_node[i]},"
                    f"{st[i].X},"
                    f"{b[i].X},"
                    f"{r[i].X}\n"
                )

        # --------------------------------------------------
        # Chance-constraint satisfaction for selected arcs
        # --------------------------------------------------

        f.write("\nChance-constraint satisfaction for selected arcs\n")
        f.write("===============================================\n")
        f.write("arc,number_of_satisfied_scenarios,required_scenarios,beta\n")

        required_satisfied = beta * len(S)

        for i, j in selected_arcs:

            satisfied_count = sum(
                1
                for s in S
                if z[(s, i, j)].X > 0.5
            )

            f.write(
                f"{i}_{j},"
                f"{satisfied_count},"
                f"{required_satisfied},"
                f"{beta}\n"
            )

        # Initial deterministic travel times

        f.write("\nInitial deterministic travel times for selected arcs\n")
        f.write("====================================================\n")
        f.write("from_node,to_node,initial_travel_time\n")

        for i, j in selected_arcs:
            f.write(f"{i},{j},{cost[(i, j)]}\n")

        # --------------------------------------------------
        # Stochastic travel times for selected arcs
        # --------------------------------------------------

        f.write("\nStochastic travel times for selected arcs\n")
        f.write("=========================================\n")
        f.write("scenario_id,from_node,to_node,stochastic_time\n")

        for s in S:
            for i, j in selected_arcs:
                f.write(
                    f"{s},"
                    f"{i},"
                    f"{j},"
                    f"{tau[(s, i, j)]}\n"
                )

        # --------------------------------------------------
        # Expected travel time per selected arc
        # --------------------------------------------------

        f.write("\nExpected travel time per selected arc\n")
        f.write("=====================================\n")
        f.write("from_node,to_node,expected_stochastic_time\n")

        for i, j in selected_arcs:

            expected_arc_time = sum(
                tau[(s, i, j)]
                for s in S
            ) / len(S)

            f.write(
                f"{i},"
                f"{j},"
                f"{expected_arc_time}\n"
            )

    print("\nSolution saved to:", solution_path)

    print("\nSelected arcs:")
    for i, j in selected_arcs:
        print(f"x_{i}_{j}:", x[(i, j)].X)

    print("\nNonzero loading/unloading decisions:")
    for i in nodes:
        if abs(y[i].X) > 1e-6:
            print(f"y_{i}:", y[i].X)