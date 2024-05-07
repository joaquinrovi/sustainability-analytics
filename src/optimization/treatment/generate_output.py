# -*- coding: utf-8 -*-
"""
generate_output.py
====================================
This script has the functions and methods to process and structure model results

@author:
     - c.maldonado
     - ivo.pajor
     - j.rodriguez.villegas
     - g.munera.gonzalez
     - yeison.diaz
"""

from array import array
import math, json
import pandas as pd
import pyomo.environ as pe


def generate_model_output(model, result, df_nodes, df_arcs, parameters):
    """It extracts the model's summmary. It contains the objective function model's type and termination 
    conditions.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    result : Pyomo Results Object
        The optimization results (it has the model's termination conditions).
    df_nodes : Pandas Dataframe
        It contains the nodes data (parameters and model's decision variables)
    df_arcs : Pandas Dataframe
        It contains the arcs data (parameters and model's decision variables)
    parameters : dictionary(string, string)
        It has stored all the not-model's parameters.
    Returns
    -------
    Pandas Dataframe
        It contains the objective function model's type and termination conditions.
    """
    date = list(range(1, parameters["time_periods"] + 1))
    
    df_nodes_group = df_nodes.groupby(by = 'Date')
    cost_nodes = df_nodes_group['Other_costs'].sum() + df_nodes_group['Energy_Cost'].sum()
    
    supply_demand_balance = df_nodes[df_nodes['Source'].isin(list(model.ending_max))].groupby(by = 'Date')['Water_Stored'].sum() -\
                            df_nodes[df_nodes['Source'].isin(list(model.initial_min))].groupby(by = 'Date')['Water_Stored'].sum()
    
    
    water_volume = df_nodes[df_nodes['Type'] == 'Initial'].groupby(by = 'Date')['Water_In'].sum()
    water_to_reuse = df_nodes[df_nodes['Source'].isin(list(model.reuse))].groupby(by = 'Date')['Water_In'].sum()
    water_neutrality_KPI=(water_volume-water_to_reuse)*parameters["barrel_to_liters"]/parameters["day_to_sec"]


    d = {'DATE' : date,
         'COST' : cost_nodes + df_arcs.groupby(by = 'Date')["Other_costs"].sum(),
         'SUPPLY/DEMAND BALANCE': supply_demand_balance,
         'RECIRCULATION' : df_arcs.groupby(by = 'Date')['Reuse'].sum(),
         'ENERGY_CONSUMPTION_KWH' : df_nodes_group['Energy_Consumption'].sum(),
         'CO2_TONS' : df_nodes_group['CO2_TONS'].sum(),
         'WATER_VOLUME' : water_volume,
         'WATER_TO_REUSE' : water_to_reuse,
         'WATER_NEUTRALITY': water_neutrality_KPI
         }
    
    df = pd.DataFrame(d)
    return df



def node_type(model, node):
    """Given a node i of the model, it returns the node's type. It could be: Initial, Ending, Tank, Pump, 
    Splitter, Mixer, Process, Treatment, Oil Treatment, Cooling TW, Boiler.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    node : string
        The node.

    Returns
    -------
    string
        It represents the node's type.
    """
    list_sets = [model.initial, model.ending, model.tanks, model.pumps, model.split, model.mix, \
                 model.process, model.treatment, model.oil_treatment, model.cooling_towers, model.boiler, model.loss_tanks, \
                 model.ponds]
    list_types = ["Initial", "Ending", "Tank", "Pump", "Splitter", "Mixer", \
                  "Process", "Treatment", "Oil Treatment", "Cooling TW", "Boiler", "Loss", \
                  "Ponds"]
    for i, s in enumerate(list_sets):
        if node in s:
            return list_types[i]
    return None
    
def extract_contaminants (model, in_out, contaminants_dict, df):
    """This function add the contaminants to the dataframe to complete outpus
    Parameters
    ----------    
    model : Pyomo ConcreteModel
        The optimization model.
    in_out : str
        Decide if contaminants are going "In" or "Out" of the node.
    contaminants_dict : dict
        The amount of contaminant per type of contaminant in each node per time t.        
    df : Dataframe
        It is the dataframe that is processing the outputs.
    Returns
    -------
    Pandas Dataframe
        It is the dataframe that is processing the outputs.
    """
    for i in model.contaminants:
        df[i+"_"+in_out] = df.apply(lambda row: contaminants_dict[i, row.Source, row.Date][0][0], axis = 1)
    return df

def generate_nodes_output(model, processed_data):
    """It extracts the model's nodes' summmary. It contains both parameters and model's decision variables.

    Parameters
    ----------    
    model : Pyomo ConcreteModel
        The optimization model.
    processed_data : ProcessedData
        It has all the model's processed data.
    Returns
    -------
    df_nodes : pandas.core.frame.DataFrame
        It contains the nodes' data (parameters and model's decision variables)
    dates : list
            List of dates with start node storage
    """
    #region Active Nodes
    active_nodes = list(model.nodes)
    #endregion

    #region Fluid In
    water_in, oil_in, contaminants_in, min_capacity, max_capacity, nodes, nodes_type, time_data = nodes_fluid_in(model, active_nodes)
    #endregion
        
    #region Stored Fluids
    water_stored, oil_stored = [], []
    for t in model.time_dim:
        water_stored.extend([model.y_water[node, t].value for node in active_nodes])
        oil_stored.extend([0 if node not in model.oil_nodes else model.y_oil[node, t].value\
            for node in active_nodes])

    #endregion]

    #region Fluid Out
    water_out, oil_out, contaminants_out = nodes_fluid_out(model, active_nodes)

    #endregion

    #region Nodes data extration
    d = {'Source':nodes,
        'Date': time_data,
        'Type': nodes_type,
        'Min_capacity': min_capacity,
        'Max_capacity': max_capacity,
        'Water_In':water_in,
        'Oil_In':oil_in}

    df = pd.DataFrame(d)
    
    df = extract_contaminants(model, "In", contaminants_in, df)

    df["Water_Stored"] = water_stored
    df["Oil_Stored"] = oil_stored
    df["Water_Out"] = water_out
    df["Oil_Out"] = oil_out

    df = extract_contaminants(model, "Out", contaminants_out, df)
    
    #endregion

    #region Adding parameters
    df = add_params(model, processed_data, df)
    #endregion

    #getting bottleneck on network
    df, dates = get_storage(df, processed_data)
    
    return df, dates

def nodes_fluid_in(model, active_nodes):
    """This function add parameters to the dataframe to complete outpus

    Parameters
    ----------    
    model : Pyomo ConcreteModel
        The optimization model.
    active_nodes : list
        List with model active nodes
  
    Returns
    -------
    water_in : list
        water inflow per node each time t
    oil_in : list
        oil inflow per node each time t
    contaminants_in : dict
        The amount of contaminant per type of contaminant in each node per time t. 
        Every key is a contaminant type, a node and in time t
    min_capacity : list
        minimum capacity per node  each time t
    max_capacity : list
        maximum capacity per node each time t
    nodes : list
        contains each node in each time t
    nodes_type: list
        contains type of node in each time t
    time_data: list
        contains a time t per node
    """
    water_in = []
    oil_in = []
    contaminants_in = {}
    time_data=[]
    min_capacity = []
    max_capacity = []
    nodes =[]
    nodes_type=[]

    for t in model.time_dim:
        for node in active_nodes:
            node_water_in = sum([model.x_water[j,node,t].value for j in model.entry[node]])
            node_oil_in = sum([model.x_oil[j,node,t].value\
                if (j, node) in model.oil_arcs else 0 for j in model.entry[node]])
            min_cap=model.min_capacity[node]
            max_cap=model.max_capacity[node]

            if node in model.initial:
                node_water_in = model.water_in[node,t]
                node_oil_in = model.oil_in[node,t]
            water_in.append(node_water_in)
            oil_in.append(node_oil_in)
            time_data.append(t)
            min_capacity.append(min_cap)
            max_capacity.append(max_cap)
            nodes.append(node)
            nodes_type.append(node_type(model, node))   
            
            for contaminant in model.contaminants:
                contaminant_data = []
                
                if node in model.initial:
                    contaminant_data.append([model.contaminant_in[node, contaminant,t],t,node])

                elif node_water_in > 0:
                    if len(model.process)==0\
                        and sum(model.contaminant_in.extract_values().values())==0\
                            and (sum(model.initial_content_contaminants_ponds.extract_values().values())\
                                + sum(model.initial_content_contaminants_tanks.extract_values().values()))==0:
                        contaminant_data.append([0,t,node])
                    else:
                        node_contaminant = sum([model.x_contaminant[j, node, contaminant,t].value\
                            *model.x_water[j,node,t].value for j in model.entry[node]])
                        contaminant_data.append([node_contaminant / node_water_in,t,node])
                else:
                    contaminant_data.append([0,t,node])
                
                contaminants_in[contaminant,node,t] = contaminant_data

    return water_in, oil_in, contaminants_in, min_capacity, max_capacity, nodes, nodes_type, time_data

def nodes_fluid_out(model, active_nodes):
    """This function add parameters to the dataframe to complete outpus

    Parameters
    ----------    
    model : Pyomo ConcreteModel
        The optimization model.
    active_nodes : list
        List with model active nodes
  
    Returns
    -------
    water_out : list
        water outflow per node
    oil_out : list
        oil outflow per node
    contaminants_out : dict
        The amount of contaminant per type of contaminant in each node per time t. 
        Every key is a contaminant type, a node and in time t
    """
    water_out = []
    oil_out = []
    contaminants_out = {}
    for t in model.time_dim:
        for node in active_nodes:
            node_water_out = sum([model.x_water[node, j,t].value for j in model.exit[node]])
            node_oil_out = sum([model.x_oil[node, j,t].value\
                if (node, j) in model.oil_arcs else 0 for j in model.exit[node]])
        
            water_out.append(node_water_out)
            oil_out.append(node_oil_out)

            for contaminant in model.contaminants:
                contaminant_data = []
                
                if node_water_out > 0:
                    if len(model.process)==0\
                        and sum(model.contaminant_in.extract_values().values())==0\
                        and (sum(model.initial_content_contaminants_ponds.extract_values().values())\
                            + sum(model.initial_content_contaminants_tanks.extract_values().values()))==0:
                        contaminant_data.append([0,t,node])
                    else:
                        node_contaminant = sum([model.x_contaminant[node, j, contaminant,t].value\
                            * model.x_water[node, j,t].value for j in model.exit[node]])
                        contaminant_data.append([node_contaminant / node_water_out,t,node])
                else:
                    contaminant_data.append([0,t,node])
                    
                contaminants_out[contaminant,node,t] = contaminant_data
    return water_out, oil_out, contaminants_out

def add_params(model, processed_data, df):
    """This function add parameters to the dataframe to complete outpus

    Parameters
    ----------    
    model : Pyomo ConcreteModel
        The optimization model.
    processed_data : ProcessedData
        It has all the model's processed data.
    df : pandas.DataFrame
        dataframe with results without aditional parameters
  
    Returns
    -------
    Pandas Dataframe
        It contains the nodes' data (parameters and model's decision variables)
    """
    df["Other_costs"] = df.apply(lambda row: sum((model.x_water[i, row.Source, row.Date].value + model.x_oil[i, row.Source, row.Date].value)* pe.value(model.other_cost[i, row.Source, row.Date])\
                                                    if i in model.oil_nodes else (model.x_water[i, row.Source, row.Date].value)\
                                                 * pe.value(model.other_cost[i, row.Source, row.Date]) for i in model.entry[row.Source]), axis = 1)
    df["Has_Oil"] = df.apply(lambda row: model.node_has_oil[row.Source], axis = 1)

    df["Pressure_In"] = df[df["Type"] == "Pump"].apply(lambda row: model.pressure_in[row.Source] ,axis = 1, result_type = 'reduce')
    df["Pressure_Out"] = df[df["Type"] == "Pump"].apply(lambda row: model.pressure_out[row.Source] ,axis = 1, result_type = 'reduce')
    df["B_P"] = df[df["Source"].isin(model.pumps_linear_regression)].apply(lambda row: model.pumps_energy_model_pressure_coef[row.Source], axis = 1, result_type = 'reduce')
    df["B_INTERCEPT"] = df[df["Source"].isin(model.pumps_linear_regression)].apply(lambda row: model.pumps_energy_model_intercept_coef[row.Source], axis = 1, result_type = 'reduce')
    df["Efficiency"] = df[df["Source"].isin(model.pumps_fixed_efficiency)].apply(lambda row: model.efficiency[row.Source], axis = 1, result_type = 'reduce')

    df["Energy_Consumption"] = df[df["Type"] == "Pump"].apply(lambda row: model.y_elec_amount[row.Source, row.Date].value ,axis = 1, result_type = 'reduce')
    df["Energy_Consumption"].fillna(0, inplace = True)

    df["Energy_Cost"] = df["Energy_Consumption"] * model.energy_cost
    df['CO2_TONS'] = df['Energy_Consumption'] * processed_data.energy_co2
    
    for contaminant in model.contaminants:
        df[contaminant + "_Removal_Rate"] = df[df["Type"] == "Treatment"].apply(lambda row: model.contaminant_removal_rate[row.Source, contaminant], axis = 1, result_type = 'reduce')
    
    for contaminant in model.contaminants:
        df[contaminant + "_Addition_pmm"] = df[df["Type"] == "Process"].apply(lambda row: model.contaminant_addition_ppm[row.Source, contaminant], axis = 1, result_type = 'reduce')

    df = df.fillna(0)

    return df

def get_storage(df_nodes, processed_data):
    '''Function with the scope of getting storage in input nodes
    
    Parameters
    ----------
        df_nodes : pandas.core.frame.DataFrame
            Nodes file output dataframe
        processed_data : ProcessedData
            It has all the model's processed data.
    
    Returns
    -------
        storage : pandas.core.frame.DataFrame
            df_nodes with a extra column of booleans telling where is a row with a start node storing fluid. This is important on bottleneck detection
        dates : list
            List of dates with start node storage
    '''
    storage = df_nodes[df_nodes.Source.isin(processed_data.initial_nodes_data.index.tolist())]
    df_nodes = df_nodes[~df_nodes.Source.isin(processed_data.initial_nodes_data.index.tolist())].assign(SOURCE_EXCESS=False)
    storage = storage.sort_values(by=['Source', 'Date']).reset_index(drop=True)
    proc_storage = storage.groupby(['Source'])[['Water_Stored', 'Oil_Stored']].diff()
    storage = storage.join(proc_storage, rsuffix='_diff')
    storage = storage.fillna({'Water_Stored_diff': storage.Water_Stored, 'Oil_Stored_diff': storage.Oil_Stored})
    storage = storage.assign(
        SOURCE_EXCESS=(storage.Water_Stored_diff.round(0)>0)|(storage.Oil_Stored_diff.round(0)>0)
    ).drop(['Water_Stored_diff', 'Oil_Stored_diff'], axis=1)
    dates = storage[storage.SOURCE_EXCESS].Date.unique()
    df_nodes = pd.concat([df_nodes, storage])
    return df_nodes, dates

def generate_arcs_output(model, processed_data, dates):
    """It extracts the model's arcs' summmary. It contains both parameters and model's decision variables.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    processed_data : ProcessedData
        It has all the model's processed data.
    parameters : dictionary(string, string)
        It has stored all the not-model's parameters.
    dates : list
        List of dates with start node storage

    Returns
    -------
    Pandas Dataframe
        It contains the arcs' data (parameters and model's decision variables)
    """
    #Obtaining arcs variables results
    active_arcs, active_water_arcs, active_oil_arcs = get_active_arcs(model)

    source = [i for i, j,t in active_arcs]
    target = [j for i, j,t in active_arcs]
    time_data = [t for i, j, t in active_arcs]

    min_flow = [model.min_flow[i,j] for i,j,t in active_arcs]
    max_flow = [model.max_flow[i,j] * model.usable_percentage[i,j,t] for i,j,t in active_arcs]
    
    usable_percentage_available = [model.usable_percentage[i,j,t] for i,j,t in active_arcs]

    water = map(lambda arc: active_water_arcs[arc], active_arcs)
    contaminants = {}
    for contaminant in model.contaminants:
        contaminant_data = []
        for i,j,t in active_arcs:
            if len(model.process)==0\
                and sum(model.contaminant_in.extract_values().values())==0\
                and (sum(model.initial_content_contaminants_ponds.extract_values().values())\
                    + sum(model.initial_content_contaminants_tanks.extract_values().values()))==0:
                contaminant_data.append(0)
            else:
                contaminant_data.append(model.x_contaminant[i,j, contaminant,t].value)
        
        contaminants[contaminant] = contaminant_data
    
    oil =  map(lambda arc: (active_oil_arcs[arc]) if (arc in active_oil_arcs) else 0, active_arcs)

    other_cost = [model.flow_cost[i,j] for i, j, t in active_arcs]
    #Arc data extration

    d = {'Source':source,
        'Date': time_data,
        'Target':target,
        'Min_capacity': min_flow,
        'Max_capacity': max_flow,
        'Usable percentage available': usable_percentage_available,
        'Water': water,
        'Oil': oil,
        'Other_cost_per_volume' : other_cost}
    df = pd.DataFrame(d)
    
    for contaminant in model.contaminants:
        df[str(contaminant)] =  contaminants[contaminant]

    df["Fluid_Total"] = df["Water"] + df["Oil"]
    df["Other_costs"] = df["Fluid_Total"] * df["Other_cost_per_volume"]
    #calculing recirculation
    arcs_data = processed_data.arcs_data.reset_index()
    arcs_data = arcs_data[
        arcs_data.Recirculation.str.contains('^y', case=False, regex=True)
        ][['Node_Start', 'Node_End']]
    reuse = df.join(arcs_data.set_index(['Node_Start', 'Node_End']), on=['Source', 'Target'], how='inner')
    reuse = reuse[['Source', 'Target', 'Water', 'Date']].rename({'Water': 'Reuse'}, axis=1)
    df = df.join(reuse.set_index(['Source', 'Target', 'Date']), on=['Source', 'Target', 'Date']).fillna(0)

    #getting bottleneck on network
    df = get_capacity(df, processed_data, dates)

    return df

def get_active_arcs(model):
    """Get the active model arc to process arc results

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.

    Returns
    -------
    active_arcs : list
        Active arcs on model
    active_water_arcs : dict
        Active water arcs on model
    active_oil_arcs : dict
        Active oil arcs on model
    """
    active_arcs = []
    active_water_arcs = {}
    active_oil_arcs = {}

    for v in model.component_objects(pe.Var, active=True):
        for index in v:
            if v.getname()=="x_water":
                active_arcs.append(index)
        
        for index in v:
            if v.getname()=="x_water":
                active_water_arcs[index] = v[index].value
            if v.getname()=="x_oil":
                active_oil_arcs[index] = v[index].value
    
    return active_arcs, active_water_arcs, active_oil_arcs

def get_capacity(edge_output, processed_data, dates):
    '''
    Parameters
    ----------
        edge_output : pandas.core.frame.DataFrame
            Arcs file output dataframe
        processed_data : ProcessedData
            It has all the model's processed data.
        dates : list
            List of dates with start node storage
    
    Returns
    -------
        capacity : pandas.core.frame.DataFrame
            df_arcs with a extra columns with useful data to get insights on bottleneck detection
    '''
    capacity = edge_output.join(processed_data.arcs_data[['MinFlow', 'MaxFlow']], on=['Source', 'Target'])
    capacity = capacity.assign(GAP=capacity.MaxFlow-(capacity.Water+capacity.Oil))
    capacity = capacity.assign(CAPACITY_USED=100-(capacity.GAP*100/capacity.MaxFlow).round(0)).drop(['MinFlow', 'MaxFlow'], axis=1)
    capacity = capacity.assign(BOTTLENECK=(capacity.CAPACITY_USED==100))
    return capacity


def standardize_outputs(df_nodes, df_arcs, model):
    """This methods filters the useful information on both Dataframes

    Parameters
    ----------
    df_nodes : Pandas Dataframe
        It contains the nodes' data (parameters and model's decision variables)
    df_arcs : Pandas Dataframe
        It contains the arcs' data (parameters and model's decision variables)
    Returns
    -------
    Pandas Dataframe
        It contains the nodes' data standardized 
    Pandas Dataframe
        It contains the arcs' data standardized
    """
    contaminants_removal_rate = [contaminant + "_Removal_Rate" for contaminant in model.contaminants]
    
    df_nodes = df_nodes.drop(['Min_capacity', \
                            'Max_capacity', 'Efficiency', 'B_P', 'B_INTERCEPT']\
                            + contaminants_removal_rate, axis = 1)
    df_arcs = df_arcs.drop(['Min_capacity', 'Max_capacity'], axis = 1)
    return df_nodes, df_arcs


def generate_output(model, result, parameters, processed_data):
    """Generates model's, nodes' and arcs' output files.

    Parameters
    ----------
    model : Pyomo ConcreteModel
        The optimization model.
    result : Pyomo Results Object
        The optimization results (it has the model's termination conditions).
    parameters : dictionary(string, string)
        It has stored all the not-model's parameters.
    processed_data : ProcessedData
        It has all the model's processed data.
    
    Returns
    -------
    outputs : dict
        Readed outputs from model ran. Following the keys:
            - model: For summary
            - nodes: For nodes output
            - arcs: For arcs output
    """
    
    df_nodes, dates = generate_nodes_output(model, processed_data)
    df_arcs = generate_arcs_output(model, processed_data, dates)
    df_summary = generate_model_output(model, result, df_nodes, df_arcs, parameters)
    
    df_nodes, df_arcs = standardize_outputs(df_nodes, df_arcs, model)


    df_list = [df_nodes, df_arcs, df_summary]
    paths_list = [parameters["output_nodes_dir"], parameters["output_arcs_dir"], parameters["output_model_dir"]]

    for i, df in enumerate(df_list):
        df.to_csv(paths_list[i], index=False)

    # saving parameters json file
    with open(parameters['output_json_dir'], 'w') as f:
        json.dump(parameters['json_file'], f)

    outputs = {'nodes': df_nodes, 'edges': df_arcs, 'summary': df_summary}
    return outputs