from collections import OrderedDict, namedtuple
import os
import csv

class ResultManager:
	
	def __init__(self, result, analysis_type, time_step):
		'''During evaluation, keeps running table of node with worst-case result (highest stress/damage)
			During result showing, restores the final result table from file'''
		file_name = analysis_type.stress_state + " " + analysis_type.result_type + " Result " + str(result.Id) + ".csv"
		self.output_file = os.path.join(result.Analysis.WorkingDir, file_name)
		self.time_step = time_step
		self.analysis_type = analysis_type
		if analysis_type.stress_state == "Uniaxial":
			if analysis_type.result_type == "Stress":
				self.running_table = OrderedDict([('Alternating Stress', 0), ('Mean Stress', 0), ('Fully-Reversed Stress', -1)])
			elif analysis_type.result_type == "Cycles to Failure":
				self.running_table = OrderedDict([('Alternating Stress', 0), ('Mean Stress', 0), ('Fully-Reversed Stress', -1), ('Cycles to Failure', 0)])
			elif analysis_type.result_type == "Damage - Constant":
				self.running_table = OrderedDict([('Alternating Stress', 0), ('Mean Stress', 0), ('Fully-Reversed Stress', -1), ('Allowable Stress', 0), 
													('Cycles to Failure', 0), ('Applied Cycles', 0), ('Miner Sum', 0)])
			elif analysis_type.result_type == "Damage - Random":
				self.running_table = [OrderedDict([('Stress Level', 1), ('Alternating Stress', 0), ('Mean Stress', 0), ('Fully-Reversed Stress', -1), 
									('Cycle Percentage', 68.3), ('Applied Cycles', 0), ('Cycles to Failure', 0), ('Damage', 0)]), 
									OrderedDict([('Stress Level', 1), ('Alternating Stress', 0), ('Mean Stress', 0), ('Fully-Reversed Stress', -1), 
									('Cycle Percentage', 27.1), ('Applied Cycles', 0), ('Cycles to Failure', 0), ('Damage', 0)]),
									OrderedDict([('Stress Level', 1), ('Alternating Stress', 0), ('Mean Stress', 0), ('Fully-Reversed Stress', -1), 
									('Cycle Percentage', 4.33), ('Applied Cycles', 0), ('Cycles to Failure', 0), ('Damage', 0)]),
									{'Miner Sum': 0}]
		else:
			self.running_table = [OrderedDict([('Principal Axis', 1), ('Alternating Stress', 0), ('Mean Stress', 0)]), 
									OrderedDict([('Principal Axis', 2), ('Alternating Stress', 0), ('Mean Stress', 0)]),
									OrderedDict([('Principal Axis', 3), ('Alternating Stress', 0), ('Mean Stress', 0)]),
									OrderedDict([('Effective Alternating Stress', 0), ('Effective Mean Stress', 0), ('Fully-Reversed Stress', 0)])]
			if analysis_type.result_type == "Cycles to Failure":
				self.running_table[3].update({'Cycles to Failure': 0})
			elif analysis_type.result_type == "Damage - Constant":
				self.running_table[3].update({'Cycles to Failure': 0})
				self.running_table[3].update({'Applied Cycles': 0})
				self.running_table[3].update({'Miner Sum': 0})
		
	def update_result(self, table):
		'''Compares given node result with stored result and replaces stored result if the given result is worse'''
		if self.analysis_type.stress_state == "Uniaxial":
			if self.analysis_type.result_type != 'Damage - Random':
				if table['Fully-Reversed Stress'] > self.running_table['Fully-Reversed Stress']:
					self.running_table.update(table)
			else:
				if table[3]['Miner Sum'] > self.running_table[3]['Miner Sum']:
					for i in range(4):
						self.running_table[i].update(table[i])
		else:
			if table[3]['Fully-Reversed Stress'] > self.running_table[3]['Fully-Reversed Stress']:
				for i in range(4):
					self.running_table[i].update(table[i])
		
	def store(self):
		'''Prints result table to csv file in the analysis working directory (MECH folder)'''
		def check_duplicate():
			with open(self.output_file, 'r') as file:
				reader = csv.reader(file, dialect=csv.excel, lineterminator='\n')
				for row in reader:
					try:
						if int(row[0]) == self.time_step:
							return True
					except:
						continue
			return False
		def write_multiaxial():
			for i in range(3):
				writer.writerow([self.time_step] + self.running_table[i].values())
			for key, value in self.running_table[3].items():
				writer.writerow([self.time_step, key, " ", value])
		if self.analysis_type.stress_state == "Uniaxial":
			if self.analysis_type.result_type != 'Damage - Random':
				if not os.path.exists(self.output_file):
					with open(self.output_file, 'w') as file:
						writer = csv.writer(file, dialect=csv.excel, lineterminator='\n')
						writer.writerow([self.analysis_type.result_type])
						writer.writerow(['Time Step'] + self.running_table.keys())
						writer.writerow([self.time_step] + self.running_table.values())
				else:
					if not check_duplicate():
						with open(self.output_file, 'a') as file:
							writer = csv.writer(file, dialect=csv.excel, lineterminator='\n')
							writer.writerow([self.time_step] + self.running_table.values())
			else:
				with open(self.output_file, 'w') as file:
					writer = csv.writer(file, dialect=csv.excel, lineterminator='\n')
					writer.writerow([self.analysis_type.result_type])
					writer.writerow(self.running_table[0].keys())
					for i in range(3):
						writer.writerow(self.running_table[i].values())
					writer.writerow(['Miner Sum', self.running_table[3]['Miner Sum']])
		else:
			if not os.path.exists(self.output_file):
				with open(self.output_file, 'w') as file:
					writer = csv.writer(file, dialect=csv.excel, lineterminator='\n')
					writer.writerow([self.analysis_type.result_type])
					writer.writerow(['Time Step'] + self.running_table[0].keys())
					write_multiaxial()
			else:
				if not check_duplicate():
					with open(self.output_file, 'a') as file:
						writer = csv.writer(file, dialect=csv.excel, lineterminator='\n')
						writer.writerow([self.time_step] + self.running_table.values())
						write_multiaxial()
				
				