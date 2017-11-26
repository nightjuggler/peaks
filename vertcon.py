#!/usr/bin/python
import struct

class Grid(object):
	def __init__(self, region, margin):
		self.region = region
		self.margin = margin
		self.data = None
		self.readHeader()

	def __del__(self):
		if self.data is None:
			self.dataFile.close()

	def __str__(self):
		return ("Grid(region={}, margin={}, numLng={}, numLat={}, "
			"minLng={}, maxLng={}, minLat={}, maxLat={})".format(
			self.region, self.margin,
			self.numLng, self.numLat,
			self.minLng, round(self.maxLng, 2),
			self.minLat, round(self.maxLat, 2)))

	def readHeader(self):
		fileName = "data/vertcon/vertcon{}.94".format(self.region)
		self.dataFile = f = open(fileName, "rb")

		ident = "vertCON{}.94".format(self.region)
		ident += " " * (56 - len(ident))
		ident += "vertc2.0"

		assert f.read(64) == ident

		(self.numLng, self.numLat, numZ,
			self.minLng, self.deltaLng,
			self.minLat, self.deltaLat) = struct.unpack("<iiiffff", f.read(28))

		assert 3 <= self.numLng <= 461
		assert 3 <= self.numLat

		self.maxLng = self.minLng + self.deltaLng * (self.numLng - 1)
		self.maxLat = self.minLat + self.deltaLat * (self.numLat - 1)

	def readData(self):
		f = self.dataFile
		recordLen = 4 + self.numLng * 4
		unpackFormat = "<" + "f" * self.numLng
		f.seek(recordLen)
		self.data = [struct.unpack_from(unpackFormat, f.read(recordLen), 4)
			for n in xrange(self.numLat)]
		f.close()

	def interpolate(self, lat, lng):
		if self.data is None:
			self.readData()

		xgrid = (lng - self.minLng) / self.deltaLng
		ygrid = (lat - self.minLat) / self.deltaLat

		row = int(ygrid)
		col = int(xgrid)

		z = self.data[row]
		t1, t3 = z[col], z[col + 1]
		if t1 == 9999.0 or t3 == 9999.0:
			return None

		z = self.data[row + 1]
		t2, t4 = z[col], z[col + 1]
		if t2 == 9999.0 or t4 == 9999.0:
			return None

		row = ygrid - row
		col = xgrid - col

		return round((t1 +
			(t3 - t1) * col +
			(t2 - t1) * row +
			(t4 - t3 - t2 + t1) * col * row) / 1000.0, 3)

class Vertcon(object):
	def __init__(self):
		self.grids = [Grid("w", 5.0), Grid("c", 5.0), Grid("e", 0.0)]

	def getShift(self, lat, lng):
		for grid in self.grids:
			if (grid.minLat <= lat <= grid.maxLat and
				grid.minLng <= lng <= (grid.maxLng - grid.margin)):
				return grid.interpolate(lat, lng)
		return None

globalVertcon = None

def getShift(*args):
	global globalVertcon

	if globalVertcon is None:
		globalVertcon = Vertcon()

	return globalVertcon.getShift(*args)

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("latitude", nargs="?", default=37.561394, type=float)
	parser.add_argument("longitude", nargs="?", default=-118.858424, type=float)
	args = parser.parse_args()

	assert -90 <= args.latitude <= 90
	assert -180 <= args.longitude <= 180

	print getShift(args.latitude, args.longitude)

if __name__ == "__main__":
	main()
