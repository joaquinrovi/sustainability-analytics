# -*- coding: utf-8 -*-
"""
make_model.py
====================================
This script store the functions to build and run pyomo model

@author:
     - c.maldonado
     - yeison.diaz
     - ivo.pajor
     - j.rodriguez.villegas
     - g.munera.gonzalez
"""

from re import T
import pyomo.environ as pe
import pandas as pd
import src.optimization.treatment.constraints.constraints as constraints
import datetime as dt
from src.optimization.treatment.preprocess_data import preprocess_data

def set_sets(model, useful_sets):
    """Defines the useful_sets in the model.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    useful_sets : UsefulSets
        It has all the model's sets. 

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    #Define Sets
    #Time Dimension
    model.time_dim = pe.RangeSet(list(useful_sets.time_projection)[0])
    #Nodes
    model.nodes = pe.Set(initialize=useful_sets.nodes)
    #Define start nodes that must be in nodes
    model.initial = pe.Set(within=model.nodes, initialize=useful_sets.initial_nodes)
    #Define end nodes that must be in nodes
    model.ending = pe.Set(within=model.nodes, initialize=useful_sets.ending_nodes)
    
    model.initial_min = pe.Set(within = model.initial, initialize = useful_sets.initial_nodes_min_flow)
    model.ending_max = pe.Set(within = model.ending, initialize = useful_sets.ending_nodes_max_flow)
    model.reuse = pe.Set(within = model.ending, initialize = useful_sets.ending_nodes_reuse)

    #Define the pumps that must be in nodes
    model.pumps = pe.Set(within=model.nodes, initialize=useful_sets.pumps_nodes)
    #Define the pumps subcategories
    model.pumps_fixed_efficiency = pe.Set(within= model.pumps, initialize=useful_sets.pumps_nodes_fixed_efficiency)
    model.pumps_linear_regression = pe.Set(within= model.pumps, initialize=useful_sets.pumps_nodes_linear_regression)
    #Define process nodes that must be a subset of principal nodes
    model.process = pe.Set(within=model.nodes, initialize=useful_sets.process_nodes)
    #Define treatment nodes that must be a subset of principal nodes
    model.treatment = pe.Set(within=model.nodes, initialize=useful_sets.treatment_nodes)
    #Define fixed oil treatment nodes that must be a subset of principal nodes
    model.oil_treatment = pe.Set(within=model.nodes, initialize=useful_sets.oil_treatment_nodes)
    #Define mix nodes that must be a subset of principal nodes
    model.mix = pe.Set(within=model.nodes, initialize=useful_sets.mixer_nodes)
    #Define split nodes that must be a subset of principal nodes
    model.split = pe.Set(within=model.nodes, initialize=useful_sets.splitter_nodes)
    model.splitter_with_loss_tanks = pe.Set(within=model.nodes, initialize=useful_sets.splitter_nodes_with_loss_tanks)
    model.splitter_without_loss_tanks = pe.Set(within=model.nodes, initialize=useful_sets.splitter_nodes_without_loss_tanks)
    #Define tank nodes that must be a subset of principal nodes
    model.tanks = pe.Set(within = model.nodes, initialize = useful_sets.tank_nodes)
    model.loss_tanks = pe.Set(within = model.nodes, initialize = useful_sets.loss_tank_nodes)
    model.ponds = pe.Set(within = model.nodes, initialize = useful_sets.pond_nodes)
    #Define cooling system nodes that must be a subset of principal nodes
    model.cooling_towers = pe.Set(within = model.nodes, initialize = useful_sets.cooling_tower_nodes)
    #Define boiler nodes that must be a subset of principal nodes
    model.boiler = pe.Set(within = model.nodes, initialize = useful_sets.boiler_nodes)
    #Define the nodes that will have oil
    model.oil_nodes = pe.Set(within = model.nodes, initialize = useful_sets.oil_nodes)

    #Contaminants
    model.contaminants = pe.Set(initialize = useful_sets.contaminants)

    #Valid Arcs that must be a combination of principal nodes (within is not necessary but is good practice for error checking)
    model.arcs = pe.Set(within = model.nodes*model.nodes, initialize = useful_sets.arcs)
    #Valid Arcs with nominal values that must be a subset of the arcs (within is not necessary but is good practice for error checking)
    model.arcs_nominal = pe.Set(within = model.arcs, initialize = useful_sets.arcs_nominal_values)
    #Define arcs after splitter nodes
    model.fixed_splitter_arcs = pe.Set(within = model.nodes*model.nodes, initialize = useful_sets.fixed_splitter_arcs)
    #Define arcs after oil treatment nodes
    model.fixed_oil_treatment_arcs = pe.Set(within = model.oil_treatment*model.nodes, initialize = useful_sets.fixed_oil_treatment_arcs)
    #Some arcs have oil:
    model.oil_arcs = pe.Set(within = model.nodes*model.nodes, initialize = useful_sets.oil_arcs)
    #Define the arcs that have "flags"
    model.flags_arcs = pe.Set(within = model.nodes*model.nodes, initialize = useful_sets.flag_arcs)
    #Define the arcs that are considered for water mix stability
    model.arcs_water_stability = pe.Set(within = model.nodes*model.nodes, initialize = useful_sets.arcs_water_stability)
    model.arcs_water_stability_low_priority = pe.Set(within = model.nodes*model.nodes, initialize = useful_sets.arcs_water_stability_low_priority)
    #Define the arcs that are considered for pond stability
    model.arcs_pond_stability = pe.Set(within = model.nodes*model.nodes, initialize = useful_sets.arcs_pond_stability)

    return model


def set_parameters(model, processed_data, useful_sets, attributes_with_time):
    """Defines the model's processed_data parameters in the model.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    processed_data : ProcessedData
        It has all the model's processed data.
    useful_sets : UsefulSets
        It has all the model's sets. 
    attributes_with_time: Dictionary(string, pd.Dataframe)
    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    #ARCS PARAMETERS:

    model.min_flow = pe.Param(model.arcs, initialize=processed_data.arcs_data["MinFlow"].to_dict())
    model.max_flow = pe.Param(model.arcs, initialize=processed_data.arcs_data["MaxFlow"].to_dict()) 
    #This would be opening and closing the gate
    model.usable_percentage = pe.Param(model.arcs, model.time_dim, initialize=attributes_with_time['arcs_data']["UsablePercentage"].to_dict())
    model.flow_cost = pe.Param(model.arcs, initialize=processed_data.arcs_data["ArcFlowCost"].to_dict())
    model.other_cost = pe.Param(model.arcs, model.time_dim, initialize=attributes_with_time['arcs_data']['OtherCosts'].to_dict(),within=pe.Any,mutable=True)
    model.arc_has_oil = pe.Param(model.arcs, initialize=processed_data.arcs_data['HasOil'].to_dict(),within=pe.Any)
    
    model.arc_flag = pe.Param(model.arcs, initialize=processed_data.arcs_data['Recirculation'].to_dict(),within=pe.Any)

    #Some arcs have the water percentage fixed
    model.fixed_water_percentage = pe.Param(model.fixed_oil_treatment_arcs, initialize=processed_data.oil_treatment_arcs_data['FixedWaterPercentage'].to_dict(), within=pe.Any)
    #Some arcs have the Oil Percentage fixed
    model.fixed_oil_percentage = pe.Param(model.fixed_oil_treatment_arcs, initialize=processed_data.oil_treatment_arcs_data['FixedOilPercentage'].to_dict(), within=pe.Any)
    #Splitting oil arcs parameter
    model.fixed_percentage = pe.Param(model.fixed_splitter_arcs, initialize=processed_data.splitter_arcs_data['FixedPercentage'].to_dict(), within=pe.Any)
    #Nominal values per arc
    model.nominal_values = pe.Param(model.arcs, model.time_dim, initialize=attributes_with_time['arcs_data']["Nominal_Value"].to_dict(), within=pe.Any)

    #NODES PARAMETERS
    #Nodes that  are connected in and out each node
    model.entry = pe.Param(model.nodes, initialize=useful_sets.entry, default=set(), within=pe.Any)
    model.exit = pe.Param(model.nodes, initialize=useful_sets.exits, default=set(), within=pe.Any)

    model.min_capacity = pe.Param(model.nodes, initialize=processed_data.nodes_data["MinCapacity"].to_dict())
    model.max_capacity = pe.Param(model.nodes, initialize=processed_data.nodes_data["MaxCapacity"].to_dict())

    model.node_has_oil = pe.Param(model.nodes, initialize=processed_data.nodes_data["HasOil"].to_dict())
    
    #Starting nodes parameters
    model.water_in = pe.Param(model.initial, model.time_dim, initialize=processed_data.tanks_flow["WaterQty"].to_dict())
    model.oil_in = pe.Param(model.initial,model.time_dim,  initialize=processed_data.tanks_flow["OilQty"].to_dict())
    model.contaminant_in = pe.Param(model.initial,model.contaminants,model.time_dim, initialize=processed_data.initial_nodes_contaminants_data["value"].to_dict(), within=pe.Any)
    model.initial_content_contaminants_tanks = pe.Param(model.tanks,model.contaminants, initialize=processed_data.initial_content_contaminants_tanks["value"].to_dict(), within=pe.Any)
    model.initial_content_contaminants_ponds = pe.Param(model.ponds,model.contaminants, initialize=processed_data.initial_content_contaminants_ponds["value"].to_dict(), within=pe.Any)

    #Ending nodes parameters
    model.ending_demand = pe.Param(model.ending,model.time_dim, initialize=processed_data.terminal_dinamic_capacity["Aditional Total Capacity"].to_dict(), within=pe.Any)

    #Pump nodes parameters
    model.pressure_in = pe.Param(model.pumps, initialize=processed_data.pumps_nodes_data["PressureIn"].to_dict(),within=pe.Any)
    model.pressure_out = pe.Param(model.pumps, initialize=processed_data.pumps_nodes_data["PressureOut"].to_dict(),within=pe.Any)

    model.efficiency = pe.Param(model.pumps, initialize=processed_data.pumps_nodes_data["Efficiency"].to_dict(),within=pe.Any)
    
    model.pumps_energy_model_pressure_coef = pe.Param(model.pumps_linear_regression, initialize=processed_data.pumps_energy_models_data["SLOPE_P"].to_dict(), within=pe.Any)
    model.pumps_energy_model_flow_rate_coef = pe.Param(model.pumps_linear_regression, initialize=processed_data.pumps_energy_models_data["SLOPE_Q"].to_dict(), within=pe.Any)
    model.pumps_energy_model_intercept_coef = pe.Param(model.pumps_linear_regression, initialize=processed_data.pumps_energy_models_data["INTERCEPT"].to_dict(), within=pe.Any)

    #Process Nodes parameters:
    model.contaminant_addition_ppm = pe.Param(model.process * model.contaminants, initialize=processed_data.process_nodes_contaminants_data['Addition_Qty(mg)'].to_dict(),within=pe.Any)

    #Treatment Nodes parameters:
    model.contaminant_removal_rate = pe.Param(model.treatment * model.contaminants, initialize=processed_data.treatment_nodes_contaminants_data['Removal_Percentage'].to_dict(),within=pe.Any)

    #Tanks and Ponds parameters:
    model.initial_content = pe.Param(model.tanks.union(model.ponds), initialize=processed_data.inital_content, within=pe.Any)
    
    #Pond Nodes Parameters:
    model.pond_average_surface = pe.Param(model.ponds, initialize=processed_data.ponds_nodes_data['avg_area'].to_dict())
    model.forecasted_evap_rate = pe.Param(model.time_dim, initialize=processed_data.evaporation_rates['evaporation_rate'].to_dict())

    #OTHER PARAMETERS:

    #Energy cost in dollars
    model.energy_cost = processed_data.energy_cost
    model.watt_to_kwh = processed_data.watt_to_kwh
    #Penalization of initial storage
    model.BigPenalty=processed_data.nodes_data["MaxCapacity"].max()
    model.BigPenaltyArcs=processed_data.arcs_data["MaxFlow"].max()

    return model

def set_variables(model):
    """Sets the model's variables.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    # let´s define the arc's variables (Quantity to send by arc)
    model.x_water       = pe.Var(model.arcs,model.time_dim,domain=pe.NonNegativeReals)
    model.x_oil         = pe.Var(model.oil_arcs,model.time_dim,domain=pe.NonNegativeReals)
    model.x_contaminant = pe.Var(model.arcs * model.contaminants,model.time_dim, domain=pe.NonNegativeReals)
    model.x_water_delta = pe.Var(model.arcs, model.time_dim, domain=pe.NonNegativeReals)
    model.x_active_arc_watermix  = pe.Var(model.arcs_water_stability.union(model.arcs_water_stability_low_priority), model.time_dim, domain=pe.Binary) #binary variables for arcs of water mix
    model.x_active_arc_pond  = pe.Var(model.arcs_pond_stability, model.time_dim, domain=pe.Binary) #binary variables for arcs of pond stability

    # Slack variables for arcs for water mix and pond stability. One positive and one negative to allow to model to be less or more than target (best practice to have slacks >=0)
    model.slack_positive_watermix = pe.Var(model.arcs_water_stability.union(model.arcs_water_stability_low_priority), model.time_dim, domain=pe.NonNegativeReals) 
    model.slack_negative_watermix = pe.Var(model.arcs_water_stability.union(model.arcs_water_stability_low_priority), model.time_dim, domain=pe.NonNegativeReals) 

    model.slack_positive_pond = pe.Var(model.arcs_pond_stability, model.time_dim, domain=pe.NonNegativeReals) 
    model.slack_negative_pond = pe.Var(model.arcs_pond_stability, model.time_dim, domain=pe.NonNegativeReals) 

    # let's define the node's variables
    model.y_water       = pe.Var(model.nodes, model.time_dim, domain=pe.NonNegativeReals)
    model.y_oil         = pe.Var(model.oil_nodes, model.time_dim, domain=pe.NonNegativeReals)
    model.y_elec_amount = pe.Var(model.pumps, model.time_dim, domain=pe.NonNegativeReals)
    model.y_contaminant = pe.Var(model.nodes,model.contaminants,model.time_dim, domain=pe.NonNegativeReals)
    model.xActivePump   = pe.Var(model.nodes, model.time_dim, domain = pe.Binary)
    model.xActivePonds  = pe.Var(model.ponds, model.time_dim, domain = pe.Binary)
    return model

def penalty_initial_nodes(model): 
    storage_penalty= sum(model.y_water[i,t] * model.BigPenalty\
        for i in model.initial\
            for t in model.time_dim)
    return storage_penalty

def calculate_recirculation(model):
    '''
    Function that calculates the recirculation of the model.
    The recirculation is defined as the water that pass through some marked arcs in each period.
    
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Return
    ------------
    double
        Recirculation value
    '''
    recirculation_function = sum(model.x_water[i,j,t] for (i,j) in model.flags_arcs\
        for t in model.time_dim)

    return recirculation_function

def calculate_delta_water_nominal(model):
    '''
    Function that calculates the delta of the water flow of an arc based on the nominal value.    
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Return
    ------------
    double
        Delta of water between nominal value and water flow
    '''
    nominal_function = sum(model.x_water_delta[i,j,t] for (i,j) in model.arcs_nominal\
        for t in model.time_dim)

    return nominal_function


def calculate_cost(model):
    """ 
    Given a model, it calculates its cost.
    The cost is defined as the sum of:
    - Electrical costs of each pump in each period. The electrical cost is calculated as the product of the energy consumed by the pump and the energy cost.
    - Other costs of each water arc in each period. This is the flow of water times the other cost for each arc.
    - Similar to the previous one but with oil arcs.
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    double
        the model's cost

    """
    electrical_costs = sum(model.y_elec_amount[i,t]*model.energy_cost for i in model.pumps\
        for t in model.time_dim)
    
    flow_costs_water = sum(model.x_water[i,j,t] * model.flow_cost[i,j]\
        for (i, j) in model.arcs if i not in list(model.ending)\
        for t in model.time_dim)
    
    flow_costs_oil = sum((model.x_oil[i,j,t]) * model.flow_cost[i,j]\
        for (i, j) in model.oil_arcs if i not in list(model.ending)\
        for t in model.time_dim)
    
    other_costs_water = sum((model.x_water[i,j,t]) * model.other_cost[i,j,t]\
        for (i, j) in model.arcs if i not in list(model.ending)\
            for t in model.time_dim)
    
    other_costs_oil = sum((model.x_oil[i,j,t]) * model.other_cost[i,j,t]\
        for (i, j) in model.oil_arcs if i not in list(model.ending)\
            for t in model.time_dim)
    
    return electrical_costs + flow_costs_water + flow_costs_oil + other_costs_water + other_costs_oil


def calculate_supply_demand_flow(model):
    """
    Function that returns the sum of:
        - Inflow of certain ending nodes.
        - Outflow of certain initial nodes.
    
    The idea is that we are trying to make that all the water goes to some subset of ending nodes. and at the same time
    we are trying to reduce the use of some subset of the initial nodes.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    double
        The sum defined

    """
    chosen_initial_nodes_flow = sum(model.y_water[i,t] for i in model.initial_min\
        for t in model.time_dim)

    chosen_ending_nodes_flow = sum(model.y_water[i,t] for i in model.ending_max\
        for t in model.time_dim)

    flow = chosen_ending_nodes_flow  - chosen_initial_nodes_flow
    return flow 


def calculate_energy_cost(model):
    """
    This function calculate the energy cost of the model.
    The energy cost is defined as the sum of the products of the electrical consumption of each pump and the energy cost.
    This is done considering all periods.    

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    double
        the model's electricity cost
 
    """
    electrical_costs = sum(model.y_elec_amount[i,t]*model.energy_cost for i in model.pumps\
        for t in model.time_dim)
    
    return electrical_costs


def calculate_end_benefit(model):
    '''
    This function returns the end benefit of the model.
    The enf benefit is defined as the sum of the inflow of every end node in every period.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    double
        End benefit of the model
    '''
    end_benefit= sum((model.x_water[i,j,t])\
        for (i, j) in model.arcs if j in list(model.ending)\
            for t in model.time_dim)
    

    return end_benefit


def calculate_water_stability(model):
    """
    This function returns the sum of the slack_positive and slack_negative variables for each arcs involved in water mix stability for each period as well as the sum of the binary variables for each period.

    The goal of the water mix stability is to keep the same amount of water from one period to another on a subset of ARCS linked to mixer_nodes, tagged with WaterMixStability column in config file.
    The reason to get the same amount of water on those arcs is to keep the same proportion of BRACKISH and PRODUCED water to supply demand. This is a requirement from the business as they have to change the physical setup as soon as the proportions change.
    This makes the trick as long as the demand remains constant. If the demand changes, the model will change the amounts of water to be able to supply the demand (main objective) and the proportions might change as well.
    The objective of the model will then be to minimize the difference of the amounts of water between each period on those arcs.
    On top of this, the model will try to use as few arcs as possible to supply the demand (100% PRODUCED or 100% BRACKISH) as it reduces cost as well. This is done through the BINARY variables.
    There will be a small trade-off between keeping the same amount of water and using less arcs to fulfill the demand.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    double
        Sum of the slacks variables and binary variables
    """
    sum_slacks = sum((model.slack_positive_watermix[i,j,t]) + (model.slack_negative_watermix[i,j,t]) + (model.x_active_arc_watermix[i,j,t])\
        for (i, j) in model.arcs_water_stability\
            for t in model.time_dim)

    return sum_slacks

def calculate_water_stability_low_priority(model):
    """
    This function returns the sum of the slack_positive and slack_negative variables for each arcs involved in water mix stability for each period as well as the sum of the binary variables for each period.

    The goal of the water mix stability is to keep the same amount of water from one period to another on a subset of ARCS linked to mixer_nodes, tagged with WaterMixStability column in config file.
    The reason to get the same amount of water on those arcs is to keep the same proportion of BRACKISH and PRODUCED water to supply demand. This is a requirement from the business as they have to change the physical setup as soon as the proportions change.
    This makes the trick as long as the demand remains constant. If the demand changes, the model will change the amounts of water to be able to supply the demand (main objective) and the proportions might change as well.
    The objective of the model will then be to minimize the difference of the amounts of water between each period on those arcs.
    On top of this, the model will try to use as few arcs as possible to supply the demand (100% PRODUCED or 100% BRACKISH) as it reduces cost as well. This is done through the BINARY variables.
    There will be a small trade-off between keeping the same amount of water and using less arcs to fulfill the demand.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    double
        Sum of the slacks variables and binary variables
    """
    sum_slacks = sum((model.slack_positive_watermix[i,j,t]) + (model.slack_negative_watermix[i,j,t]) + (model.x_active_arc_watermix[i,j,t])\
        for (i, j) in model.arcs_water_stability_low_priority\
            for t in model.time_dim)

    return sum_slacks

def calculate_pond_stability(model):
    """
    This function returns the sum of the slack_positive and slack_negative variables for each arcs involved in pond stability for each period as well as the sum of the binary variables for each period.

    The goal of the pond stability is to keep ONE SINGLE source pond to supply water to the demand throughout the whole period.
    For instance, if a job runs over 10 days. You start using POND 1 on day 1, the goal is to keep using water from POND 1 until day 10. If POND 1 runs out of water, interpond transfers from other ponds to POND 1 will have to happen in order to keep using the same pond until the end of the demand job.
    This will be applied to a subset of ARCS linked to mixer_nodes, tagged with PondStability column in config file.
    The objective of the model will then be to minimize the difference of the binary variables each period on those arcs.
    On top of this, the model will try to use as few arcs (so as few ponds) as possible to supply the demand as it reduces cost as well. This is done through the BINARY variables.
    There will be a small trade-off between keeping the same amount of water and using less arcs to fulfill the demand.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    double
        Sum of the slacks variables and binary variables
    """
    sum_slacks_stability = sum((model.slack_positive_pond[i,j,t]) + (model.slack_negative_pond[i,j,t]) + (model.x_active_arc_pond[i,j,t])\
        for (i, j) in model.arcs_pond_stability\
            for t in model.time_dim)
    
    return sum_slacks_stability

def set_objective_function(model, parameters):
    """Sets the model's objective function.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    parameters : dictionary(string, string)
        It has stored all the not-model's parameters.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.has_initial_solution = False
    if parameters["object_funct"] == "downstream_minimize_costs":
         model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                                (calculate_delta_water_nominal, pe.minimize),
                                                                (calculate_cost, pe.minimize),
                                                                (calculate_recirculation, pe.maximize)])
    elif parameters["object_funct"] == "downstream_maximize_recirculation":
         model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                               (calculate_delta_water_nominal, pe.minimize),
                                                                (calculate_recirculation, pe.maximize),
                                                                (calculate_cost, pe.minimize)])
    elif parameters["object_funct"] == "upstream_minimize_electrical_consumption":
        model = hierarchical_optimization(model, parameters, [(calculate_end_benefit, pe.maximize),
                                                            (calculate_energy_cost, pe.minimize),
                                                            (calculate_cost, pe.minimize)])
    
    #PERMIAN
    elif parameters["object_funct"] == "upstream_supply_demand_cost":
        model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                            (calculate_recirculation, pe.maximize),
                                                            (calculate_cost, pe.minimize)])
    
    elif parameters["object_funct"] == "upstream_supply_demand_cost_water_mix_stabilized":
        model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                            (calculate_recirculation, pe.maximize),
                                                            (calculate_water_stability, pe.minimize),
                                                            (calculate_cost, pe.minimize),
                                                            ])
        
    elif parameters["object_funct"] == "upstream_supply_demand_cost_water_mix_stabilized_inverted":
        model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                            (calculate_water_stability, pe.minimize),
                                                            (calculate_recirculation, pe.maximize),
                                                            (calculate_cost, pe.minimize),
                                                            ])

    elif parameters["object_funct"] == "upstream_supply_demand_cost_fully_stabilized":
        model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                            (calculate_recirculation, pe.maximize),
                                                            (calculate_water_stability, pe.minimize),
                                                            (calculate_pond_stability, pe.minimize),
                                                            (calculate_cost, pe.minimize),
                                                            (calculate_water_stability_low_priority, pe.minimize),
                                                            ])
        
    elif parameters["object_funct"] == "upstream_supply_demand_cost_fully_stabilized_inverted":
        model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                            (calculate_water_stability, pe.minimize),
                                                            (calculate_recirculation, pe.maximize),
                                                            (calculate_pond_stability, pe.minimize),
                                                            (calculate_cost, pe.minimize),
                                                            (calculate_water_stability_low_priority, pe.minimize),
                                                            ])

    # This elif does the same function as upstream_supply_demand_cost. It was supposed to be another function than calculate_supply_demand_flow but because of an issue of the UX team, we put that one (hot_fix)
    elif parameters["object_funct"] == "upstream_maximize_reuse" or parameters["object_funct"] == "upstream_minimize_costs":
        model = hierarchical_optimization(model, parameters, [(calculate_supply_demand_flow, pe.maximize),
                                                            (calculate_cost, pe.minimize)])
    else:
        raise ValueError(f"Objective function '{parameters['object_funct']}' is not a valid optimization function for treatment model")

    return model


def hierarchical_optimization(model, parameters, objective_functions):
    objective_function_number = 1
    for obj_f, sense in objective_functions[:-1]:
        model.obj_function = pe.Objective(sense=sense, rule=obj_f)
        print("      Solving the objective function number " + str(objective_function_number))
        solver, result = optimize(model, parameters)
        print(f"        Solver status: {result.solver.status}")
        print(f"        Solver termination condition: {result.solver.termination_condition}")
        print(f"Solution count: {len(model.solutions)}")
        if ((result.solver.status==pe.SolverStatus.ok) and (result.solver.termination_condition==pe.TerminationCondition.optimal))\
            or ((result.solver.status==pe.SolverStatus.aborted) and (result.solver.termination_condition==pe.TerminationCondition.maxTimeLimit) and (len(model.solutions)>0)): #if the optimization is aborted because of the timelimit set, we still keep the last result obtained by Gurobi, if any
            percentage = parameters["percentage_hierarchical_optimization"]
            bound = pe.value(obj_f(model))
            print("        Optimal value: " + str(bound))
            model.has_initial_solution = True
            if sense==pe.minimize:
                constraint = pe.Constraint(rule = lambda m: obj_f(m)<= max(bound*percentage, bound*(2-percentage)))
                print("        New constraint: " + obj_f.__name__ + " " + str(sense) + ": should be less than or equal to " + str(max(bound*percentage, bound*(2-percentage))))
            if sense==pe.maximize:
                constraint = pe.Constraint(rule = lambda m: obj_f(m)>= min(bound*percentage, bound*(2-percentage)))
                print("        New constraint: " + obj_f.__name__ + " " + str(sense) + ": should be greater than or equal to " + str(min(bound*percentage, bound*(2-percentage))))
           
            setattr(model, "lower_bound_constraint_" + str(objective_function_number), constraint)
        else:
            print("         An error ocurred while solving the objective function number " + str(objective_function_number))
            break
        objective_function_number += 1
   
    print("Solving the LAST objective function!")
    last_obj_f, sense = objective_functions[-1]
    model.obj_function = pe.Objective(sense = sense, rule = last_obj_f)
   
    return model

def set_constraints(model):
    """Sets the model's constraints:
    - Node's - Arc's Capacity 
    - Node's Electrical Cost 
    - Water/Oil/Contaminant Flow Balance 
    - Storing Flow Proportion 
    - Oil Splitter Fixed Arcs 
    - Oil Treatment Fixed Arcs
    - Water Mix Stability
    - Pond Stability
    - 2 constraints to link binary variables to continuous arc variables

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """

    model = constraints.add_nodes_capacity(model)
    model = constraints.add_arcs_capacity(model)

    model = constraints.add_elect_cost(model)

    model = constraints.add_water_flow_balance(model)
    model = constraints.add_oil_flow_balance(model)
    model = constraints.add_contaminant_flow_balance(model)
    

    model = constraints.add_storing_water_oil_proportion(model)

    model = constraints.add_water_stability(model)
    model = constraints.add_pond_stability(model)
    model = constraints.add_active_arcs_zero_watermix(model) #constraint to force binary to 0 if not active arc
    model = constraints.add_active_arcs_positive_watermix(model) #constraint to force binary to 1 if active arc
    model = constraints.add_active_arcs_zero_pond(model) #constraint to force binary to 0 if not active arc
    model = constraints.add_active_arcs_positive_pond(model) #constraint to force binary to 1 if active arc

    model = constraints.add_fixed_splitter_values(model)
    model = constraints.add_fixed_treatment_values(model)
    model = constraints.add_pond_evaporation(model)

    model = constraints.add_initial_nodes_flow_balance(model)
    model = constraints.add_initial_ending_nodes_spill(model)
    model = constraints.add_demand_ending_nodes(model)

    model = constraints.add_active_pumps_max(model)    
    model = constraints.add_active_pumps_min(model)
    model = constraints.add_positive_energy(model)

    model = constraints.add_linear_abs_nominal_error (model)

    model = constraints.add_active_ponds_max(model)    
    model = constraints.add_active_ponds_min(model)
    return model


def optimize(model, parameters):
    """Optimizates the model with Gurobi Solver.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    parameters : dictionary(string, string)
        It has stored all the not-model's parameters.

    Returns
    -------
    Pyomo SolverFactory('gurobi')
        The factory where the solver solved the problem.
    Pyomo Results Object
        The optimization results (it has the model termination conditions).
    """
    solver = pe.SolverFactory('gurobi')

    #The string that we use in the options is dependent on the solver used. For instance, if Gurobi does not have a NonConvex option, Pyomo will not say anything, but the solver will fail.
    solver.options['NonConvex'] = 2
    solver.options['TimeLimit'] = parameters["json_file"]["gurobi_time_limit"] #in seconds
    solver.options['CSAppName'] = parameters['json_file']['run_name'] #allow Gurobi Cluster Manager to retrieve the run name

    result = solver.solve(model, 
                          tee=False, #print the output of the solver in the terminal, which can be also found in the log of Gurobi Cluster Manager
                          logfile=parameters['solver_log'], report_timing=True, warmstart = model.has_initial_solution)
 
    return solver, result

def make_model(processed_data, useful_sets, parameters,attributes_with_time):
    """Generates and optimizes the optimization model.

    Parameters
    ----------
    processed_data : ProcessedData
        It has all the model's processed data.
    useful_sets : UsefulSets
        It has all the model's sets. 
    parameters : dictionary(string, string)
        It has stored all the not-model's parameters.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    Pyomo SolverFactory('gurobi')
        The factory where the solver solved the problem.
    Pyomo Results Object
        The optimization results (it has the model's termination conditions).
    """
    print('        ['+str(dt.datetime.now())+'] Creating ConcreteModel...')
    model = pe.ConcreteModel("Dummy_Ocelote")
    print('        ['+str(dt.datetime.now())+'] Creating sets...')
    model = set_sets(model, useful_sets)
    print('        ['+str(dt.datetime.now())+'] Creating parameters...')
    model = set_parameters(model, processed_data, useful_sets, attributes_with_time)
    print('        ['+str(dt.datetime.now())+'] Creating Variables...')
    model = set_variables(model)
    print('        ['+str(dt.datetime.now())+'] Creating Constraints...')
    model = set_constraints(model)
    print('        ['+str(dt.datetime.now())+'] Creating Objectives...')
    model = set_objective_function(model, parameters)
   
    solver, result = optimize(model, parameters)

    return model, solver, result