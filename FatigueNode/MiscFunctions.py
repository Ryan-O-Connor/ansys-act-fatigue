from math import acos, cos, sqrt, pi, copysign
	
	
def get_von_mises(principal_stresses):
	'''Computes Von-Mises stress'''
	s1 = principal_stresses[0]
	s2 = principal_stresses[1]
	s3 = principal_stresses[2]
	return sqrt(((s1-s2)**2 + (s1-s3)**2 + (s2-s3)**2)/2)

def get_stress_component(stress_component, principal_stresses):
	'''Computes stress component from reverse-sorted list of principal stresses'''
	if stress_component == "Von-Mises Stress (Signed)":
		von_mises_stress = get_von_mises(principal_stresses)
		if abs(principal_stresses[0]) < abs(principal_stresses[2]):
			von_mises_stress *= -1
		return von_mises_stress
	elif stress_component == "Maximum Principal Stress":
		return principal_stresses[0]
	elif stress_component == "Middle Principal Stress":
		return principal_stresses[1]
	elif stress_component == "Minimum Principal Stress":
		return principal_stresses[2]
		

def get_principal_stresses(tensor):
	'''Computes eigenvalues of a symmetric tensor using cubic polynomial trigonometric solution formula
		and returns in reverse-sorted order'''
	EP = 1e-4
	a = tensor[0]
	b = tensor[1]
	c = tensor[2]
	d = tensor[3]
	e = tensor[5]
	f = tensor[4]
	if abs(d) > EP or abs(e) > EP or abs(f) > EP:
		# Solve cubic equation using trigonometric formula
		A = -(a+b+c)
		B = a*b+a*c+b*c-d*d-e*e-f*f
		C = d*d*c+f*f*a+e*e*b-2*d*e*f-a*b*c
		Q = (3*B-A**2)/9
		R = (9*A*B-27*C-2*A**3)/54
		phi = acos(R/sqrt(-(Q**3)))
		s1 = 2*sqrt(-Q)*cos(phi/3)-A/3
		s2 = 2*sqrt(-Q)*cos(phi/3 + 2*pi/3)-A/3
		s3 = 2*sqrt(-Q)*cos(phi/3 + 4*pi/3)-A/3
		eigs = [s1, s2, s3]
	else:
		eigs = [a, b, c]
	return sorted(eigs, reverse=True)

		
def SI_length_factor(unit_sys):
	'''Supplies conversion factor from SI MKS unit system'''
	if unit_sys == "StandardMKS": # meters
		return 1
	elif unit_sys == "StandardCGS": # cm
		return 100
	elif unit_sys in ("StandardNMM", "StandardNMMton", "StandardNMMdat") : # mm
		return 1000
	elif unit_sys == "StandardUMKS": # um
		return 1000000
	elif unit_sys == "StandardBFT": # feet
		return 1000 / 25.4 / 12
	elif unit_sys == "StandardBIN": # inches
		return 1000 / 25.4

		
def mean(list):
	'''Calculates mean of a list of numerical values'''
	return sum(list) / len(list)
	
	
def stdev(list):
	'''Calculates standard deviation of a list of numerical values'''
	u = mean(list)
	n = len(list)
	variance = 0
	for x in list:
		variance += (x-u)**2
	return sqrt(variance / n)