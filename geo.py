import math
import sys

radiansPerDegree = 0.0174532925199433 # round(math.pi / 180, 16)

class Spheroid(object):
	def __init__(self, equatorialRadius, inverseFlattening):
		self.a = equatorialRadius
		self.f = 1 / inverseFlattening if inverseFlattening else 0

		# a = equatorial radius (aka semi-major axis)
		# b = polar radius (aka semi-minor axis)
		# f = flattening = 1 - b/a
		# ee = eccentricity squared = 1 - (b*b)/(a*a) = (1 - b/a)*(1 + b/a) = f*(2 - f)
		# e = eccentricity = sqrt(ee)

		self.b = self.a * (1 - self.f)
		self.ee = self.f * (2 - self.f)
		self.e = math.sqrt(self.ee)

Clarke_1866_Ellipsoid = Spheroid(6_378_206.4, 294.9786982) # https://en.wikipedia.org/wiki/North_American_Datum
GRS_1980_Ellipsoid = Spheroid(6_378_137, 298.257222101) # https://en.wikipedia.org/wiki/Geodetic_Reference_System_1980
WGS_84_Ellipsoid = Spheroid(6_378_137, 298.257223563) # https://en.wikipedia.org/wiki/World_Geodetic_System

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

		if not self.spheroid.f:
			self.p0 *= 2

		self.falseEasting = 0
		self.falseNorthing = 0

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

		if not self.spheroid.f:
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

		if not self.spheroid.f:
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
		if not self.spheroid.f:
			n /= 2

		x -= self.falseEasting
		y -= self.falseNorthing
		y = self.p0 - y

		theta = math.atan2(x, y)
		p = math.hypot(x, y)
		q = (self.C - p*p*n*n/(a*a)) / n

		longitude = self.originLongitude + theta / n / radiansPerDegree
		latitude = math.asin(q / 2)

		if not self.spheroid.f:
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
	return AlbersEllipsoid(-120, 0, 34, 40.5, GRS_1980_Ellipsoid).setFalseNorthing(-4_000_000)

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

		self.n = (s1 + s2) / 2
		self.C = c1*c1 + 2*self.n*s1
		self.p0 = R * math.sqrt(self.C - 2*self.n*s0) / self.n

		self.falseEasting = 0
		self.falseNorthing = 0

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

def csv(v): return ', '.join(map(str, v))
def csv2csv(a, b): return f'({csv(a)}) => ({csv(b)})'

def check(projection, inputValues, expectedOutput, roundDigits=6, inverse=False):
	inputFields = 'lng', 'lat'
	outputFields = 'x', 'y'

	if inverse:
		inputFields, outputFields = outputFields, inputFields
		output = projection.inverse(*inputValues)
	else:
		output = projection.project(*inputValues)

	roundedOutput = [round(o, roundDigits) for o in output]
	result = ('OK',) if roundedOutput == list(expectedOutput) else (
		'FAIL\nExpected', csv2csv(inputValues, expectedOutput))
	print(
		csv2csv(inputFields, outputFields),
		csv2csv(inputValues, roundedOutput), *result, sep=': ')

	return output

def test1(args):
	#
	# Numerical Example from page 291 of "Map Projections"
	#
	spec = -96, 23, 29.5, 45.5
	lnglat = -75, 35
	expected_xy = 0.2952720, 0.2416774

	for projection in (
		AlbersSphere(*spec, 1),
		AlbersEllipsoid(*spec, Spheroid(1, 0)),
	):
		xy = check(projection, lnglat, expected_xy, roundDigits=7)
		check(projection, xy, lnglat, inverse=True)

	#
	# Numerical Example from pages 292-294 of "Map Projections"
	#
	projection = AlbersEllipsoid(*spec, Clarke_1866_Ellipsoid)
	expected_xy = 1_885_472.7, 1_535_925.0

	xy = check(projection, lnglat, expected_xy, roundDigits=1)
	check(projection, xy, lnglat, inverse=True)

	#
	# The following two tests check inverse projection when the latitude is +90 or -90 degrees
	# (when abs(q) should be equal to qlat90).
	#
	lnglat = -120, 90
	xy = projection.project(*lnglat)
	check(projection, xy, lnglat, inverse=True)

	lnglat = -120, -90
	xy = projection.project(*lnglat)
	check(projection, xy, lnglat, inverse=True)

def test2(args):
	#
	# Location of the BLM Field Office in Bishop, CA
	# from http://www.blm.gov/ca/gis/GeodatabasesZIP/admu_v10.gdb.zip
	# (ogrinfo -q -where 'ADMU_NAME="Bishop Field Office"' admu_v10.gdb.zip admu_ofc_pt)
	# The coordinate system used is EPSG:3310 (see http://epsg.io/3310)
	# aka NAD83 / California Albers
	#
	projection = CaliforniaAlbers()

	xy = 140545.134, -71493.1984
	expectedLngLat = -118.410863, 37.362647

	lnglat = check(projection, xy, expectedLngLat, inverse=True)
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
	# https://mappingsupport.com/p2/gissurfer.php?basemap=Open_Street_Map&data=label=on||37.182288,-118.412701^Incorrect+Location||37.362647,-118.410863^Correct+Location
	#
	*spec, R, falseNorthing = (
		projection.originLongitude,
		projection.originLatitude,
		projection.standardParallel1,
		projection.standardParallel2,
		projection.spheroid.a,
		projection.falseNorthing,
	)
	for projection in (
		AlbersEllipsoid(*spec, Spheroid(R, 0)).setFalseNorthing(falseNorthing),
		AlbersSphere(*spec, R).setFalseNorthing(falseNorthing),
	):
		check(projection, xy, expectedLngLat, inverse=True)
#
# https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system#Simplified_formulae
#
def utm_values():
	a = WGS_84_Ellipsoid.a / 1000
	f = WGS_84_Ellipsoid.f
	n = f / (2 - f)
	r = a / (1 + n) * (1 + n**2/4 + n**4/64) # https://en.wikipedia.org/wiki/Earth_radius#Rectifying_radius
	return n, n**2, n**3, 0.9996*r

def ll2utm(args):
	lat, lng = args[:2]
	args[:2] = []

	lat = float(lat)
	lng = float(lng)
	assert -80 <= lat <= 84
	assert -180 < lng < 180

	y0 = 10_000 if lat < 0 else 0
	zone = 60 - -int(lng-180)//6
	lng0 = zone*6 - 183
	lat = lat*radiansPerDegree
	lng = (lng-lng0)*radiansPerDegree

	sin = math.sin
	cos = math.cos
	sinh = math.sinh
	cosh = math.cosh
	atanh = math.atanh

	n, nn, nnn, k = utm_values()
	alpha = n/2 - nn*2/3 + nnn*5/16, nn*13/48 - nnn*3/5, nnn*61/240

	t = 2*math.sqrt(n) / (1 + n)
	t = sinh(atanh(sin(lat)) - t*atanh(t*sin(lat)))
	xi = math.atan2(t, cos(lng))
	eta = atanh(sin(lng) / math.sqrt(1 + t**2))

	northing = y0 + k*(xi + sum(a*sin(2*j*xi)*cosh(2*j*eta) for j, a in enumerate(alpha, start=1)))
	easting = 500 + k*(eta + sum(a*cos(2*j*xi)*sinh(2*j*eta) for j, a in enumerate(alpha, start=1)))

	spec = ',.3f'
	print(zone, format(northing*1000, spec), format(easting*1000, spec))

def utm2ll(args):
	zone, northing, easting = args[:3]
	args[:3] = []

	y0 = 0
	if zone.endswith(('S', 's')):
		y0 = 10_000
		zone = zone[:-1]
	elif zone.endswith(('N', 'n')):
		zone = zone[:-1]
	zone = int(zone)
	assert 1 <= zone <= 60

	northing = float(northing.replace(',', '')) / 1000
	easting = float(easting.replace(',', '')) / 1000

	sin = math.sin
	cos = math.cos
	sinh = math.sinh
	cosh = math.cosh

	n, nn, nnn, k = utm_values()
	beta = n/2 - nn*2/3 + nnn*37/96, nn/48 + nnn/15, nnn*17/480
	delta = n*2 - nn*2/3 - nnn*2, nn*7/3 - nnn*8/5, nnn*56/15

	xi0 = (northing - y0) / k
	eta0 = (easting - 500) / k

	xi = xi0 - sum(b*sin(2*j*xi0)*cosh(2*j*eta0) for j, b in enumerate(beta, start=1))
	eta = eta0 - sum(b*cos(2*j*xi0)*sinh(2*j*eta0) for j, b in enumerate(beta, start=1))

	chi = math.asin(sin(xi) / cosh(eta))
	lat = chi + sum(d*sin(2*j*chi) for j, d in enumerate(delta, start=1))
	lng = math.atan2(sinh(eta), cos(xi))

	lat = round(lat/radiansPerDegree, 6)
	lng = round(lng/radiansPerDegree + zone*6 - 183, 6)

	print(lat, lng)

def main(args):
	cmds = {
		'll2utm': ll2utm,
		'utm2ll': utm2ll,
		'test1': test1,
		'test2': test2,
	}
	def err(args):
		sys.exit(f'Usage: python3 {prog} {"|".join(cmds)} ...')

	prog = args.pop(0)
	while args:
		cmds.get(args.pop(0), err)(args)

if __name__ == '__main__':
	main(sys.argv)
