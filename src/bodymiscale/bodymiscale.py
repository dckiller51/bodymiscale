import datetime, time
import logging
from math import floor

__namemybodymiscale__ = "bodymiscale"
class bodymiscale:
	def __init__(self, weight, height, age, gender, impedance):
		self._weight = weight
		self._height = height
		self._age = age
		self._gender = gender
		self._impedance = impedance

		# Check for potential out of boundaries
		if self.height > 220:
			raise Exception("Height is too high (limit: >220cm)")
		elif weight < 10 or weight > 200:
			raise Exception("Weight is either too low or too high (limits: <10kg and >200kg)")
		elif age > 99:
			raise Exception("Age is too high (limit >99 years)")
		elif impedance > 3000:
			raise Exception("Impedance is too high (limit >3000ohm)")

	# Set the value to a boundary if it overflows
	def checkValueOverflow(self, value, minimum, maximum):
		if value < minimum:
			return minimum
		elif value > maximum:
			return maximum
		else:
			return value

	# Get LBM coefficient (with impedance)
	def getLBMCoefficient(self):
		lbm =  (self._height * 9.058 / 100) * (self._height / 100)
		lbm += self._weight * 0.32 + 12.226
		lbm -= self._impedance * 0.0068
		lbm -= self._age * 0.0542
		return lbm

	# Get BMR
	def getBMR(self):
		if self._gender == 'female':
			bmr = 864.6 + self._weight * 10.2036
			bmr -= self._height * 0.39336
			bmr -= self._age * 6.204
		else:
			bmr = 877.8 + self._weight * 14.916
			bmr -= self._height * 0.726
			bmr -= self._age * 8.976

		# Capping
		#if self._gender == 'female' and bmr > 2996:
		#	bmr = 5000
		#elif self._gender == 'male' and bmr > 2322:
		#	bmr = 5000
		return self._checkValueOverflow(bmr, 500, 10000)

	# Get BMR scale
	def getBMRScale(self):
		coefficients = {
			'female': {12: 34, 15: 29, 17: 24, 29: 22, 50: 20, 120: 19},
			'male': {12: 36, 15: 30, 17: 26, 29: 23, 50: 21, 120: 20}
		}

		for age, coefficient in coefficients[self._gender].items():
			if self._age < age:
				return [self._weight * coefficient]
				break

	# Get fat percentage
	def getFatPercentage(self):
		# Set a constant to remove from LBM
		if self._gender == 'female' and self._age <= 49:
			const = 9.25
		elif self._gender == 'female' and self._age > 49:
			const = 7.25
		else:
			const = 0.8

		# Calculate body fat percentage
		LBM = self._getLBMCoefficient()

		if self._gender == 'male' and self._weight < 61:
			coefficient = 0.98
		elif self._gender == 'female' and self._weight > 60:
			coefficient = 0.96
			if self._height > 160:
				coefficient *= 1.03
		elif self._gender == 'female' and self._weight < 50:
			coefficient = 1.02
			if self._height > 160:
				coefficient *= 1.03
		else:
			coefficient = 1.0
		fatPercentage = (1.0 - (((LBM - const) * coefficient) / self._weight)) * 100

		# Capping body fat percentage
		if fatPercentage > 63:
			fatPercentage = 75
		return self._checkValueOverflow(fatPercentage, 5, 75)

	# Get fat percentage scale
	def getFatPercentageScale(self):
		# The included tables where quite strange, maybe bogus, replaced them with better ones...
		scales = [
			{'min': 0, 'max': 20, 'female': [18, 23, 30, 35], 'male': [8, 14, 21, 25]},
			{'min': 21, 'max': 25, 'female': [19, 24, 30, 35], 'male': [10, 15, 22, 26]},
			{'min': 26, 'max': 30, 'female': [20, 25, 31, 36], 'male': [11, 16, 21, 27]},
			{'min': 31, 'max': 35, 'female': [21, 26, 33, 36], 'male': [13, 17, 25, 28]},
			{'min': 36, 'max': 40, 'female': [22, 27, 34, 37], 'male': [15, 20, 26, 29]},
			{'min': 41, 'max': 45, 'female': [23, 28, 35, 38], 'male': [16, 22, 27, 30]},
			{'min': 46, 'max': 50, 'female': [24, 30, 36, 38], 'male': [17, 23, 29, 31]},
			{'min': 51, 'max': 55, 'female': [26, 31, 36, 39], 'male': [19, 25, 30, 33]},
			{'min': 56, 'max': 100, 'female': [27, 32, 37, 40], 'male': [21, 26, 31, 34]},
		]

		for scale in scales:
			if self._age >= scale['min'] and self._age <= scale['max']:
				return scale[self._gender]

	# Get water percentage
	def getWaterPercentage(self):
		waterPercentage = (100 - self._getFatPercentage()) * 0.7

		if (waterPercentage <= 50):
			coefficient = 1.02
		else:
			coefficient = 0.98

		# Capping water percentage
		if waterPercentage * coefficient >= 65:
			waterPercentage = 75
		return self._checkValueOverflow(waterPercentage * coefficient, 35, 75)

	# Get water percentage scale
	def getWaterPercentageScale(self):
		return [53, 67]

	# Get bone mass
	def getBoneMass(self):
		if self._gender == 'female':
			base = 0.245691014
		else:
			base = 0.18016894

		boneMass = (base - (self._getLBMCoefficient() * 0.05158)) * -1

		if boneMass > 2.2:
			boneMass += 0.1
		else:
			boneMass -= 0.1

		# Capping boneMass
		if self._gender == 'female' and boneMass > 5.1:
			boneMass = 8
		elif self._gender == 'male' and boneMass > 5.2:
			boneMass = 8
		return self._checkValueOverflow(boneMass, 0.5 , 8)

	# Get bone mass scale
	def getBoneMassScale(self):
		scales = [
			{'female': {'min': 60, 'optimal': 2.5}, 'male': {'min': 75, 'optimal': 3.2}},
			{'female': {'min': 45, 'optimal': 2.2}, 'male': {'min': 69, 'optimal': 2.9}},
			{'female': {'min': 0, 'optimal': 1.8}, 'male': {'min': 0, 'optimal': 2.5}}
		]

		for scale in scales:
			if self._weight >= scale[self._gender]['min']:
				return [scale[self._gender]['optimal']-1, scale[self._gender]['optimal']+1]

	# Get muscle mass
	def getMuscleMass(self):
		muscleMass = self._weight - ((self._getFatPercentage() * 0.01) * self._weight) - self._getBoneMass()

		# Capping muscle mass
		if self._gender == 'female' and muscleMass >= 84:
			muscleMass = 120
		elif self._gender == 'male' and muscleMass >= 93.5:
			muscleMass = 120

		return self._checkValueOverflow(muscleMass, 10 ,120)

	# Get muscle mass scale
	def getMuscleMassScale(self):
		scales = [
			{'min': 170, 'female': [36.5, 42.5], 'male': [49.5, 59.4]},
			{'min': 160, 'female': [32.9, 37.5], 'male': [44.0, 52.4]},
			{'min': 0, 'female': [29.1, 34.7], 'male': [38.5, 46.5]}
		]

		for scale in scales:
			if self._height >= scale['min']:
				return scale[self._gender]

	# Get Visceral Fat
	def getVisceralFat(self):
		if self._gender == 'female':
			if self._weight > (13 - (self._height * 0.5)) * -1:
				subsubcalc = ((self._height * 1.45) + (self._height * 0.1158) * self._height) - 120
				subcalc = self._weight * 500 / subsubcalc
				vfal = (subcalc - 6) + (self._age * 0.07)
			else:
				subcalc = 0.691 + (self._height * -0.0024) + (self._height * -0.0024)
				vfal = (((self._height * 0.027) - (subcalc * self._weight)) * -1) + (self._age * 0.07) - self._age
		else:
			if self._height < self._weight * 1.6:
				subcalc = ((self._height * 0.4) - (self._height * (self._height * 0.0826))) * -1
				vfal = ((self._weight * 305) / (subcalc + 48)) - 2.9 + (self._age * 0.15)
			else:
				subcalc = 0.765 + self._height * -0.0015
				vfal = (((self._height * 0.143) - (self._weight * subcalc)) * -1) + (self._age * 0.15) - 5.0

		return self._checkValueOverflow(vfal, 1 ,50)

	# Get visceral fat scale
	def getVisceralFatScale(self):
		return [10, 15]

	# Get BMI
	def getBMI(self):
		return self._checkValueOverflow(self._weight/((self._height/100)*(self._height/100)), 10, 90)

	# Get BMI scale
	def getBMIScale(self):
		# Replaced library's version by mi fit scale, it seems better
		return [18.5, 25, 28, 32]

	# Get ideal weight (just doing a reverse BMI, should be something better)
	def getIdealWeight(self):
		return self._checkValueOverflow((22*self._height)*self._height/10000, 5.5, 198)

	# Get ideal weight scale (BMI scale converted to weights)
	def getIdealWeightScale(self):
		scale = []
		for bmiScale in self._getBMIScale():
			scale.append((bmiScale*self._height)*self._height/10000)
		return scale

	# Get fat mass to ideal (guessing mi fit formula)
	def getFatMassToIdeal(self):
		mass = (self._weight * (self._getFatPercentage() / 100)) - (self._weight * (self._getFatPercentageScale()[2] / 100))
		return mass

	# Get protetin percentage (warn: guessed formula)
	def getProteinPercentage(self):
		proteinPercentage = 100 - (floor(self._getFatPercentage() * 100) / 100)
		proteinPercentage -= floor(self._getWaterPercentage() * 100) / 100
		proteinPercentage -= floor((self._getBoneMass()/self._weight*100) * 100) / 100
		return proteinPercentage

	# Get protein scale (hardcoded in mi fit)
	def getProteinPercentageScale(self):
		return [16, 20]

	# Get body type (out of nine possible)
	def getBodyType(self):
		if self._getFatPercentage() > self._getFatPercentageScale()[2]:
			factor = 0
		elif self._getFatPercentage() < self._getFatPercentageScale()[1]:
			factor = 2
		else:
			factor = 1

		if self._getMuscleMass() > self._getMuscleMassScale()[1]:
			return self._getBodyTypeScale()[2 + (factor * 3)]
		elif self._getMuscleMass() < self._getMuscleMassScale()[0]:
			return self._getBodyTypeScale()[(factor * 3)]
		else:
			return self._getBodyTypeScale()[1 + (factor * 3)]

	# Return body type scale
	def getBodyTypeScale(self):
		return ['Obèse', 'Surpoids', 'Trapu', 'Manque d\'exercice', 'Equilibré', 'Equilibré musclé', 'Maigre', 'Equilibré maigre', 'Maigre musclé']

	def getImcLabel(self):
		imc = self._getBMI()
		if imc <18.5:
			return 'Maigreur'
		elif imc >= 18.5 and imc <25:
			return 'Corpulence Normale'
		elif imc >= 25 and imc <27:
			return 'Léger surpoids'
		elif imc >= 27 and imc <30:
			return 'Surpoids'
		elif imc >= 30 and imc <35:
			return 'Obésité modérée'
		elif imc >= 35 and imc <40:
			return 'Obésité sévère'
		elif imc >= 40:
			return 'Obésité massive'