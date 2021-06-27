###########################################################################################################################
# This script provides the functions for performing uniaxial and multiaxial fatigue analysis
#
# This file contains 1 class, 3 global variables, 1 global constant, and 10 functions
# 
# Author: Ryan O'Connor
# Date: July 2018
###########################################################################################################################


# Imports

from collections import namedtuple
from itertools import permutations
from datetime import datetime
from materials import GetMaterialPropertyByName
from units import ConvertUnit
from MiscFunctions import *
from FileManagement import *

# Global variables

context = ExtAPI.Context
if context == "Mechanical":
	'''This dictionary maps the midside nodes of all quadratic elements to their connected corner nodes'''
	link = {}
	# Quadratic brick
	link.Add(ElementTypeEnum.kHex20,{ 8:[0,1], 9:[1,2], 10:[2,3], 11:[3,0], 12:[4,5], 13:[5,6], 14:[6,7], 15:[7,4], 16:[0,4], 17:[1,5], 18:[2,6], 19:[3,7]})
	# Quadratic pyramid
	link.Add(ElementTypeEnum.kPyramid13,{ 5:[0,1], 6:[1,2], 7:[2,3], 8:[3,0], 9:[0,4], 10:[1,4], 11:[2,4], 12:[3,4]})
	# Quadratic quadrilateral
	link.Add(ElementTypeEnum.kQuad8, { 4:[0,1], 5:[1,2], 6:[2,3], 7:[3,0]})
	# Quadratic tetrahedral
	link.Add(ElementTypeEnum.kTet10,{ 4:[0,1], 5:[1,2], 6:[2,0], 7:[0,3], 8:[1,3], 9:[2,3]})
	# Quadratic triangle
	link.Add(ElementTypeEnum.kTri6, { 3:[0,1], 4:[1,2], 5:[2,0]})
	# Quadratic wedge
	link.Add(ElementTypeEnum.kWedge15,{6:[0,1], 7:[1,2], 8:[2,0], 9:[3,4], 10:[4,5], 11:[5,3], 12:[0,3], 13:[1,4], 14:[2,5]})
	
	
# Callback Functions
# These functions are directly called by the XML document.	They delegate functions 
# to the controllers or manipulate the GUI.
	
def Create_Uniaxial_Stress_Result(analysis):
	analysis.CreateResultObject("Uniaxial Stress")

def Create_Uniaxial_Life_Result(analysis):
	analysis.CreateResultObject("Uniaxial Life")

def Create_Multiaxial_Stress_Result(analysis):
	analysis.CreateResultObject("Multiaxial Stress")

def Create_Multiaxial_Life_Result(analysis):
	analysis.CreateResultObject("Multiaxial Life")
	
def uniaxial_stress_eval(result, stepInfo, collector):
	result.Controller.evaluate_uniaxial_stress(result, stepInfo, collector)
	
def uniaxial_life_eval(result, stepInfo, collector):
	result.Controller.evaluate_uniaxial_life(result, stepInfo, collector)
	
def multiaxial_stress_eval(result, stepInfo, collector):
	result.Controller.evaluate_multiaxial_stress(result, stepInfo, collector)
	
def multiaxial_life_eval(result, stepInfo, collector):
	result.Controller.evaluate_multiaxial_life(result, stepInfo, collector)
		
def change_time_hist(result, property):
	'''Toggles whether the time history is calculated'''
	if property.Value == "Yes":
		result.CalculateTimeHistory = True
	else:
		result.CalculateTimeHistory = False
		
def establish_stress_properties(result):
	'''Changes result properties depending on the analysis system'''
	if str(result.Analysis.AnalysisType) == 'Static':
		if result.Name.split(" ")[0] == "Uniaxial":
			result.Properties["Stress Component"].Options.Add("Maximum Principal Stress")
			result.Properties["Stress Component"].Options.Add("Middle Principal Stress")
			result.Properties["Stress Component"].Options.Add("Minimum Principal Stress")
			result.Properties["Scale Factor"].Visible = False
		result.Properties["Load History"].Properties["Load History"].Options.Add("Half-Reversed")		
	else:
		result.Properties["Stress Component"].ReadOnly = True
		if str(result.Analysis.AnalysisType) == 'Spectrum':		
			result.Properties["Scale Factor"].Visible = True
			result.Properties["Load History"].Properties["Load History"].Options.Add("Half-Reversed")
		elif str(result.Analysis.AnalysisType) == 'Harmonic':
			result.Properties["Scale Factor"].Visible = False
			result.Properties["Load History"].Properties["Load History"].ReadOnly = True
	result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Time"].Visible = False
	result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Value"].Visible = False
		
def change_load_history(result, property):
	'''Changes result properties depending on the analysis system'''
	if property.Value == "Yes":
		if str(result.Analysis.AnalysisType) == 'Static':
			result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Time"].Visible = True
			result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Value"].Visible = False
		else:
			result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Time"].Visible = False
			result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Value"].Visible = True
	else:
		result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Time"].Visible = False
		result.Properties["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Value"].Visible = False
		
def establish_life_properties(result):
	'''Changes result properties depending on the analysis system'''
	establish_stress_properties(result)
	if result.Name.split(" ")[0] == "Uniaxial":
		result.Properties['Life Measure'].Properties['Life Measure'].Properties["Number of Cycles"].Visible = False
		result.Properties['Life Measure'].Properties['Life Measure'].Properties["Vibration Test"].Visible = False
		
def change_life_properties(result, property):
	'''Changes result properties depending on the analysis system'''
	if property.Value == "Miner Sum":
		if str(result.Analysis.AnalysisType) == 'Static':
			result.Properties['Life Measure'].Properties['Life Measure'].Properties["Number of Cycles"].Visible = True
			result.Properties['Life Measure'].Properties['Life Measure'].Properties["Vibration Test"].Visible = False
		else:
			result.Properties['Life Measure'].Properties['Life Measure'].Properties["Number of Cycles"].Visible = False
			result.Properties['Life Measure'].Properties['Life Measure'].Properties["Vibration Test"].Visible = True
	else:
		result.Properties['Life Measure'].Properties['Life Measure'].Properties["Number of Cycles"].Visible = False
		result.Properties['Life Measure'].Properties['Life Measure'].Properties["Vibration Test"].Visible = False


# Fatigue Analysis Classes

AnalysisType = namedtuple('AnalysisType', ['analysis', 'stress_state', 'output', 'selection', 'load_history', 'prestress', 'notched', 'result_type'])
	
class UniaxialStressLife:

	### FatigueAnalysis Section 1: Initialization methods
		
	def __init__(self, api, result):
		pass
		
	def reinit(self, result, collector, eval_time):
		'''Reinitializes instance variables for each time step evaluated'''
		self.result = result
		self.analysis = result.Analysis
		self.mesh = self.analysis.MeshData
		self.geo_data = self.analysis.GeoData
		self.stress_conv_factor = self.get_stress_conv_factor()
		propGeo = self.result.Properties["Geometry"]
		self.ref_ids = propGeo.Value.Ids
		self.input = self.get_input()
		if self.analysis_type.analysis == "Static":
			self.eval_element_stresses = self.get_element_values(collector, eval_time, "S")
			if self.analysis_type.prestress == "Yes":
				self.prestress_element_stresses = self.get_element_values(collector, self.input["Prestress Time"], "S")
		elif self.analysis_type.analysis == "Spectrum":
			self.eval_element_stresses = self.get_element_values(collector, 2, "SPSD")
		elif self.analysis_type.analysis == "Harmonic":
			self.eval_element_stresses = self.get_element_values(collector, eval_time, "S")
			
	def get_input(self):
		'''Extracts all user input from the result properties'''
		rp = self.result.Properties
		k_temperature = rp["Material"].Properties["Temperature Factor"].Value
		dict = {"Temperature Factor": k_temperature}
		if self.analysis_type.stress_state == "Uniaxial":
			stress_comp = rp["Stress Component"].Value
			mean_stress_theory = rp["Mean Stress Theory"].Properties["Mean Stress Theory"].Value
			if self.analysis_type.notched == "Notched":
				Kt = rp["Material"].Properties["Notch"].Properties["Stress Concentration Factor"].Value
				notch_sensitivity_correlation = rp["Material"].Properties["Notch"].Properties["Notch Sensitivity Correlation"].Value
				r = rp["Material"].Properties["Notch"].Properties["Notch Radius"].Value
				dict.update({"Kt": Kt, "Notch Sensitivity Correlation": notch_sensitivity_correlation, "Notch Radius": r})
			dict.update({"Stress Component": stress_comp, "Mean Stress Theory": mean_stress_theory})
		if self.analysis_type.result_type != "Stress":
			k_scatter_stress = rp["Material"].Properties["Scatter Factor Stress"].Value
			k_scatter_life = rp["Material"].Properties["Scatter Factor Life"].Value
			k_misc = rp["Material"].Properties["Miscellaneous Factor"].Value
			dict.update({"Scatter Factor (Stress)": k_scatter_stress, "Scatter Factor (Life)": k_scatter_life, 
					"Miscellaneous Factor": k_misc})
		if self.analysis_type.notched == "Notched" and self.analysis_type.result_type.split(" ")[0] == "Damage":
			cycle_sensitivity_correlation = rp["Material"].Properties["Notch"].Properties["Cycle Sensitivity Correlation"].Value
			dict.update({"Cycle Sensitivity Correlation": cycle_sensitivity_correlation})
		if self.analysis_type.analysis == "Static":
			if self.analysis_type.prestress == "Yes":
				prestress_time = rp["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress Time"].Value
				dict.update({"Prestress Time": prestress_time})
			if self.analysis_type.result_type == "Damage - Constant":
				cycles = rp["Life Measure"].Properties["Life Measure"].Properties["Number of Cycles"].Value
				dict.update({"Cycles": cycles})
		else:
			if rp["Load History"].Properties["Load History"].Properties["Prestress Select"].Value == "Yes":
				prestress = rp["Load History"].Properties["Load History"].Properties["Prestress Select"].Properties["Prestress"].Value
			else:
				prestress = 0.
			dict.update({"Prestress": prestress})
			if self.analysis_type.result_type.split(" ")[0] == "Damage":
				length_of_test = rp["Life Measure"].Properties["Life Measure"].Properties["Vibration Test"].Properties["Length of Test"].Value
				expected_freq = rp["Life Measure"].Properties["Life Measure"].Properties["Vibration Test"].Properties["Expected Frequency"].Value
				test_cycles = length_of_test * expected_freq * 3600 
				dict.update({"Cycles": test_cycles})
			if self.analysis_type.analysis == "Spectrum":
				scale_factor = float(rp["Scale Factor"].Value[0])
				dict.update({"Scale Factor": scale_factor})
		return dict
		
	def get_analysis_type(self, result, stepInfo, stress_state, output):
		'''Collects all properties related to analysis/result type definition for use in later functions.  
			Creates result manager.'''
		rp = result.Properties
		analysis = str(result.Analysis.AnalysisType)
		if analysis != "Spectrum":
			eval_time = stepInfo.Set
		else:
			eval_time = 2
		load_history = rp["Load History"].Properties["Load History"].Value
		prestress = rp["Load History"].Properties["Load History"].Properties["Prestress Select"].Value
		notched = rp["Material"].Properties["Notch"].Value
		if output == "Life":
			life_measure = rp["Life Measure"].Properties["Life Measure"].Value
			if life_measure == "Miner Sum":
				if analysis == "Spectrum":
					result_type = "Damage - Random"
				else:
					result_type = "Damage - Constant"
			else:
				result_type = "Cycles to Failure"
		else:
			result_type = "Stress"
		# Determine selection type by attempting to access material
		ref_id = result.Properties["Geometry"].Value.Ids[0]
		try: result.Analysis.GeoData.GeoEntityById(ref_id).Part.Bodies[0].Material
		except AttributeError: selection = "Node"
		else: selection = "Geometric Entity"
		finally: self.analysis_type = AnalysisType(analysis, stress_state, output, selection, load_history, prestress, notched, result_type)
		self.result_manager = ResultManager(result, self.analysis_type, eval_time)
		
	def get_element_values(self, collector, time, result_name):
		'''Collects all element corner node stresses into dictionary for a given time step'''
		element_values = {}
		element_ids = set()		# Collect all unique element ids in a set
		for node_id in collector.Ids:
			connected_element_ids = self.mesh.NodeById(node_id).ConnectedElementIds
			element_ids.update(id for id in connected_element_ids)
		if self.analysis_type.analysis == "Harmonic":
			reader = self.analysis.GetResultsData()
			reader.CurrentResultSet = time	# Real result set
			stress = reader.GetResult(result_name)
			for element_id in element_ids:
				element_value = stress.GetElementValues(element_id)
				element_values.update({element_id: [element_value]})
			reader = self.analysis.GetResultsData()
			reader.CurrentResultSet = time + 1	# Imaginary result set
			stress = reader.GetResult(result_name)
			for element_id in element_ids:
				element_value = stress.GetElementValues(element_id)
				element_values[element_id].Add(element_value)
		else:
			reader = self.analysis.GetResultsData()
			reader.CurrentResultSet = time
			stress = reader.GetResult(result_name)
			for element_id in element_ids:
				element_value = stress.GetElementValues(element_id)
				element_values.update({element_id: element_value})
		return element_values
		
	def get_stress_conv_factor(self):
		'''Gets the conversion factor from the current unit system to SI units'''
		reader = self.analysis.GetResultsData()
		reader.CurrentResultSet = 1
		stress = reader.GetResult("S")
		unit_stress = stress.GetComponentInfo('X').Unit
		return ConvertUnit(1., unit_stress, "Pa", "Stress") 
		
	### FatigueAnalysis Section 2: These methods define different result evaluations
	
	def evaluate_uniaxial_stress(self, result, stepInfo, collector):
		'''Defines stress evaluation function and passes it to general evaluate function'''
		def uniaxial_stress_function(mat_props, eval_node_tensor=None, prestress_node_tensor=None, eval_stress=None):
			if self.analysis_type.analysis == "Static" or self.analysis_type.analysis == "Harmonic":
				fully_reversed_stress, alternating_stress, mean_stress = self.get_uniaxial_fully_reversed_stress(mat_props, eval_node_tensor, prestress_node_tensor)
			elif self.analysis_type.analysis == "Spectrum":
				fully_reversed_stress, alternating_stress, mean_stress = self.get_uniaxial_fully_reversed_stress(mat_props, eval_stress=eval_stress)
				scale = self.input["Scale Factor"]
				fully_reversed_stress *= scale
				alternating_stress *= scale
			result_table = {"Alternating Stress": alternating_stress, 'Mean Stress': mean_stress, 'Fully-Reversed Stress': fully_reversed_stress}
			self.result_manager.update_result(result_table)
			return fully_reversed_stress * self.stress_conv_factor
		self.get_analysis_type(result, stepInfo, stress_state="Uniaxial", output="Stress")
		self.evaluate(result, stepInfo, collector, uniaxial_stress_function)
		
	def evaluate_uniaxial_life(self, result, stepInfo, collector):
		'''Defines life evaluation function and passes it to general evaluate function'''
		def uniaxial_life_function(mat_props, eval_node_tensor=None, prestress_node_tensor=None, eval_stress=None):
			if self.analysis_type.analysis == "Static" or self.analysis_type.analysis == "Harmonic":
				fully_reversed_stress, alternating_stress, mean_stress = self.get_uniaxial_fully_reversed_stress(mat_props, eval_node_tensor, prestress_node_tensor)
				cycles_to_failure = self.get_cycles_to_failure(mat_props, fully_reversed_stress * self.stress_conv_factor)
				if self.analysis_type.result_type == "Damage - Constant":
					cycles = self.input["Cycles"]
					allowable_stress = self.get_allowable_stress(mat_props, cycles) / self.stress_conv_factor
					result = cycles / cycles_to_failure
					result_table = {'Applied Cycles': cycles, 'Cycles to Failure': cycles_to_failure, 'Miner Sum': result, 'Allowable Stress': allowable_stress,
									'Alternating Stress': alternating_stress, 'Mean Stress': mean_stress, 'Fully-Reversed Stress': fully_reversed_stress}
				else:
					result = cycles_to_failure
					result_table = {'Cycles to Failure': result, 'Alternating Stress': alternating_stress, 'Mean Stress': mean_stress, 
									'Fully-Reversed Stress': fully_reversed_stress}
			elif self.analysis_type.analysis == "Spectrum":
				if self.analysis_type.result_type == "Damage - Random":
					reversed_stress1, alt_stress1, mean_stress1 = self.get_uniaxial_fully_reversed_stress(mat_props, eval_stress=eval_stress)
					reversed_stress2, alt_stress2, mean_stress2 = self.get_uniaxial_fully_reversed_stress(mat_props, eval_stress=2*eval_stress)
					reversed_stress3, alt_stress3, mean_stress3 = self.get_uniaxial_fully_reversed_stress(mat_props, eval_stress=3*eval_stress)
					cycles_to_failure1 = self.get_cycles_to_failure(mat_props, reversed_stress1 * self.stress_conv_factor)
					cycles_to_failure2 = self.get_cycles_to_failure(mat_props, reversed_stress2 * self.stress_conv_factor)
					cycles_to_failure3 = self.get_cycles_to_failure(mat_props, reversed_stress3 * self.stress_conv_factor)
					total_test_cycles = self.input["Cycles"]
					cycles1 = total_test_cycles * 0.683
					cycles2 = total_test_cycles * 0.271
					cycles3 = total_test_cycles * 0.0433
					damage1 = cycles1 / cycles_to_failure1
					damage2 = cycles2 / cycles_to_failure2
					damage3 = cycles3 / cycles_to_failure3
					result = damage1 + damage2 + damage3
					result_table = [{'Stress Level': 1, 'Alternating Stress': alt_stress1, 'Mean Stress': mean_stress1, 'Fully-Reversed Stress': reversed_stress1, 
									'Cycle Percentage': 68.3, 'Applied Cycles': cycles1, 'Cycles to Failure': cycles_to_failure1, 'Damage': damage1},
									{'Stress Level': 2, 'Alternating Stress': alt_stress2, 'Mean Stress': mean_stress2, 'Fully-Reversed Stress': reversed_stress2, 
									'Cycle Percentage': 27.1, 'Applied Cycles': cycles2, 'Cycles to Failure': cycles_to_failure2, 'Damage': damage2}, 
									{'Stress Level': 3, 'Alternating Stress': alt_stress3, 'Mean Stress': mean_stress3, 'Fully-Reversed Stress': reversed_stress3, 
									'Cycle Percentage': 4.33, 'Applied Cycles': cycles3, 'Cycles to Failure': cycles_to_failure3, 'Damage': damage3}, 
									{'Miner Sum': result}]
				else:
					fully_reversed_stress, alternating_stress, mean_stress = self.get_uniaxial_fully_reversed_stress(mat_props, eval_stress=eval_stress)
					scale = self.input["Scale Factor"]
					fully_reversed_stress *= scale
					alternating_stress *= scale
					mean_stress *= scale
					result = self.get_cycles_to_failure(mat_props, fully_reversed_stress * self.stress_conv_factor)
					result_table = {'Cycles to Failure': result, 'Alternating Stress': alternating_stress, 'Mean Stress': mean_stress, 
									'Fully-Reversed Stress': fully_reversed_stress}
			self.result_manager.update_result(result_table)
			return result
		self.get_analysis_type(result, stepInfo, stress_state="Uniaxial", output="Life")
		self.evaluate(result, stepInfo, collector, uniaxial_life_function)	
		
	def evaluate(self, result, stepInfo, collector, func):
		'''General evaluation function for all result types.  The particular result is defined by the "func" passed to it.'''
		eval_time = stepInfo.Set
		ExtAPI.Log.WriteMessage("Reinitializing variables for step "+str(eval_time)+"..."+str(datetime.time(datetime.now())))
		self.reinit(result, collector, eval_time)
		ExtAPI.Log.WriteMessage("Evaluating stresses..."+str(datetime.time(datetime.now())))
		# Extract all node ids and materal properties
		ref_data = {}
		for ref_id in self.ref_ids:
			mat_props = self.get_material_props(ref_id)
			if self.analysis_type.selection == "Geometric Entity":
				node_ids = self.mesh.MeshRegionById(ref_id).NodeIds
			else:
				node_ids = [ref_id]
			ref_data.update({ref_id: [mat_props, node_ids]})
		# Determine average stresses at each node
		eval_node_stresses = self.get_average_node_stresses(self.eval_element_stresses, ref_data)
		if self.analysis_type.analysis == "Static" and self.analysis_type.prestress == "Yes":
			prestress_node_stresses = self.get_average_node_stresses(self.prestress_element_stresses, ref_data)
		# Loop through all nodes and calculate result, then set corresponding node value in collector.
		for mat_props, node_ids in ref_data.values():	
			for node_id in node_ids:
				eval_node_stress = eval_node_stresses[node_id]
				if self.analysis_type.prestress == "Yes":
					prestress_node_stress = prestress_node_stresses[node_id]
					node_result = func(mat_props, eval_node_stress, prestress_node_stress)
				else:
					if self.analysis_type.analysis == "Spectrum":
						node_result = func(mat_props, eval_stress=eval_node_stress)
					else:
						node_result = func(mat_props, eval_node_stress)
				collector.SetValues(node_id, [node_result])
		ExtAPI.Log.WriteMessage("Finished evaluation..."+str(datetime.time(datetime.now())))
		self.result_manager.store()
	
	def get_average_node_stresses(self, element_stresses, ref_data):
		'''Creates dictionary of average stresses at every node.  Performs stress averaging across corner nodes, then 
			interpolates the averaged corner node stresses at the midside nodes.'''
		def stress_init():
			if self.analysis_type.analysis == "Spectrum":
				return 0.
			else:
				return [0., 0., 0., 0., 0., 0.]
		global link
		# Loop across all nodes.  If it's a corner node, determine the average stresses across all connected elements.	
		# If it's a midside node, determine the ids of the connected corner nodes. cnid = "Corner node id".
		node_stress_avg_map, midside_cnid_map = {}, {}
		for _, node_ids in ref_data.values():
			for node_id in node_ids:
				element_ids = self.mesh.NodeById(node_id).ConnectedElementIds
				node_stress = stress_init()
				for element_id in element_ids:
					element = self.mesh.ElementById(element_id)
					cpt = element.NodeIds.IndexOf(node_id)
					if cpt < element.CornerNodeIds.Count:	# Corner node
						element_stress = element_stresses[element_id]
						if self.analysis_type.analysis == "Spectrum":
							node_stress += element_stress[cpt]
						else:
							if self.analysis_type.analysis == "Static":
								for i in range(6):
									node_stress[i] += element_stress[6*cpt+i]
							if self.analysis_type.analysis == "Harmonic":
								for i in range(6):
									node_stress[i] += copysign(sqrt(element_stress[0][6*cpt+i]**2 + element_stress[1][6*cpt+i]**2), element_stress[1][6*cpt+i])
					else:	# Midside node
						itoadd = link[element.Type][cpt]
						cnids = [element.NodeIds[itoadd[0]], element.NodeIds[itoadd[1]]]
						midside_cnid_map.update({node_id: cnids})
						break
				else:
					if self.analysis_type.analysis == "Spectrum":
						node_stress /= element_ids.Count
					else:
						for i in range(6):
							node_stress[i] /= element_ids.Count
					node_stress_avg_map.update({node_id: node_stress})
		# Loop through all the midside nodes and compute their average stresses using the averaged stresses at the corner nodes.
		for midside_node_id, corner_node_ids in midside_cnid_map.items():
			node_stress = stress_init()
			for cnid in corner_node_ids:
				if self.analysis_type.analysis == "Spectrum":
					node_stress += node_stress_avg_map[cnid] / 2
				else:
					for i in range(6):
						node_stress[i] += node_stress_avg_map[cnid][i] / 2
			node_stress_avg_map.update({midside_node_id: node_stress})
		return node_stress_avg_map
		
	### FatigueAnalysis Section 3: Material property lookups
		
	def get_material_props(self, ref_id):
#		'''Extract all required material properties for given geometry reference id.
#			Inner functions help break up the work.'''
		def get_stress_prop(material, property):
			property_list = GetMaterialPropertyByName(material, property)
			property = property_list[property][1]
			return property
		def get_SN_data(material):
			k_scatter_stress = self.input["Scatter Factor (Stress)"]
			k_scatter_life = self.input["Scatter Factor (Life)"]
			k_temperature = self.input["Temperature Factor"]
			k_misc = self.input["Miscellaneous Factor"]
			SN = GetMaterialPropertyByName(material, 'Alternating Stress')
			if "R-Ratio" in SN:
				Rdata = SN['R-Ratio'][1:]
				Sdata = SN['Alternating Stress'][1:]
				Ndata = SN['Cycles'][1:]
				# Throw out all but R=-1 data
				Sdata = [s for r, s in zip(Rdata, Sdata) if r==-1]
				Ndata = [n for r, n in zip(Rdata, Ndata) if r==-1]
			elif "Mean Stress" in SN:
				Smdata = SN['Mean Stress'][1:]
				Sdata = SN['Alternating Stress'][1:]
				Ndata = SN['Cycles'][1:]
				# Throw out all but Sm=0 data
				Sdata = [s for sm, s in zip(Smdata, Sdata) if sm==0]
				Ndata = [n for sm, n in zip(Smdata, Ndata) if sm==0]
			Sdata = [k_scatter_stress * k_temperature * k_misc * s for s in Sdata]
			Ndata = [n / k_scatter_life for n in Ndata]
			return Sdata, Ndata
		def get_notch_sensitivity(Ftu):
			unit_sys = str(ExtAPI.DataModel.Project.UnitSystem)
			length_conv_factor = SI_length_factor(unit_sys)
			r = self.input["Notch Radius"] * length_conv_factor * 25.4 / 1000 # Convert to inches
			if self.input["Notch Sensitivity Correlation"] == "Steel (Peterson)":
				a = -2.58e-9*Ftu**3 + 1.62e-6*Ftu**2 - 3.55e-4*Ftu + 2.89e-2
			else:
				a = .020
			q = 1 / (1 + a / r)
			if self.analysis_type.result_type.split(" ")[0] == "Damage":
				if self.input["Cycle Sensitivity Correlation"] == "None":
					qp = 1
				else:
					if self.input["Cycle Sensitivity Correlation"] == "Steel (Juvinall)":
						juvinall_factor = -5.08e-6*Ftu**2 + 4.65e-3*Ftu - .212
					else: # Aluminum (Juvinall)
						juvinall_factor = -4.57e-5*Ftu**2 + 1.4e-2*Ftu - .212	
					cycles = self.input["Cycles"]
					if cycles >= 10^6:
						qp = 1.0
					elif cycles <= 10^3:
						qp = juvinall_factor
					else:
						# Log-log interpolate between 10^6 and 10^3
						m = log10(1/juvinall_factor) / 3
						qp = juvinall_factor*(cycles/10**3)**m
				q *= qp
			mat_props.update({"Notch Sensitivity": q})
		# Create material property dictionary and extract material from reference id
		mat_props = {}
		if self.analysis_type.selection == "Geometric Entity":
			material = self.geo_data.GeoEntityById(ref_id).Part.Bodies[0].Material
		else:
			body_id = self.mesh.NodeById(ref_id).BodyIds[0]
			material = self.geo_data.GeoEntityById(body_id).Material
		# Extract properties of material
		k_temperature = self.input["Temperature Factor"]
		Ftu = k_temperature * get_stress_prop(material, "Tensile Ultimate Strength") / 6894760	# Convert to ksi
		if self.analysis_type.notched == "Notched":
			get_notch_sensitivity(Ftu)
		Ftu /= (self.stress_conv_factor / 6894760)
		mat_props.update({"Ftu": Ftu})
		if self.analysis_type.output == "Life":
			Fty = k_temperature * get_stress_prop(material, "Tensile Yield Strength") / self.stress_conv_factor
			Sdata, Ndata = get_SN_data(material)
			mat_props.update({"Fty": Fty, "Sdata": Sdata, "Ndata": Ndata})
		return mat_props
		
	def get_cycles_to_failure(self, mat_props, fully_reversed_stress):
		'''Calculates life from fully-reversed stress.'''
		Sdata = mat_props["Sdata"]
		Ndata = mat_props["Ndata"]
		if fully_reversed_stress >= max(Sdata):
			return min(Ndata)
		elif fully_reversed_stress <= min(Sdata):
			return max(Ndata)
		else:
			# Find interpolating index
			index = max(i for i, s in enumerate(Sdata) if s > fully_reversed_stress)
			# Log-log interpolate between the two data points
			m = log10(Sdata[index+1]/Sdata[index]) / log10(Ndata[index+1]/Ndata[index])
			return Ndata[index]*(fully_reversed_stress/Sdata[index])**(1/m)
				
	def get_allowable_stress(self, mat_props, N):
		'''Calculates allowable fully-reversed stress for given number of cycles N.'''
		Sdata = mat_props["Sdata"]
		Ndata = mat_props["Ndata"]
		if N >= max(Ndata):
			return min(Sdata)
		elif N <= min(Ndata):
			return max(Sdata)
		else:
			# Find interpolating index	
			index = max(i for i, n in enumerate(Ndata) if n < N)
			# Log-log interpolate between the two data points
			m = log10(Sdata[index+1]/Sdata[index]) / log10(Ndata[index+1]/Ndata[index])
			return Sdata[index]*(N/Ndata[index])**m
			
	### FatigueAnalysis Section 4: Uniaxial stress calculations
	
	def get_uniaxial_fully_reversed_stress(self, mat_props, eval_node_tensor=None, prestress_node_tensor=None, eval_stress=None):
		'''Calculates fully-reversed stress prestressd on given tensor or stress.'''
		if eval_stress is None:
			sa, sm = self.get_uniaxial_alt_mean_stress(eval_node_tensor, prestress_node_tensor)
		else:
			sa, sm = self.get_uniaxial_alt_mean_stress(eval_stress=eval_stress)
		if self.analysis_type.notched == "Notched":
			Kt = self.input["Kt"]
			q = mat_props["Notch Sensitivity"]
			Kf = 1 + q*(Kt-1)
			sa *= Kf / Kt
			sm *= 1 / Kt
		sfr = self.get_fully_reversed_stress(mat_props, sa, sm)
		return sfr, sa, sm
		
	def get_uniaxial_alt_mean_stress(self, eval_node_tensor=None, prestress_node_tensor=None, eval_stress=None):
		'''Calculates alternating and mean stress prestressd on given tensors or stresses along with load history.'''
		if eval_stress is None:
			eval_principal_stresses = get_principal_stresses(eval_node_tensor)
			eval_stress = get_stress_component(self.input["Stress Component"], eval_principal_stresses)
		if prestress_node_tensor is not None:	# For static analyses
			prestress_principal_stresses = get_principal_stresses(prestress_node_tensor)
			prestress_stress = get_stress_component(self.input["Stress Component"], prestress_principal_stresses)
		else:
			prestress_stress = 0
		max_stress = eval_stress	
		if self.analysis_type.load_history == "Fully-Reversed":
			if self.analysis_type.analysis == "Static":
				min_stress = 2 * prestress_stress - eval_stress
			else:
				min_stress = 2 * self.input["Prestress"] - eval_stress
		elif self.analysis_type.load_history == "Half-Reversed":
			if self.analysis_type.analysis == "Static":
				min_stress = prestress_stress
			else:
				min_stress = self.input["Prestress"]
		sa = abs(max_stress - min_stress) / 2.
		sm = (max_stress + min_stress) / 2.
		return sa, sm
		
	def get_fully_reversed_stress(self, mat_props, sa, sm):
		'''Calculates fully-reversed stress given alternating and mean stress using 
			selected mean stress theory.'''
		theory = self.input["Mean Stress Theory"]
		if theory == "Smith-Watson-Topper":
			if sa*(sm+sa) > 0.:
				return sqrt(sa*(sm+sa))
			else:
				return 0.
		else:
			Ftu = mat_props["Ftu"]
			if theory == "Modified Goodman":
				if sm > 0.0:
					return sa/(1-sm/Ftu)
				else:
					return sa
			elif theory == "Modified Goodman (Extrapolated)":
				return sa/(1-sm/Ftu)
			elif theory == "Gerber":
				return sa/(1-(sm/Ftu)**2)
		
		
class MultiaxialEquivalentStressLife(UniaxialStressLife):

	def get_input(self):
		'''Multiaxial analysis collects additional user input'''
		dict = UniaxialStressLife.get_input(self)
		rp = self.result.Properties
		multiaxial_theory = rp["Multiaxial Stress Theory"].Properties["Multiaxial Stress Theory"].Value
		dict.update({"Multiaxial Stress Theory": multiaxial_theory})
		if multiaxial_theory == "Equivalent Stress (Sines)":
			sines_constant_select = rp["Multiaxial Stress Theory"].Properties["Multiaxial Stress Theory"].Properties["Sines Constant"].Value
			if sines_constant_select == "User Input":
				sines_constant = sines_constant_select = rp["Multiaxial Stress Theory"].Properties["Multiaxial Stress Theory"].Properties["Sines Constant"].Properties["Sines Constant"].Value
			else:
				sines_constant = float(sines_constant_select.split("=")[-1].split(")")[0])
			dict.update({"Sines Constant": sines_constant})
		else:
			mean_stress_theory = rp["Multiaxial Stress Theory"].Properties["Multiaxial Stress Theory"].Properties["Mean Stress Theory"].Value
			dict.update({"Mean Stress Theory": mean_stress_theory})
		if self.analysis_type.notched == "Notched":
			Kt1 = rp["Material"].Properties["Notch"].Properties["Kt - Maximum Principal Stress"].Value
			Kt2 = rp["Material"].Properties["Notch"].Properties["Kt - Middle Principal Stress"].Value
			Kt3 = rp["Material"].Properties["Notch"].Properties["Kt - Minimum Principal Stress"].Value
			q_correlation = rp["Material"].Properties["Notch"].Properties["Notch Sensitivity Correlation"].Value
			r = rp["Material"].Properties["Notch"].Properties["Notch Radius"].Value
			dict.update({"Kt1": Kt1, "Kt2": Kt2, "Kt3": Kt3, "Notch Sensitivity Correlation": q_correlation, "Notch Radius": r})
		return dict

	def evaluate_multiaxial_stress(self, result, stepInfo, collector):
		'''Defines multiaxial stress evaluation function and passes it to general evaluate function'''
		def multiaxial_stress_function(mat_props, eval_node_tensor, prestress_node_tensor=None):
			fully_reversed_stress, _, _, result_table = self.get_multiaxial_fully_reversed_stress(mat_props, eval_node_tensor, prestress_node_tensor)
			self.result_manager.update_result(result_table)
			return fully_reversed_stress * self.stress_conv_factor
		self.get_analysis_type(result, stepInfo, stress_state="Multiaxial", output="Stress")
		self.evaluate(result, stepInfo, collector, multiaxial_stress_function)
	
	def evaluate_multiaxial_life(self, result, stepInfo, collector):
		'''Defines multiaxial life evaluation function and passes it to general evaluate function'''
		def multiaxial_life_function(mat_props, eval_node_tensor, prestress_node_tensor=None):
			fully_reversed_stress, alternating_stress, mean_stress, result_table = self.get_multiaxial_fully_reversed_stress(mat_props, eval_node_tensor, prestress_node_tensor)
			cycles_to_failure = self.get_cycles_to_failure(mat_props, fully_reversed_stress * self.stress_conv_factor)
			result_table[3].update({'Cycles to Failure': cycles_to_failure})
			if self.analysis_type.result_type == "Damage - Constant":
				cycles = self.input["Cycles"]
				result = cycles / cycles_to_failure
				result_table[3].update({'Applied Cycles': cycles, 'Miner Sum': result})
			else:
				result = cycles_to_failure
			self.result_manager.update_result(result_table)
			return result
		self.get_analysis_type(result, stepInfo, stress_state="Multiaxial", output="Life")
		self.evaluate(result, stepInfo, collector, multiaxial_life_function)		
			
	def get_multiaxial_fully_reversed_stress(self, mat_props, eval_node_tensor, prestress_node_tensor=None):
		'''Calculates fully-reversed stress prestressd on given node tensors using selected multiaxial stress theory'''
		theory = self.input["Multiaxial Stress Theory"]
		s1a, s2a, s3a, s1m, s2m, s3m = self.get_multiaxial_alt_mean_stress(mat_props, eval_node_tensor, prestress_node_tensor)
		alt_stress = get_von_mises([s1a, s2a, s3a])
		if theory == "Equivalent Stress (Sines)":
			mean_stress = s1m + s2m + s3m
			a = self.input["Sines Constant"]
			reversed_stress = alt_stress + a * mean_stress
		elif theory == "Equivalent Stress (Hydrostatic Mean)":	
			mean_stress = s1m + s2m + s3m
			reversed_stress = self.get_fully_reversed_stress(mat_props, alt_stress, mean_stress)
		elif theory == "Equivalent Stress (Signed Von-Mises Mean)":	
			mean_stress = get_von_mises([s1m, s2m, s3m])
			reversed_stress = self.get_fully_reversed_stress(mat_props, alt_stress, mean_stress)
		result_table = [{'Alternating Stress': s1a, 'Mean Stress': s1m}, {'Alternating Stress': s2a, 'Mean Stress': s2m}, 
				{'Alternating Stress': s3a, 'Mean Stress': s3m}, {'Effective Alternating Stress': alt_stress, 
				'Effective Mean Stress': mean_stress, 'Fully-Reversed Stress': reversed_stress}]
		return reversed_stress, alt_stress, mean_stress, result_table
	
	def get_multiaxial_alt_mean_stress(self, mat_props, eval_node_tensor, prestress_node_tensor=None):
		'''Calculates alternating and mean stresses for each principal axis'''
		eval_principal_stresses = get_principal_stresses(eval_node_tensor)
		if prestress_node_tensor is not None:
			prestress_principal_stresses = get_principal_stresses(prestress_node_tensor)
			# Match up prestress principal stresses with eval principal stresses by determining 
			# which pairing of axes most closely gives proportional loading (eval_stress = Constant * prestress_stress).
			min_standard_deviation = 1e100
			for e0, e1, e2 in permutations((0, 1, 2)):
				c0 = eval_principal_stresses[0] / prestress_principal_stresses[e0]
				c1 = eval_principal_stresses[1] / prestress_principal_stresses[e1]
				c2 = eval_principal_stresses[2] / prestress_principal_stresses[e2]
				standard_deviation = stdev([c0, c1, c2])
				if standard_deviation < min_standard_deviation:
					min_standard_deviation = standard_deviation
					proportional_prestress_axes = (e0, e1, e2)
			e0, e1, e2 = proportional_prestress_axes
		s1max = eval_principal_stresses[0]
		s2max = eval_principal_stresses[1]
		s3max = eval_principal_stresses[2]
		if self.analysis_type.load_history == "Fully-Reversed":
			if self.analysis_type.prestress == "Yes":				
				s1min = 2 * prestress_principal_stresses[e0] - s1max
				s2min = 2 * prestress_principal_stresses[e1] - s2max
				s3min = 2 * prestress_principal_stresses[e2] - s3max
			else:
				s1min, s2min, s3min = -s1max, -s2max, -s3max
		elif self.analysis_type.load_history == "Half-Reversed":
			if self.analysis_type.prestress == "Yes": 
				s1min = prestress_principal_stresses[e0]
				s2min = prestress_principal_stresses[e1]
				s3min = prestress_principal_stresses[e2]
			else:
				s1min, s2min, s3min = 0, 0, 0
		s1a = (s1max - s1min) / 2
		s2a = (s2max - s2min) / 2
		s3a = (s3max - s3min) / 2
		s1m = (s1max + s1min) / 2
		s2m = (s2max + s2min) / 2
		s3m = (s3max + s3min) / 2
		if self.analysis_type.notched == "Notched":
			Kt1, Kt2, Kt3 = self.input["Kt1"], self.input["Kt2"], self.input["Kt3"]
			q = mat_props["Notch Sensitivity"]
			Kf1 = 1 + q*(Kt1-1)
			Kf2 = 1 + q*(Kt2-1)
			Kf3 = 1 + q*(Kt3-1)
			s1a *= Kf1 / Kt1
			s2a *= Kf2 / Kt2
			s3a *= Kf3 / Kt3
			s1m /= Kt1
			s2m /= Kt2
			s3m /= Kt3
		return s1a, s2a, s3a, s1m, s2m, s3m