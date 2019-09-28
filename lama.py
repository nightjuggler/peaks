#!/usr/bin/python
from __future__ import print_function
import json
import subprocess
import time
from ppjson import prettyPrint

def makePrefixedFields(*prefixesWithFields):
	return [("{}.{}".format(prefix, field), alias)
			for prefix, fields in prefixesWithFields
				for field, alias in fields]

class Query(object):
	fields = []
	printSpec = None
	processFields = None
	serverType = "Map"

	@classmethod
	def query(self, geometry, distance=20, raw=False, returnGeometry=False, verbose=False, where=None):
		params = ["f=json"]
		if geometry:
			params.append("geometry={}".format(geometry))
			params.append("geometryType=esriGeometryPoint")
			params.append("inSR=4326")
			params.append("spatialRel=esriSpatialRelIntersects")

		params.append("outFields={}".format(",".join([field for field, alias in self.fields])
			if self.fields and not raw else "*"))

		if returnGeometry:
			params.append("returnGeometry=true")
			params.append("geometryPrecision=5")
			params.append("outSR=4326")
		else:
			params.append("returnGeometry=false")

		if distance:
			params.append("distance={}".format(distance))
			params.append("units=esriSRUnit_Meter")
		if where:
			params.append("where={}".format(where))

		url = "{}/{}/{}Server/{}/query?{}".format(self.home, self.service, self.serverType, self.layer,
			"&".join(params))
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

		features = jsonData.get("features")
		if features is None:
			print("Query response doesn't have the \"features\" property!")
			prettyPrint(jsonData)
			return

		for feature in features:
			response = feature["attributes"]
			if raw or not (self.fields and self.printSpec):
				prettyPrint(response)
				if returnGeometry:
					prettyPrint(feature["geometry"])
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

#	home = "https://irmaservices.nps.gov/arcgis/rest/services" # 10.41
#	service = "IMDData/IMD_Boundaries_WebMercator"
#	layer = 0 # sr = 102100 (3857)

	home = "https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services" # 10.7
	service = "NPS_Park_Boundaries"
	serverType = "Feature"
	layer = 0 # sr = 102100

	fields = [
#		("OBJECTID", "id"),
		("UNIT_NAME", "name"),
#		("UNIT_CODE", "code"),
	]
	printSpec = "{name}"

class NWR_Query(Query):
	name = "National Wildlife Refuge"
	home = "https://gis.fws.gov/arcgis/rest/services" # 10.51
	service = "FWS_Refuge_Boundaries"
	layer = 3 # sr = 4269 (NAD 83)
	fields = [("ORGNAME", "name"), ("SUM_GISACRES", "acres")]
	printSpec = "{name} ({acres:,.0f} acres)"

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
	layer = 3 # sr = 102100 (3857) # 1=State, 2=District, 3=Field Office, 4=Other
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
	layer = 1 # sr = 102100 (3857)
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
	home = "https://services.nationalmap.gov/arcgis/rest/services" # 10.61
	service = "WFS/govunits"
	layer = 3 # sr = 4326
	fields = [
#		("OBJECTID", "id"),
#		("COUNTY_NAME", "county"), # "White Pine" or "Carson City"
		("GNIS_NAME", "name"),     # "White Pine County" or "Carson City"
		("STATE_NAME", "state"),   # "Nevada"
		("POPULATION", "pop"),     # 10030 or 55274
	]
	printSpec = "{name}, {state} (Population: {pop:,})"

class USGS_TopoQuery(Query):
	name = "USGS 7.5' Topo"
	home = "https://index.nationalmap.gov/arcgis/rest/services" # 10.61
	service = "USTopoAvailability"
	layer = 0 # sr = 102100 (3857)
	fields = [
		("CELL_NAME", "cell"),
		("STATE_ALPHA", "state"),
	]
	printSpec = "{cell}, {state}"

class USGS_TopoViewQuery(Query):
	name = "USGS TopoView"
	home = "https://ngmdb.usgs.gov/arcgis/rest/services"
	service = "topoView/ustOverlay"
	layer = 0 # sr = 102100 (3857)

class TigerCountyQuery(Query):
	name = "County (TIGERweb)"
	home = "https://tigerweb.geo.census.gov/arcgis/rest/services" # 10.51
	service = "TIGERweb/State_County"
	layer = 13 # sr = 102100 (3857)
	fields = [
#		("OBJECTID", "id"),
#		("BASENAME", "county"), # Sierra
		("NAME", "name"),       # Sierra County
	]
	printSpec = "{name}"

class TigerStateQuery(Query):
	name = "State (TIGERweb)"
	home = "https://tigerweb.geo.census.gov/arcgis/rest/services" # 10.51
	service = "TIGERweb/State_County"
	layer = 12 # sr = 102100 (3857)
	fields = [
#		("OBJECTID", "id"),
		("NAME", "name"),
		("STUSAB", "state"),
	]
	printSpec = "{name} ({state})"

class CensusCountyQuery(Query):
	name = "County (2010 Census)"
	home = "https://tigerweb.geo.census.gov/arcgis/rest/services" # 10.51
	service = "TIGERweb/tigerWMS_Census2010"
	layer = 100 # sr = 102100 (3857)
	fields = [("NAME", "name"), ("POP100", "pop")]
	printSpec = "{name} (Population: {pop:,})"

class CA_StateParksQuery(Query):
	name = "California State Parks"
	home = "https://services.gis.ca.gov/arcgis/rest/services" # 10.51
	service = "Boundaries/CA_State_Parks"
	layer = 0 # sr = 102100 (3857)
	fields = [("UNITNAME", "name"), ("MgmtStatus", "status"), ("GISACRES", "acres")]
	printSpec = "{name} ({status}) ({acres:,.0f} acres)"

class CA_ZIP_Code_Query(Query):
	name = "ZIP Code (California)"
	home = "https://services.gis.ca.gov/arcgis/rest/services" # 10.51
	service = "Boundaries/Zips"
	layer = 0 # sr = 102100 (3857)
	fields = [
		("ZIP_CODE", "zip"),
		("NAME", "name"),
		("STATE", "state"),
		("POPULATION", "pop"),
		("SQMI", "area"),
	]
	printSpec = "{name}, {state} {zip} / Population: {pop:,} (2014) / {area:,.2f} square miles"

class CNRA_ConservancyQuery(Query):
	name = "CNRA Conservancy"
	home = "https://gis.cnra.ca.gov/arcgis/rest/services" # 10.3
	service = "Boundaries/CNRA_Conservancy_Boundaries"
	layer = 0 # sr = 102100 (3857)
	fields = [("Name", "name")]
	printSpec = "{name}"

class CPAD_HoldingsQuery(Query):
	name = "CPAD (California Protected Areas Database)"
	home = "https://gis.cnra.ca.gov/arcgis/rest/services" # 10.3
	service = "Boundaries/CPAD_AgencyClassification"
	layer = 0 # sr = 102100 (3857)

class AIANNH_Query(Query):
	name = "American Indian, Alaska Native, and Native Hawaiian Areas"
	home = "https://tigerweb.geo.census.gov/arcgis/rest/services" # 10.51
	service = "TIGERweb/AIANNHA"
	layer = 47 # sr = 102100 (3857)
	fields = [("NAME", "name")]
	printSpec = "{name}"

class GeoMAC_CurrentPerimetersQuery(Query):
	name = "GeoMAC Current Fire Perimeters"
	home = "https://wildfire.cr.usgs.gov/arcgis/rest/services" # 10.51
	service = "geomac_dyn"
	layer = 2 # sr = 102100 (3857)
	fields = [
		("objectid", "id"),
		("active", "isActive"),
		("complexname", "complexName"),
		("incomplex", "inComplex"),
		("incidentname", "name"),
		("datecurrent", "date"),
		("perimeterdatetime", "perimeterTime"),
		("gisacres", "acres"),
		("uniquefireidentifier", "fid"),
	]
	printSpec = "{name} Fire"

	@classmethod
	def processFields(self, fields):
		fields["name"] = fields["name"].title()
		isActive = fields["isActive"]
		fields["isActive"] = "Yes" if isActive == "Y" else "No" if isActive == "N" else isActive
		fields["date"] = time.strftime("%Y-%m-%d %H:%M:%S",
			time.gmtime(fields["date"] / 1000))
		fields["perimeterTime"] = time.strftime("%Y-%m-%d %H:%M:%S",
			time.gmtime(fields["perimeterTime"] / 1000))
		if fields["inComplex"] == "Y":
			self.printSpec += " ({complexName})"
		self.printSpec = "\n".join([
			self.printSpec,
			"\tActive: {isActive}",
			"\tSize: {acres:,.2f} acres",
			"\tDate Current: {date}",
			"\tPerimeter Date/Time: {perimeterTime}",
			"\tUnique Fire Identifier: {fid}",
		])

class GeoMAC_LatestPerimetersQuery(GeoMAC_CurrentPerimetersQuery):
	name = "GeoMAC Latest Fire Perimeters"
	layer = 3 # sr = 102100 (3857)

class GeoMAC_PerimetersDD83_Query(GeoMAC_CurrentPerimetersQuery):
	name = "GeoMAC Perimeters DD83"
	service = "geomac_perims"
	layer = 4 # sr = 4269

class GeoMAC_MODIS_Query(Query):
	name = "GeoMAC MODIS Fire Detection"
	home = "https://wildfire.cr.usgs.gov/arcgis/rest/services" # 10.51
	service = "geomac_dyn"
	layer = 4 # sr = 102100 (3857)

class GeoMAC_VIIRS_Query(Query):
	name = "GeoMAC VIIRS IBAND Fire Detection"
	home = "https://wildfire.cr.usgs.gov/arcgis/rest/services" # 10.51
	service = "geomac_dyn"
	layer = 5 # sr = 102100 (3857)

class NV_StateParksQuery(Query):
	name = "Nevada State Parks"
	home = "https://arcgis.shpo.nv.gov/arcgis/rest/services" # 10.51
	service = "NV_StateManagedLands"
	layer = 52 # sr = 102100 (3857)
	fields = [("LandName", "name"), ("Acres", "acres")]
	printSpec = "{name} ({acres:,.0f} acres)"

class SLO_OpenSpaceQuery(Query):
	name = "City of San Luis Obispo Open Space"
	home = "https://services.arcgis.com/yygmGNIVQrHqSELP/arcgis/rest/services" # 10.61
	service = "OpenSpaceSLO"
	serverType = "Feature"
	layer = 0 # sr = 2874

class SCC_ParksQuery(Query):
	name = "Santa Clara County Parks"
	home = "https://services1.arcgis.com/4QPaqCJqF1UIaPbN/arcgis/rest/services" # 10.61
	service = "SCCParks_SantaClaraCountyParks"
	serverType = "Feature"
	layer = 0 # sr = 102100
	fields = [
		("PARK_NAME", "name"),
		("PARK_SUFFIX", "suffix"),
		("ACRES", "acres"),
	]
	printSpec = "{name} {suffix} ({acres:,.1f} acres)"

class SCC_ProtectedLandsQuery(Query):
	name = "Santa Clara County Protected Lands"
	home = "https://services1.arcgis.com/4QPaqCJqF1UIaPbN/arcgis/rest/services" # 10.61
	service = "SCCParks_ProtectedLands"
	serverType = "Feature"
	layer = 0 # sr = 102643
	fields = [
		("Operator", "operator"),
		("Park_Name", "name"),
		("Acres", "acres"),
	]
	printSpec = "{name} ({operator}) ({acres:,.1f} acres)"

def checkDegrees(degrees, minValue, maxValue):
	try:
		degrees = float(degrees)
	except ValueError:
		return False

	if degrees < minValue or degrees > maxValue:
		return False

	return True

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("latlong")
	parser.add_argument("-d", "--distance", type=float, default=20)
	parser.add_argument("-q", "--query", default="state,county,zip_ca,topo,nps,rd,nlcs,blm,sma,w,wsa")
	parser.add_argument("--raw", action="store_true")
	parser.add_argument("--return-geometry", action="store_true")
	parser.add_argument("-v", "--verbose", action="store_true")
	parser.add_argument("-w", "--where")
	args = parser.parse_args()

	if args.latlong == "none":
		geometry = None
	else:
		try:
			latitude, longitude = args.latlong.split(",")
		except ValueError:
			print("Latitude,Longitude not valid!")
			return

		if not checkDegrees(latitude, -90, 90) or not checkDegrees(longitude, -180, 180):
			print("Latitude,Longitude not valid!")
			return

		geometry = "{},{}".format(longitude, latitude)

	queryMap = {
		"aiannh": AIANNH_Query,
		"blm": BLM_Query,
		"ca_parks": CA_StateParksQuery,
		"cnra_conservancy": CNRA_ConservancyQuery,
		"county": TigerCountyQuery,
		"county_census": CensusCountyQuery,
		"county_usfs": USFS_CountyQuery,
		"county_usgs": USGS_CountyQuery,
		"cpad_holdings": CPAD_HoldingsQuery,
		"fs": USFS_Query,
		"geomac_cp": GeoMAC_CurrentPerimetersQuery,
		"geomac_dd83": GeoMAC_PerimetersDD83_Query,
		"geomac_lp": GeoMAC_LatestPerimetersQuery,
		"geomac_modis": GeoMAC_MODIS_Query,
		"geomac_viirs": GeoMAC_VIIRS_Query,
		"nlcs": BLM_NLCS_Query,
		"nps": NPS_Query,
		"nv_parks": NV_StateParksQuery,
		"nwr": NWR_Query,
		"rd": USFS_RangerDistrictQuery,
		"scc_parks": SCC_ParksQuery,
		"scc_protected": SCC_ProtectedLandsQuery,
		"slo": SLO_OpenSpaceQuery,
		"sma": BLM_SMA_Query,
		"state": TigerStateQuery,
		"topo": USGS_TopoQuery,
		"topoview": USGS_TopoViewQuery,
		"w": WildernessQuery,
		"wsa": BLM_WSA_Query,
		"zip_ca": CA_ZIP_Code_Query,
	}
	queries = args.query.split(",")

	kwargs = {
		"distance":             args.distance,
		"raw":                  args.raw,
		"returnGeometry":       args.return_geometry,
		"verbose":              args.verbose,
		"where":                args.where,
	}

	for q in [queryMap[k] for k in queries]:
		q.query(geometry, **kwargs)

if __name__ == "__main__":
	main()
