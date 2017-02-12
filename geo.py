#!/usr/bin/python
import math

radiansPerDegree = 0.0174532925199433 # round(math.pi / 180.0, 16)

class Spheroid(object):
	def __init__(self, equatorialRadius, inverseFlattening):
		self.a = equatorialRadius

		if inverseFlattening == 0 or inverseFlattening is None:
			self.f = 0.0
		else:
			self.f = 1.0 / inverseFlattening

		# a = equatorial radius (aka semi-major axis)
		# b = polar radius (aka semi-minor axis)
		# f = flattening = 1 - b/a
		# ee = eccentricity squared = 1 - (b*b)/(a*a) = (1 - b/a)*(1 + b/a) = f*(2 - f)
		# e = eccentricity = sqrt(ee)

		self.b = self.a * (1 - self.f)
		self.ee = self.f * (2 - self.f)
		self.e = math.sqrt(self.ee)

Clarke_1866_Ellipsoid = Spheroid(6378206.4, 294.9786982) # See https://en.wikipedia.org/wiki/North_American_Datum
GRS_1980_Ellipsoid = Spheroid(6378137.0, 298.257222101) # See https://en.wikipedia.org/wiki/GRS_80
WGS_84_Ellipsoid = Spheroid(6378137.0, 298.257223563) # See https://en.wikipedia.org/wiki/World_Geodetic_System

class AlbersEllipsoid(object):
	#
	# Formulas according to pages 101-102 of "Map Projections - A Working Manual"
	# by John P. Snyder, 1987 (U.S. Geological Survey Professional Paper 1395)
	# (Chapter 14. Albers Equal-Area Conic Projection - Formulas for the Ellipsoid)
	# Available at https://pubs.er.usgs.gov/publication/pp1395
	#
	def __init__(self, lng0, lat0, lat1, lat2, spheroid):
		self.originLatitude = lat0
		self.originLongitude = lng0
		self.standardParallel1 = lat1
		self.standardParallel2 = lat2
		self.spheroid = spheroid

		m0, q0 = self.genMQ(lat0)
		m1, q1 = self.genMQ(lat1)
		m2, q2 = self.genMQ(lat2)

		self.n = (m1*m1 - m2*m2) / (q2 - q1)
		self.C = m1*m1 + self.n*q1
		self.p0 = self.spheroid.a * math.sqrt(self.C - self.n*q0) / self.n

		if self.spheroid.f == 0:
			self.p0 *= 2

		self.falseEasting = 0.0
		self.falseNorthing = 0.0

	def setFalseEasting(self, falseEasting):
		self.falseEasting = falseEasting
		return self

	def setFalseNorthing(self, falseNorthing):
		self.falseNorthing = falseNorthing
		return self

	def genMQ(self, latitude):
		latitude *= radiansPerDegree
		sinlat = math.sin(latitude)
		coslat = math.cos(latitude)

		if self.spheroid.f == 0:
			return coslat, sinlat

		e = self.spheroid.e
		ee = self.spheroid.ee
		es = e * sinlat
		eess = 1 - ee * sinlat * sinlat

		m = coslat / math.sqrt(eess)
		q = (1 - ee) * (sinlat / eess - math.log((1 - es) / (1 + es)) / (2*e))

		return m, q

	def project(self, longitude, latitude):
		m, q = self.genMQ(latitude)

		theta = self.n * (longitude - self.originLongitude) * radiansPerDegree
		p = self.spheroid.a * math.sqrt(self.C - self.n*q) / self.n

		if self.spheroid.f == 0:
			theta /= 2
			p *= 2

		x = p * math.sin(theta)
		y = self.p0 - p * math.cos(theta)

		return x + self.falseEasting, y + self.falseNorthing

	def inverse(self, x, y):
		a = self.spheroid.a
		e = self.spheroid.e
		ee = self.spheroid.ee
		n = self.n
		if self.spheroid.f == 0:
			n /= 2

		x -= self.falseEasting
		y -= self.falseNorthing
		y = self.p0 - y

		theta = math.atan2(x, y)
		p = math.hypot(x, y)
		q = (self.C - p*p*n*n/(a*a)) / n

		longitude = self.originLongitude + theta / n / radiansPerDegree
		latitude = math.asin(q / 2.0)

		if self.spheroid.f == 0:
			return longitude, latitude / radiansPerDegree

		qlat90 = 1 - (1 - ee)/(2*e) * math.log((1 - e) / (1 + e))

		if round(abs(q), 12) == round(qlat90, 12):
			return longitude, math.copysign(90, q)

		while True:
			sinlat = math.sin(latitude)
			es = e * sinlat
			eess = 1 - ee * sinlat * sinlat

			d1 = eess * eess / (2 * math.cos(latitude))
			d2 = q / (1 - ee) - sinlat / eess + math.log((1 - es) / (1 + es)) / (2*e)

			delta = d1 * d2
			latitude += delta

			if abs(delta / radiansPerDegree) < 1e-8:
				break

		return longitude, latitude / radiansPerDegree

def CaliforniaAlbers():
	return AlbersEllipsoid(-120.0, 0.0, 34.0, 40.5, GRS_1980_Ellipsoid).setFalseNorthing(-4000000.0)

class AlbersSphere(object):
	#
	# This should be mathematically identical to using AlbersEllipsoid with an
	# unflattened spheroid, i.e. with Spheroid(R, 0). The equations used in this
	# class are the simpler "Formulas for the Sphere" from pages 100-101 of
	# Snyder's "Map Projections - A Working Manual".
	#
	def __init__(self, lng0, lat0, lat1, lat2, R):
		self.originLatitude = lat0
		self.originLongitude = lng0
		self.standardParallel1 = lat1
		self.standardParallel2 = lat2
		self.R = R

		s0 = math.sin(lat0 * radiansPerDegree)
		s1 = math.sin(lat1 * radiansPerDegree)
		s2 = math.sin(lat2 * radiansPerDegree)
		c1 = math.cos(lat1 * radiansPerDegree)

		self.n = (s1 + s2) / 2.0
		self.C = c1*c1 + 2*self.n*s1
		self.p0 = R * math.sqrt(self.C - 2*self.n*s0) / self.n

		self.falseEasting = 0.0
		self.falseNorthing = 0.0

	def setFalseEasting(self, falseEasting):
		self.falseEasting = falseEasting
		return self

	def setFalseNorthing(self, falseNorthing):
		self.falseNorthing = falseNorthing
		return self

	def project(self, longitude, latitude):
		s = math.sin(latitude * radiansPerDegree)

		theta = self.n * (longitude - self.originLongitude) * radiansPerDegree
		p = self.R * math.sqrt(self.C - 2*self.n*s) / self.n

		x = p * math.sin(theta)
		y = self.p0 - p * math.cos(theta)

		return x + self.falseEasting, y + self.falseNorthing

	def inverse(self, x, y):
		x -= self.falseEasting
		y -= self.falseNorthing
		y = self.p0 - y
		n = self.n

		theta = math.atan2(x, y)
		p = math.hypot(x, y)
		pnR = p * n / self.R

		longitude = self.originLongitude + theta / n / radiansPerDegree
		latitude = math.asin((self.C - pnR*pnR) / (2*n))

		return longitude, latitude / radiansPerDegree

def check(projection, input, expectedOutput, roundDigits=4, inverse=False):
	inputFields = ('longitude', 'latitude')
	outputFields = ('x', 'y')

	if inverse:
		inputFields, outputFields = outputFields, inputFields
		output = projection.inverse(*input)
	else:
		output = projection.project(*input)

	print '({}, {}) => ({}, {})'.format(*(inputFields + outputFields))

	roundedOutput = [round(o, roundDigits) for o in output]
	expected = all([o == e for o, e in zip(roundedOutput, expectedOutput)])

	print '\t({}, {}) => ({}, {})'.format(input[0], input[1], roundedOutput[0], roundedOutput[1]),

	if expected:
		print u'\u2713'
	else:
		print u'\u2717'
		print '\tExpected:'
		print '\t({}, {}) => ({}, {})'.format(input[0], input[1], expectedOutput[0], expectedOutput[1])

	return output

def test1():
	#
	# Numerical Example from page 291 of "Map Projections"
	#
	lnglat = (-75, 35)
	xy = (0.2952720, 0.2416774)

	projection = AlbersSphere(-96.0, 23.0, 29.5, 45.5, 1)
	output = check(projection, lnglat, xy, roundDigits=7)
	check(projection, output, lnglat, roundDigits=0, inverse=True)

	projection = AlbersEllipsoid(-96.0, 23.0, 29.5, 45.5, Spheroid(1, 0))
	output = check(projection, lnglat, xy, roundDigits=7)
	check(projection, output, lnglat, roundDigits=0, inverse=True)

	#
	# Numerical Example from page 292 of "Map Projections"
	#
	projection = AlbersEllipsoid(-96.0, 23.0, 29.5, 45.5, Clarke_1866_Ellipsoid)

	lnglat = (-75, 35)
	xy = (1885472.7, 1535925.0)
	xy = check(projection, lnglat, xy, roundDigits=1)
	check(projection, xy, lnglat, roundDigits=0, inverse=True)

	#
	# The following two tests check inverse projection when the latitude is +90 or -90 degrees
	# (when abs(q) should be equal to qlat90).
	#
	lnglat = (-120.0, 90.0)
	xy = projection.project(*lnglat)
	check(projection, xy, lnglat, inverse=True)

	lnglat = (-120.0, -90.0)
	xy = projection.project(*lnglat)
	check(projection, xy, lnglat, inverse=True)

def test2():
	#
	# Location of the BLM Field Office in Bishop, CA
	# from http://www.blm.gov/ca/gis/GeodatabasesZIP/admu_v10.gdb.zip
	# (ogrinfo -q -where 'ADMU_NAME="Bishop Field Office"' admu_v10.gdb.zip admu_ofc_pt)
	# The coordinate system used is EPSG:3310 (see http://epsg.io/3310)
	# aka NAD83 / California Albers
	#
	projection = CaliforniaAlbers()

	xy = (140545.134, -71493.1984)
	expectedLngLat = (-118.410863, 37.362647)

	lnglat = check(projection, xy, expectedLngLat, roundDigits=6, inverse=True)
	check(projection, lnglat, xy)

	#
	# The following two tests are expected to fail with identical results.
	#
	# The first test uses the AlbersEllipsoid class, while the second uses AlbersSphere,
	# but they both do the same thing. They inverse project the x and y coordinates of
	# the Bishop Field Office back to longitude and latitude using the Albers projection
	# for a sphere.
	#
	# Since the original projection used the GRS 1980 ellipsoid, the location resulting
	# from the inverse projection here is some 12.5 miles away from the correct location:
	#
	# https://mappingsupport.com/p/gmap4.php?t=h&z=11&label=on&markers=37.182288,-118.412701%5EIncorrect%20Location||37.362647,-118.410863%5ECorrect%20Location
	#
	R = GRS_1980_Ellipsoid.a # Equatorial Radius of the Earth

	projection = AlbersEllipsoid(-120.0, 0.0, 34.0, 40.5, Spheroid(R, 0)).setFalseNorthing(-4000000.0)
	check(projection, xy, expectedLngLat, roundDigits=6, inverse=True)

	projection = AlbersSphere(-120.0, 0.0, 34.0, 40.5, R).setFalseNorthing(-4000000.0)
	check(projection, xy, expectedLngLat, roundDigits=6, inverse=True)

if __name__ == '__main__':
	test1()
	test2()
