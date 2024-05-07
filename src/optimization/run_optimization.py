# -*- coding: utf-8 -*-
"""
run_optimization.py
====================================
Script to concatenate the model runing. It reads parameters.json and use its information to configure model running

@author:
     - g.munera.gonzalez
     - ivo.pajor
     - yeison.diaz
"""

import sys, os, re, json

import pandas as pd
import numpy as np
import json
from src.commons.s3_manager import S3Manager
from src.optimization.treatment.treatment import process_treatment_results, treatment_model
from src.commons.system_util import get_athenas_error
from src.optimization.injection.injection import injection_model, process_injection_results
from src.recommendations.injection_recommendations import get_action_arc_use, get_action_operational_pump

from water_models.rainfall import build_precipitation_model
import water_models.evaporation as evaporation


def run_optimization(system_utilities, s3_data, param_file, date):
    '''Function to configure and run the optimization model. It helps using parameters.json to configure models running.
    Parameters
    ----------
    system_utilities : src.commons.system_util.SystemUtilities
        system_utilities objecto that contains parameters.json file information. It also has the model parameters
        like paths and configuration features
    s3_data : bool
        Tell the model if run from s3 or not
    param_file : str
        Parameters file name
    date : datetime.datetime
        Running time
    '''
    parameters = system_utilities.parameters

    local = not system_utilities.s3_data
    local = False if re.match('linux.*', sys.platform) else local
    #running custom models (rainfall-evaporation):
    if system_utilities.params['rainfall']:
        print('    ############################PROCESSING RAINFALL MODEL############################')
        path = os.path.join(os.path.dirname(sys.path[0]), '01_data')
        path_rainfall = os.path.join(path, 'OpenWeather - Barrancabermeja.csv')
        path_out, flow_rates = parameters['flow_file'], parameters['flow_file']
        build_precipitation_model(system_utilities.params, flow_rates, path_rainfall, path_out, local)
    if system_utilities.params['evaporation']:
        print('    ##########################PROCESSING EVAPORATION MODEL##########################')
        print('    reading data...')
        data = evaporation.read_data(system_utilities.params, local)
        print('    building flow_rates.xlsx...')
        flow_rates = os.path.basename(system_utilities.params['water_flow_file'])
        evaporation.build_evap_excel(system_utilities.params, data,'EVAPORATION', local=local, flow_rates=flow_rates)
        print('    ###############################MODEL RUN END####################################')
    
    #defining objects to store outputs
    athena, times, pandas_dataframe = [], {}, None
    delta, iterations = parameters['delta'], parameters['iterations']

    if parameters['water'] == True and parameters['injection'] == True:
        athena, times, pandas_dataframe = blender_descomposition(system_utilities, s3_data, param_file, date,\
                                                     athena, times, delta, iterations, parameters['json_file']['time_periods'])
    
    elif parameters['water'] == True:
        model, result, runtime = treatment_model('water', s3_data, param_file, date, None)
        model_athena = process_treatment_results('water', s3_data, param_file, date, None, model, result)
        athena, times = save_optimization_results(system_utilities, athena, times, 'water', model, model_athena, runtime)

    elif parameters['injection'] == True:
        qwat = system_utilities.parameters['json_file']['injection_qwat']
        inj_model, runtime, _ = injection_model(qwat, s3_data, param_file, date, 1)
        (model_athena, pandas_dataframe) = process_injection_results(s3_data,param_file, date, inj_model)      
        athena, times = save_optimization_results(system_utilities, athena, times, 'injection', inj_model.model, model_athena, runtime)
    
    save_results_csv(system_utilities, pandas_dataframe)
    
    export_athenas_database(system_utilities, athena)

    save_recommendations(system_utilities, athena)

    save_results_in_s3_bucket(system_utilities, s3_data, parameters)
    
    export_time_report(times) 


def blender_descomposition(system_utilities, s3_data, param_file, date, athena, times, delta, iterations, time_periods):
    cost_per_liter_df = pd.DataFrame({'ID' : np.full(time_periods, "TO_INJECT_TANK_MIX"),
                                    'OtherCosts' : np.full(time_periods, 0),
                                    'time' : np.arange(1, time_periods + 1),
                                    'old_cost' : np.full(time_periods, 0)})
    is_equal=False
    while iterations > 0 :
        model_treatment, result_treatment, runtime_treatment,\
        models_injection, runtime_injection,\
        costs_per_liter_new = run_treatment_and_injection(s3_data, param_file, date, cost_per_liter_df, time_periods)
        cost_per_liter_df['mean'] = cost_per_liter_df[['OtherCosts', 'old_cost']].mean(axis=1)
        mean2_old=cost_per_liter_df[["time", "mean"]].set_index("time")["mean"].to_dict() 
               
        if len(costs_per_liter_new) != len(cost_per_liter_df['OtherCosts']) or \
            (abs((costs_per_liter_new - np.array(cost_per_liter_df['OtherCosts'])) / costs_per_liter_new) < delta).all() or\
                is_equal==True:
            break
    
        cost_per_liter_df['old_cost'] = cost_per_liter_df['OtherCosts']
        cost_per_liter_df['OtherCosts'] = costs_per_liter_new
        cost_per_liter_df['mean'] = cost_per_liter_df[['OtherCosts', 'old_cost']].mean(axis=1)
        mean2_new=cost_per_liter_df[["time", "mean"]].set_index("time")["mean"].to_dict()
        is_equal=mean2_old==mean2_new
        iterations -= 1 
    
    model_injection = None if len(cost_per_liter_df['OtherCosts']) != time_periods else models_injection[-1]
    injection_results = [ process_injection_results(s3_data, param_file, date, model) for model in models_injection ]
    injection_results = list(zip(*injection_results))
    athena_injection = pd.concat(injection_results[0], ignore_index = True)
    names_df = ['nodes', 'edges', 'summary']
    pandas_dataframes = {name:pd.concat(list(map(lambda dict: dict[name], injection_results[1])), ignore_index = True) for name in names_df}
    model_treatment.other_cost[:,'TO_INJECT_TANK_MIX',:]=0
    athena_treatment = process_treatment_results('water', s3_data, param_file, date, cost_per_liter_df, model_treatment, result_treatment)
    athena, times = save_optimization_results(system_utilities, athena, times,\
                                                         'water', model_treatment, athena_treatment, runtime_treatment) 
    athena, times = save_optimization_results(system_utilities, athena, times,\
                                                         'injection', model_injection, athena_injection, runtime_injection)                      
    return athena, times, pandas_dataframes 

def run_treatment_and_injection(s3_data, param_file, date, cost_per_liter_df, time_periods):
    
    model_treatment, result_treatment , runtime_treatment  = treatment_model('water', s3_data, param_file, date, cost_per_liter_df)
    qwats = calculate_water_to_inject(model_treatment, time_periods)
    costs_per_liter = np.array([])
    models_injection = np.array([])
    for t, qwat in enumerate(qwats):
        model_injection, runtime_injection , cost_per_liter = injection_model(qwat, s3_data, param_file, date, t+1)
        if cost_per_liter is None:
            break
        models_injection = np.append(models_injection, model_injection)
        costs_per_liter = np.append(costs_per_liter, cost_per_liter) 
    return model_treatment, result_treatment, runtime_treatment,\
            models_injection, runtime_injection,\
            costs_per_liter

def save_optimization_results(system_utilities, athena, times, model_name, model, model_athena, runtime):
    times[model_name] = runtime
    if model!=None:
        athena.append(model_athena)
    else:
        athena.append(get_athenas_error(runtime, model_name, system_utilities.parameters['json_file']['run_name']))
    return athena, times

def calculate_water_to_inject(treatment_model, time_periods):
    node_for_injection = ["TO_INJECT_TANK_MIX"]
    qwats = np.full(time_periods, 0)
    for (i,j,t) in treatment_model.x_water.extract_values().keys():
        if j in node_for_injection:
            qwats[t-1] += treatment_model.x_water.extract_values().get((i,j,t))
    return qwats

def save_results_csv(system_utilities, pandas_dataframe = None):
    if pandas_dataframe is not None:
        system_utilities.generate_parameters('injection')
        parameters = system_utilities.parameters
        output_path = {'nodes': parameters['output_nodes_dir'], 'edges': parameters["output_arcs_dir"],\
                     'summary': parameters["output_model_dir"]} 
        for table in pandas_dataframe.keys():
            pandas_dataframe[table].to_csv(output_path[table], index=0)
        with open(parameters["output_json_dir"], 'w') as f:
            json.dump(parameters['json_file'], f)
        system_utilities.generate_parameters('water')

def export_athenas_database(system_utilities, athena):
    athenas = pd.concat(athena)
    athenas = athenas.sort_values([
            'DATE', 'OPERATIONS', 'ASSET', 'LEVEL_1', 'LEVEL_2', 'LEVEL_3', 'LEVEL_4', 'LEVEL_5', 'LEVEL_6', 'SOURCE', 'VARIABLE'
            ])
    print('saving athenas results...')
    output_path = os.path.join(system_utilities.path_out, f'{system_utilities.v_data}.csv')
    athenas.to_csv(output_path, index=0)

def save_recommendations(system_utilities, athena):
    '''Function defined to create and save recommendations from athenas database objects

    PARAMETERS:
    -----------
    system_utilities : :py:func:`src.commons.system_util.SystemUtilities`
        Object with run basic data
    athena : list
        Database list for all dates
    '''
    print('saving recommendations...')
    athena = pd.concat(athena)
    actions = get_action_arc_use(athena)
    operat = get_action_operational_pump(athena)
    actions.extend(operat)
    if len(actions):
        with open(os.path.join(system_utilities.path_out, 'recommendations_injection.json'), 'w') as f:
            json.dump(actions, f)

def save_results_in_s3_bucket(system_utilities, s3_data, parameters):
    if re.match('linux.*', sys.platform) or s3_data:
        print('saving results in s3 bucket...')
        test_ = S3Manager()
        test_.save_s3results(os.path.dirname(parameters["output_model_dir"]), parameters['s3_output_model'])
        test_.client.upload_file(
            os.path.join(os.path.dirname(parameters["output_model_dir"]), f'{system_utilities.v_data}.csv'),
            test_.bucket,
            parameters['s3_output_appsync']
        )

def export_time_report(times):
    print('\n'+'*'*50)
    print('RUNING TIME REPORT:')
    for model, t in times.items():
        print('*'*10+f'{model.upper()} MODEL TIME'+'*'*10)
        print(' '*15+t)
    print('*'*50)