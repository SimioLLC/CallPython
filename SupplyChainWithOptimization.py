# import modules
from gurobipy import *
import numpy as np
import pandas as pd
import pyodbc

# connect to database
conn = pyodbc.connect('DSN=JDATA;database=SupplyChainWithOptimization;Trusted_Connection=yes;')
cursor = conn.cursor()

# # # # # # # # # # #
# DATA DEFINITION   #
# # # # # # # # # # #

# store current simulationtime
simulationtime = pd.read_sql("SELECT TOP 1 Datetime FROM Log ORDER BY Datetime DESC;", conn)["Datetime"][0]

#retrieve data from database
database = pd.read_sql("SELECT OpenOrders.OrderNumber, TransportationLanes.OriginLocation, OpenOrders.Quantity, Inventories.InventoryPosition, OpenOrders.DueDate, TransportationLanes.ExpectedTravelTime, Inventories.MaterialName  FROM OpenOrders INNER JOIN TransportationLanes ON (OpenOrders.DestinationLocation = TransportationLanes.DestinationLocation) INNER JOIN Inventories ON (TransportationLanes.OriginLocation = Inventories.LocationName) AND (OpenOrders.MaterialName = Inventories.MaterialName)", conn, parse_dates=['DueDate'])

# define set of distribution centers and inventory levels
DC_Inventory = database.drop_duplicates(subset=['OriginLocation'])[['OriginLocation','InventoryPosition']]
dist_centers, inventory = multidict(dict(zip(DC_Inventory.OriginLocation,DC_Inventory.InventoryPosition)))

# define set of orders and quantities
Orders_Qty = database.drop_duplicates(subset=['OrderNumber'])[['OrderNumber','Quantity']]
orders, quantity = multidict(dict(zip(Orders_Qty.OrderNumber,Orders_Qty.Quantity)))

# define travel matrix
traveltime = database.pivot(index='OrderNumber', columns='OriginLocation', values='ExpectedTravelTime').to_dict()

# define reward matrix
database['Reward'] = 100
reward = database.pivot(index='OrderNumber', columns='OriginLocation', values='Reward').to_dict()

# # # # # # # # # # # # # # # # # # # # # #
# GUROBI MODELING AND OPTIMIZATION        #
# # # # # # # # # # # # # # # # # # # # # #

# create empty model object
model = Model('Sourcing')

# create and fill dictionaries for variable x_ij
x = model.addVars(dist_centers, orders, vtype=GRB.BINARY, name = 'Source')

# define balance constraints
for DC in dist_centers:
    model.addConstr( quicksum( x[DC,order]*quantity[order] for order in orders ) <= inventory[DC] )

# define fulfillment constraints
for order in orders:
    model.addConstr( quicksum( x[DC,order] for DC in dist_centers ) <= 1 )

# set model objective
obj = quicksum(
    x[DC,order] * reward[DC][order] - x[DC,order] * traveltime[DC][order]
    for DC in dist_centers
    for order in orders
)
model.setObjective(obj, GRB.MAXIMIZE)

# solve model
model.optimize()

# display solution
print("Obj: {:.5f}".format(model.objVal))
model.printAttr('X')


# # # # # # # # # # # # # # # # # # # # # #
# Commit Results to Database              #
# # # # # # # # # # # # # # # # # # # # # #

# extract solution from model object to dataframe
temp = []
for v in model.getVars():
    if float(v.x) == 1.0:
        temp.append([v.varName[v.varName.index('[')+1:v.varName.index(']')].split(',')[0],
               int(v.varName[v.varName.index('[')+1:v.varName.index(']')].split(',')[1]),
               float(v.x)])
result = pd.DataFrame(temp, columns=['OriginLocation','OrderNumber','Value'])

# commit sourcing results to database
for index, row in result.iterrows():
    qry = "UPDATE OpenOrders SET PlannedShipDate='{:}', OriginLocation='{:}' WHERE OrderNumber='{:}'".format(
        simulationtime,
        row['OriginLocation'],
        row['OrderNumber']
        )
    cursor.execute(qry)
cursor.commit()

# Add Entry to Log Table
description = "{:} open orders were found. {:} decisions were made.".format(
    len(Orders_Qty.index),
    len(result.index)
    )
cursor.execute("INSERT INTO Log (Program, EventType, Description, Datetime) VALUES ('{:}','{:}','{:}','{:}');".format(
    'Python',
    'Optimization',
    description,
    simulationtime.strftime('%Y-%m-%d %H:%M:%S')
    ))
cursor.commit()

# close database connection
conn.close()