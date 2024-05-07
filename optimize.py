import sys, re, os, datetime, logging, traceback, json

from src.commons.system_util import SystemUtilities, S3Manager, get_athenas_error
from src.optimization.run_optimization import run_optimization

logging.getLogger('pyomo.core').setLevel(logging.ERROR)

if __name__=='__main__':
    #defining basic inputs
    s3_data, param_file = False, "parameters_permian_test_APP.json"  #please maintain this values: False and None, once you have finished your development
    if re.match('linux.*', sys.platform) or s3_data:
        s3, file = S3Manager(), ''
        parameters_path = os.environ['PARAMETERS_PATH']
        print('\n\n\n'+'*'*50)
        try:
            file = s3.get_recent_file(parameters_path)
            if file!=None:
                date = None if re.match('linux.*', sys.platform) else datetime.datetime.now()
                system_utilities = SystemUtilities(s3_data, param_file=param_file, date=date)
                system_utilities.read_parameters()
                system_utilities.generate_parameters('water')
                run_optimization(system_utilities, s3_data, param_file, date)
        except Exception as e:
            error = get_athenas_error(traceback.format_exc()+'  ', 'RunTimeError', system_utilities.parameters['json_file']['run_name'])
            print('saving athenas results...')
            output_path = os.path.join(system_utilities.path_out, f'{system_utilities.v_data}.csv')
            with open(system_utilities.parameters["output_json_dir"], 'w') as f:
                json.dump(system_utilities.parameters['json_file'], f)
            error.to_csv(output_path, index=0)
            s3.client.upload_file(
                os.path.join(os.path.dirname(system_utilities.parameters["output_model_dir"]), f'{system_utilities.v_data}.csv'),
                s3.bucket,
                system_utilities.parameters['s3_output_appsync']
            )
            s3.save_s3results(
                os.path.dirname(system_utilities.parameters["output_model_dir"]),
                system_utilities.parameters['s3_output_model']
                )
    else:
        try:
            date = None if re.match('linux.*', sys.platform) else datetime.datetime.now()
            system_utilities = SystemUtilities(s3_data, param_file=param_file, date=date)
            system_utilities.read_parameters()
            system_utilities.generate_parameters('water')
            run_optimization(system_utilities, s3_data, param_file, date)
        except Exception as e:
            error = get_athenas_error(traceback.format_exc()+'  ', 'RunTimeError', system_utilities.parameters['json_file']['run_name'])
            print('saving athenas results...')
            output_path = os.path.join(system_utilities.path_out, f'{system_utilities.v_data}.csv')
            with open(system_utilities.parameters["output_json_dir"], 'w') as f:
                json.dump(system_utilities.parameters['json_file'], f)
            error.to_csv(output_path, index=0)