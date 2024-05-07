# -*- coding: utf-8 -*-
"""
useful_sets.py
====================================
Auxiliar class to help storing model sets

@author:
     - c.maldonado
     - g.munera.gonzalez
"""

class UsefulSets:
    """The goal is to make the model's creation easier. It stores some sets.
    """    
    def __init__(self, sets) -> None:
        """UsefulSets Initializer

        Parameters
        ----------
        sets : dict
            Dictionary of sets. Has all the sets needed to run the model. We have the following keys on the dict
                nodes : Set(string)
                    All active model's nodes
                initial_nodes : Set(string)
                    All active initial model's nodes
                ending_nodes : Set(string)
                    All active ending model's nodes
                pumps_nodes : Set(string)
                    All active model's pumps
                pump_nodes_linear_regression : Set(string)
                    All active model's pumps that theirs electricity consumption is calculated via a linear regression
                pumps_nodes_fixed_effiency : Set(string)
                    All active model's pumps that theirs electricity consumption is calculated via fixed effiency
                tank_nodes : Set(string)
                    All active model's tanks
                process_nodes : Set(string)
                    All active process model's nodes
                treatment_nodes : Set(string)
                    All active treatment model's nodes
                oil_treatment_nodes : Set(string)
                    All active oil treatment model's nodes
                splitter_nodes : Set(string)
                    All active splitter model's nodes
                mixer_nodes : Set(string)
                    All active mixer model's nodes
                cooling_tower_nodes : Set(string)
                    All active cooling tower model's nodes
                boiler_nodes : Set(string)
                    All active boiler model's nodes
                oil_nodes : Set(string)
                    All active nodes that can store oil
                contaminants : Set(string)
                    All active model's contaminants
                arcs : Set((string, string))
                    All active model's arcs 
                fixed_oil_splitter_arcs : Set((string, string))
                    All active model's arcs that are after a splitter oil node
                fixed_oil_treatment_arcs : Set((string, string))
                    All active model's arcs that are after a treatment oil node
                oil_arcs : Set(string)
                    All active arcs that can have oil inside.
                flag_arcs : Set(string)
                    All active arcs that will be use to calculate recirculation
                entry : Dictionary(string, set(string))
                    Given a node_1, it returns all the node_2 that are connected via an arc (node_1, node_2)
                exits : Dictionary(string, set(string))
                    Given a node_2, it returns all the node_3 that are connected via an arc (node_2, node_3)
                time_projection : Set (int)
                    Given the number of time periods to run the model
        """

        for key, value in sets.items():
            setattr(self, key, value)