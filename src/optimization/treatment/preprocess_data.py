# -*- coding: utf-8 -*-
"""
preprocess_data.py
====================================
Functions to read, process, store and instantiate all related objects, databases and parameters

@author:
     - c.maldonado
     - ivo.pajor
     - j.rodriguez.villegas
     - g.munera.gonzalez
     - yeison.diaz
"""

from collections import defaultdict
import pandas as pd
from src.optimization.treatment.preprocess_classes.useful_sets import UsefulSets
from src.optimization.treatment.preprocess_classes.processed_data import ProcessedData


def separate_splitter_nodes(processed_data, splitter_nodes, loss_tanks):
    """Method that takes a Dataframe with contaminants information and cleans it

    Parameters
    ----------
    processed_data : ProcessedData
        It has all the processed model's data.
    splitter_nodes: set(string)
        All the splitter nodes in the system.
    loss_tanks: set(string)
        All the loss tank nodes in the system.

    Returns
    -------
    set(string)
        Set that contains all the splitter nodes that are connected to a loss tanks.
    set(string)
        Set that contains all the splitter nodes that are not connected to a loss tanks.
    """

    splitter_nodes_with_loss_tanks = set()
    splitter_nodes_without_loss_tanks = set()
    for node in splitter_nodes:
        splitter_outflow_arcs_to_loss_tank = processed_data.arcs_data[processed_data.arcs_data.index.get_level_values('Node_Start').isin([node]) \
                                                        & processed_data.arcs_data.index.get_level_values('Node_End').isin(loss_tanks)]
        
        if len(splitter_outflow_arcs_to_loss_tank) > 0:
            splitter_nodes_with_loss_tanks.add(node)
        else:
            splitter_nodes_without_loss_tanks.add(node)

    return splitter_nodes_with_loss_tanks, splitter_nodes_without_loss_tanks


def generate_useful_sets(processed_data):
    """Generates some sets that will make the model's generation easier.

    Parameters
    ----------
    processed_data : ProcessedData
        It has all the processed model's data.

    Returns
    -------
    UsefulSets
        It has all the model's sets. 
    """
    #Total nodes of the network
    nodes = set(processed_data.nodes_data.index)

    #Nodes where the flow starts
    initial_nodes = set(processed_data.initial_nodes_data.index)

    #Nodes where the flow ends
    ending_nodes = set(processed_data.ending_nodes_data.index)

    # Initial nodes for which we want to minimize the outflow
    initial_nodes_min_flow = set(processed_data.initial_nodes_data[processed_data.initial_nodes_data['Maximize_Usage'] == 'Y'].index)
    
    # Ending nodes for which we want to maximize the inflow
    ending_nodes_max_flow = set(processed_data.ending_nodes_data[processed_data.ending_nodes_data['Maximize_Usage'] == 'Y'].index)

    # Reuse ending nodes for which we want to maximize the reuse cases
    ending_nodes_reuse = set(processed_data.ending_nodes_data[processed_data.ending_nodes_data['Reuse'] == 'Y'].index)

    #Nodes that have pumps
    pumps_nodes = set(processed_data.pumps_nodes_data.index)

    #Pump nodes have two subcategories, one with linear regresion electriciy consumption,
    pumps_nodes_linear_regression = set([i for i in processed_data.pumps_energy_models_data.index if i in pumps_nodes])

    #The other ones with fixed efficiency 
    pumps_nodes_fixed_efficiency = set([i for i in pumps_nodes if i not in pumps_nodes_linear_regression])

    #Nodes where water gets contaminated
    process_nodes = set(processed_data.process_nodes_data.index)

    #Nodes where contaminants are eliminated
    treatment_nodes = set(processed_data.treatment_nodes_data.index)

    #Nodes that have tanks
    tank_nodes = set(processed_data.tanks_nodes_data.index)

    #evaporation tank nodes 
    loss_tank_nodes = set(processed_data.loss_tanks_nodes_data.index)

    
    #not closed tank nodes 
    pond_nodes = set(processed_data.ponds_nodes_data.index)

    #Nodes where more than one pipe gets in and only one out
    splitter_nodes = set(processed_data.splitter_nodes_data.index)

    splitter_nodes_with_loss_tanks, splitter_nodes_without_loss_tanks = separate_splitter_nodes(processed_data, splitter_nodes, loss_tank_nodes)

    #Nodes where only one pipe gets in and many one out
    mixer_nodes = set(processed_data.mixer_nodes_data.index)

    # Nodes and Arcs that are linked to Water Mix Stability
    mixer_nodes_water_stability = set(processed_data.mixer_nodes_data[processed_data.mixer_nodes_data['WaterMixStability'] == 'Y'].index)
    arcs_water_stability = set(processed_data.arcs_data[processed_data.arcs_data.index.get_level_values("Node_End").isin(mixer_nodes_water_stability)].index)

    # Nodes and Arcs that are linked to Water Mix Stability with Low Priority
    mixer_nodes_water_stability_low_priority = set(processed_data.mixer_nodes_data[processed_data.mixer_nodes_data['WaterMixStability_LowPriority'] == 'Y'].index)
    arcs_water_stability_low_priority = set(processed_data.arcs_data[processed_data.arcs_data.index.get_level_values("Node_End").isin(mixer_nodes_water_stability_low_priority)].index)

    # Nodes and Arcs that are linked to Pond Stability
    mixer_nodes_pond_stability = set(processed_data.mixer_nodes_data[processed_data.mixer_nodes_data['PondStability'] == 'Y'].index)
    arcs_pond_stability = set(processed_data.arcs_data[processed_data.arcs_data.index.get_level_values("Node_End").isin(mixer_nodes_pond_stability)].index)

    # Fixed oil treatment nodes
    oil_treatment_nodes = set(processed_data.oil_treatment_nodes_data.index)

    #nodes that modify temperature:
    cooling_tower_nodes = set(processed_data.cooling_tower_nodes_data.index)
    boiler_nodes = set(processed_data.boiler_nodes_data.index)

    #Contaminants
    contaminants = set([i for i in processed_data.initial_nodes_contaminants_data.index.get_level_values("Contaminant")])

    #Total arcs of the network
    arcs = set(processed_data.arcs_data.index)

    #All arcs that are after a oil splitter
    fixed_splitter_arcs = set(processed_data.splitter_arcs_data.index)

    #All arcs that are after a oil treatment node
    fixed_oil_treatment_arcs = set(processed_data.oil_treatment_arcs_data.index)

    #Let's create 2 sets, one for flow that comes in a Node (entry) and one for flow that goes out from a node (exit)
    exits = defaultdict(set)
    entry = defaultdict(set)

    for (i, j) in set(processed_data.arcs_data.index):
        exits[i].add(j)
        entry[j].add(i)
         
    #Time period
    time_projection={int(processed_data.time_periods)}
    
    oil_nodes = set(processed_data.nodes_data[processed_data.nodes_data["HasOil"] == "Y"].index)

    oil_arcs   = set(processed_data.arcs_data[processed_data.arcs_data["HasOil"] == "Y"].index)
    #These flags represent the recirculation over the system level
    flag_arcs   = set(processed_data.arcs_data[processed_data.arcs_data["Recirculation"] == "Y"].index)

    #Arcs with Nominal Values
    arcs_nominal_values=set(processed_data.arcs_data[processed_data.arcs_data["Nominal_Value"].notnull()].index)

    sets = {
        'nodes': nodes, 
        'initial_nodes': initial_nodes, 
        'ending_nodes': ending_nodes,
        'initial_nodes_min_flow': initial_nodes_min_flow,
        'ending_nodes_max_flow': ending_nodes_max_flow,
        'ending_nodes_reuse': ending_nodes_reuse,
        'pumps_nodes': pumps_nodes,
        'pumps_nodes_linear_regression': pumps_nodes_linear_regression, 
        'pumps_nodes_fixed_efficiency': pumps_nodes_fixed_efficiency,
        'tank_nodes': tank_nodes, 
        'loss_tank_nodes': loss_tank_nodes,
        'pond_nodes': pond_nodes,
        'process_nodes': process_nodes, 
        'treatment_nodes': treatment_nodes, 
        'oil_treatment_nodes': oil_treatment_nodes,
        'splitter_nodes': splitter_nodes,
        'splitter_nodes_with_loss_tanks': splitter_nodes_with_loss_tanks,
        'splitter_nodes_without_loss_tanks': splitter_nodes_without_loss_tanks, 
        'mixer_nodes': mixer_nodes, 
        'cooling_tower_nodes': cooling_tower_nodes, 
        'boiler_nodes': boiler_nodes,
        'oil_nodes': oil_nodes, 
        'contaminants': contaminants,
        'arcs': arcs,
        'arcs_nominal_values': arcs_nominal_values,
        'fixed_splitter_arcs': fixed_splitter_arcs,
        'fixed_oil_treatment_arcs': fixed_oil_treatment_arcs,
        'mixer_nodes_water_stability': mixer_nodes_water_stability,
        'arcs_water_stability': arcs_water_stability,
        'arcs_water_stability_low_priority': arcs_water_stability_low_priority,
        'mixer_nodes_pond_stability': mixer_nodes_pond_stability,
        'arcs_pond_stability': arcs_pond_stability,
        'oil_arcs': oil_arcs, 
        'flag_arcs': flag_arcs, 
        'entry': entry, 
        'exits': exits,
        'time_projection': time_projection
    }

    useful_sets = UsefulSets(sets)

    return useful_sets


def update_processed_data(processed_data, useful_sets):
    """Updates the pumps energy models data (the dataframe should only contain the ones that 
    are going to be used).

    Parameters
    ----------
    processed_data : ProcessedData
        It has all the processed model's data.
        
    useful_sets : UsefulSets
        It has all the model's sets.

    Returns
    -------    
    ProcessedData
        It has all the processed model's data.
    """
    processed_data.pumps_energy_models_data = processed_data.pumps_energy_models_data[processed_data.pumps_energy_models_data.index.isin(list(useful_sets.pumps_nodes_linear_regression))]
    
    return processed_data

def create_time_parameters(processed_data, useful_sets):
    """ Adds the time attribute to the following parameters of the model:
    - Nodes: Min Capacity, Max Capacity, Other Costs, Active and HasOil
    - Arcs:Min Flow, Max Flow, Active, HasOil, Usable Percentage, Recirculation and ArcFlowCost
    
    and returns it in a new Dataframe
    
    Parameters
    ----------
    processed_data : ProcessedData
        It has all the model's processed data.
    useful_sets : UsefulSets
        It has all the model's sets. 
    Returns 
    ----------
    Dictionary of Dataframes
        The Dataframes which contains the new time attribute.
    """
    number_of_periods = list(useful_sets.time_projection)[0]
    
    nodes_with_time = update_nodes_parameters(processed_data, number_of_periods)

    attributes_with_time = update_arcs_parameters(processed_data, nodes_with_time)
    return attributes_with_time

def update_arcs_parameters(processed_data, nodes_with_time):
    arcs_df = processed_data.arcs_data.copy()   
    arcs_df.reset_index(inplace = True)
    attributes_with_time = {}
    attributes_with_time["arcs_data"] = pd.merge(
                                    left=arcs_df.drop('OtherCosts', axis = 1), right=nodes_with_time[['ID','time','OtherCosts']], left_on='Node_End',
                                    right_on='ID', how='left'
                                    ).drop('ID', axis=1)
    attributes_with_time["arcs_data"].set_index(["Node_Start", "Node_End", "time"], inplace = True)
    attributes_with_time["arcs_data"].update(processed_data.sparse_arcs)
    return attributes_with_time

def update_nodes_parameters(processed_data, number_of_periods):
    nodes_df = processed_data.nodes_data.copy()
    nodes_df.reset_index(inplace = True)
    nodes_df = nodes_df.rename(columns = {'index':'ID'})
    nodes_with_time = pd.concat([nodes_df.assign(time = t) for t in range(1, number_of_periods + 1)], ignore_index = True)
    nodes_with_time.set_index(['ID', 'time'], inplace = True)
    nodes_with_time.update(processed_data.sparse_node)
    nodes_with_time.update(processed_data.injection_cost)
    nodes_with_time.reset_index(inplace = True)
    nodes_with_time = nodes_with_time.rename(columns = {'index1':'ID', 'index2': 'time'})
    return nodes_with_time

def preprocess_data(parameters,period, s3_data=False, cost_of_injection = None):
    """Generates the model's processed data and useful sets. It filters the active nodes and generates the 
    index of each dataframe.

    Parameters
    ----------
    parameters : dictionary(string, string)
        It has stored all the not-model's parameters.
    s3_data : Boolean
        Define if read from S3 or not
    cost_of_injection: pd.Dataframe, optional, default None
        cost of the injection model per period
    Returns
    -------
    ProcessedData
        It has all the processed model's data.
    UsefulSets
        It has all the model's sets. 
    """
    #reding and processing input data to get ir ordered
    processed_data = ProcessedData(parameters, s3_data) #instantiating object
    load_data = processed_data.read_data(period)       #reading data
    proc_data = processed_data.process_data(load_data, cost_of_injection)  #processing data
    processed_data.create_attributes(proc_data)         #putting data into attributes
    #creting sets object
    useful_sets = generate_useful_sets(processed_data)
    #reordering to have in consumable conditions
    processed_data = update_processed_data(processed_data, useful_sets)
    #update parameters based on user preferences
    attributes_with_time = create_time_parameters(processed_data, useful_sets)

    return processed_data, useful_sets, attributes_with_time