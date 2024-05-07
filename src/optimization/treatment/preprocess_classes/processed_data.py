# -*- coding: utf-8 -*-
"""
processed_data.py
====================================
Auxiliar class to help reading, processing and storing input dataframes

@author:
     - c.maldonado
     - g.munera.gonzalez
     - yeison.diaz
"""
import sys, re
import pandas as pd
from src.commons.s3_manager import S3Manager

class ProcessedData(S3Manager):
    """ It has all the processed model related data.
    """
    def __init__(self, parameters, s3_data=False):
        '''Reads and preprocess all the model's related data. It filters active arcs and nodes.

        Parameters
        ----------
        parameters : dictionary(string, string)
            It has stored all the not-model's parameters.
        s3_data : Boolean
            Define if read from S3 or not
        '''
        self.parameters, self.s3_data = parameters, s3_data
        self.conf_file_dict = {
            'arcs_raw_data': 'Arc_CPF', 'oil_fixed_treatment_arcs_raw_data': 'Arcs_Fixed_Oil_Treat',
            'fixed_splitter_arcs_raw_data': 'Arcs_Fixed_Splitter', 'initial_nodes_raw_data': 'Node_Start',
            'ending_nodes_raw_data': 'Node_Terminal', 'pumps_nodes_raw_data': 'Node_Pump', 'tanks_nodes_raw_data': 'Node_Tank',
            'splitter_nodes_raw_data': 'Node_Splitter', 'mixer_nodes_raw_data': 'Node_Mixer',
            'process_nodes_raw_data': 'Node_Process', 'process_nodes_contaminants_raw_data': 'Node_Process_Cont',
            'treatment_nodes_raw_data': 'Node_Water_Treatment', 'treatment_nodes_contaminants_raw_data': 'Node_Water_Treatment_Cont',
            'oil_treatment_nodes_raw_data': 'Node_Oil_Treatment', 'cooling_tower_nodes_raw_data': 'Node_CoolingTW',
            'boiler_nodes_raw_data': 'Node_Boiler', 'loss_tanks_nodes_raw_data': 'Node_Loss_Tank', 
            'ponds_nodes_raw_data': 'Node_Pond', 'sparse_node' : 'Sparse_Nodes',
            'sparse_arcs': 'Sparse_Arcs'
        }

    def read_data(self, period):
        '''Method defined to get data (wherever data lies)
        
        Returns
        -------
        load_data : dict
            Dictionary with loaded data. It has:
               - Configuration file data
               - Pump energy models
               - Flow rates
        '''
        if re.match('linux.*', sys.platform) or self.s3_data:
            load_data = self.read_s3data(period)
        else:
            load_data = self.read_oddata(period)
        return load_data

    def read_oddata(self, period):
        '''Method defined to read data from one drive repository
        
        Returns
        -------
        load_data : dict
            Dictionary with loaded data. It has:
               - Configuration file data
               - Pump energy models
               - Flow rates
        '''
        print('    reading data from one drive...')
        load_data = {}
        #reading configuration file
        for key, sheet in self.conf_file_dict.items():
            load_data[key] = pd.read_excel(self.parameters["data_file_dir"], sheet_name=sheet)

        #reading pump models
        load_data['pumps_energy_models_raw_data'] = pd.read_csv(self.parameters["pump_energy_model_dir"])

        #reading flow_rates
        temp_xl = pd.ExcelFile(self.parameters["flow_file"])
        tanks_flow_raw = []
        for i in temp_xl.sheet_names:
            if i == "EVAPORATION":
                _evap_df = pd.read_excel(temp_xl, sheet_name=i)
                load_data ['evaporation_raw'] = _evap_df[_evap_df["time"]<=period]
            else:
                temp_df = pd.read_excel(temp_xl, sheet_name=i)
                temp_df['Tank'] = i 
                tanks_flow_raw.append(temp_df)
        tanks_flow_raw = pd.concat(tanks_flow_raw)
        tanks_flow_raw = tanks_flow_raw[tanks_flow_raw["time"]<=period]
        load_data['tanks_flow_raw'] = tanks_flow_raw
        return load_data

    def read_s3data(self, period):
        '''Method defined to read data from s3 bucket
        
        Returns
        -------
        load_data : dict
            Dictionary with loaded data. It has:
               - Configuration file data
               - Pump energy models
               - Flow rates
        '''
        print('    reading data from s3 bucket...')
        S3Manager.__init__(self)
        
        load_data = {}
        #reading configuration file
        for key, sheet in self.conf_file_dict.items():
            load_data[key] = self.get_s3data(self.parameters["data_file_dir"], sheet_name=sheet)

        #reading pump models
        load_data['pumps_energy_models_raw_data'] = self.get_s3data(self.parameters["pump_energy_model_dir"])

        #reading flow_rates
        obj = self.client.get_object(
            Bucket=self.bucket,
            Key=self.parameters["flow_file"]
        )
        temp_xl = pd.ExcelFile(obj['Body'].read())
        tanks_flow_raw = []
        for i in temp_xl.sheet_names:
            if i == "EVAPORATION":
                _evap_df = pd.read_excel(temp_xl, sheet_name=i)
                load_data ['evaporation_raw'] = _evap_df[_evap_df["time"]<=period]
            else:
                temp_df = pd.read_excel(temp_xl, sheet_name=i)
                temp_df['Tank'] = i 
                tanks_flow_raw.append(temp_df)
        tanks_flow_raw = pd.concat(tanks_flow_raw)
        tanks_flow_raw = tanks_flow_raw[tanks_flow_raw["time"]<=period]
        load_data['tanks_flow_raw'] = tanks_flow_raw
        return load_data

    @staticmethod
    def clean_nodes(data):
        """Method that takes a Dataframe with node information and cleans it

        Parameters
        ----------
        data : dataframe
            Dataframe with node information that we want to clean

        Returns
        -------
        clean_data
            Dataframe that contains only the active nodes without duplicates
        """
        clean_data = data[data['Active']=="Y"].drop('Active', axis=1)
        clean_data = clean_data.drop_duplicates().set_index('ID')
        return clean_data

    @staticmethod
    def clean_arcs(data):
        """Method that takes a Dataframe with arcs information and cleans it

        Parameters
        ----------
        data : dataframe
            Dataframe with arcs information that we want to clean

        Returns
        -------
        clean_data
            Dataframe that contains only the active arcs without duplicates
        """
        clean_data = data[data['Active']=="Y"].drop('Active', axis=1)
        clean_data = clean_data.drop_duplicates().set_index(['Node_Start', 'Node_End'])
        return clean_data

    @staticmethod
    def clean_contaminants(data):
        """Method that takes a Dataframe with contaminants information and cleans it

        Parameters
        ----------
        data : dataframe
            Dataframe with arcs information that we want to clean

        Returns
        -------
        clean_data
            Dataframe that contains only the active arcs without duplicates
        """
        clean_data = data[data['Active']=="Y"].drop('Active', axis=1)
        clean_data = clean_data.drop_duplicates().set_index(['ID', 'Contaminant'])
        return clean_data

    def process_data(self, load_data, cost_of_injection = None):
        '''Method defined to process read data to ensure proper attributes
        
        Parameters
        ----------
        load_data : dict (str: pandas.core.frame.DataFrame)
            Dataframe with read data
        cost_of_injection: pd.Dataframe, optional, default None
            cost of the injection model per period
        Returns
        -------
        proc_data : dict (str: pandas.core.frame.DataFrame or str: float)
            Processed data ready to be placed into class attributes
        '''
        print('    processing loaded data...')
        parameters_data = {
            "energy_cost": self.parameters["energy_cost"],
            "energy_co2": self.parameters["energy_co2"],
            "time_periods": self.parameters["time_periods"],
            "barrel_to_liters": self.parameters["barrel_to_liters"],
            "day_to_sec": self.parameters["day_to_sec"],
            "watt_to_kwh": self.parameters["watt_to_kwh"]
            }

        #Define the Other cost of the ARCS
        #Cost of the arc is going to be define as the cost of node J
        aux_columns = ['ID', 'MinCapacity', 'MaxCapacity', 'OtherCosts', 'Active', 'HasOil']
        aux_df = [
            load_data['initial_nodes_raw_data'][aux_columns], load_data['ending_nodes_raw_data'][aux_columns],
            load_data['pumps_nodes_raw_data'][aux_columns], load_data['splitter_nodes_raw_data'][aux_columns],
            load_data['mixer_nodes_raw_data'][aux_columns], load_data['process_nodes_raw_data'][aux_columns],
            load_data['treatment_nodes_raw_data'][aux_columns], load_data['oil_treatment_nodes_raw_data'][aux_columns],
            load_data['tanks_nodes_raw_data'][aux_columns], load_data['cooling_tower_nodes_raw_data'][aux_columns],
            load_data['boiler_nodes_raw_data'][aux_columns], load_data['loss_tanks_nodes_raw_data'][aux_columns],
            load_data['ponds_nodes_raw_data'][aux_columns]
        ]
        nodes_data = pd.concat(aux_df)
        nodes_cost = nodes_data[['ID', 'OtherCosts']].copy()

        cost_of_injection = cost_of_injection if (cost_of_injection is not None) else pd.DataFrame({'ID' : [], 'OtherCosts' : [], 'time' : []})
        cost_of_injection = cost_of_injection.set_index(['ID', 'time'])

        arcs_data = pd.merge(
            left=load_data['arcs_raw_data'], right=nodes_cost, left_on='Node_End',
            right_on='ID', how='left'
        ).drop('ID', axis=1)


        # Clean the arcs
        arcs_data = ProcessedData.clean_arcs(arcs_data)
        oil_fixed_treatment_arcs_data = ProcessedData.clean_arcs(load_data['oil_fixed_treatment_arcs_raw_data'])
        fixed_splitter_arcs_data = ProcessedData.clean_arcs(load_data['fixed_splitter_arcs_raw_data'])

        # Clean the nodes
        nodes_data = ProcessedData.clean_nodes(nodes_data)
        initial_nodes_data = ProcessedData.clean_nodes(load_data['initial_nodes_raw_data'])
        ending_nodes_data = ProcessedData.clean_nodes(load_data['ending_nodes_raw_data'])
        pumps_nodes_data = ProcessedData.clean_nodes(load_data['pumps_nodes_raw_data'])

        pumps_energy_models_data = load_data['pumps_energy_models_raw_data'].assign(
            PUMP='PUMP_'+load_data['pumps_energy_models_raw_data'].PUMP
        )
        pumps_energy_models_data = pumps_energy_models_data.drop_duplicates().set_index('PUMP')

        splitter_nodes_data = ProcessedData.clean_nodes(load_data['splitter_nodes_raw_data'])
        mixer_nodes_data = ProcessedData.clean_nodes(load_data['mixer_nodes_raw_data'])
        process_nodes_data = ProcessedData.clean_nodes(load_data['process_nodes_raw_data'])
        treatment_nodes_data = ProcessedData.clean_nodes(load_data['treatment_nodes_raw_data'])
        loss_tanks_nodes_data = ProcessedData.clean_nodes(load_data['loss_tanks_nodes_raw_data'])
        ponds_nodes_data = ProcessedData.clean_nodes(load_data['ponds_nodes_raw_data'])
        tanks_nodes_data = ProcessedData.clean_nodes(load_data['tanks_nodes_raw_data'])
        oil_treatment_nodes_data = ProcessedData.clean_nodes(load_data['oil_treatment_nodes_raw_data'])
        cooling_tower_nodes_data = ProcessedData.clean_nodes(load_data['cooling_tower_nodes_raw_data'])
        boiler_nodes_data = ProcessedData.clean_nodes(load_data['boiler_nodes_raw_data'])

        # SUPPLY
        tanks_flow = load_data['tanks_flow_raw'][
            load_data['tanks_flow_raw']["Tank"].isin(load_data['initial_nodes_raw_data']["ID"].to_list())
        ].set_index(['Tank','time'])

        # DEMAND
        terminal_dinamic_capacity = load_data['tanks_flow_raw'][
            load_data['tanks_flow_raw']["Tank"].isin(load_data['ending_nodes_raw_data']["ID"].to_list())
        ].set_index(['Tank','time'])

        #Clean contaminants (?)
        #initial_nodes_contaminants_data = clean_contaminants(initial_nodes_contaminants_raw_data)
        contaminants = [i for i in list(load_data['tanks_flow_raw'].columns) if "Contaminant_" in i]
        initial_nodes_contaminants_raw_data = load_data['tanks_flow_raw'][
            load_data['tanks_flow_raw']["Tank"].isin(load_data['initial_nodes_raw_data']["ID"].to_list())
        ][["Tank","time"]+contaminants]

        #Clean column names of flow rate to match the name of config file
        col_names = list(initial_nodes_contaminants_raw_data.columns)
        col_names = list(map(lambda x : re.sub("Contaminant_", "", x), col_names))
        initial_nodes_contaminants_raw_data.columns = col_names
        contaminants = list(map(lambda x : re.sub("Contaminant_", "", x) ,contaminants))

        #Melt process for the initial flow rate per time
        initial_nodes_contaminants_data=pd.melt(initial_nodes_contaminants_raw_data[["Tank","time"]+contaminants], \
            id_vars=['Tank','time'], var_name='Contaminant') \
                .set_index(['Tank','Contaminant', 'time'])

        
        #Melt process for the initial contaminant content per tank
        new_columns_to_pivot=list(contaminants+["ID"])
        _tanks=tanks_nodes_data.reset_index()
        col_names= list(_tanks.columns)
        col_names = list(map(lambda x : re.sub("Contaminant_", "", x) ,col_names))
        _tanks.columns=col_names
        initial_content_contaminants_tanks = pd.melt(_tanks[new_columns_to_pivot], \
            id_vars=["ID"], var_name='Contaminant')\
                .set_index(['ID','Contaminant'])

        #Melt process for the initial contaminant content per pond
        new_columns_to_pivot=list(contaminants+["ID"])
        _ponds = ponds_nodes_data.reset_index()
        col_names= list(_ponds.columns)
        col_names = list(map(lambda x : re.sub("Contaminant_", "", x) ,col_names))
        _ponds.columns=col_names
        initial_content_contaminants_ponds = pd.melt(_ponds[new_columns_to_pivot], \
            id_vars=["ID"], var_name='Contaminant')\
                .set_index(['ID','Contaminant'])

        process_nodes_contaminants_data = ProcessedData.clean_contaminants(load_data['process_nodes_contaminants_raw_data'])

        treatment_nodes_contaminants_data = ProcessedData.clean_contaminants(load_data['treatment_nodes_contaminants_raw_data'])

        #Union of tanks and ponds initial flow
        inital_content = tanks_nodes_data['InitialCapacity'].to_dict()
        ponds_content = ponds_nodes_data['InitialCapacity'].to_dict()
        inital_content.update(ponds_content)

        # Sparse Attributes that change with time
        sparse_node = load_data['sparse_node'].drop_duplicates().pivot(index=["ID","time"],columns="Attribute",values="Value")
        sparse_arcs = load_data['sparse_arcs'].drop_duplicates().pivot(index=['Node_Start', 'Node_End', 'time'],columns="Attribute",values="Value")

        #Evaporation Rates
        evaporation_rates = load_data['evaporation_raw'][["time","evaporation_rate"]].set_index('time')
        #Ponds Dimensions
        for i in ponds_nodes_data.index:
            length_top = ponds_nodes_data.filter(items = [i], axis=0).Dim_top_L[0]
            width_top  = ponds_nodes_data.filter(items = [i], axis=0).Dim_top_W[0]
            area_top = length_top * width_top
            length_bottom = ponds_nodes_data.filter(items = [i], axis=0).Dim_bottom_L[0]
            width_bottom = ponds_nodes_data.filter(items = [i], axis=0).Dim_bottom_W[0]
            area_bottom = length_bottom * width_bottom
            if area_top <= area_bottom:
                raise TypeError("Top surface of pond {} is smaller than bottom surface, check pond dimensions".format(i))
        #Average pond surface
        ponds_nodes_data['avg_area'] = (ponds_nodes_data['Dim_top_L'] * ponds_nodes_data['Dim_top_W'] + ponds_nodes_data['Dim_bottom_L']*ponds_nodes_data['Dim_bottom_W'])/2
        
        proc_data = {
            'nodes_data': nodes_data,
            'initial_nodes_data': initial_nodes_data,
            'ending_nodes_data': ending_nodes_data,
            'pumps_nodes_data': pumps_nodes_data,
            'pumps_energy_models_data': pumps_energy_models_data,
            'tanks_nodes_data': tanks_nodes_data,
            'loss_tanks_nodes_data': loss_tanks_nodes_data,
            'ponds_nodes_data': ponds_nodes_data,
            'splitter_nodes_data': splitter_nodes_data,
            'mixer_nodes_data': mixer_nodes_data,
            'process_nodes_data': process_nodes_data,
            'treatment_nodes_data': treatment_nodes_data,
            'oil_treatment_nodes_data': oil_treatment_nodes_data,
            'cooling_tower_nodes_data': cooling_tower_nodes_data,
            'boiler_nodes_data': boiler_nodes_data, 
            'initial_nodes_contaminants_data': initial_nodes_contaminants_data,
            'process_nodes_contaminants_data': process_nodes_contaminants_data,
            'treatment_nodes_contaminants_data': treatment_nodes_contaminants_data,
            'arcs_data': arcs_data,
            'splitter_arcs_data': fixed_splitter_arcs_data,
            'oil_treatment_arcs_data': oil_fixed_treatment_arcs_data,
            'parameters_data': parameters_data,
            'tanks_flow':tanks_flow,
            'terminal_dinamic_capacity':terminal_dinamic_capacity,
            'initial_content_contaminants_tanks': initial_content_contaminants_tanks,
            'initial_content_contaminants_ponds': initial_content_contaminants_ponds,
            'inital_content': inital_content,
            'sparse_node' : sparse_node,
            'sparse_arcs' : sparse_arcs,
            'injection_cost' : cost_of_injection,
            'evaporation_rates': evaporation_rates
        }

        return proc_data
    
    def create_attributes(self, proc_data):
        """ProcessedData initializer.

        Parameters
        ----------
        proc_data : dict
            Dict of dataframes-dict with the following key structure
            nodes_data:
            - All the active nodes' data ('ID', 'MinCapacity', 'MaxCapacity', 'OtherCosts', 'HasOil')
            initial_nodes_data:
            - All the active initial nodes' data ('ID', 'WaterQty', 'OilQty', 'ContaminantPct')
            ending_nodes_data:
            - All the active ending nodes' data ('ID')
            pumps_nodes_data:
            - All the active pumps nodes' data ('ID', 'PressureIn', 'PressureOut', 'Efficiency')
            pumps_energy_models_data:
            - All the active pumps nodes' model coefficients ('ID', 'Beta_p', 'Intercept')
            tanks_nodes_data:
            - All the active tank nodes' data ('ID')
            splitter_nodes_data:
            - All the active splitter nodes' data ('ID')
            mixer_nodes_data:
            - All the active mixer nodes' data ('ID')
            process_nodes_data:
            - All the active process nodes' data ('ID', 'ContaminantAdditionQty')
            treatment_nodes_data:
            - All the active treatment nodes' data ('ID', 'ContaminantRemovalPct')
            oil_treatment_nodes_data:
            - All the active oil treatment nodes' data ('ID')
            cooling_tower_nodes_data:
            - All the active cooling tower nodes' data ('ID')
            boiler_nodes_data:
            - All the active boiler nodes' data ('ID')
            initial_nodes_contaminants_data:
            - All the active initial nodes' contaminants data 
            process_nodes_contaminants_data:
            - All the active process nodes' contaminants data 
            treatment_nodes_contaminants_data:
            - All the active treatment nodes' contaminants data 
            arcs_data:
            - All the active arcs' data (Index: ('Node_Start', 'Node_End'), 'MinFlow', 'MaxFlow', 'UsablePercentage, 'OtherCosts', 'HasOil', 'Is_Liquid', 'ConversionFactor')
            splitter_arcs_data:
            - All the active arcs' data that are after an oil splitter node (Index: ('Node_Start', 'Node_End'), 'FixedPercentage')
            oil_treatment_arcs_data:
            - All the active arcs' data that are after an oil treatemnt node (Index: ('Node_Start', 'Node_End'), 'FixedWaterPercentage', 'FixedOilPercentage')
            parameters_data:
            - All the non nodes' or arcs' model's parameters: ['Energy Cost KWh (Dollars)', 'Energy-CO2 Equivalence (Tons)', 'Time periods']
            tanks_flow :
            - All the flow rates for each tank in time t
            evaporation_rates :
            - All the evaporation rates for ponds in time t

        """
        print('    creating class attributes...')
        for key, value in proc_data.items():
            if key != 'parameters_data':
                setattr(self, key, value)

        for key, value in proc_data['parameters_data'].items():
            setattr(self, key, value)