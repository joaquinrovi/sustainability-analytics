# -*- coding: utf-8 -*-
"""
treatment.py
====================================
This script collect high level functionalities to build and run the model. It also process model resulta and place
it in the simulations folder.

@author:
     - c.maldonado
     - g.munera.gonzalez
     - yeison.diaz
"""

import time, json
import pyomo.environ as pe
from src.optimization.treatment.preprocess_data import preprocess_data
from src.optimization.treatment.make_model import make_model
from src.optimization.treatment.generate_output import generate_output
from src.commons.system_util import SystemUtilities
from src.commons.process_results import ProcessResults
from src.commons.system_util import get_string_time

import src.recommendations.water_recommendations as wr


def treatment_model(model_name, s3_data, param_file, date, cost_of_injection = None):
    '''Treatment model execution depending on model runed
    
    Parameters
    ----------
    model_name : str
        Model string that identify what model we are running. Can be:
        - water
    s3_data : boolean
        Define if read from s3 bucket or not
    param_file : str-Nonetype, optional, default None
        parameter file name
    date : str-Nonetype, optional, default None
        datetime to add in the simulation name
    cost_of_injection: pd.Dataframe, optional, default None
        cost of the injection model per period
    
    Returns
    -------
    model : pyomo.core.base.PyomoModel.ConcreteModel
        Pyomo concrete model to access data
    result : pyo.opt.results.results.SolverResults
        Pyomo model results in a pseudo json form
    time_ : str
        string with running time
    '''
    print('*'*50)
    tik = time.time()
    print(f"RUNNING {model_name.upper()} MODEL:")
    print("    reading parameters...")
    test, parameters, simulated_period = read_parameters(model_name, s3_data, param_file, date)
    print("    Preprocessing data")
    data, useful_sets, attributes_with_time = preprocess_data(parameters, simulated_period,s3_data=s3_data, cost_of_injection = cost_of_injection)

    print("    optimizing model...")
    model, solver, result = make_model(data, useful_sets, parameters, attributes_with_time)
    time_ = get_string_time(time.time()-tik)

    return model, result, time_

def process_treatment_results(model_name, s3_data, param_file, date, cost_of_injection, model, result):
    test, parameters, simulated_period = read_parameters(model_name, s3_data, param_file, date)
    data, _, _ = preprocess_data(parameters, simulated_period,s3_data=s3_data, cost_of_injection = cost_of_injection)

    if ((result.solver.status==pe.SolverStatus.ok) and (result.solver.termination_condition==pe.TerminationCondition.optimal))\
        or ((result.solver.status==pe.SolverStatus.aborted) and (result.solver.termination_condition==pe.TerminationCondition.maxTimeLimit) and (len(model.solutions)>0)): #if the optimization is aborted because of the timelimit set, we still keep the last result obtained by Gurobi, if any
        print("    exporting results...")
        outputs = generate_output(model, result, parameters, data)
        #generating recirculation recomendations
        recirculation = wr.get_action_recirculation(data.arcs_data.reset_index(), outputs)
        #generating reuse recomendations
        reuse = wr.get_action_reuse(data.arcs_data.reset_index(), data.ending_nodes_data.reset_index(), outputs)
        #generating nominal value recomendations
        nominal = wr.get_action_nominal_values(data.arcs_data.reset_index(), outputs)
        recommendations, actions = [recirculation, reuse, nominal], []
        #putting it together and saving json
        for recomm in recommendations:
            if len(recomm):
                actions.extend(recomm)
        if len(actions):
            recomendations_path = test.parameters["output_recommendations_dir"]
            with open(recomendations_path, 'w') as f:
                json.dump(actions, f)
        print(f'PROCESSING {model_name.upper()} MODEL OUTPUTS:')
        test_results = ProcessResults(model_name, outputs,  s3_data=s3_data, param_file=param_file, date=date)
        print(f"    {model_name.upper()} running done.")
        print('*'*50)
        return test_results.athena
    else:
        print('    an error ocurred while solving the system...')
        return None
         
def read_parameters(model_name, s3_data, param_file, date):
    test = SystemUtilities(s3_data, param_file=param_file, date=date)
    test.read_parameters()
    test.check_directories()
    test.generate_parameters(model_name)
    parameters = test.parameters
    simulated_period=parameters['time_periods']
    return test,parameters,simulated_period