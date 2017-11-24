#!/usr/bin/python
import math
import struct

def readInt(f):
	return struct.unpack("<i", f.read(4))[0]
def readFloat(f):
	return struct.unpack("<f", f.read(4))[0]

class Grid(object):
	def __init__(self, region, margin):
		self.region = region
		self.margin = margin
		self.read()

	def readHeader(self, f):
		identLen = 56
		ident = "vertCON{}.94".format(self.region)
		ident += " " * (identLen - len(ident))

		assert f.read(identLen) == ident
		assert f.read(8) == "vertc2.0"

		self.numLng = readInt(f)
		self.numLat = readInt(f)
		numZ = readInt(f)

#		print "{}: numLng = {}, numLat = {}, numZ = {}".format(self.region,
#			self.numLng, self.numLat, numZ)

		self.minLng = readFloat(f)
		self.deltaLng = readFloat(f)
		self.minLat = readFloat(f)
		self.deltaLat = readFloat(f)

		self.minLng += 360
		self.maxLng = self.minLng + self.deltaLng * (self.numLng - 1)
		self.maxLat = self.minLat + self.deltaLat * (self.numLat - 1)

		assert 3 <= self.numLng <= 461
		assert 3 <= self.numLat

#		print "{}: latitude from {} to {}".format(self.region,
#			self.minLat, round(self.maxLat, 2))
#		print "{}: longitude from {} to {}".format(self.region,
#			self.minLng - 360, round(self.maxLng - 360, 2))

	def read(self):
		fileName = "data/vertcon/vertcon{}.94".format(self.region)
		f = open(fileName, "rb")

		self.readHeader(f)
		recordLen = 4 + self.numLng * 4
		unpackFormat = "<" + "f" * self.numLng

		f.seek(recordLen)
		self.data = [struct.unpack_from(unpackFormat, f.read(recordLen), 4)
			for n in xrange(self.numLat)]
		f.close()

	def interpolate(self, lat, lng):
		xgrid = (lng - self.minLng) / self.deltaLng
		ygrid = (lat - self.minLat) / self.deltaLat

		irow = int(ygrid)
		jcol = int(xgrid)

		z = self.data[irow]
		t1, t3 = z[jcol], z[jcol + 1]
		if t1 == 9999.0 or t3 == 9999.0:
			return None

		z = self.data[irow + 1]
		t2, t4 = z[jcol], z[jcol + 1]
		if t2 == 9999.0 or t4 == 9999.0:
			return None

		a = t1
		b = t3 - t1
		c = t2 - t1
		d = t4 - t3 - t2 + t1

		row = ygrid - float(irow)
		col = xgrid - float(jcol)

		return a + b*col + c*row + d*col*row

class Vertcon(object):
	def __init__(self):
		self.grids = [Grid("w", 5.0), Grid("c", 5.0), Grid("e", 0.0)]

	def interpolate(self, lat, lng):
		for grid in self.grids:
			if (grid.minLat <= lat <= grid.maxLat and
				grid.minLng <= lng <= (grid.maxLng - grid.margin)):
				return grid.interpolate(lat, lng)
		return None

	def getShift(self, lat, lng):
		n = self.interpolate(lat, lng + 360)
		if n is not None:
			# The Fortran code does the following:
			# n *= 0.001
			# n = int(math.copysign(1.0, n) * (abs(n) + 0.0005) * 1000.0)
			# n *= 0.001

			n = int(round(n)) * 0.001

		return n

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("latitude", nargs="?", default=37.561394, type=float)
	parser.add_argument("longitude", nargs="?", default=-118.858424, type=float)
	args = parser.parse_args()

	assert -90 <= args.latitude <= 90
	assert -180 <= args.longitude <= 180

	print Vertcon().getShift(args.latitude, args.longitude)

if __name__ == "__main__":
	main()
