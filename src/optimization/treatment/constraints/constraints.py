# -*- coding: utf-8 -*-
"""
constraints.py
====================================
This script collects all treatment model constraints

@author:
     - c.maldonado
     - j.rodriguez.villegas
     - ivo.pajor
     - yeison.diaz
     - g.munera.gonzalez
"""

import pyomo.environ as pe
import itertools

#region arcs capacity
def c_2_arcs_capacity(model,t,i, j):
    """Generates the capacity constraint expression for the arc (i,j) in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension    
    i : string
        The arc's initial node.
    j : string
        The arc's ending node.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    ########### c_2_Capacity ############
    usable_percentage = model.usable_percentage[i, j, t]

    max_flow = model.max_flow[i, j] * usable_percentage
    min_flow = model.min_flow[i, j] * usable_percentage

    if (i,j) in model.oil_arcs:
        flow = model.x_water[i,j,t] + model.x_oil[i,j,t]
    else:
        flow = model.x_water[i,j,t]
        
    ########### c_2_1_Capacity ############
    ########### c_2_3_Capacity ############
    return (min_flow, flow , max_flow)


def add_arcs_capacity(model):
    """Sets the capacity constraint for every arc in the model in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_2_capacity_arc = pe.Constraint(model.time_dim, model.arcs, rule = c_2_arcs_capacity)

    return model
#endregion


#region nodes capacity
def c_2_2_node_capacity(model,t,i):
    """Generates the capacity constraint expression for the node i in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    ########### c_2_2_Capacity ############
    ########### c_2_4_Capacity ############

    if i in model.oil_nodes:
        content =(model.y_water[i,t] + model.y_oil[i,t])
    else:
        content = model.y_water[i,t]
    return (model.min_capacity[i], content, model.max_capacity[i])


def add_nodes_capacity(model):
    """Sets the capacity constraint for every node in the model for time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_2_2_capacity_node = pe.Constraint(model.time_dim,model.nodes, rule = c_2_2_node_capacity)

    return model
#endregion


#region electrical cost
def c_0_elec_cost(model,t, i):
    """Generates the electrial cost constraint expression for the node i for time t.
    It has two differents expressions, ones for the linnearized and the other ones 
    with the previous expression we were managing

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    bpd_psi_to_kwh=0.00022837058567207023
    
    ########### c_0_1_Electrical cost ############

    if i in model.pumps_linear_regression:
        fluid_in = sum(model.x_water[k, i,t] for k in model.entry[i])
        return model.y_elec_amount[i,t]\
            >= ((model.pumps_energy_model_pressure_coef[i]\
                *(model.pressure_out[i]-model.pressure_in[i])\
                    + model.pumps_energy_model_flow_rate_coef[i]\
                        *fluid_in + model.pumps_energy_model_intercept_coef[i])\
                            *model.watt_to_kwh)

    elif i in model.pumps_fixed_efficiency:
    ########### c_0_2_Electrical cost ############   
        if i in model.oil_nodes:
            fluid_in = sum(model.x_water[k, i,t] + model.x_oil [k, i,t] for k in model.entry[i] if (k,i) in model.oil_arcs)
        else:
            fluid_in = sum(model.x_water[k, i,t] for k in model.entry[i])
        
        fluid_in =  bpd_psi_to_kwh*fluid_in

        return model.y_elec_amount[i,t] >= (model.pressure_out[i]-model.pressure_in[i]) / model.efficiency[i] * fluid_in


def add_elect_cost(model):
    """Set the electrical cost binding constraint for every node in the model for time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_0_elec_cost = pe.Constraint(model.time_dim,model.pumps, rule = c_0_elec_cost)

    return model
#endregion


#region water flow balance
def c_1_1_water_flow_balance(model,t,i):
    """Generates the water flow balance constraint expression for the node i in time t.

        Parameters
        ----------
        model : Pyomo ConcreteModel
            The optimization model.
        t: int
            Time dimension
        i : string
            The node.
        
        Returns
        -------
        Constraint Expression
            Relational expression for the constraint.
        """
    ########### c_1_Flow Balancing ############
    water_in  = sum([model.x_water[j, i,t] for j in model.entry[i]])
    water_out = sum([model.x_water[i, j,t] for j in model.exit[i]])      
    water_stored =  model.y_water[i,t]
    #Consolidate all the input flows of every time t

    if i in list(model.initial):
        return pe.Constraint.Skip
    
    elif t == model.time_dim.first():
        ########### c_1_1_2_Flow Balancing ############
        if i in list(model.tanks.union(model.ponds)):
            return water_in - water_out == water_stored - model.initial_content[i]
        else:
            return water_in - water_out == water_stored
    else:
        ########### c_1_1_1_Flow Balancing ############
        return water_in - water_out == water_stored - model.y_water[i,t-1]



def c_1_2_1_water_flow_balance(model,i):
    """
    Generates the water flow balance for the initial nodes by ensuring a global,
    across time, balance. This balance can be summarized as following:
    Sum(Water entering the facility) + InitialContentLevel = Sum(Exiting the facility) + LastContentLevel

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    i : string
        The node.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.

    """
    total_in_every_time=sum([model.x_water[i,j,t] for i in model.initial\
        for t in model.time_dim  for j in model.exit[i]])
    #Consolidate all the output flows of every time t    
    total_out_every_time=sum([model.x_water[i,j,t]  for j in model.ending\
        for t in model.time_dim for i in model.entry[j]])
    #Consolidate all the storage water of the last t without starting and ending nodes   
    total_storage_last_time=sum([model.y_water[i,model.time_dim.last()]\
        for i in model.nodes if i not in (list(model.ending)+list(model.initial))])
    #consolidate initial tanks content
    total_initial_content= sum( [model.initial_content[i] for i in model.tanks.union(model.ponds)])
    
         ########### c_1_2_1_Flow Balancing ############
    return total_in_every_time + total_initial_content == total_out_every_time + total_storage_last_time



def add_water_flow_balance(model):
    """Sets the water flow balance constraint for every node in the model in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_1_1_water_flow_balance = pe.Constraint(model.time_dim,
                                                   model.nodes, 
                                                   rule = c_1_1_water_flow_balance)

    model.c_1_2_1_water_flow_balance = pe.Constraint(model.initial, 
                                                   rule = c_1_2_1_water_flow_balance)

    return model



#endregion


#region oil flow balance
def c_1_3_oil_flow_balance(model,t,i):
    """Generates the oil flow balance constraint expression for the node i in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    oil_in  = sum([model.x_oil[j, i,t] for j in model.entry[i] if j in model.oil_nodes])
    oil_out = sum([model.x_oil[i, j,t] for j in model.exit[i] if j in model.oil_nodes])    
    #Consolidate all the input flows of every time t
    total_in_every_time=sum([model.x_oil[i,j,t] for i in model.initial\
         for t in model.time_dim for j in model.exit[i] ])
    #Consolidate all the output flows of every time t    
    total_out_every_time=sum([model.x_oil[i,j,t]\
        for j in model.ending for t in model.time_dim for i in model.entry[j]])
    #Consolidate all the storage oil of the last t without starting and ending nodes   
    total_storage_last_time=sum([model.y_oil[i,model.time_dim.last()]\
        for i in model.nodes if i not in (list(model.ending)+list(model.initial))])   
    
    if i in list(model.initial):
        ########### c_1_5_1_Flow Balancing ############
        return total_in_every_time == total_out_every_time + total_storage_last_time 
        
    elif t == model.time_dim.first():
        ########### c_1_3_2_Flow Balancing ############
        return oil_in - oil_out == model.y_oil[i,t]
    else:
        ########### c_1_3_1_Flow Balancing ############
        return oil_in - oil_out == model.y_oil[i,t]-model.y_oil[i,t-1]


def add_oil_flow_balance(model):
    """Sets the oil flow balance constraint for every node in the model for time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_1_3_oil_flow_balance = pe.Constraint(model.time_dim,model.oil_nodes, rule=c_1_3_oil_flow_balance)

    return model
#endregion

#region water mix stability
def c_3_1_water_stability(model,i,j, t):
    """ Generates the water mix stability for every (i,j) arc at time t.
    Create the relationship between the difference of the amount of water between 2 periods and the slack variables

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i,j : string
        The arc.
    
    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    ########### c_3_1_water_stability ############
    if t == model.time_dim.first():
        return pe.Constraint.Skip   #We cannot compare the flow of water of the first period with the previous period
    else:
        return  model.x_water[i,j,t] - model.x_water[i,j,t-1] == model.slack_positive_watermix[i,j,t] - model.slack_negative_watermix[i,j,t]

def add_water_stability(model):
    """Sets the water mix stability constraint for every decision variables on the amount of water for water mix stability arcs at time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_3_1_water_stability = pe.Constraint(model.arcs_water_stability.union(model.arcs_water_stability_low_priority), model.time_dim, rule = c_3_1_water_stability)

    return model
    
#endregion

#region pond stability
def c_3_2_pond_stability(model,i,j, t):
    """Generates the pond stability for every (i,j) arc at time t.
    Create the relationship between the difference of the binary variables between 2 periods and the slack variables

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i,j : string
        The arc.
    
    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    ########### c_3_2_water_stability ############
    if t == model.time_dim.first():
        return pe.Constraint.Skip   #We cannot compare the flow of water of the first period with the previous period
    else:
        return  model.x_active_arc_pond[i,j,t] - model.x_active_arc_pond[i,j,t-1] == model.slack_positive_pond[i,j,t] - model.slack_negative_pond[i,j,t]

def add_pond_stability(model):
    """Sets the pond stability constraint for every binary variable for pond stability arcs at time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_3_2_pond_stability = pe.Constraint(model.arcs_pond_stability, model.time_dim, rule = c_3_2_pond_stability)

    return model
    
#endregion



#region contaminant flow balance
def c_7_2_balance_contaminant_intial_node(model, t, i,contaminant):
    """
    A inital node is were the system starts, were some contaminants are
    added and the input of those contaminants needs to be the same as the 
    output of the node

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    i : String
        The starting nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### c_7_Starting Nodes ############
    for j in model.exit[i]:
        return model.x_contaminant[i,j,contaminant,t] == model.contaminant_in[i,contaminant,t]    
    
def c_7_1_balance_contaminant_process_node(model, t, j,contaminant):
    """
    A process node adds some contaminant to a node in ppm (contaminant_addition_qty)
    to the existing contaminant level of the water that is brought to the 
    process node

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The process nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### c_7_1_Process Nodes ############
    for i,k in itertools.product(model.entry[j], model.exit[j]):
        return model.x_contaminant[j,k,contaminant,t] * model.x_water[j,k,t]\
                == model.x_contaminant[i,j,contaminant,t] * model.x_water[i,j,t]\
                + model.contaminant_addition_ppm[j,contaminant]

def c_8_1_balance_contaminant_treatment_node(model, t, j,contaminant):
    """
    The treatment nodes removes a specific contaminant ratio (removal_rate) for
    a specific contaminant (or multiple). The removal_ratio is expressed in 
    percentage of the current contaminant level (i.e. it reduces the contaminant
    level by 95%)

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The treatment nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
        
    ########### c_8_1_Process Nodes ############
    for i,k in itertools.product(model.entry[j], model.exit[j]):
        return model.x_contaminant[j,k,contaminant,t]\
            == model.x_contaminant[i,j,contaminant,t] * (1 - model.contaminant_removal_rate[j,contaminant]) 

def c_5_1_balance_contaminant_split_node(model, t, j,contaminant):
    """
    A splitter that is not conected to a  loss tank maintain the contaminant level 
    from its input to all its outputs.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The split nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### c_5_1_Splitter Nodes Without Loss Tanks ############
    for i,k in itertools.product(model.entry[j], model.exit[j]):
        return model.x_contaminant[j,k,contaminant,t] == model.x_contaminant[i,j,contaminant,t]  

def c_5_1_2_balance_contaminant_split_node_with_loss_tanks(model, t, j, contaminant):
    """
    A splitter that is connected with a loss tank has to recalculate the concentration.
    As loss tanks refer to evaporation, they don't get contaminants.
    We need to recalculate the concentration so that the contaminants go into the other way.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The split nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### 5.1. Splitter Nodes With Tank Nodes ############
    bar_to_lts = 119.24047119599997
    contaminants_in  = sum([model.x_contaminant[i,j,contaminant,t] * model.x_water[i,j,t] * bar_to_lts for i in model.entry[j]])
    contaminants_out = sum([model.x_contaminant[j,k,contaminant,t] * model.x_water[j,k,t] * bar_to_lts for k in model.exit[j] if k not in model.loss_tanks])
    return contaminants_out == contaminants_in  

def c_6_1_balance_contaminant_mixer_node(model, t, j,contaminant):
    """
    See equation (6.1) - Mixer Nodes in the mathematical model 
    A mixer aggregate the contaminant level of all inputs into a single output.
    This requirement the proportional mixing of all input quantities with their 
    contaminant level

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The mixer nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### c_6_1_Mixer Nodes ############
    bar_to_lts = 119.24047119599997
    contaminants_in  = sum([model.x_contaminant[i,j, contaminant,t] * model.x_water[i,j,t] * bar_to_lts for i in model.entry[j]])
    contaminants_out = sum([model.x_contaminant[j,k, contaminant,t] * model.x_water[j,k,t] * bar_to_lts for k in model.exit[j]])
    return contaminants_out == contaminants_in
    
def c_6_2_balance_contaminant_boiler_node(model, t, j,contaminant):
    """
    See equation (6.1.2) - Bolier Nodes in the mathematical model 
    A boiler aggregate the contaminant level of all inputs into a single output.
    This requirement the proportional mixing of all input quantities with their 
    contaminant level

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The boiler nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### c_6_2_boiler Nodes ############
    bar_to_lts = 119.24047119599997
    contaminants_in  = sum([model.x_contaminant[i,j, contaminant,t] * model.x_water[i,j,t] * bar_to_lts for i in model.entry[j]])
    contaminants_out = sum([model.x_contaminant[j,k, contaminant,t] * model.x_water[j,k,t] * bar_to_lts for k in model.exit[j]])
    return contaminants_out == contaminants_in

def c_6_3_balance_contaminant_cooling_tower_node(model, t, j,contaminant):
    """
    See equation (6.1.3) - cooling tower Nodes in the mathematical model 
    A cooling towers aggregate the contaminant level of all inputs into a single output.
    This requirement the proportional mixing of all input quantities with their 
    contaminant level

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The cooling towers nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### c_6_3_cooling towers Nodes ############
    bar_to_lts = 119.24047119599997
    contaminants_in  = sum([model.x_contaminant[i,j, contaminant,t] * model.x_water[i,j,t] * bar_to_lts for i in model.entry[j]])
    contaminants_out = sum([model.x_contaminant[j,k, contaminant,t] * model.x_water[j,k,t] * bar_to_lts for k in model.exit[j]])
    return contaminants_out == contaminants_in

def c_10_1_1_balance_contaminant_tank_node(model, t, j,contaminant):
    """
    See equation (10.1.1) and (10.1.2) in the mathematical model 
    The concentration of contaminant c in a tank j depends on the current
    content's concentration of the tank, as well as the concentration of the
    inflow and outflow.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The tank nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    for i,k in itertools.product(model.entry[j], model.exit[j]):
        ########### c_10_1_2_Tank Nodes ############
        if  t == model.time_dim.first():
            return model.initial_content[j]* model.initial_content_contaminants_tanks[j,contaminant] \
                + model.y_contaminant[j,contaminant,t]* model.y_water[j,t] \
                == model.x_contaminant[i,j,contaminant,t] * model.x_water[i,j,t] \
                - model.x_contaminant[j,k,contaminant,t] * model.x_water[j,k,t]
        ########### c_10_1_1_Tank Nodes ############
        else:
            return model.y_contaminant[j,contaminant,t]* model.y_water[j,t] \
                == model.x_contaminant[i,j,contaminant,t] * model.x_water[i,j,t]\
            	- model.x_contaminant[j,k,contaminant,t] * model.x_water[j,k,t] \
                + model.y_contaminant[j,contaminant,t-1]* model.y_water[j,t-1]
    
def c_10_2_balance_contaminant_tank_node (model, t, j,contaminant):
    """
    See equation (10.2) in the mathematical model
    ASSUMPTION: We consider the output flow concentration to be equal to the 
    tank concentration at the time t-1

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The tank nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### c_10_2_Tank Nodes ############
    if  t > model.time_dim.first():
        for k in model.exit[j]:
            return model.x_contaminant[j,k,contaminant,t] == model.y_contaminant[j,contaminant,t-1]
        
    
    else:
        ########### c_5_2_Oil Splitter Nodes ############
        ########### c_5_3_Oil Splitter Nodes ############
        for i,k in itertools.product(model.entry[j], model.exit[j]):
            return model.x_contaminant[j,k,contaminant,t] == model.x_contaminant[i,j,contaminant,t]
    
def c_12_1_2_balance_contaminant_loss_tank_node(model, t, j, contaminant):
    """
    The concentration of contaminant c in a loss tank should be forced to 0

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The loss tank nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    return model.y_contaminant[j,contaminant,t] == 0

def c_12_1_1_balance_contaminant_before_loss_tank_node(model, t, j, contaminant):
    """ 
    The concentration of contaminant c in an arc before a loss tank should be forced to 0.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The loss tank nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    for i in model.entry[j]:
        return model.x_contaminant[i,j,contaminant,t] == 0

def c_14_balance_contaminant_pond_node(model, t, j, contaminant):
    """
    A pond node is like a tank but it losses water due to evaporation.
    Contaminants must be recalculated for the non evap arc (the one that is not going to the loss tank).

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The pond node.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    bar_to_lts = 119.24047119599997
    contaminants_in  = sum([model.x_contaminant[i,j,contaminant,t] * model.x_water[i,j,t] * bar_to_lts for i in model.entry[j]])
    contaminants_out = sum([model.x_contaminant[j,k,contaminant,t] * model.x_water[j,k,t] * bar_to_lts for k in model.exit[j] if k not in model.loss_tanks])

    contaminants_stored_now = model.y_contaminant[j,contaminant,t]* model.y_water[j,t] * bar_to_lts
    
    contaminants_inital_content= model.initial_content[j]* model.initial_content_contaminants_ponds[j,contaminant] 
    
    ########### c_14_1_1 Pond Nodes ############
    if  t == model.time_dim.first():
        return contaminants_stored_now+contaminants_inital_content ==  contaminants_in - contaminants_out

    ########### c_14_1_2 Pond Nodes ############
    else:
        contaminant_stored_before = model.y_contaminant[j,contaminant,t-1] * model.y_water[j,t-1] * bar_to_lts
        
        return contaminants_stored_now - contaminant_stored_before == contaminants_in - contaminants_out

def c_14_2_1_balance_contaminant_pond_node_2(model, t, j,contaminant):
    """
    ASSUMPTION: We consider the output flow concentration to be equal to the 
    tank concentration at the time t-1

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The pond node.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    ########### 10.1.2 Tank Nodes ############
    if  t > model.time_dim.first():
        for k in model.exit[j]:
            if k not in model.loss_tanks:
                return model.x_contaminant[j,k,contaminant,t] == model.y_contaminant[j,contaminant,t-1]

    else:
        return pe.Constraint.Skip


def c_10_3_balance_contaminant_all_other_nodes(model, t, j,contaminant):
    """
    For nodes of the system that are not process, treatment, spli, mix,
    cooling towers, boilers, tanks, initial or ending nodes the input 
    of those contaminants needs to be the same as the 
    output of the node

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension.
    j : String
        The nodes of the system.
    contaminant : String
        Aditional substance that can be found within the principal fluid.

    Returns
    -------
    Constraint Expression
        Balance equation for contaminants for specific type of nodes.

    """
    if j in list(model.process)\
        +list(model.treatment)\
        +list(model.split)\
        +list(model.mix)\
        +list(model.tanks)\
        +list(model.initial)\
        +list(model.ending)\
        +list(model.cooling_towers)\
        +list(model.boiler)\
        +list(model.loss_tanks)\
        +list(model.ponds):
        return pe.Constraint.Skip
    else:
        for i,k in itertools.product(model.entry[j], model.exit[j]):
            return model.x_contaminant[j,k,contaminant,t] == model.x_contaminant[i,j,contaminant,t]

def add_contaminant_flow_balance (model):
    """Sets the contaminant flow balance constraint for every arc in the model for time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    if len(model.process)!=0\
        or sum(model.contaminant_in.extract_values().values())!=0\
        or (sum(model.initial_content_contaminants_ponds.extract_values().values())\
            + sum(model.initial_content_contaminants_tanks.extract_values().values()))!=0:  
        
        model.c_7_2_balance_contaminant_intial_node = pe.Constraint(model.time_dim, 
                                                        model.initial,model.contaminants, 
                                                        rule = c_7_2_balance_contaminant_intial_node)
        model.c_7_1_balance_contaminant_process_node = pe.Constraint(model.time_dim, 
                                                            model.process,model.contaminants,
                                                            rule=c_7_1_balance_contaminant_process_node)
        model.c_8_1_balance_contaminant_treatment_node = pe.Constraint(model.time_dim, 
                                                            model.treatment,model.contaminants, 
                                                            rule=c_8_1_balance_contaminant_treatment_node)
        model.c_5_1_balance_contaminant_split_node  = pe.Constraint(model.time_dim, 
                                                        model.splitter_without_loss_tanks,
                                                        model.contaminants,
                                                        rule=c_5_1_balance_contaminant_split_node)
        model.c_5_1_2_balance_contaminant_split_node_with_loss_tanks = pe.Constraint(model.time_dim, 
                                                        model.splitter_with_loss_tanks,
                                                        model.contaminants,
                                                        rule=c_5_1_2_balance_contaminant_split_node_with_loss_tanks)
        model.c_6_1_balance_contaminant_mixer_node = pe.Constraint(model.time_dim, 
                                                        model.mix,model.contaminants,
                                                        rule=c_6_1_balance_contaminant_mixer_node)
        model.c_6_1_2_balance_contaminant_boiler_node = pe.Constraint(model.time_dim, 
                                                        model.boiler,model.contaminants,
                                                        rule=c_6_2_balance_contaminant_boiler_node)
        model.c_6_1_3_balance_contaminant_cooling_tower_node = pe.Constraint(model.time_dim, 
                                                        model.cooling_towers,model.contaminants,
                                                        rule=c_6_3_balance_contaminant_cooling_tower_node)
        model.c_10_1_1_balance_contaminant_tank_node = pe.Constraint(model.time_dim, 
                                                        model.tanks,model.contaminants, 
                                                        rule=c_10_1_1_balance_contaminant_tank_node)
        model.c_10_2_balance_contaminant_tank_node = pe.Constraint(model.time_dim, 
                                                        model.tanks,model.contaminants,
                                                        rule=c_10_2_balance_contaminant_tank_node)
        model.c_12_1_2_balance_contaminant_loss_tank_node = pe.Constraint(model.time_dim, 
                                                        model.loss_tanks,model.contaminants, 
                                                        rule=c_12_1_2_balance_contaminant_loss_tank_node)
        model.c_12_1_1_balance_contaminant_before_loss_tank_node = pe.Constraint(model.time_dim, 
                                                        model.loss_tanks, model.contaminants, 
                                                        rule=c_12_1_1_balance_contaminant_before_loss_tank_node)
        model.c_14_balance_contaminant_pond_node = pe.Constraint(model.time_dim, 
                                                        model.ponds, model.contaminants, 
                                                        rule=c_14_balance_contaminant_pond_node)
        model.c_14_2_1_balance_contaminant_pond_node_2 = pe.Constraint(model.time_dim, 
                                                        model.ponds, model.contaminants, 
                                                        rule=c_14_2_1_balance_contaminant_pond_node_2)
        model.c_10_3_balance_contaminant_all_other_nodes = pe.Constraint(model.time_dim, 
                                                            model.nodes,model.contaminants, 
                                                            rule=c_10_3_balance_contaminant_all_other_nodes)

    return model

#endregion


#region storing in tanks water - oil proportion
def c_1_4_storing_water_oil_proportion(model,t,j):
    """Generates the storing flow porportion constraint expression for the node i in time t.
    This constraint forces the stored fluid to respect the same proportion as the inflow.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """

    if len(model.entry[j]) == 0 and len(model.exit[j]) == 0:
        return pe.Constraint.Skip
        
    water_in = sum([model.x_water[i, j,t] for i in model.entry[j]])
    oil_in = sum([model.x_oil[i, j,t] for i in model.entry[j]])

    #Initial nodes
    if j in list(model.initial):
        water_in = model.water_in[j,t]
        oil_in = model.oil_in[j,t]
    ########### c_1_4_Flow Balancing ############
    return water_in * model.y_oil[j,t] == oil_in * model.y_water[j,t]


def add_storing_water_oil_proportion(model):
    """Sets the stored water - oil proportion constraint in every node. 
    This constraint forces the stored fluid to respect the same proportion as the inflow.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_1_4_storing_water_oil_proportion = pe.Constraint(model.time_dim,model.oil_nodes, rule=c_1_4_storing_water_oil_proportion)

    return model
#endregion


#region fixed splitter values
def c_5_2_water_fixed_splitter_values(model,t,j,k):
    """Generates the oil splitter fixed water flow constraint expression for the arc (i, j) in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    j : string
        The arc's initial node.
    k : string
        The arc's ending node.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    water_in = sum([model.x_water[i, j,t] for i in model.entry[j]])
    rate = model.fixed_percentage[j, k]
    ########### c_5_2_Splitter Nodes ############
    return model.x_water[j,k,t] == (water_in - model.y_water[j,t]) * rate


def c_5_3_oil_fixed_splitter_values(model,t,j, k):
    """Generates the oil splitter fixed oil flow constraint expression for the arc (i, j) in time t.
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension
    i : string
        The arc's initial node.
    j : string
        The arc's ending node.
        
    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    if (j, k)  not in model.oil_arcs:
        return pe.Constraint.Skip

    oil_in = sum([model.x_oil[i, j,t] for i in model.entry[j] if (i, j) in model.oil_arcs])
    rate = model.fixed_percentage[j, k]
    ########### c_5_3_Splitter Nodes ############
    return model.x_oil[j, k,t] == (oil_in - model.y_oil[j,t]) * rate

def add_fixed_splitter_values(model):
    """Sets the arcs fixed value constraints for the arcs that are after oil splitters for time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_5_2_water_fixed_spliting_values = pe.Constraint(model.time_dim,model.fixed_splitter_arcs, rule=c_5_2_water_fixed_splitter_values)
    model.c_5_3_oil_fixed_spliting_values = pe.Constraint(model.time_dim,model.fixed_splitter_arcs, rule=c_5_3_oil_fixed_splitter_values)

    return model
#endregion


#region fixed oil-treatment values
def c_9_2_oil_fixed_treatment_values(model,t, j, k):
    """Generates the oil treatment fixed water flow constraint expression for the arc (i, j) in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t : int
        Time dimension
    j : string
        The arc's initial node.
    k : string
        The arc's ending node.
        
    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """

    flow_in = sum([model.x_oil[i, j,t] for i in model.entry[j]])
    rate = model.fixed_oil_percentage[j,k]
    ########### c_9_2_Treatment Nodes ############
    return model.x_oil[j,k,t] == (flow_in - model.y_oil[j,t]) * rate
    

def c_9_1_water_fixed_treatment_values(model,t,j, k):
    """Generates the oil treatment fixed oil flow constraint expression for the arc (i, j) in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    j : string
        The arc's initial node.
    k : string
        The arc's ending node.
        
    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    water_in = sum([model.x_water[i, j,t] for i in model.entry[j]])
    rate = model.fixed_water_percentage[j, k]
    ########### c_9_1_Treatment Nodes ############
    return model.x_water[j, k,t] == (water_in - model.y_water[j,t]) * rate


def add_fixed_treatment_values(model):
    """Sets the arcs fixed value constraints for the arcs that are after oil treatment nodes for time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_9_1_water_fixed_treatment_values = pe.Constraint(model.time_dim,model.fixed_oil_treatment_arcs, rule=c_9_1_water_fixed_treatment_values)
    model.c_9_2_oil_fixed_treatment_values = pe.Constraint(model.time_dim,model.fixed_oil_treatment_arcs, rule=c_9_2_oil_fixed_treatment_values)

    return model

#endregion


#region ponds evaporation forecasted/fixed
def c_14_3_1_pond_evaporation(model, t, j):
    """Generates the water evaporation constraint for the pond j in time t .

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    j : string
        The pond node.
        
    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    evap_flow = model.forecasted_evap_rate[t] * model.pond_average_surface[j] * model.xActivePonds[j, t] * 6.28981077

    evap_water_out = sum([model.x_water[j, k, t] for k in model.exit[j] if k in model.loss_tanks])

    return evap_water_out == evap_flow


def add_pond_evaporation(model):
    """Sets the evaporation of each ponds to theirs loss tanks.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_14_3_1_pond_evaporation = pe.Constraint(model.time_dim, model.ponds, rule=c_14_3_1_pond_evaporation)
    
    return model



#endregion


#region initial nodes
def c_4_3_initial_nodes_water(model,t,i):
    """Generates the water flow balance constraint expression for the inital nodes i in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node from inital nodes set and terminal nodes set.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    water_out = sum([model.x_water[i, j,t] for j in model.exit[i]])
    if t==model.time_dim.first():
        ########### c_4_3_Flow Balancing Relationship ############
        return model.y_water[i,t] + water_out == model.water_in[i,t]
    else:
        ########### c_4_4_Flow Balancing Relationship ############
        return model.y_water[i,t] + water_out == model.water_in[i,t] + model.y_water[i,t-1]

def c_4_5_initial_nodes_oil(model,t,i):
    """Generates the oil flow balance constraint expression for the inital nodes i in time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node from inital nodes set and terminal nodes set.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    if i in model.oil_nodes:
        oil_out = sum([model.x_oil[i, j,t] for j in model.exit[i]])
        if t==model.time_dim.first():
            ########### c_4_5_Flow Balancing Relationship ############
            return model.y_oil[i,t] + oil_out == model.oil_in[i,t]
        else:
            ########### c_4_6_Flow Balancing Relationship ############
            return model.y_oil[i,t] + oil_out == model.oil_in[i,t] + model.y_oil[i,t-1]
    else:
        return pe.Constraint.Skip


def add_initial_nodes_flow_balance(model):
    """Sets the flow balance constraint for initial nodes for time t.

    Parameters
    ----------
    model : Pyomo ConcreteModel
    The optimization model.
    
    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_4_3_initial_nodes_water = pe.Constraint(model.time_dim,model.initial, rule=c_4_3_initial_nodes_water)
    model.c_4_5_initial_nodes_oil = pe.Constraint(model.time_dim,model.initial, rule=c_4_5_initial_nodes_oil)

    return model
    
def c_11_1_3_initial_ending_spill_oil(model,t,i):
    """Ensure the content oil for inital nodes in t cannot be used in t+1.
    And water in terminal nodes can  not be empty

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node from inital nodes set and terminal nodes set.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    if i in model.oil_nodes:
        if t==model.time_dim.first():
            ########### c_4_8_1_Flow Balancing Relationship ############
            ########### c_11_1_3 Flow Balancing ############
            return model.y_oil[i,t] >= 0
        else:
            ########### c_4_8_2_Flow Balancing Relationship ############
            ########### c_11_1_4 Flow Balancing ############
            return model.y_oil[i,t] >= model.y_oil[i,t-1]
    else:
        return pe.Constraint.Skip

def c_11_1_1_initial_ending_spill_water(model,t,i):
    """Ensure the content water for initial nodes in t cannot be used in t+1.
    And water in terminal nodes can  not be empty

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    i : string
        The node from inital nodes set and terminal nodes set.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    if t==model.time_dim.first():
        ########### c_4_7_1_Flow Balancing Relationship ############
        ########### c_11_1_1_Constraint in ending nodes ############
        return model.y_water[i,t] >=0
    else:
        ########### c_4_7_2_Flow Balancing Relationship ############
        ########### c_11_1_2_Constraint in ending nodes ############
        return model.y_water[i,t] >= model.y_water[i,t-1]


def add_initial_ending_nodes_spill (model):
    """Sets the constraint for initial nodes to avoid content in t can be used in t+1 .
    And water in terminal nodes can  not be empty
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_11_1_1_initial_ending_spill_water = pe.Constraint(model.time_dim,model.initial.union(model.ending), rule=c_11_1_1_initial_ending_spill_water)
    model.c_11_1_3_initial_ending_spill_oil = pe.Constraint(model.time_dim,model.initial.union(model.ending), rule= c_11_1_3_initial_ending_spill_oil)

    return model
#endregion



#region ending nodes
def c_11_2_demand_ending_nodes (model,t,j):
    """Ensure the content water for ending nodes in t is below the maximum allowed
    for each time

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    t: int
        Time dimension
    j : string
        The node from ending nodes set.

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    """
    if j in model.oil_nodes:
        oil_in  = sum([model.x_oil[i,j,t] for i in model.entry[j]])
         ########### c_11_2_2_Constraint in ending nodes ############
        return oil_in <= model.ending_demand[j,t]
    else:
        water_in  = sum([model.x_water[i,j,t] for i in model.entry[j]])
        ########### c_11_2_1_Constraint in ending nodes ############
        return water_in <= model.ending_demand[j,t]

def add_demand_ending_nodes (model):
    """Sets the constraint for ending nodes to avoid content in t be over the allowed
    capacity
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_11_2_demand_ending_nodes = pe.Constraint(model.time_dim,model.ending, rule=c_11_2_demand_ending_nodes)
    return model

#endregion

#region positive energy for pumps
       
def c_13_1_active_pumps_max(model, pump, t):
    '''Constraint that defines the variable that indicates if a pump is active (has inflow greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pump : pyomo.core.base.set.Set
        Pyomo pumps_inject set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if pump isn't active then the variable should be zero.
    '''
    water_in  = sum([model.x_water[i, pump, t] for i in model.entry[pump]]) 
    epsilon = 1e-30

    return model.xActivePump[pump, t] <= 1 + water_in - epsilon

def add_active_pumps_max (model):
    """Sets the constraint for detect the active pumps upper bound
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_13_1_active_pumps_max = pe.Constraint(model.pumps, model.time_dim, rule=c_13_1_active_pumps_max)
    return model


def c_13_2_active_pumps_min(model, pump, t):
    '''Constraint that defines the variable that indicates if a pump is active (has inflow greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pump : pyomo.core.base.set.Set
        Pyomo pumps_inject set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if the pump is active then the variable should be one.
    '''
    water_in  = sum([model.x_water[i, pump, t] for i in model.entry[pump]])  
    
    return water_in <= model.xActivePump[pump, t] * model.BigPenalty

def add_active_pumps_min (model):
    """Sets the constraint for detect the active pumps lower bound
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_13_2_active_pumps_min = pe.Constraint(model.pumps, model.time_dim, rule=c_13_2_active_pumps_min)
    return model

def c_13_3_positive_energy(model, pump, t):
        '''Constraint defined to avoid negative values from energy function

        Parameters
        ----------
        model : pyomo.core.base.PyomoModel
            Pyomo's model instance
        pump : pyomo.core.base.set.Set
            Pyomo pumps_inject set element to index contraints objects

        Returns
        -------
        value pyomo.core.base.constraint.Constraint
            Checked if the energy function value is negative
        '''
        constant = 400

        return model.y_elec_amount[pump, t]>=constant*model.xActivePump[pump, t]

def add_positive_energy (model):
    """Sets the constraint for have always positive energy
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_13_3_positive_energy = pe.Constraint(model.pumps, model.time_dim, rule=c_13_3_positive_energy)
    return model

#endregion

#region linking binary and continuous variables for WATER MIX STABILITY ARCS

def c_15_1_active_arcs_zero_watermix(model,i,j,t):
    '''Constraint that defines the variable that indicates if an arc is active (has inflow greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pump : pyomo.core.base.set.Set
        Pyomo pumps_inject set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if arc isn't active then the variable should be zero.
    '''
    epsilon = 1e-30

    return model.x_active_arc_watermix[i,j,t] <= 1 + model.x_water[i,j,t] - epsilon

def add_active_arcs_zero_watermix(model):
    """Sets the constraint to force binary variable to be 0 if not active arc: for water mix stability arcs
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_15_1_active_arcs_zero_watermix = pe.Constraint(model.arcs_water_stability.union(model.arcs_water_stability_low_priority), model.time_dim, rule=c_15_1_active_arcs_zero_watermix)
    return model

def c_15_2_active_arcs_positive_watermix(model,i,j,t):
    '''Constraint that defines the variable that indicates if an arc is active (has inflow greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pump : pyomo.core.base.set.Set
        Pyomo pumps_inject set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if the arc is active then the variable should be one.
    '''
    
    return model.x_water[i,j,t] <= model.x_active_arc_watermix[i,j,t] * model.BigPenaltyArcs

def add_active_arcs_positive_watermix(model):
    """Sets the constraint to force binary variable to be 1 if active arc: for water mix and pond stability arcs
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_15_2_active_arcs_positive_watermix = pe.Constraint(model.arcs_water_stability.union(model.arcs_water_stability_low_priority), model.time_dim, rule=c_15_2_active_arcs_positive_watermix)
    return model

#endregion

#region linking binary and continuous variables for POND STABILITY ARCS

def c_15_3_active_arcs_zero_pond(model,i,j,t):
    '''Constraint that defines the variable that indicates if an arc is active (has inflow greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pump : pyomo.core.base.set.Set
        Pyomo pumps_inject set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if arc isn't active then the variable should be zero.
    '''
    epsilon = 1e-30

    return model.x_active_arc_pond[i,j,t] <= 1 + model.x_water[i,j,t] - epsilon

def add_active_arcs_zero_pond(model):
    """Sets the constraint to force binary variable to be 0 if not active arc: for pond stability arcs
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_15_3_active_arcs_zero_pond = pe.Constraint(model.arcs_pond_stability, model.time_dim, rule=c_15_3_active_arcs_zero_pond)
    return model

def c_15_4_active_arcs_positive_pond(model,i,j,t):
    '''Constraint that defines the variable that indicates if an arc is active (has inflow greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pump : pyomo.core.base.set.Set
        Pyomo pumps_inject set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if the arc is active then the variable should be one.
    '''
    
    return model.x_water[i,j,t] <= model.x_active_arc_pond[i,j,t] * model.BigPenaltyArcs

def add_active_arcs_positive_pond(model):
    """Sets the constraint to force binary variable to be 1 if active arc: for water mix stability arcs
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_15_4_active_arcs_positive_pond = pe.Constraint(model.arcs_pond_stability, model.time_dim, rule=c_15_4_active_arcs_positive_pond)
    return model

#endregion

#region Linearizing absolute value error of nominal values 
       
def c_16_1_positive_delta_nominal (model, t, i, j):
    '''Generates the constraint used for linearize the absolute difference between the nominal value and the water flow of the arc (i, j) in time t.
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    t: int
        Time dimension
    i : string
        The arc's initial node.
    j : string
        The arc's ending node

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    '''
    water_in  = model.x_water[i, j, t]
    nominal = model.nominal_values [i, j, t]

    return model.x_water_delta[i, j, t] >= water_in - nominal

def c_16_2_negative_delta_nominal (model, t, i, j):
    '''Generates the constraint used for linearize the absolute difference between the nominal value and the water flow of the arc (i, j) in time t.
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    t: int
        Time dimension
    i : string
        The arc's initial node.
    j : string
        The arc's ending node

    Returns
    -------
    Constraint Expression
        Relational expression for the constraint.
    '''
    water_in  = model.x_water[i, j, t]
    nominal = model.nominal_values [i, j, t]

    return model.x_water_delta[i, j, t] >= nominal - water_in


def add_linear_abs_nominal_error (model):
    """Sets the constraints for linearize the absolute difference between the nominal value and the water flow of the arc (i, j) in time t.
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_16_1_positive_delta_nominal = pe.Constraint(model.time_dim, model.arcs_nominal, rule=c_16_1_positive_delta_nominal)
    model.c_16_2_negative_delta_nominal = pe.Constraint(model.time_dim, model.arcs_nominal, rule=c_16_2_negative_delta_nominal)
    return model


    
#endregion

#region ponds in use
       
def c_17_1_active_ponds_max(model, pond, t):
    '''Constraint that defines the variable that indicates if a pond is active (has water stored greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pond : pyomo.core.base.set.Set
        Pyomo ponds set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if pond isn't active then the variable should be zero.
    '''
    water_stored  = model.y_water[pond, t]
    epsilon = 1e-6

    return model.xActivePonds[pond, t] <= 1 + water_stored - epsilon

def add_active_ponds_max (model):
    """Sets the constraint for detect the active ponds upper bound
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_17_1_active_ponds_max = pe.Constraint(model.ponds, model.time_dim, rule=c_17_1_active_ponds_max)
    return model


def c_17_1_active_ponds_min(model, pond, t):
    '''Constraint that defines the variable that indicates if a pond is active (has water stored greater than 0) or not.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel
        Pyomo's model instance
    pond : pyomo.core.base.set.Set
        Pyomo ponds set element to index contraints objects

    Returns
    -------
    value pyomo.core.base.constraint.Constraint
        Check if the pump is active then the variable should be one.
    '''
    water_stored  = model.y_water[pond, t]
    
    return water_stored <= model.xActivePonds[pond, t] * model.BigPenalty

def add_active_ponds_min (model):
    """Sets the constraint for detect the active ponds lower bound
    
    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    Pyomo ConcreteModel
        The optimization model.
    """
    model.c_17_1_active_ponds_min = pe.Constraint(model.ponds, model.time_dim, rule=c_17_1_active_ponds_min)
    return model
# endregion