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
solution_folder = Path("SolutionsTime/ZeroDemand")
solution_folder.mkdir(parents=True, exist_ok=True)

# Scenario file produced from empirical distributions
scenario_file = Path(
    r"C:\Users\aliki\OneDrive\Jobs - Companies\NTUA\5. Papers\7. Rebalancing 2\dott data\Net bike change\scenario_draws_15min_by_dimotiko_diamerisma.csv"
)

# Number of scenarios to use
# This is |S| in the mathematical formulation
number_of_scenarios_to_use = 1000

# Penalty for unmet stochastic demand
p = 1500

# Big M
M = 100000

# Number of vehicles
K = 2

# ============================================================
# 2. Data files
# ============================================================

datafiles = []

datafiles.append("Coordinates_7_Athens.txt")
'''
datafiles.append("Coordinates_12_RC_NYC.txt")
datafiles.append("Coordinates_12_Cluster_NYC.txt")
datafiles.append("Coordinates_12_Random_Ber.txt")
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
# 3. Read stochastic scenarios
# ============================================================

scenario_df_full = pd.read_csv(scenario_file)

print("Scenario file columns:")
print(scenario_df_full.columns)

required_scenario_cols = [
    "scenario_id",
    "name_en",
    "stochastic_net_bike_change_15min"
]

missing_scenario_cols = [
    col for col in required_scenario_cols
    if col not in scenario_df_full.columns
]

if missing_scenario_cols:
    raise KeyError(
        f"Missing required columns in scenario file: {missing_scenario_cols}\n"
        f"Available columns are: {list(scenario_df_full.columns)}"
    )

scenario_df_full["scenario_id"] = pd.to_numeric(scenario_df_full["scenario_id"],errors="coerce")

scenario_df_full["stochastic_net_bike_change_15min"] = pd.to_numeric(scenario_df_full["stochastic_net_bike_change_15min"],errors="coerce")

scenario_df_full = scenario_df_full.dropna(
    subset=[
        "scenario_id",
        "name_en",
        "stochastic_net_bike_change_15min"
    ]
)

scenario_df_full["scenario_id"] = scenario_df_full["scenario_id"].astype(int)
scenario_df_full["stochastic_net_bike_change_15min"] = (scenario_df_full["stochastic_net_bike_change_15min"].astype(int))

# ------------------------------------------------------------
# Negative net change becomes demand.
# Positive net change becomes inflow.
# ------------------------------------------------------------

scenario_df_full["stochastic_demand_15min"] = (-scenario_df_full["stochastic_net_bike_change_15min"]).clip(lower=0)

scenario_df_full["stochastic_inflow_15min"] = (scenario_df_full["stochastic_net_bike_change_15min"]).clip(lower=0)

scenario_df_full["stochastic_demand_15min"] = (scenario_df_full["stochastic_demand_15min"].astype(int))

scenario_df_full["stochastic_inflow_15min"] = (scenario_df_full["stochastic_inflow_15min"].astype(int))

available_scenarios = sorted(scenario_df_full["scenario_id"].unique())

selected_scenarios = tuple(available_scenarios[:number_of_scenarios_to_use])

scenario_df_full = scenario_df_full[scenario_df_full["scenario_id"].isin(selected_scenarios)].copy()

S = selected_scenarios

print("\nAvailable geographic areas in scenario file:")
print(sorted(scenario_df_full["name_en"].unique()))

print("\nNumber of selected scenarios:", len(selected_scenarios))

# ============================================================
# 4. Map optimization nodes to municipal districts
# ============================================================

node_to_area = {
    1: "1st",
    2: "2nd",
    3: "3rd",
    4: "4th",
    5: "5th",
    6: "6th",
    7: "7th",
}

# ============================================================
# 5. Read deterministic optimization instance
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

# ------------------------------------------------------------
# Check node-to-area mapping
# ------------------------------------------------------------

scenario_areas = sorted(scenario_df_full["name_en"].unique())

missing_node_mapping = [
    i for i in range(1, numberOfNodes + 1)
    if i not in node_to_area
]

if missing_node_mapping:
    raise ValueError(
        f"Missing node_to_area mapping for nodes: {missing_node_mapping}\n"
        f"Number of optimization nodes is {numberOfNodes}, "
        f"but node_to_area only contains {len(node_to_area)} mapped nodes."
    )

missing_areas = [
    area for area in node_to_area.values()
    if area not in scenario_areas
]

if missing_areas:
    raise ValueError(
        f"These areas from node_to_area were not found in the scenario file: {missing_areas}\n"
        f"Available areas are: {scenario_areas}"
    )

print("\nNode-to-area mapping used:")
for node_id in range(1, numberOfNodes + 1):
    print(node_id, "->", node_to_area[node_id])


# ============================================================
# 6. Read distance, capacity, and initial status
# ============================================================

distanceMatrix = {}
cost = {}
P = {}
status_node = {}

for i in nodes:

    if i != end:
        P[i] = int(data_main_body[i, numberOfNodes + 3])
        status_node[i] = int(data_main_body[i, numberOfNodes + 4])

    else:
        P[i] = int(data_main_body[0, numberOfNodes + 3])
        status_node[i] = int(data_main_body[0, numberOfNodes + 4])

    for j in nodes:

        if j != end:

            if i != end:
                distanceMatrix[(i, j)] = data_main_body[i, j + 1]
                cost[(i, j)] = distanceMatrix[(i, j)]

            else:
                distanceMatrix[(i, j)] = data_main_body[0, j + 1]
                cost[(i, j)] = distanceMatrix[(0, j)]

        else:

            if i != end:
                distanceMatrix[(i, j)] = data_main_body[i, 0]
                cost[(i, j)] = distanceMatrix[(i, 0)]

            else:
                distanceMatrix[(i, j)] = data_main_body[0, 0]
                cost[(i, j)] = distanceMatrix[(0, 0)]

# Depot and artificial end depot
P[0] = 0
P[end] = 0
status_node[0] = 0
status_node[end] = 0

initial_load = {i: 0 for i in nodes}

print("\nInitial load:")
print(initial_load)

# ============================================================
# 7. Build scenario dictionaries
# ============================================================

stochastic_net_change = {}
stochastic_demand = {}
stochastic_inflow = {}

for s in S:

    for i in nodes:

        if i == 0 or i == end:
            stochastic_net_change[(s, i)] = 0
            stochastic_demand[(s, i)] = 0
            stochastic_inflow[(s, i)] = 0

        else:
            area_name = node_to_area[i]

            row = scenario_df_full[
                (scenario_df_full["scenario_id"] == s)
                & (scenario_df_full["name_en"] == area_name)
            ]

            if row.empty:
                raise ValueError(
                    f"No scenario data found for scenario {s}, "
                    f"node {i}, area '{area_name}'."
                )

            net_change = int(
                row["stochastic_net_bike_change_15min"].iloc[0]
            )

            demand = max(-net_change, 0)
            inflow = max(net_change, 0)

            stochastic_net_change[(s, i)] = net_change
            stochastic_demand[(s, i)] = demand
            stochastic_inflow[(s, i)] = inflow

print("\nScenario dictionaries created.")
print("Number of scenarios used:", len(S))


# ============================================================
# 8. Create optimization model
# ============================================================

Rebalancing = grb.Model(name="Stochastic_SAA_Rebalancing")

# ============================================================
# 9. Decision variables
# ============================================================

# x[i,j] = 1 if arc i,j is traversed
x = {(i, j): Rebalancing.addVar(vtype=grb.GRB.BINARY,name=f"x_{i}_{j}") for i in nodes for j in nodes if i != end}

# Load of vehicle after serving node i
l = {i: Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=0, name=f"l_{i}") for i in nodes}

# eta_i: station status after rebalancing, before stochastic demand/inflow
st = {i: Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=0, name=f"st_{i}") for i in nodes}

# y[i] > 0 means bikes loaded from station i onto vehicle. y[i] < 0 means bikes unloaded from vehicle to station i
y = {i: Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"y_{i}") for i in nodes}

# Scenario-dependent auxiliary variables
b = {(s, i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"b_{s}_{i}") for s in S for i in nodes}

r = {(s, i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=0, name=f"r_{s}_{i}") for s in S for i in nodes}

theta = {(s, i): Rebalancing.addVar(vtype=grb.GRB.BINARY,name=f"theta_{s}_{i}") for s in S for i in nodes}

# Time component
t = {i: Rebalancing.addVar(vtype=grb.GRB.INTEGER,lb=-10000000,name=f"t_{i}") for i in nodes}

Rebalancing.update()

# ============================================================
# 10. Initial constraints
# ============================================================

for i in nodes:
    Rebalancing.addConstr(l[i] >= 0)
    Rebalancing.addConstr(st[i] >= 0)
    Rebalancing.addConstr(y[i] >= -40)

Rebalancing.addConstr(y[0] == 0)
Rebalancing.addConstr(t[0] == 0)
Rebalancing.addConstr(y[end] == 0)

for s in S:
    Rebalancing.addConstr(theta[(s, 0)] == 0)
    Rebalancing.addConstr(r[(s, 0)] == 0)
    Rebalancing.addConstr(b[(s, 0)] == 0)

    Rebalancing.addConstr(theta[(s, end)] == 0)
    Rebalancing.addConstr(r[(s, end)] == 0)
    Rebalancing.addConstr(b[(s, end)] == 0)

for i in nodes:
    for j in nodes:
        if i == j and i < end:
            Rebalancing.addConstr(x[(i, j)] == 0)

# Depot status
Rebalancing.addConstr(st[0] == 0)
Rebalancing.addConstr(st[end] == 0)


# ============================================================
# 11. Objective function: Sample Average Approximation
# ============================================================
routing_cost = grb.quicksum(cost[(i, j)] * x[(i, j)] for i in nodes for j in nodes if i != j and i < end)

expected_shortage_penalty = (p / len(S)) * grb.quicksum(r[(s, i)] for s in S for i in nodes if i != 0 and i != end)

Rebalancing.setObjective(routing_cost + expected_shortage_penalty, grb.GRB.MINIMIZE)

# ============================================================
# 12. Routing constraints
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

# Time sequencing
for i in nodes:
    for j in nodes:
        if i != j and j != 0 and i < end:
            Rebalancing.addConstr(t[j] >= t[i] + cost[(i, j)] - M * (1 - x[(i, j)]))

# Do not allow direct 0 -> end
Rebalancing.addConstr(x[(0, end)] == 0)

# No node returns to initial depot 0
for i in nodes:
    if i != 0 and i < end:
        Rebalancing.addConstr(x[(i, 0)] == 0)

# ============================================================
# 13. Vehicle load constraints
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
# 14. Station inventory constraints
# ============================================================

# eta_i = station inventory after rebalancing, before demand/inflow
for i in nodes:
    Rebalancing.addConstr(st[i] == status_node[i] - y[i])

# Capacity immediately after rebalancing - parking station capacity cannot be exceeded
for i in nodes:
    if i != 0 and i != end:
        Rebalancing.addConstr(st[i] <= P[i])

# !!!NEW CONSTRAINT!!!
# Scenario-dependent capacity after stochastic demand and inflow
# Positive net change is treated as inflow and may create capacity pressure.
for s in S:
    for i in nodes:
        if i != 0 and i != end:
            Rebalancing.addConstr(st[i] - stochastic_demand[(s, i)] + stochastic_inflow[(s, i)] <= P[i])

# ============================================================
# 15. Scenario-based unmet demand constraints
# ============================================================
# Negative net change becomes stochastic demand. Positive net change becomes stochastic inflow.
# b[s,i] = demand[s,i] - inflow[s,i] - eta[i]
# r[s,i] = max(b[s,i], 0)

for s in S:
    for i in nodes:
        if i != 0 and i != end:
            Rebalancing.addConstr(b[(s, i)] == stochastic_demand[(s, i)] - stochastic_inflow[(s, i)] - st[i])

            Rebalancing.addConstr(r[(s, i)] >= b[(s, i)])

            Rebalancing.addConstr(r[(s, i)] >= 0)

            Rebalancing.addConstr(r[(s, i)] <= M * theta[(s, i)])

            Rebalancing.addConstr(r[(s, i)] <= b[(s, i)] + M * (1 - theta[(s, i)]))

# ============================================================
# 16. Optimize
# ============================================================

Rebalancing.setParam("TimeLimit", 7200)
Rebalancing.setParam("MIPGap", 0.00)

Rebalancing.optimize()

# ============================================================
# 17. Save results
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

    RoutingCosts = 0

    for i, j in x:
        if x[(i, j)].X > 0.1:
            RoutingCosts += cost[(i, j)]

    obj = Rebalancing.ObjVal

    print("\nRoutingCosts:", RoutingCosts)
    print("Objective value:", obj)
    print("Runtime:", runtime)
    print("MIP gap:", gap)

    solution_path = solution_folder / path

    with open(solution_path, "w") as f:

        f.write(f"{RoutingCosts} {obj} {runtime} {gap}\n")

        f.write("\nStochastic scenario information\n")
        f.write(f"Number of scenarios used: {len(S)}\n")
        f.write("Scenario IDs used:\n")
        f.write(", ".join(str(s) for s in S))
        f.write("\n")

        f.write("\nSelected routing arcs x[i,j]\n")
        for i, j in x:
            if x[(i, j)].X > 0.1:
                f.write(f"{i}_{j}\n")

        f.write("\nLoading/unloading variables y[i]\n")
        for i in nodes:
            if abs(y[i].X) > 1e-6:
                f.write(f"y_{i} {y[i].X}\n")

        f.write("\nStation status after rebalancing eta[i]\n")
        for i in nodes:
            if i != 0 and i != end:
                f.write(f"st_{i} {st[i].X}\n")

        f.write("\nScenario shortage variables r[s,i]\n")
        for s in S:
            for i in nodes:
                if i != 0 and i != end:
                    if r[(s, i)].X > 1e-6:
                        f.write(f"r_{s}_{i} {r[(s, i)].X}\n")

    print("\nSolution saved to:", solution_path)

    print("\nSelected arcs:")
    for i, j in x:
        if x[(i, j)].X > 0.1:
            print(f"x_{i}_{j}:", x[(i, j)].X)

    print("\nNonzero loading/unloading decisions:")
    for i in nodes:
        if abs(y[i].X) > 1e-6:
            print(f"y_{i}:", y[i].X)


