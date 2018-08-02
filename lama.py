#!/usr/bin/python
from __future__ import print_function
import json
import subprocess
from ppjson import prettyPrint

def makePrefixedFields(*prefixesWithFields):
	return [("{}.{}".format(prefix, field), alias)
			for prefix, fields in prefixesWithFields
				for field, alias in fields]

class Query(object):
	fields = []
	printSpec = None
	processFields = None

	@classmethod
	def query(self, geometry, distance=20, verbose=False):
		fields = ",".join([field for field, alias in self.fields]) if self.fields else "*"

		params = [
			"f=json",
			"geometry={}".format(geometry),
			"geometryType=esriGeometryPoint",
			"inSR=4326",
			"spatialRel=esriSpatialRelIntersects",
			"outFields={}".format(fields),
			"returnGeometry=false",
		]
		if distance:
			params.append("distance={}".format(distance))
			params.append("units=esriSRUnit_Meter")

		url = "{}/{}/MapServer/{}/query?{}".format(self.home, self.service, self.layer, "&".join(params))
		fileName = "lama.out"

		command = ["/usr/local/opt/curl/bin/curl",
			"-o", fileName,
#			"--user-agent", "Mozilla/5.0",
			"--connect-timeout", "6",
			"--max-time", "12",
			"--retry", "2",
			url]

		print("-----", self.name)
		if verbose:
			print(*command)
		else:
			command.insert(1, "-s")

		rc = subprocess.call(command)

		if rc != 0:
			if not verbose:
				print(*command)
			print("Exit code", rc)
			return

		with open(fileName) as f:
			jsonData = json.load(f)

		for feature in jsonData["features"]:
			response = feature["attributes"]
			if not (self.fields and self.printSpec):
				prettyPrint(response)
				continue

			fields = {alias: response[field] for field, alias in self.fields}
			if self.processFields:
				self.processFields(fields)
			print(self.printSpec.format(**fields))

class WildernessQuery(Query):
	name = "Wilderness Areas"
	home = "https://gisservices.cfc.umt.edu/arcgis/rest/services" # 10.51
	service = "ProtectedAreas/National_Wilderness_Preservation_System"
	layer = 0 # sr = 102113 (3785)
	fields = [
#		("OBJECTID_1", "id"),
		("NAME", "name"),
#		("URL", "url"),
		("Agency", "agency"),
		("YearDesignated", "year"),
	]
	printSpec = "{name} ({agency}) ({year})"

	@classmethod
	def processFields(self, fields):
		if fields["agency"] == "FS":
			fields["agency"] = "USFS"

class NPS_Query(Query):
	name = "National Park Service Unit"
	home = "https://mapservices.nps.gov/arcgis/rest/services" # 10.22
	service = "LandResourcesDivisionTractAndBoundaryService"
	layer = 2 # sr = 102100 (3857)
	fields = [
#		("OBJECTID", "id"),
		("UNIT_NAME", "name"),
#		("UNIT_CODE", "code"),
	]
	printSpec = "{name}"

class USFS_Query(Query):
	name = "USFS Administrative Forest"
	home = "https://apps.fs.usda.gov/arcx/rest/services" # 10.51
	service = "EDW/EDW_ForestSystemBoundaries_01"
	layer = 1 # sr = 102100 (3857)
	fields = [
#		("OBJECTID", "id"),
#		("REGION", "region"),
		("FORESTNAME", "forest"),
	]
	printSpec = "{forest}"

class USFS_CountyQuery(Query):
	name = "County (USFS)"
	home = "https://apps.fs.usda.gov/arcx/rest/services" # 10.51
	service = "EDW/EDW_County_01"
	layer = 1 # sr = 102100 (3857)
	fields = [
#		("OBJECTID", "id"),
#		("COUNTYNAME", "county"),       # "White Pine" or "Carson City"
		("LEGAL_NAME", "name"),         # "White Pine County" or "Carson City"
#		("STATENAME", "state"),         # "Nevada"
		("STATE_POSTAL_ABBR", "state"), # "NV"
	]
	printSpec = "{name}, {state}"

class USFS_RangerDistrictQuery(Query):
	name = "USFS Ranger District"
	home = "https://apps.fs.usda.gov/arcx/rest/services" # 10.51
	service = "EDW/EDW_RangerDistricts_01"
	layer = 1 # sr = 102100 (3857)
	fields = [
#		("OBJECTID", "id"),
#		("REGION", "region"),
		("FORESTNAME", "forest"),
		("DISTRICTNAME", "district"),
	]
	printSpec = "{forest} ({district})"

class BLM_Query(Query):
	name = "BLM Administrative Unit"
	home = "https://gis.blm.gov/arcgis/rest/services" # 10.41
	service = "admin_boundaries/BLM_Natl_AdminUnit"
	layer = 3 # sr = 102100 (3857) # also try layers 1 (State), 2 (District), and 4 (Other)
	fields = [
#		("OBJECTID", "id"),
		("ADMU_NAME", "name"),
		("ADMIN_ST", "state"),
#		("ADMU_ST_URL", "url"),
		("PARENT_NAME", "parent"),
	]
	printSpec = "{name} ({state}) ({parent})"

class BLM_NLCS_Query(Query):
	name = "National Landscape Conservation System"
	home = "https://gis.blm.gov/arcgis/rest/services" # 10.41
	service = "lands/BLM_Natl_NLCS_NM_NCA_poly"
	layer = 1 # sr = 102100 (3857) # also try layer 0
	fields = makePrefixedFields(
		("Monuments_NCAs_SimilarDesignation2015", (
#			("OBJECTID", "id"),
			("sma_code", "code"),
			("NCA_NAME", "name"),
			("STATE_GEOG", "state"),
		)),
		("nlcs_desc", (
#			("WEBLINK", "url"),
		)),
	)
	printSpec = "{name} ({code}) ({state})"

class BLM_SMA_Query(Query):
	name = "Surface Management Agency"
	home = "https://gis.blm.gov/arcgis/rest/services" # 10.41
	service = "lands/BLM_Natl_SMA_LimitedScale"
	layer = 1 # sr = 102100 (3857)
	fields = [
#		("OBJECTID", "id"),
		("ADMIN_UNIT_NAME", "name"),
		("ADMIN_AGENCY_CODE", "agency"),
	]
	printSpec = "{name} ({agency})"

	@classmethod
	def processFields(self, fields):
		if fields["name"] is None:
			fields["name"] = "Unit Name Not Specified"

class BLM_WSA_Query(Query):
	name = "Wilderness Study Areas"
	home = "https://gis.blm.gov/arcgis/rest/services" # 10.41
	service = "lands/BLM_Natl_NLCS_WLD_WSA"
	layer = 1 # sr = 102100 (3857)
	fields = makePrefixedFields(
		("nlcs_wsa_poly", (
#			("OBJECTID", "id"),
			("NLCS_NAME", "name"),
			("ADMIN_ST", "state"),
			("WSA_RCMND", "rcmnd"),
		)),
	)
	printSpec = "{name} ({state}) ({rcmnd})"

class USGS_CountyQuery(Query):
	name = "County (The National Map)"
	home = "https://services.nationalmap.gov/arcgis/rest/services" # 10.41
	service = "WFS/govunits"
	layer = 3 # sr = 4326
	fields = [
#		("OBJECTID", "id"),
#		("COUNTY_NAME", "county"), # "White Pine" or "Carson City"
		("GNIS_NAME", "name"),     # "White Pine County" or "Carson City"
		("STATE_NAME", "state"),   # "Nevada"
#		("POPULATION", "pop"),     # 10030 or 55274
	]
	printSpec = "{name}, {state}"

class USGS_TopoQuery(Query):
	name = "USGS 7.5' Topo"
	home = "https://services.nationalmap.gov/arcgis/rest/services" # 10.41
	service = "US_Topo_Availability"
	layer = 0 # sr = 4326
	fields = [
		("CELL_NAME", "cell"),
		("STATE_ALPHA", "state"),
	]
	printSpec = "{cell}, {state}"

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("latlong")
	parser.add_argument("-q", "--query", default="county,topo,nps,rd,nlcs,blm,sma,w,wsa")
	parser.add_argument("-v", "--verbose", action="store_true")
	args = parser.parse_args()

	latitude, longitude = args.latlong.split(",")

	geometry = "{},{}".format(longitude, latitude)

	queryMap = {
		"blm": BLM_Query,
		"county": USGS_CountyQuery,
		"county_usfs": USFS_CountyQuery,
		"fs": USFS_Query,
		"nlcs": BLM_NLCS_Query,
		"nps": NPS_Query,
		"rd": USFS_RangerDistrictQuery,
		"sma": BLM_SMA_Query,
		"topo": USGS_TopoQuery,
		"w": WildernessQuery,
		"wsa": BLM_WSA_Query,
	}
	queries = args.query.split(",")

	for q in [queryMap[k] for k in queries]:
		q.query(geometry, verbose=args.verbose)

if __name__ == "__main__":
	main()
