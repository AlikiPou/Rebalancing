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
# vehicles = []
distanceMatrix = {}
status_node = {}
P = {}
cost = {}
actual_demand = {}
forecast_node = {}
S = 3

datafiles = []

'''
datafiles.append("Coordinates_7_Athens.txt")

datafiles.append("Coordinates_12_Cluster_Ber.txt")
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
datafiles.append("Coordinates_12_Cluster_NYC.txt")
datafiles.append("Coordinates_12_RC_NYC.txt")


datafiles.append("Coordinates_15_Random_NYC.txt")
datafiles.append("Coordinates_15_RC_Ber.txt")
'''
datafiles.append("Coordinates_15_Random_Ber.txt")
'''
datafiles.append("Coordinates_15_Cluster_Ber.txt")
datafiles.append("Coordinates_15_RC_Bar.txt")
datafiles.append("Coordinates_15_Random_Bar.txt")
datafiles.append("Coordinates_15_Cluster_Bar.txt")
datafiles.append("Coordinates_15_RC_PoA.txt")
datafiles.append("Coordinates_15_Random_PoA.txt")
datafiles.append("Coordinates_15_Cluster_PoA.txt")
datafiles.append("Coordinates_15_RC_NYC.txt")
datafiles.append("Coordinates_15_RC_NYC.txt")
datafiles.append("Coordinates_15_Cluster_NYC.txt")

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
foldername = 'Instances/ZeroDemand/'

import os

for i in datafiles:

    path = i
    data_header = np.loadtxt(foldername + path, max_rows=1, dtype=int)
    print('----------', path, '----------------------------')
    numberOfNodes = data_header[0]
    #   numberOfVehicles = data_header[1]
    vehicleCapacity = data_header[2]

    data_main_body = np.loadtxt(foldername + path, skiprows=1, dtype=float)
    for i in range(0, numberOfNodes + 2):
        if (i != numberOfNodes + 1):
            actual_demand[i] = int(data_main_body[i, numberOfNodes + 2])
            P[i] = int(data_main_body[i, numberOfNodes + 3])
            status_node[i] = int(data_main_body[i, numberOfNodes + 4])
            forecast_node[i] = status_node[i] - actual_demand[i]
        else:
            actual_demand[i] = int(data_main_body[0, numberOfNodes + 2])
            P[i] = int(data_main_body[0, numberOfNodes + 3])
            status_node[i] = int(data_main_body[0, numberOfNodes + 4])
            forecast_node[i] = status_node[0] - actual_demand[0]
        for j in range(0, numberOfNodes + 2):
            if(j != numberOfNodes + 1):
                if( i != numberOfNodes + 1):
                    distanceMatrix[(i, j)] = data_main_body[i, j + 1]
                    cost[(i, j)] = distanceMatrix[(i, j)]
                else:
                    distanceMatrix[(i, j)] = data_main_body[0, j + 1]
                    cost[(i, j)] = distanceMatrix[(0, j)]
            else:
                if (i != numberOfNodes + 1):
                    distanceMatrix[(i, j)] = data_main_body[i, 0]
                    cost[(i, j)] = distanceMatrix[(i, 0)]
                else:
                    distanceMatrix[(i, j)] = data_main_body[0, 0]
                    cost[(i, j)] = distanceMatrix[(0, 0)]

    # Now you can use the nodes, vehicles, and cost variables
    '''
    print('Nodes:', numberOfNodes)
    # print("Vehicles:", numberOfVehicles)
    print("Vehicle Capacity:", vehicleCapacity)
    print("Cost:", distanceMatrix)
    print('Parking Station:', P)
    print('Status in node:', status_node)
    print('Actual demand:', actual_demand)
    '''
    nodes = (i for i in range(0, numberOfNodes + 2))
    nodes = tuple(nodes)
    # print("Nodes:", nodes)

    locations = (i for i in range(1, numberOfNodes + 2))
    locations = tuple(locations)
    # print("Locations:", locations)

    # initial load of vehicle k
    initial_load = {(i): 0 for i in nodes}
    print("The initial load is:", initial_load)

    # number of vehicles
    K = 2

    # penalty
    p = 1500
    # print("The penalty for unmet demand is:", p)

    # big M
    M = 100000

    #### decision variables ####
    # Test if 1 y variable taking all values would work and remove g variable
    # if vehicle k traverses arc i,j
    x = {(i, j): Rebalancing.addVar(vtype=grb.GRB.BINARY, name=f"x_{i}_{j}".format(i, j)) for i in nodes for j in nodes if i!= (numberOfNodes +1)}

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

    # time component
    t = {(i): Rebalancing.addVar(vtype=grb.GRB.INTEGER, lb=-10000000, name=f"t_{i}".format(i)) for i in nodes}

    # initialisations
    for i in nodes:
        # Rebalancing.addConstr(y[i] >= 0)
        Rebalancing.addConstr(l[i] >= 0)
        Rebalancing.addConstr(st[i] >= 0)
        Rebalancing.addConstr(y[i] >= -40)

    Rebalancing.addConstr(y[0] == 0)
    Rebalancing.addConstr(theta[0] == 0)
    Rebalancing.addConstr(t[0] == 0)
    Rebalancing.addConstr(r[0] == 0)
    Rebalancing.addConstr(b[0] == 0)

    Rebalancing.addConstr(y[numberOfNodes +1] == 0)
    Rebalancing.addConstr(theta[numberOfNodes +1] == 0)
    Rebalancing.addConstr(r[numberOfNodes +1] == 0)
    Rebalancing.addConstr(b[numberOfNodes +1] == 0)
    for i in nodes:
        for j in nodes:
            if i == j and i < numberOfNodes + 1:
                Rebalancing.addConstr(x[i, j] == 0)

    # initialize status
    st[0] = 0
    P[0] = 0
    st[numberOfNodes +1] = 0
    P[numberOfNodes +1] = 0

    #### Objective function (minimize total cost & penalty of unmet demand) #### (1)
    Rebalancing.setObjective(
        grb.quicksum(cost[i, j] * x[i, j] for i in nodes for j in nodes if i != j and i < (numberOfNodes + 1) )
        + p * grb.quicksum(r[i] for i in nodes), grb.GRB.MINIMIZE)

    #### Constraints ####

    # Everything leaves from the depot (2)
    Rebalancing.addConstr((grb.quicksum(x[0, j] for j in nodes if j != 0 and j != (numberOfNodes + 1))) == K)

    # Everything returns at the depot (3)
    Rebalancing.addConstr((grb.quicksum(x[j, numberOfNodes+1] for j in nodes if j != 0 and j != (numberOfNodes + 1))) == K)

    # Every node is served at most once (4)
    for i in nodes:
        if i != 0 and i < (numberOfNodes + 1):
            Rebalancing.addConstr(grb.quicksum((x[i, j] for j in nodes if j != i and j != 0)) <= 1)

    # Flow conservation excluding 0 (5)
    for j in nodes:
        if j != 0 and j != (numberOfNodes + 1):
            Rebalancing.addConstr(
                (grb.quicksum(x[i, j] for i in nodes if j != i and i < (numberOfNodes + 1)) - grb.quicksum(x[j, i] for i in nodes if j != i and i !=0) == 0))

    # Time sequencing (6)
    for i in nodes:
        for j in nodes:
            if i != j and j != 0 and i < (numberOfNodes + 1):
                Rebalancing.addConstr(t[j] >= t[i] + cost[i, j] - M * (1 - x[i, j]))

    # calculate the number of bikes loaded on vehicle after serving node i (7),(8)
    for i in nodes:
        for j in nodes:
            if i != j and j != 0 and j != (numberOfNodes + 1) and i < (numberOfNodes + 1):
                Rebalancing.addConstr(l[j] >= l[i] + y[j] - vehicleCapacity * (1 - x[i, j]))

    for i in nodes:
        for j in nodes:
            if i != j and j != 0 and j != (numberOfNodes + 1) and i < (numberOfNodes + 1):
                Rebalancing.addConstr(l[j] <= l[i] + y[j] + vehicleCapacity * (1 - x[i, j]))

    # load cannot exceed capacity (9)
    for i in nodes:
        Rebalancing.addConstr(l[i] <= vehicleCapacity)

    # the available bikes to load at station cannot exceed the initial status at the station (10)
    for i in nodes:
        Rebalancing.addConstr(y[i] <= status_node[i])

    # If y[j] > 0, cannot load more than remaining vehicle capacity (11)
    for i in nodes:
        for j in nodes:
            if i != j and j != 0 and j != (numberOfNodes + 1) and i < (numberOfNodes + 1):
                Rebalancing.addConstr(y[j] <= vehicleCapacity - l[i] + M * (1 - x[i, j]))

    # If y[j] < 0, cannot unload more than current vehicle load (12)
    for i in nodes:
        for j in nodes:
            if i != j and j != 0 and j != (numberOfNodes + 1) and i < (numberOfNodes + 1):
                Rebalancing.addConstr(-y[j] <= l[i] + M * (1 - x[i, j]))

    # If a station is not visited, y[i] must be zero (13), (14)
    for j in nodes:
        Rebalancing.addConstr(y[j] >= - M * grb.quicksum(x[i, j] for i in nodes if i != j and i < (numberOfNodes + 1)))

    for j in nodes:
        Rebalancing.addConstr(y[j] <= M * grb.quicksum(x[i, j] for i in nodes if i != j and i < (numberOfNodes + 1)))

    # the final status of the station after being served (16)
    for i in nodes:
        Rebalancing.addConstr(st[i] == status_node[i] - y[i])

    # parking station capacity cannot be exceeded (15)
    for i in nodes:
        Rebalancing.addConstr(P[i] >= st[i])

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

    # Set the load of vehicle k when leaving the depot equal to the initial vehicle load
    Rebalancing.addConstr(l[0] == initial_load[0])
    Rebalancing.addConstr(l[numberOfNodes+1] == initial_load[0])

    end = numberOfNodes + 1

    # Μην επιτρέπεις απευθείας 0 -> end
    Rebalancing.addConstr(x[0, end] == 0)

    # Κανένας κόμβος δεν πρέπει να επιστρέφει στο αρχικό depot 0
    for i in nodes:
        if i != 0 and i < end:
            Rebalancing.addConstr(x[i, 0] == 0)

    #Optimize the model
    Rebalancing.setParam('Timelimit', 7200)  # finish running once 2hrs has passed
    Rebalancing._x = x

    #Rebalancing.Params.LazyConstraints = 1
    Rebalancing.setParam('MIPGap', 0.00)  # finish running once 5% gap is reached
    Rebalancing.setParam('Timelimit', 7200)  # finish running once 2hrs has passed
    # Rebalancing.optimize(subtourelim)
    Rebalancing.optimize()


    runtime = Rebalancing.Runtime
    runtime = "%.2f" % runtime
    RoutingCosts = 0
    gap = Rebalancing.MIPGap
    for i, j in x:
        if x[i, j].x > 0.1:
            RoutingCosts = RoutingCosts + cost[i, j]
            #            print(f"x_{i}_{j}:", x[i, j])
    print("RoutingCosts", RoutingCosts)
    obj = 0
    obj = Rebalancing.objVal

    f = open('SolutionsTime/ZeroDemand/' + path, 'w')
    counter = 0
    f.write(f"{RoutingCosts} {obj} {runtime} {gap}\n")
    for i, j in x:
        if x[i, j].x > 0.0:
            f.write(f"{i}_{j}\n")

    f.write("\nLoading/unloading variables y[i]\n")
    for i in nodes:
        if abs(y[i].x) > 1e-6:
            f.write(f"y_{i} {y[i].x}\n")

    f.close()
    # Rebalancing.setParam(grb.Param.heuristics, 0.0)

    print("Start from here")
    '''
    for v in Rebalancing.getVars():
        print('%s %g' % (v.varName, v.x))a
    Rebalancing.printAttr('x')
    '''
    #print("Values of x:")
    for i, j, in x:
        if x[i, j].x > 0.1:
            print(f"x_{i}_{j}:", x[i, j])

    Rebalancing.reset()