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
import openpyxl

# ============================================================
# 1. General settings
# ============================================================

# Folder with the original optimization instance files
foldername = Path(r"C:\Users\aliki\PycharmProjects\Latest version 18.09\Instances\ZeroDemand")

# Folder for solution files
solution_folder = Path("SolutionsJointStochastic/ZeroDemand")
solution_folder.mkdir(parents=True, exist_ok=True)

# Scenario file produced from empirical distributions
scenario_file = Path(
    r"C:\Users\aliki\OneDrive\Jobs - Companies\NTUA\5. Papers\7. Rebalancing 2\dott data\Net bike change\scenario_draws_15min_by_dimotiko_diamerisma.csv"
)

# Number of scenarios to use
# This is |S| in the mathematical formulation
number_of_scenarios_to_use = 50

# Random seed used for both demand and travel-time scenarios
run_seed = 123

# Lognormal dispersion parameter for stochastic travel times
travel_time_sigma = 0.20

# Percentage beta that must be satisfied across the stochastic travel-time scenarios
beta = 0.90

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
'''
datafiles.append("Coordinates_7_Athens.txt")

datafiles.append("Coordinates_12_RC_NYC.txt")
datafiles.append("Coordinates_12_Cluster_NYC.txt")
'''
datafiles.append("Coordinates_12_Random_Ber.txt")
'''
datafiles.append("Coordinates_12_RC_Ber.txt")
'''
datafiles.append("Coordinates_12_Cluster_Ber.txt")
'''
datafiles.append("Coordinates_12_RC_Bar.txt")
'''
datafiles.append("Coordinates_12_Random_Bar.txt")
datafiles.append("Coordinates_12_Cluster_Bar.txt")
'''
datafiles.append("Coordinates_12_RC_PoA.txt")
datafiles.append("Coordinates_12_Random_PoA.txt")
datafiles.append("Coordinates_12_Cluster_PoA.txt")
datafiles.append("Coordinates_12_Random_NYC.txt")

datafiles.append("Coordinates_15_Cluster_NYC.txt")
datafiles.append("Coordinates_15_RC_NYC.txt")
datafiles.append("Coordinates_15_Random_NYC.txt")
'''
datafiles.append("Coordinates_15_Cluster_Ber.txt")
'''
datafiles.append("Coordinates_15_RC_Ber.txt")
'''
datafiles.append("Coordinates_15_Random_Ber.txt")
datafiles.append("Coordinates_15_Cluster_Bar.txt")
'''
datafiles.append("Coordinates_15_RC_Bar.txt")
'''
datafiles.append("Coordinates_15_Random_Bar.txt")
'''
datafiles.append("Coordinates_15_Cluster_PoA.txt")
datafiles.append("Coordinates_15_RC_PoA.txt")
datafiles.append("Coordinates_15_Random_PoA.txt")

datafiles.append("Coordinates_20_RC_NYC.txt")
datafiles.append("Coordinates_20_Random_NYC.txt")
datafiles.append("Coordinates_20_Cluster_NYC.txt")
datafiles.append("Coordinates_20_RC_Ber.txt")
datafiles.append("Coordinates_20_Random_PoA.txt")
'''
datafiles.append("Coordinates_20_Random_Ber.txt")
datafiles.append("Coordinates_20_Cluster_Ber.txt")
'''
datafiles.append("Coordinates_20_RC_Bar.txt")
'''
datafiles.append("Coordinates_20_Random_Bar.txt")
datafiles.append("Coordinates_20_Cluster_Bar.txt")
'''
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

#path = datafiles[0]

for i in datafiles:

    path = i

    print("\nOptimization instance selected:")
    print(path)


    # ============================================================
    # 3. Create synthetic stochastic scenarios for stress testing
    # ============================================================

    # ------------------------------------------------------------
    # ORIGINAL EMPIRICAL-SCENARIO INPUT (COMMENTED OUT)
    # ------------------------------------------------------------
    # The following line originally read the stochastic demand data
    # from the scenario-draws CSV file:
    #
    # scenario_df_full = pd.read_csv(scenario_file)
    #
    # For stress-testing purposes, the empirical scenario input is
    # replaced below by independently generated discrete net bike
    # changes for every optimization node and every scenario.
    # ------------------------------------------------------------

    # Read only the header of the selected optimization instance here
    # so that the synthetic generator creates exactly one demand draw
    # for each station/node in the instance. For example, a 15-node
    # instance receives 15 independent net-bike-change draws per scenario.
    instance_file_for_synthetic_scenarios = foldername / path

    if not instance_file_for_synthetic_scenarios.exists():
        raise FileNotFoundError(
            f"Instance file not found: {instance_file_for_synthetic_scenarios}"
        )

    synthetic_data_header = np.loadtxt(
        instance_file_for_synthetic_scenarios,
        max_rows=1,
        dtype=int
    )

    numberOfNodes_for_synthetic_scenarios = int(synthetic_data_header[0])

    # Reproducible random-number generator.
    # Change 123 to another integer for a different stress-test replication.
    rng = np.random.default_rng(run_seed)

    # Possible discrete net bike changes.
    synthetic_net_change_values = np.arange(-5, 6)

    # Symmetric discrete probability distribution:
    # P(0) = 20%, P(+/-1) = 18% each, P(+/-2) = 15% each.
    # The remaining 24% is assigned symmetrically to +/-3, +/-4, and +/-5.
    synthetic_net_change_probabilities = np.array([
        0.005,  # -5
        0.015,  # -4
        0.050,  # -3
        0.150,  # -2
        0.180,  # -1
        0.200,  #  0
        0.180,  #  1
        0.150,  #  2
        0.050,  #  3
        0.015,  #  4
        0.005   #  5
    ])

    if not np.isclose(synthetic_net_change_probabilities.sum(), 1.0):
        raise ValueError(
            "Synthetic demand probabilities must sum to 1.0. "
            f"Current sum: {synthetic_net_change_probabilities.sum()}"
        )

    # Generate one discrete net-bike-change draw for every combination
    # of scenario and optimization node.
    synthetic_scenario_rows = []

    for scenario_id in range(1, number_of_scenarios_to_use + 1):
        scenario_draws = rng.choice(
            synthetic_net_change_values,
            size=numberOfNodes_for_synthetic_scenarios,
            replace=True,
            p=synthetic_net_change_probabilities
        )

        for node_id, net_change in enumerate(scenario_draws, start=1):
            synthetic_scenario_rows.append({
                "scenario_id": scenario_id,
                "name_en": f"node_{node_id}",
                "stochastic_net_bike_change_15min": int(net_change)
            })

    scenario_df_full = pd.DataFrame(synthetic_scenario_rows)

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
            f"Missing required columns in synthetic scenario data: {missing_scenario_cols}\n"
            f"Available columns are: {list(scenario_df_full.columns)}"
        )

    scenario_df_full["scenario_id"] = pd.to_numeric(
        scenario_df_full["scenario_id"],
        errors="coerce"
    )

    scenario_df_full["stochastic_net_bike_change_15min"] = pd.to_numeric(
        scenario_df_full["stochastic_net_bike_change_15min"],
        errors="coerce"
    )

    scenario_df_full = scenario_df_full.dropna(
        subset=[
            "scenario_id",
            "name_en",
            "stochastic_net_bike_change_15min"
        ]
    )

    scenario_df_full["scenario_id"] = scenario_df_full["scenario_id"].astype(int)
    scenario_df_full["stochastic_net_bike_change_15min"] = (
        scenario_df_full["stochastic_net_bike_change_15min"].astype(int)
    )

    # ------------------------------------------------------------
    # Negative net change becomes demand.
    # Positive net change becomes inflow.
    # ------------------------------------------------------------

    scenario_df_full["stochastic_demand_15min"] = (
        -scenario_df_full["stochastic_net_bike_change_15min"]
    ).clip(lower=0)

    scenario_df_full["stochastic_inflow_15min"] = (
        scenario_df_full["stochastic_net_bike_change_15min"]
    ).clip(lower=0)

    scenario_df_full["stochastic_demand_15min"] = (
        scenario_df_full["stochastic_demand_15min"].astype(int)
    )

    scenario_df_full["stochastic_inflow_15min"] = (
        scenario_df_full["stochastic_inflow_15min"].astype(int)
    )

    # Save all generated random demand data to a separate Excel file.
    synthetic_scenario_output_file = solution_folder / (
        f"synthetic_scenario_draws_{Path(path).stem}_"
        f"{number_of_scenarios_to_use}_scenarios_seed_{run_seed}.xlsx"
    )

    scenario_df_full.to_excel(
        synthetic_scenario_output_file,
        index=False
    )

    print("\nSynthetic scenario data saved to:")
    print(synthetic_scenario_output_file)

    available_scenarios = sorted(scenario_df_full["scenario_id"].unique())

    if number_of_scenarios_to_use <= len(available_scenarios):
        selected_scenarios = tuple(
            rng.choice(
                available_scenarios,
                size=number_of_scenarios_to_use,
                replace=False
            )
        )
    else:
        selected_scenarios = tuple(
            rng.choice(
                available_scenarios,
                size=number_of_scenarios_to_use,
                replace=True
            )
        )

    selected_scenarios = tuple(sorted(selected_scenarios))

    scenario_df_full = scenario_df_full[
        scenario_df_full["scenario_id"].isin(selected_scenarios)
    ].copy()

    S = selected_scenarios

    print("\nAvailable synthetic node labels:")
    print(sorted(scenario_df_full["name_en"].unique()))

    print("\nNumber of selected scenarios:", len(selected_scenarios))

    # ============================================================
    # 4. Map optimization nodes to municipal districts
    # ============================================================

    # Original seven-district mapping retained below as a comment.
    # node_to_area = {
    #     1: "1st",
    #     2: "2nd",
    #     3: "3rd",
    #     4: "4th",
    #     5: "5th",
    #     6: "6th",
    #     7: "7th",
    # }

    # Synthetic stress-test scenarios are generated directly for every
    # optimization node, regardless of whether the instance has 5, 7,
    # 10, 15, 20, or another number of nodes.
    node_to_area = {
        i: f"node_{i}"
        for i in range(1, numberOfNodes_for_synthetic_scenarios + 1)
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
    # 8. Generate stochastic travel-time scenarios tau[s,i,j]
    # ============================================================

    # Arcs used in the objective and chance-time constraints.
    # Included: 0 -> real nodes, real node -> real node, real node -> end depot.
    # Excluded: i -> i, any node -> 0, 0 -> end, end -> anything.
    model_arcs = [
        (i, j)
        for i in nodes
        for j in nodes
        if i != j
        and i < end
        and j != 0
        and not (i == 0 and j == end)
    ]

    if travel_time_sigma < 0:
        raise ValueError("travel_time_sigma must be non-negative.")

    # The same scenario identifier s represents one joint realization of
    # stochastic station demand/inflow and stochastic arc travel times.
    time_rng = np.random.default_rng(run_seed)
    tau = {}
    travel_time_scenario_rows = []

    for s in S:
        for i, j in model_arcs:

            deterministic_time = float(cost[(i, j)])

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

            if deterministic_time == 0:
                standard_normal_value = 0.0
                multiplier = 1.0
                stochastic_time = 0.0
            else:
                standard_normal_value = float(time_rng.standard_normal())

                multiplier = float(
                    np.exp(
                        -0.5 * travel_time_sigma ** 2
                        + travel_time_sigma * standard_normal_value
                    )
                )

                stochastic_time = deterministic_time * multiplier

            tau[(s, i, j)] = float(stochastic_time)

            travel_time_scenario_rows.append({
                "scenario_id": s,
                "from_node": i,
                "to_node": j,
                "deterministic_time": deterministic_time,
                "standard_normal_value": standard_normal_value,
                "lognormal_multiplier": multiplier,
                "stochastic_time": stochastic_time
            })

    travel_time_scenario_df = pd.DataFrame(travel_time_scenario_rows)

    travel_time_scenario_output_file = solution_folder / (
        f"joint_travel_time_scenarios_{Path(path).stem}_"
        f"{number_of_scenarios_to_use}_scenarios_seed_{run_seed}.csv"
    )

    travel_time_scenario_df.to_csv(
        travel_time_scenario_output_file,
        index=False
    )

    print("\nStochastic travel-time dictionary created.")
    print("Number of model arcs:", len(model_arcs))
    print("Number of generated scenario-arc values:", len(tau))
    print("Stochastic travel-time scenarios saved to:")
    print(travel_time_scenario_output_file)


    # ============================================================
    # 9. Create optimization model
    # ============================================================

    Rebalancing = grb.Model(name="Joint_Stochastic_Demand_Time_SAA_Rebalancing")

    # ============================================================
    # 10. Decision variables
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

    # Scenario-dependent time variable
    # t[s,i] is the arrival/sequence time at node i under scenario s
    t = {(s, i): Rebalancing.addVar(vtype=grb.GRB.CONTINUOUS,lb=0,name=f"t_{s}_{i}") for s in S for i in nodes}

    # C[s,i,j] expression variable used in the chance constraint
    C = {(s, i, j): Rebalancing.addVar(vtype=grb.GRB.CONTINUOUS,lb=-grb.GRB.INFINITY,name=f"C_{s}_{i}_{j}") for s in S for i, j in model_arcs}

    # z[s,i,j] = 1 if the time-sequencing condition is satisfied in scenario s
    z = {(s, i, j): Rebalancing.addVar(vtype=grb.GRB.BINARY,name=f"z_{s}_{i}_{j}") for s in S for i, j in model_arcs}

    Rebalancing.update()

    # ============================================================
    # 11. Initial constraints
    # ============================================================

    for i in nodes:
        Rebalancing.addConstr(l[i] >= 0)
        Rebalancing.addConstr(st[i] >= 0)
        Rebalancing.addConstr(y[i] >= -40)

    Rebalancing.addConstr(y[0] == 0)
    Rebalancing.addConstr(y[end] == 0)

    for s in S:
        Rebalancing.addConstr(t[(s, 0)] == 0)

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
    # 12. Objective function: Sample Average Approximation
    # ============================================================
    expected_routing_cost = (1 / len(S)) * grb.quicksum(tau[(s, i, j)] * x[(i, j)] for s in S for i, j in model_arcs)

    expected_shortage_penalty = (p / len(S)) * grb.quicksum(r[(s, i)] for s in S for i in nodes if i != 0 and i != end)

    Rebalancing.setObjective(expected_routing_cost + expected_shortage_penalty, grb.GRB.MINIMIZE)

    # ============================================================
    # 19. Routing constraints
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

    # ============================================================
    # 18. Chance-constrained time sequencing
    # ============================================================
    # C[s,i,j] = t[s,j] - t[s,i] - tau[s,i,j] + M(1 - x[i,j])
    # If z[s,i,j] = 1, then C[s,i,j] >= 0 must hold.
    # z[s,i,j] <= x[i,j] links scenario satisfaction to arc selection.
    # The chance constraint requires the sequencing condition to hold in
    # at least beta * |S| joint demand-and-travel-time scenarios.

    for s in S:
        for i, j in model_arcs:

            Rebalancing.addConstr(C[(s, i, j)] == t[(s, j)] - t[(s, i)] - tau[(s, i, j)] + M * (1 - x[(i, j)]))

            Rebalancing.addConstr(C[(s, i, j)] >= -M * (1 - z[(s, i, j)]))

            Rebalancing.addConstr(z[(s, i, j)] <= x[(i, j)])

    for i, j in model_arcs:
        Rebalancing.addConstr(grb.quicksum(z[(s, i, j)] for s in S) >= beta * len(S) * x[(i, j)])

    # Do not allow direct 0 -> end
    Rebalancing.addConstr(x[(0, end)] == 0)

    # No node returns to initial depot 0
    for i in nodes:
        if i != 0 and i < end:
            Rebalancing.addConstr(x[(i, 0)] == 0)

    # ============================================================
    # 19. Vehicle load constraints
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
    # 18. Station inventory constraints
    # ============================================================

    # eta_i = station inventory after rebalancing, before demand/inflow
    for i in nodes:
        Rebalancing.addConstr(st[i] == status_node[i] - y[i])

    # Capacity immediately after rebalancing - parking station capacity cannot be exceeded
    for i in nodes:
        if i != 0 and i != end:
            Rebalancing.addConstr(st[i] <= P[i])
    '''
    # !!!NEW CONSTRAINT!!!
    # Scenario-dependent capacity after stochastic demand and inflow
    # Positive net change is treated as inflow and may create capacity pressure.
    for s in S:
        for i in nodes:
            if i != 0 and i != end:
                Rebalancing.addConstr(st[i] - stochastic_demand[(s, i)] + stochastic_inflow[(s, i)] <= P[i])
    '''

    # ============================================================
    # 19. Scenario-based unmet demand constraints
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
    # 18. Optimize
    # ============================================================

    Rebalancing.setParam("TimeLimit", 7200)
    Rebalancing.setParam("MIPGap", 0.00)

    Rebalancing.optimize()

    # ============================================================
    # 19. Save results
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

        expected_time_cost_value = sum(
            tau[(s, i, j)] * x[(i, j)].X
            for s in S
            for i, j in model_arcs
        ) / len(S)

        expected_shortage_value = sum(
            r[(s, i)].X
            for s in S
            for i in nodes
            if i != 0 and i != end
        ) / len(S)

        expected_penalty_cost = p * expected_shortage_value

        obj = Rebalancing.ObjVal

        print("\nExpected stochastic travel-time cost:", expected_time_cost_value)
        print("Expected stochastic shortage:", expected_shortage_value)
        print("Expected shortage penalty:", expected_penalty_cost)
        print("Objective value:", obj)
        print("Runtime:", runtime)
        print("MIP gap:", gap)

        # Save solution file
        solution_path = solution_folder / f"solution_{path}"

        with open(solution_path, "w") as f:

            # --------------------------------------------------
            # Main solution summary
            # --------------------------------------------------

            f.write("Solution summary\n")
            f.write("================\n")
            f.write(f"Input instance: {path}\n")
            f.write(f"Expected stochastic travel-time cost: {expected_time_cost_value}\n")
            f.write(f"Expected stochastic shortage: {expected_shortage_value}\n")
            f.write(f"Expected shortage penalty: {expected_penalty_cost}\n")
            f.write(f"Objective value: {obj}\n")
            f.write(f"Runtime: {runtime}\n")
            f.write(f"MIP gap: {gap}\n")

            # --------------------------------------------------
            # Stochastic scenario information
            # --------------------------------------------------

            f.write("\nStochastic scenario information\n")
            f.write("===============================\n")
            f.write(f"Number of joint scenarios used: {len(S)}\n")
            f.write(f"Travel-time sigma: {travel_time_sigma}\n")
            f.write(f"Beta: {beta}\n")
            f.write("Joint scenario IDs used:\n")
            f.write(", ".join(str(s) for s in S))
            f.write("\n")

            # --------------------------------------------------
            # Selected routing arcs
            # --------------------------------------------------

            f.write("\nSelected routing arcs x[i,j]\n")
            f.write("============================\n")

            for i, j in x:
                if x[(i, j)].X > 0.1:
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
            # Station status after rebalancing
            # --------------------------------------------------

            f.write("\nStation status after rebalancing eta[i]\n")
            f.write("=======================================\n")
            f.write("st[i] = bikes at node i after rebalancing, before stochastic demand/inflow\n\n")

            for i in nodes:
                if i != 0 and i != end:
                    f.write(
                        f"node {i}, "
                        f"area {node_to_area[i]}, "
                        f"st_{i} {st[i].X}\n"
                    )

            # --------------------------------------------------
            # Positive unmet demand only
            # --------------------------------------------------

            f.write("\nPositive unmet demand only: r[s,i]\n")
            f.write("==================================\n")
            f.write("Only scenario-node pairs with positive shortage are shown here.\n")
            f.write("If r[s,i] is not listed, then shortage is zero for that scenario and node.\n\n")

            for s in S:
                for i in nodes:
                    if i != 0 and i != end:
                        if r[(s, i)].X > 1e-6:
                            f.write(
                                f"scenario {s}, "
                                f"node {i}, "
                                f"area {node_to_area[i]}, "
                                f"shortage {r[(s, i)].X}\n"
                            )

            # --------------------------------------------------
            # Chance-constraint satisfaction for selected arcs
            # --------------------------------------------------

            f.write("\nChance-constraint satisfaction for selected arcs\n")
            f.write("===============================================\n")
            f.write("arc,number_of_satisfied_scenarios,required_scenarios,beta\n")

            required_satisfied = beta * len(S)

            for i, j in model_arcs:
                if x[(i, j)].X > 0.1:

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

            # --------------------------------------------------
            # All joint scenario outcomes
            # --------------------------------------------------

            f.write("\nAll joint scenario outcomes\n")
            f.write("=====================\n")
            f.write(
                "scenario_id,node,name_en,"
                "stochastic_net_change,"
                "stochastic_demand,"
                "stochastic_inflow,"
                "station_status_after_rebalancing,"
                "shortage\n"
            )

            for s in S:
                for i in nodes:
                    if i != 0 and i != end:
                        f.write(
                            f"{s},"
                            f"{i},"
                            f"{node_to_area[i]},"
                            f"{stochastic_net_change[(s, i)]},"
                            f"{stochastic_demand[(s, i)]},"
                            f"{stochastic_inflow[(s, i)]},"
                            f"{st[i].X},"
                            f"{r[(s, i)].X}\n"
                        )

            # --------------------------------------------------
            # Stochastic travel times for selected arcs
            # --------------------------------------------------

            f.write("\nStochastic travel times for selected arcs\n")
            f.write("==========================================\n")
            f.write("scenario_id,from_node,to_node,deterministic_time,stochastic_time,z\n")

            for s in S:
                for i, j in model_arcs:
                    if x[(i, j)].X > 0.1:
                        f.write(
                            f"{s},"
                            f"{i},"
                            f"{j},"
                            f"{cost[(i, j)]},"
                            f"{tau[(s, i, j)]},"
                            f"{z[(s, i, j)].X}\n"
                        )

        print("\nSolution saved to:", solution_path)