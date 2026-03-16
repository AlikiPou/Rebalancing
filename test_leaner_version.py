import sys
import math
import random
from itertools import permutations
import numpy as np
import gurobipy as grb
import itertools
from collections import defaultdict
from pathlib import Path

# Testing the case without k index in the decision variables, aka making the assumption of having a uniform fleet of vehicles. Initial load is always 0.

# Create a new model
Rebalancing = grb.Model(name="MIP Model")

# ensure that I keep the same random numbers
rnd = np.random
rnd.seed(0)

nodes = []
#vehicles = []
distanceMatrix = {}
status_node = {}
P = {}
cost = {}
actual_demand = {}
forecast_node = {}

datafiles = []
'''
datafiles.append("Penteli_case.txt")
'''
'''
datafiles.append("Coordinates_12_RC_NYC.txt")
datafiles.append("Coordinates_12_Cluster_NYC.txt")
datafiles.append("Coordinates_15_RC_NYC.txt")
datafiles.append("Coordinates_15_Cluster_NYC.txt")

datafiles.append("Coordinates_12_Cluster_Ber.txt")
datafiles.append("Coordinates_12_Random_Ber.txt")
datafiles.append("Coordinates_12_RC_Ber.txt")
datafiles.append("Coordinates_12_Cluster_Ber.txt")
datafiles.append("Coordinates_12_RC_Bar.txt")
datafiles.append("Coordinates_12_Random_Bar.txt")
datafiles.append("Coordinates_12_Cluster_Bar.txt")
datafiles.append("Coordinates_12_RC_PoA.txt")
datafiles.append("Coordinates_12_Random_PoA.txt")
datafiles.append("Coordinates_12_Cluster_poa.txt")
datafiles.append("Coordinates_12_Random_NYC.txt")

datafiles.append("Coordinates_15_Random_NYC.txt")
datafiles.append("Coordinates_15_RC_Ber.txt")
datafiles.append("Coordinates_15_Random_Ber.txt")
datafiles.append("Coordinates_15_Cluster_Ber.txt")
datafiles.append("Coordinates_15_RC_Bar.txt")
datafiles.append("Coordinates_15_Random_Bar.txt")
datafiles.append("Coordinates_15_Cluster_Bar.txt")
datafiles.append("Coordinates_15_RC_PoA.txt")
datafiles.append("Coordinates_15_Random_PoA.txt")
datafiles.append("Coordinates_15_Cluster_poa.txt")

datafiles.append("Coordinates_20_RC_NYC.txt")
datafiles.append("Coordinates_20_Random_NYC.txt")
datafiles.append("Coordinates_20_Cluster_NYC.txt")
datafiles.append("Coordinates_20_RC_Ber.txt")
datafiles.append("Coordinates_20_Random_Ber.txt")
datafiles.append("Coordinates_20_Cluster_Ber.txt")
datafiles.append("Coordinates_20_RC_Bar.txt")
datafiles.append("Coordinates_20_Random_Bar.txt")
datafiles.append("Coordinates_20_Cluster_Bar.txt")
datafiles.append("Coordinates_20_RC_poa.txt")
datafiles.append("Coordinates_20_Random_PoA.txt")
datafiles.append("Coordinates_20_Cluster_poa.txt")
'''
'''
datafiles.append("Coordinates_5_Random_PoA.txt")
datafiles.append("Coordinates_5_Random_NYC.txt")

datafiles.append("Coordinates_5_Random_Bar.txt")
datafiles.append("Coordinates_5_Random_Ber.txt")

datafiles.append("Coordinates_8_Random_PoA.txt")
datafiles.append("Coordinates_8_Random_NYC.txt")
'''
datafiles.append("Coordinates_8_Random_Bar.txt")
'''
datafiles.append("Coordinates_8_Random_Ber.txt")

datafiles.append("Coordinates_10_Random_PoA.txt")
datafiles.append("Coordinates_10_Random_NYC.txt")
datafiles.append("Coordinates_10_Random_Bar.txt")
datafiles.append("Coordinates_10_Random_Ber.txt")
'''
foldername = 'Instances/DataSetI/'

import os
for i in datafiles:

    path = i
    data_header = np.loadtxt(foldername + path, max_rows=1, dtype=int)
    print(data_header)
    numberOfNodes = data_header[0]
 #   numberOfVehicles = data_header[1]
    vehicleCapacity = data_header[2]

    data_main_body = np.loadtxt(foldername + path, skiprows=1, dtype=float)
    for i in range(0, numberOfNodes + 1):
        actual_demand[i] = int(data_main_body[i, numberOfNodes + 2])
        P[i] = int(data_main_body[i, numberOfNodes + 3])
        status_node[i] = int(data_main_body[i, numberOfNodes + 4])
        forecast_node[i] = status_node[i] - actual_demand[i]
        for j in range(0, numberOfNodes + 1):
            distanceMatrix[(i, j)] = data_main_body[i, j + 1]
            cost[(i, j)] = distanceMatrix[(i, j)]

    # Now you can use the nodes, vehicles, and cost variables
    print('Nodes:', numberOfNodes)
    #print("Vehicles:", numberOfVehicles)
    print("Vehicle Capacity:", vehicleCapacity)
    print("Cost:", distanceMatrix)
    print('Parking Station:', P)
    print('Status in node:', status_node)
    print('Actual demand:', actual_demand)

    nodes = (i for i in range(0, numberOfNodes + 1))
    nodes = tuple(nodes)
    print("Nodes:", nodes)

    locations = (i for i in range(1, numberOfNodes + 1))
    locations = tuple(locations)
    print("Locations:", locations)

    # initial load of vehicle k
    initial_load = {(i): 0 for i in nodes}
    print("The initial load is:", initial_load)

    # number of vehicles
    K = 1

    # penalty
    p = 1500
    print("The penalty for unmet demand is:", p)

    # big M
    M = 100000

    validCut1_subset = {(i, j): [] for i in locations for j in locations}
    for i in locations:
        for j in locations:
            if j <= i:
                continue
            for h in locations:
                if h != i and h != j and i != j:
                    if abs(actual_demand[i] + actual_demand[j] + actual_demand[h]) > vehicleCapacity:
                        subset = h
                        validCut1_subset[i, j].append(subset)

    for i in locations:
        for j in locations:
            if len(validCut1_subset[i, j]) == 0:
                del validCut1_subset[i, j]

    #### decision variables ####
    # Test if 1 y variable taking all values would work and remove g variable
    # if vehicle k traverses arc i,j
    x = {(i, j): Rebalancing.addVar(vtype=grb.GRB.BINARY, name=f"x_{i}_{j}".format(i, j)) for i in nodes for j in nodes}

    # load of vehicle k after serving node i
    l = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"l_{i}".format(i)) for i in nodes}

    # status of station i ∈ N after being served (eta)
    st = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"st_{i}".format(i)) for i in nodes}

    # Number of bikes loaded on vehicle k in station i
    y = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"y_{i}".format(i)) for i in nodes}

    # supporting integer variable to incorporate penalty of unmet demand, calculates excess or shortage
    b = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"b_{i}".format(i)) for i in nodes}

    # integer auxiliary variable used to bound bi
    r = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"r_{i}".format(i)) for i in nodes}

    # binary auxiliary variable used to bound bi, where θi = 1 if there is a shortage of bicycles
    theta = {(i): Rebalancing.addVar(vtype=grb.GRB.BINARY, name=f"theta_{i}".format(i)) for i in nodes}

    # integer auxiliary variable used to bound y_i
    psi = {(i):Rebalancing.addVar(vtype=grb.GRB.BINARY, name=f"psi_{i}".format(i)) for i in nodes}

    # initialisations
    for i in nodes:
        #Rebalancing.addConstr(y[i] >= 0)
        Rebalancing.addConstr(l[i] >= 0)
        Rebalancing.addConstr(st[i] >= 0)
        Rebalancing.addConstr(y[i] >= -40)

    Rebalancing.addConstr(y[0] == 0)
    Rebalancing.addConstr(theta[0] == 0)
    Rebalancing.addConstr(r[0] == 0)
    Rebalancing.addConstr(b[0] == 0)
    for i in nodes:
        for j in nodes:
            if i == j:
                Rebalancing.addConstr(x[i, j] == 0)

    # initialize status
    Rebalancing.addConstr(st[0] == 0)
    Rebalancing.addConstr(P[0] == 0)

    #### Objective function (minimize total cost & penalty of unmet demand) #### (1)
    Rebalancing.setObjective(
        grb.quicksum(cost[i, j] * x[i, j] for i in nodes for j in nodes if i != j)
       + p * grb.quicksum(r[i] for i in nodes), grb.GRB.MINIMIZE)

    #### Constraints ####

    # Everything leaves from the depot (2)
    Rebalancing.addConstr((grb.quicksum(x[0, j] for j in nodes if j != 0)) == K)

    # Everything returns at the depot (3)
    Rebalancing.addConstr((grb.quicksum(x[j, 0] for j in nodes if j != 0)) == K)

    # Every node is served by 1 vehicle and visited at most once (4)
    for i in nodes:
        if i != 0:
            if actual_demand[i] < 0:
                Rebalancing.addConstr(grb.quicksum((x[i, j] for j in nodes if j != i)) == 1)
            else:
                Rebalancing.addConstr(grb.quicksum((x[i, j] for j in nodes if j != i)) <= 1)
    
    # Flow conservation excluding 0 (5)
    for j in nodes:
        if j != 0:
            Rebalancing.addConstr((grb.quicksum(x[i, j] for i in nodes if j != i) - grb.quicksum(x[j, i] for i in nodes if j != i) == 0))


    ## # # # # # # # # # # # # #  Subtour elimination constraint (6)
    ## Excluded 0, Dantzig constraint
    # for s in subset:
    #    Rebalancing.addConstr(grb.quicksum(x[i, j, k] for i in s for j in s if i != j if i!=0 if j!=0 for k in vehicles) <= len(s) - 1)

    # calculate the number of bikes loaded in vehicle after serving node i (7), (8)
    for i in nodes:
        for j in nodes:
            if i != j and j != 0:
                Rebalancing.addConstr(l[j] >= l[i] + y[j] - vehicleCapacity * (1 - x[i, j]))

    for i in nodes:
        for j in nodes:
            if i != j and j != 0:
                Rebalancing.addConstr(l[j] <= l[i] + y[j] + vehicleCapacity * (1 - x[i, j]))
    '''
        # add constraints for unload (negative y[i])
        for i in nodes:
            if i != 0:
                Rebalancing.addConstr(l[i] - y[i] >= - M * psi[i])
    '''

    # load cannot exceed capacity (9)
    for i in nodes:
        Rebalancing.addConstr(l[i] <= vehicleCapacity)

    # the available bikes to load at station cannot exceed the initial status at the station
    for i in nodes:
        Rebalancing.addConstr(y[i] <= status_node[i])

    # parking station capacity cannot be exceeded
    for i in nodes:
        Rebalancing.addConstr(P[i] >= status_node[i] - y[i])

    # the final status of the station after being served
    for i in nodes:
        Rebalancing.addConstr(st[i] == status_node[i] - y[i])

    # the penalty is charged if only there is a shortage of bikes in node i (20), (21), (22), (23)
    for i in nodes:
        if i != 0:
            Rebalancing.addConstr(b[i] == forecast_node[i] - st[i])

    for i in nodes:
        if i != 0:
            Rebalancing.addConstr(r[i] >= b[i])

    for i in nodes:
        if i != 0:
            Rebalancing.addConstr(r[i] <= M * theta[i])

    for i in nodes:
        if i != 0:
            Rebalancing.addConstr(r[i] <= b[i] + M * (1 - theta[i]))

    for i in nodes:
        if i != 0:
            Rebalancing.addConstr(r[i] >= 0)

    # Set the load of vehicle k when leaving the depot equal to the initial vehicle load
    Rebalancing.addConstr(l[0] == initial_load[0])

    ######## VALID INEQUALITIES ######## (30) and (31) from paper
    for h in validCut1_subset:
        for i in locations:
            for j in locations:
                if (i, j) == h:
                    Rebalancing.addConstr(
                        x[i, j] + grb.quicksum(x[j, h] for h in validCut1_subset[i, j]) <= 1)

    for h in validCut1_subset:
        for i in locations:
            for j in locations:
                if (i, j) == h:
                    Rebalancing.addConstr(
                        grb.quicksum(x[h, i] for h in validCut1_subset[i, j]) + x[i, j] <= 1)


    ###CALLBACK METHOD- LAZY CONSTRAINTS - SUBTOUR ELIMINATION

    # Callback - use lazy constraints to eliminate sub-tours
    def subtourelim(Rebalancing, where):
        if where == grb.GRB.Callback.MIPSOL:
            # make a list of edges selected in the solution
            vals = Rebalancing.cbGetSolution(Rebalancing._x)
            #for f in range(1, numberOfVehicles + 1):  # subtouring for each vehicle
            selected = grb.tuplelist(
                (i, j) for i, j in Rebalancing._x.keys() if vals[i, j] > 0.5)
                ##find the shortest cycle in the selected edge list
                ## tour = subtour(selected)
                # tour = find_subtours(selected, f)
            tour = shortest_subtour(selected)
            if tour != None:
                # Rebalancing.cbLazy(grb.quicksum(Rebalancing._x[i, j, k] for i, j, k in permutations(tour, 3)) <= len(tour) - 1)
                Rebalancing.cbLazy(grb.quicksum(
                    Rebalancing._x[i, j] for i in tour for j in tour if i != j if i != 0 if j != 0) <= len(tour) - 1)


    # Given a tuplelist of edges, find the shortest subtour not containing depot
    def shortest_subtour(selected):
        """Given a list of edges, return the shortest subtour (as a list of nodes)
        found by following those edges. It is assumed there is exactly one 'in'
        edge and one 'out' edge for every node represented in the edge list."""

        # Create a mapping from each node to its neighbours
        node_neighbors = defaultdict(list)

        for i, j in selected:
            node_neighbors[i].append(i)
            node_neighbors[i].append(j)
            # counter = counter + 1
        # assert all(len(neighbors) == 2 for neighbors in node_neighbors.values())

        keys = list(node_neighbors.keys())
        node_neighbors_arr = []
        rows, cols = len(selected), 2
        for i in keys:
            col = []
            for j in range(cols):
                col.append(node_neighbors[i][j])
            node_neighbors_arr.append(col)

        # Follow edges to find cycles. Each time a new cycle is found, keep track
        # of the shortest cycle found so far and restart from an unvisited node.
        unvisited = set(node_neighbors)
        subtour = None
        subtourExists = False
        cycle = []
        firstNode = -1
        lastNode = -1
        neighbors = list(unvisited)
        next = 0
        counter = 0
        count = False
        while node_neighbors:
            for i in range(0, len(node_neighbors_arr)):
                if i >= len(node_neighbors_arr):
                    count == False
                    break

                if count == True:
                    i = i - 1
                if next != node_neighbors_arr[i][0] and subtourExists == False:
                    counter = counter + 1
                    continue
                prev = node_neighbors_arr[i][0]
                if i == 0 or subtourExists == True:
                    if count == False:
                        firstNode = prev
                        cycle.append(prev)
                        subtourExists = False
                next = node_neighbors_arr[i][1]
                cycle.append(next)
                del node_neighbors_arr[i]
                del node_neighbors[prev]
                count = True
                counter = counter + 1
                if next == 0:
                    if firstNode == 0:
                        if len(node_neighbors) == 0:
                            return subtour  # No subtour
                        else:
                            cycle.clear()
                            subtourExists = True
                            count = False
                            break
                elif firstNode == next:  # and len(node_neighbors) == 0:
                    subtour = cycle
                    return subtour

        assert subtour is not None
        return subtour


    # Optimize the model
    Rebalancing._x = x
    Rebalancing.Params.LazyConstraints = 1
    Rebalancing.setParam('MIPGap', 0.00)  # finish running once 5% gap is reached
    Rebalancing.setParam('Timelimit', 7200) # finish running once 2hrs has passed
    Rebalancing.optimize(subtourelim)

    runtime = Rebalancing.Runtime
    runtime = "%.2f" % runtime
    RoutingCosts = 0
    gap = Rebalancing.MIPGap
    for i, j in x:
        if x[i, j].x > 0.1:
            RoutingCosts = RoutingCosts + cost[i, j]
            print(f"x_{i}_{j}:", x[i, j])
    print("RoutingCosts", RoutingCosts)
    obj = 0
    obj = Rebalancing.objVal

    f = open('Solutions/DataSetI/DataSetI_test' + path, 'w')
    counter = 0
    f.write(f"{RoutingCosts} {obj} {runtime} {gap}\n")
    for i, j in x:
        if x[i, j].x > 0.0:
            f.write(f"{i}_{j}\n")

    # Rebalancing.setParam(grb.Param.heuristics, 0.0)

    print("Start from here")

    for v in Rebalancing.getVars():
        print('%s %g' % (v.varName, v.x))
    Rebalancing.printAttr('x')

    print("Values of x:")
    for i, j, in x:
        if x[i, j].x > 0.1:
            print(f"x_{i}_{j}:", x[i, j])

    Rebalancing.reset()