#!/usr/bin/python
import json
import os
from ppjson import prettyPrint

class Query(object):
	fields = "*"

	@classmethod
	def processResponse(self, features):
		prettyPrint(features)

	@classmethod
	def query(self, geometry, distance=20, verbose=False):
		params = [
			"f=json",
			"geometry={}".format(geometry),
			"geometryType=esriGeometryPoint",
			"inSR=4326",
			"spatialRel=esriSpatialRelIntersects",
			"outFields={}".format(self.fields),
			"returnGeometry=false",
		]
		if distance:
			params.append("distance={}".format(distance))
			params.append("units=esriSRUnit_Meter")

		url = "{}/{}/MapServer/{}/query?{}".format(self.home, self.service, self.layer, "&".join(params))
		fileName = "lama.out"

		command = "/usr/bin/curl {}-o '{}' --retry 2 '{}'".format("" if verbose else "-s ", fileName, url)
		if verbose:
			print command
		os.system(command)

		with open(fileName) as f:
			jsonData = json.load(f)

		features = [f['attributes'] for f in jsonData['features']]

		self.processResponse(features)

class WildernessQuery(Query):
	name = 'Wilderness Boundaries'
	home = 'https://gisservices.cfc.umt.edu/arcgis/rest/services' # 10.51
	service = 'ProtectedAreas/National_Wilderness_Preservation_System'
	layer = 0 # sr = 102113 (3785)
	fields = 'OBJECTID_1,NAME,URL,Agency,YearDesignated'

	@classmethod
	def processResponse(self, features):
		for f in features:
			name = f['NAME']
			agency = f['Agency']
			year = f['YearDesignated']
			if agency == 'FS':
				agency = 'USFS'
			print '{} ({}) ({})'.format(name, agency, year)

class NPS_Query(Query):
	name = 'National Park Service Boundaries'
	home = 'https://mapservices.nps.gov/arcgis/rest/services' # 10.22
	service = 'LandResourcesDivisionTractAndBoundaryService'
	layer = 2 # sr = 102100 (3857)
	fields = 'OBJECTID,UNIT_NAME,UNIT_CODE'

	@classmethod
	def processResponse(self, features):
		for f in features:
			print f['UNIT_NAME']

class USFS_Query(Query):
	name = 'USFS Administrative Forest Boundaries'
	home = 'https://apps.fs.usda.gov/arcx/rest/services' # 10.51
	service = 'EDW/EDW_ForestSystemBoundaries_01'
	layer = 1 # sr = 102100 (3857)
	fields = 'OBJECTID,REGION,FORESTNAME'

	@classmethod
	def processResponse(self, features):
		for f in features:
			print f['FORESTNAME']

class USFS_RangerDistrictQuery(Query):
	name = 'USFS Ranger District Boundaries'
	home = 'https://apps.fs.usda.gov/arcx/rest/services' # 10.51
	service = 'EDW/EDW_RangerDistricts_01'
	layer = 1 # sr = 102100 (3857)
	fields = 'OBJECTID,REGION,FORESTNAME,DISTRICTNAME'

	@classmethod
	def processResponse(self, features):
		for f in features:
			forest = f['FORESTNAME']
			district = f['DISTRICTNAME']
			print '{} ({})'.format(forest, district)

class BLM_Query(Query):
	name = 'BLM Field Office Boundaries'
	home = 'https://gis.blm.gov/arcgis/rest/services' # 10.41
	service = 'admin_boundaries/BLM_Natl_AdminUnit'
	layer = 3 # sr = 102100 (3857) # also try layers 1 (State), 2 (District), and 4 (Other)
	fields = 'OBJECTID,ADMIN_ST,ADMU_NAME,ADMU_ST_URL,PARENT_NAME'

	@classmethod
	def processResponse(self, features):
		for f in features:
			state = f['ADMIN_ST']
			name = f['ADMU_NAME']
			parent = f['PARENT_NAME']
			print '{} ({}) ({})'.format(name, state, parent)

class BLM_SMA_Query(Query):
	name = 'Surface Management Agency'
	home = 'https://gis.blm.gov/arcgis/rest/services' # 10.41
	service = 'lands/BLM_Natl_SMA_LimitedScale'
	layer = 1 # sr = 102100 (3857)
	fields = 'OBJECTID,ADMIN_AGENCY_CODE,ADMIN_UNIT_NAME'

	@classmethod
	def processResponse(self, features):
		for f in features:
			name = f['ADMIN_UNIT_NAME']
			agency = f['ADMIN_AGENCY_CODE']
			print '{} ({})'.format(name, agency)

class BLM_NLCS_Query(Query):
	name = 'National Landscape Conservation System'
	home = 'https://gis.blm.gov/arcgis/rest/services' # 10.41
	service = 'lands/BLM_Natl_NLCS_NM_NCA_poly'
	layer = 1 # sr = 102100 (3857) # also try layer 0

	field_prefix1 = 'Monuments_NCAs_SimilarDesignation2015'
	field_prefix2 = 'nlcs_desc'

	fields1 = ['OBJECTID', 'sma_code', 'NCA_NAME', 'STATE_ADMN', 'STATE_GEOG']
	fields2 = ['WEBLINK']

	fields1 = ["{}.{}".format(field_prefix1, field) for field in fields1]
	fields2 = ["{}.{}".format(field_prefix2, field) for field in fields2]

	fields = ','.join(fields1 + fields2)

	@classmethod
	def processResponse(self, features):
		nameField = "{}.{}".format(self.field_prefix1, 'NCA_NAME')
		codeField = "{}.{}".format(self.field_prefix1, 'sma_code')
		stateField = "{}.{}".format(self.field_prefix1, 'STATE_GEOG')
		for f in features:
			name = f[nameField]
			code = f[codeField]
			state = f[stateField]
			print '{} ({}) ({})'.format(name, code, state)

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('latlong')
	args = parser.parse_args()

	latitude, longitude = args.latlong.split(",")

	geometry = "{},{}".format(longitude, latitude)

	queryMap = {
		"blm": BLM_Query,
		"nlcs": BLM_NLCS_Query,
		"nps": NPS_Query,
		"sma": BLM_SMA_Query,
		"usfs": USFS_Query,
		"usfsrd": USFS_RangerDistrictQuery,
		"w": WildernessQuery,
	}
	queries = ("nps", "usfsrd", "nlcs", "blm", "sma", "w")

	for q in [queryMap[k] for k in queries]:
		q.query(geometry)

if __name__ == "__main__":
	main()
