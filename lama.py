import json
import math
import re
import subprocess
import time
from ppjson import prettyPrint

CURL = "/usr/local/opt/curl/bin/curl"

def makePrefixedFields(*prefixesWithFields):
	return [("{}.{}".format(prefix, field), alias)
			for prefix, fields in prefixesWithFields
				for field, alias in fields]

def formatDate(date):
	date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(date / 1000))
	if date[-3:] == ":00":
		return date[:-9] if date[-9:] == " 00:00:00" else date[:-3]
	return date

# See JPL Publication 07-3 "Some Algorithms for Polygons on a Sphere"
# by Robert G. Chamberlain and William H. Duquette, Jet Propulsion Laboratory, 2007
# https://trs.jpl.nasa.gov/handle/2014/40409

def ringArea(points):
	R = 6378137
	N = len(points)

	assert N >= 4
	assert points[0] == points[-1]

	area = 0
	p1 = points[-2]
	p2 = points[0]
	for p3 in points[1:]:
		area += (p3[0] - p1[0]) * math.sin(p2[1] * math.pi/180)
		p1 = p2
		p2 = p3

	area *= math.pi/180 * R*R/2

#	print("ringArea = {:,.2f}".format(area))
	return area

def polygonArea(rings):
	N = len(rings)
	assert N > 0

	area = ringArea(rings[0])
	if N > 1:
		assert area > 0
		for hole in rings[1:]:
			_ringArea = ringArea(hole)
			assert _ringArea < 0
			area += _ringArea

#	print("polygonArea = {:,.2f}".format(area))
	return area

def printArea(feature, geojson, jsonData):
	geometry = feature.get("geometry")
	if geometry is None:
		print("Feature doesn't have the \"geometry\" property!")
		return
	if geojson:
		geometryType = geometry["type"]
		coordinates = geometry["coordinates"]

		if geometryType == "Polygon":
			area = polygonArea(coordinates)
		elif geometryType == "MultiPolygon":
			area = sum([polygonArea(polygon) for polygon in coordinates])
		else:
			area = 0
	else:
		geometryType = jsonData.get("geometryType")

		if geometryType == "esriGeometryPolygon":
			area = sum([ringArea(ring) for ring in geometry["rings"]])
#			printExtentArea(getExtent(geometry["rings"]))
		else:
			area = 0

	print("Area({}) = {:,.2f} square meters = {:,.2f} acres".format(geometryType, area, area / 4046.9))

def getExtent(rings):
	xmin, ymin = xmax, ymax = rings[0][0]

	for ring in rings:
		for x, y in ring:
			if x < xmin: xmin = x
			elif x > xmax: xmax = x
			if y < ymin: ymin = y
			elif y > ymax: ymax = y

	extent = {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax}
	prettyPrint(extent)
	return extent

def printExtentArea(extent):
	xmin = extent["xmin"]
	xmax = extent["xmax"]
	ymin = extent["ymin"]
	ymax = extent["ymax"]
	ring = [[xmin, ymax], [xmax, ymax], [xmax, ymin], [xmin, ymin]]
	ring.append(ring[0])
	area = ringArea(ring)
	print("Extent Area = {:,.2f} square meters = {:,.2f} acres".format(area, area / 4046.9))

encodeURIComponentPattern = re.compile("[^-.0-9A-Z_a-z]")
def encodeURIComponent(s):
	return encodeURIComponentPattern.sub(lambda m: "%{:02X}".format(ord(m.group(0))), s)

class Query(object):
	fields = []
	orderByFields = None
	printSpec = None
	processFields = None
	serverType = "Map"
	sortkey = None

	@classmethod
	def query(self, geometry,
		computeArea=False,
		distance=20,
		fieldsOnly=False,
		geojson=False,
		groupBy=None,
		precision=5,
		raw=False,
		reprocess=False,
		returnCountOnly=False,
		returnExtentOnly=False,
		returnGeometry=False,
		verbose=False,
		where=None
	):
		params = ["f=" + ("geojson" if geojson else "json")]
		if geometry:
			params.append("geometry={}".format(geometry))
			params.append("geometryType=esriGeometryPoint")
			params.append("inSR=4326")
			params.append("spatialRel=esriSpatialRelIntersects")

		params.append("outFields={}".format(",".join([field for field, alias in self.fields])
			if self.fields and not raw else "*"))

		if groupBy:
			groupFields, stats, printFields = groupBy
			params.append("groupByFieldsForStatistics=" + groupFields)
			params.append("outStatistics=" + stats)
			params.append("orderByFields=" + groupFields)

		elif self.orderByFields and not returnExtentOnly:
			params.append("orderByFields=" + encodeURIComponent(self.orderByFields))

		if returnGeometry or (computeArea and not (returnCountOnly or returnExtentOnly)):
			params.append("returnGeometry=true")
			params.append("geometryPrecision={}".format(precision))
			params.append("outSR=4326")
		else:
			params.append("returnGeometry=false")

		if distance:
			params.append("distance={}".format(distance))
			params.append("units=esriSRUnit_Meter")
		if where:
			params.append("where=" + encodeURIComponent(where))
		if returnCountOnly:
			params.append("returnCountOnly=true")
		if returnExtentOnly:
			params.append("returnExtentOnly=true")
			params.append("geometryPrecision={}".format(precision))
			params.append("outSR=4326")

		url = "{}/{}/{}Server/{}".format(self.home, self.service, self.serverType, self.layer)
		url += "?f=json" if fieldsOnly else "/query?" + "&".join(params)

		fileName = "lama.out"

		command = [CURL,
			"-o", fileName,
			"--connect-timeout", "6",
			"--max-time", "12",
			"--retry", "2",
			url]

		print("-----", self.name)
		if verbose:
			print(*command)
		else:
			command.insert(1, "-s")

		if not reprocess:
			rc = subprocess.call(command)
			if rc != 0:
				if not verbose:
					print(*command)
				print("Exit code", rc)
				return

		with open(fileName) as f:
			jsonData = json.load(f)

		if fieldsOnly:
			fields = jsonData.get("fields")
			if fields is None:
				print("Query response doesn't have the \"fields\" property!")
				prettyPrint(jsonData)
				return
			for f in fields:
				if "length" not in f:
					f["length"] = ""
				if f["type"][:13] == "esriFieldType":
					f["type"] = f["type"][13:]
				sqlType = f.get("sqlType")
				if sqlType is None:
					f["sqlType"] = ""
				elif sqlType[:7] == "sqlType":
					f["sqlType"] = sqlType[7:]
				if "defaultValue" not in f:
					f["defaultValue"] = None
				print("{name:28} {type:12} {sqlType:10} {length:4} {defaultValue}".format(**f))
			return

		if returnCountOnly or returnExtentOnly:
			prettyPrint(jsonData)
			if computeArea and returnExtentOnly:
				printExtentArea(jsonData["extent"])
			return

		features = jsonData.get("features")
		if features is None:
			print("Query response doesn't have the \"features\" property!")
			prettyPrint(jsonData)
			return

		attrKey = "properties" if geojson else "attributes"

		if self.sortkey and not groupBy:
			features.sort(key = lambda feature: self.sortkey(feature[attrKey]))

		for feature in features:
			response = feature[attrKey]
			if groupBy:
				if raw:
					prettyPrint(response)
					continue
				values = []
				for field, (spec, nullSpec) in printFields:
					value = response[field]
					if value is None:
						spec = nullSpec
						value = "null"
					values.append(format(value, spec))
				print(*values)
				continue

			if raw or not self.printSpec:
				prettyPrint(response)
				if returnGeometry:
					geometry = feature.get("geometry")
					if geometry is None:
						print("Feature doesn't have the \"geometry\" property!")
						continue
					prettyPrint(geometry)
				if computeArea:
					printArea(feature, geojson, jsonData)
				continue

			if self.fields:
				fields = {alias: response[field] for field, alias in self.fields}
			else:
				fields = response
			if self.processFields:
				self.processFields(fields)
			print(self.printSpec.format(**fields))
			if computeArea:
				printArea(feature, geojson, jsonData)

		if jsonData.get("exceededTransferLimit"):
			print("Transfer Limit Exceeded!")

class WildernessQuery(Query):
	name = "Wilderness Areas"
	home = "https://services1.arcgis.com/ERdCHt0sNM6dENSD/arcgis/rest/services"
	service = "Wilderness_Areas_in_the_United_States"
	serverType = "Feature"
	layer = 0
	fields = [
		("NAME", "name"),
		("Agency", "agency"),
		("Designated", "year"),
	]
	printSpec = "{name} ({agency}) ({year})"

	@classmethod
	def processFields(self, fields):
		if fields["agency"] == "FS":
			fields["agency"] = "USFS"

class NPS_Query(Query):
	name = "National Park Service Unit"
	home = "https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services"
	service = "NPS_Park_Boundaries"
	serverType = "Feature"
	layer = 0
	fields = [("UNIT_NAME", "name")]
	printSpec = "{name}"

class NPS_IRMA_Query(Query):
	name = "National Park Service Unit (IRMA)"
	home = "https://irmaservices.nps.gov/arcgis/rest/services"
	service = "IMDData/IMD_Boundaries_wgs"
	layer = 0
	fields = [("UNITNAME", "name")]
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

class USFS_OtherNationalDesignatedArea_Query(Query):
	name = "USFS Other National Designated Area"
	home = "https://apps.fs.usda.gov/arcx/rest/services"
	service = "EDW/EDW_OtherNationalDesignatedArea_01" # e.g. National Scenic Area
	layer = 0
	fields = [("FULLNAME", "name")]
	printSpec = "{name}"

class USFS_SpecialInterestManagementArea_Query(Query):
	name = "USFS Special Interest Management Area"
	home = "https://apps.fs.usda.gov/arcx/rest/services"
	service = "EDW/EDW_SpecialInterestManagementArea_01" # e.g. Research Natural Area
	layer = 0
	fields = [("AREANAME", "name"), ("AREATYPE", "type"), ("GIS_ACRES", "acres")]
	printSpec = "{name} {type} ({acres:,.0f} acres)"

	@classmethod
	def processFields(self, fields):
		if fields["type"] == "RESEARCH NATURAL AREA":
			fields["type"] = "RNA"

class USFS_Wilderness_Query(Query):
	name = "USFS National Wilderness Areas"
	home = "https://apps.fs.usda.gov/arcx/rest/services"
	service = "EDW/EDW_Wilderness_01"
	layer = 0
	fields = [("WILDERNESSNAME", "name"), ("GIS_ACRES", "acres"), ("WID", "wid")]
	printSpec = "{name} ({acres:,.0f} acres) https://wilderness.net/visit-wilderness/?ID={wid}"

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
	service = "topoview/ustOverlay"
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

class AirNow_BaseQuery(Query):
	home = "https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services"
	serverType = "Feature"
	layer = 0

class AirNowPointQuery(AirNow_BaseQuery):
	printSpec = "{PM25_AQI:4} | {PM10_AQI:4} | {OZONE_AQI:4} | {LocalTimeString:22} | {SiteName} ({DataSource})"

	@classmethod
	def sortkey(self, fields):
		date = fields["LocalTimeString"] # e.g. "Sat 10/03/2020 07:00 AM PDT"
		if len(date) >= 27:
			hour = date[15:17]
			if date[21] == "P":
				if hour != "12":
					hour = str(int(hour) + 12)
			else:
				assert date[21] == "A"
				if hour == "12":
					hour = "00"

			fields["LocalTimeString"] = date = "{}-{}-{} {}:{} {}".format(
				date[10:14], date[4:6], date[7:9], hour, date[18:20], date[24:])

		site = fields.get("SiteName")
		if site is None:
			fields["SiteName"] = site = "null"

		return (site, date)

	@classmethod
	def processFields(self, fields):
		def checkValue(key):
			value = fields.get(key)
			if value is None:
				fields[key] = "null"
			elif isinstance(value, str):
				fields[key] = round(float(value))
			elif isinstance(value, float):
				fields[key] = round(value)

		checkValue("PM25_AQI")
		checkValue("PM10_AQI")
		checkValue("OZONE_AQI")

		state = fields.get("StateName")
		if state:
			fields["SiteName"] += ", " + state
		country = fields.get("CountryCode")
		if country:
			fields["SiteName"] += ", " + country

class AirNow_Query(AirNowPointQuery):
	name = "Air Now"
	service = "Air_Now_Monitor_Data_Public"

class AirNow_Current_Query(AirNowPointQuery):
	name = "Air Now - Current"
	service = encodeURIComponent("Air Now Current Monitor Data Public")

class AirNowOzonePM_Query(AirNowPointQuery):
	name = "Air Now - PM 2.5, PM 10, and Ozone"
	service = "Air_Now_Monitors_Ozone_and_PM"

class AirNowOzonePM_Current_Query(AirNowPointQuery):
	name = "Air Now - PM 2.5, PM 10, and Ozone - Current"
	service = "Air_Now_Current_Monitors_Ozone_and_PM"

class AirNowContours_PM25_Query(AirNow_BaseQuery):
	name = "Air Now Contours - PM 2.5"
	service = "AirNowLatestContoursPM25"

class AirNowContours_Ozone_Query(AirNow_BaseQuery):
	name = "Air Now Contours - Ozone"
	service = "AirNowLatestContoursOzone"

class AirNowContours_Combined_Query(AirNow_BaseQuery):
	name = "Air Now Contours - Combined"
	service = "AirNowLatestContoursCombined"

class NIFC_BaseQuery(Query):
	home = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"
	serverType = "Feature"

class NIFC_HistoryBaseQuery(NIFC_BaseQuery):
	layer = 0
	fields = [
		("FID", "id"),
		("DATE_CUR", "date"),
		("FIRE_YEAR", "year"),
		("INCIDENT", "name"),
		("GIS_ACRES", "size"),
	]
	orderByFields = "FID"
	printSpec = "{id:6} | {year} | {date:16} | {size:11,.1f} ac | {name}"

	@classmethod
	def processFields(self, fields):
		date = fields["date"]
		if len(date) == 12 and date.isdecimal() and date != "999909090000":
			date = "{}-{}-{} {}:{}".format(date[:4], date[4:6], date[6:8], date[8:10], date[10:])
		else:
			date = ""
		fields["date"] = date

def newFireHistoryQuery(_service):
	class NIFC_HistoryQuery(NIFC_HistoryBaseQuery):
		name = "Interagency Fire Perimeter History: " + _service
		service = "Interagency_Fire_Perimeter_History_" + _service + "_Read_Only"

	return NIFC_HistoryQuery

def addFireHistoryQueries(queryMap):
	for key, service in (
		("fire_history",         "All_Years"),
		("fire_history_pre1980", "1979_And_Prior"),
		("fire_history_1980s",   "1980s"),
		("fire_history_1990s",   "1990s"),
		("fire_history_2000s",   "2000s"),
		("fire_history_decade",  "Current_Decade"),
		("fire_history_year",    "Previous_Year"),
	):
		queryMap[key] = newFireHistoryQuery(service)

class GeomacBaseQuery(NIFC_BaseQuery):
	fields = [
		("complexname", "complex"),
		("gisacres", "size"),
		("incidentname", "name"),
		("incomplex", "incomplex"),
		("perimeterdatetime", "date"),
		("uniquefireidentifier", "id"),
	]
	orderByFields = "uniquefireidentifier,perimeterdatetime"
	printSpec = "{id:19} {date:19} {size:12,.2f}  {incomplex}  {name}"

	@classmethod
	def processFields(self, fields):
		fields["date"] = formatDate(fields["date"])

		name = fields["name"]
		name = "" if name is None else name.strip()

		complex = fields["complex"]
		complex = "" if complex is None else complex.strip()

		if complex:
			if not name:
				name = complex
			elif name.lower() != complex.lower():
				name += " ({})".format(complex)

		fields["name"] = name

def newGeomacQuery(_name, _service, _layer):
	class GeomacQuery(GeomacBaseQuery):
		name = _name
		service = _service
		layer = _layer

	return GeomacQuery

def addGeomacQueries(queryMap):
	namePrefix = "Historic GeoMAC Perimeters "
	servicePrefix = "Historic_Geomac_Perimeters_"

	for year in range(2000, 2020):
		year = str(year)
		queryMap["geomac_" + year] = newGeomacQuery(namePrefix + year, servicePrefix + year, 0)

	queryMap["geomac_2000_2018"] = newGeomacQuery(namePrefix + "2000-2018",
		servicePrefix + "Combined_2000_2018", 0)

	namePrefix = "Historic Fire Perimeters "
	service = servicePrefix + "All_Years_2000_2018"

	for layer in range(19):
		year = str(2000 + layer)
		queryMap["us_fires_" + year] = newGeomacQuery(namePrefix + year, service, layer)

	queryMap["us_fires_2000_2018"] = newGeomacQuery(namePrefix + "2000-2018", service, 19)

class IRWIN_InciWebQuery(NIFC_BaseQuery):
	#
	# IRWIN = Integrated Reporting of Wildland Fire Information
	#
	name = "IRWIN to InciWeb"
	service = "IRWIN_to_Inciweb_View"
	layer = 0
	fields = [
		("OBJECTID", "oid"),
		("Title", "name"),
		("Id", "inciweb"),
		("LinkURI", "url"),
		("IrwinID", "irwin"),
	]
	orderByFields = "IrwinID"
	printSpec = "{irwin:36}  {inciweb:>5}  {name}"

	IRWIN_ID_Pattern = re.compile("^[0-9a-f]{8}(?:-[0-9a-f]{4}){4}[0-9a-f]{8}$")

	@classmethod
	def processFields(self, fields):
		name = fields["name"]
		inciweb = fields["inciweb"]
		url = fields["url"]

		if not self.IRWIN_ID_Pattern.match(fields["irwin"]):
			fields["irwin"] = "(*)"

		if inciweb != url or url[:33] != "http://inciweb.nwcg.gov/incident/" or url[-1] != "/":
			fields["inciweb"] = "(*)"
		else:
			fields["inciweb"] = url[33:-1]

		if name.endswith(" (Wildfire)"):
			fields["name"] = name[:-11]
		else:
			fields["name"] = name + " (*)"

class NIFC_CurrentPerimetersQuery(NIFC_BaseQuery):
	name = "NIFC Current Wildfire Perimeters"
	service = "WFIGS_Interagency_Perimeters_Current"
	layer = 0 # sr = 4326

class NIFC_CurrentIncidentsQuery(NIFC_BaseQuery):
	name = "NIFC Current Wildfire Incidents"
	service = "WFIGS_Incident_Locations_Current"
	layer = 0 # sr = 4269

class USA_WildfireIncidentsQuery(Query):
	name = "USA Wildfire Incidents"
	home = "https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services"
	service = "USA_Wildfires_v1"
	serverType = "Feature"
	layer = 0 # sr = 4326

class USA_WildfirePerimetersQuery(Query):
	name = "USA Wildfire Perimeters"
	home = "https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services"
	service = "USA_Wildfires_v1"
	serverType = "Feature"
	layer = 1 # sr = 4326

class FIRIS_Query(Query):
	name = "FIRIS Perimeters"
	home = "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/ArcGIS/rest/services"
	service = "FIRIS_FIRE_PERIMETERS_PUBLIC_view"
	serverType = "Feature"
	layer = 2

class CalFire_UnitsQuery(Query):
	name = "Cal Fire Units"
	home = "https://egis.fire.ca.gov/arcgis/rest/services"
	service = "FRAP/CalFireUnits"
	layer = 0 # sr = 102100

class CalFireCZU_EvacQuery(NIFC_BaseQuery):
	name = "Cal Fire CZU Evacuation Zones"
	service = "CZU_Lightning_Evac_VIEW"
	layer = 0 # sr = 4326

class SonomaEvacAreasQuery(Query):
	name = "Sonoma County Evacuation Areas"
	home = "https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services"
	service = "Sonoma_County_Evacuation_Areas_public"
	serverType = "Feature"
	layer = 0 # sr = 102100 (3857)

class SonomaEvacZonesQuery(Query):
	name = "Sonoma County Evacuation Zones"
	home = "https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services"
	service = "Sonoma_County_Evacuation_Zone_Reference"
	serverType = "Feature"
	layer = 0 # sr = 102100 (3857)

class NASA_MODIS_Query(Query):
	name = "MODIS"
	home = "https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services"
	service = "MODIS_Thermal_v1"
	serverType = "Feature"
	layer = 0 # sr = 102100

class NASA_VIIRS_Query(Query):
	name = "VIIRS"
	home = "https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services"
	service = "Satellite_VIIRS_Thermal_Hotspots_and_Fire_Activity"
	serverType = "Feature"
	layer = 0 # sr = 102100

class NV_StateParksQuery(Query):
	name = "Nevada State Parks"
	home = "https://arcgis.shpo.nv.gov/arcgis/rest/services" # 10.51
	service = "State_Lands/StateLands_PublicMap"
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

GovUnits_AgencyLookup = {
	# See https://carto.nationalmap.gov/arcgis/rest/services/govunits/MapServer/25?f=pjson
	3: "BLM",
	10: "FWS",
	11: "USFS",
	13: "NPS",
}

class GovUnits_BLM_Query(Query):
	name = "GovUnits - BLM"
	home = "https://carto.nationalmap.gov/arcgis/rest/services"
	service = "govunits"
	layer = 33
	fields = [("NAME", "name")]
	printSpec = "{name}"

class GovUnits_NPS_Query(Query):
	name = "GovUnits - National Park"
	home = "https://carto.nationalmap.gov/arcgis/rest/services"
	service = "govunits"
	layer = 23
	fields = [("NAME", "name")]
	printSpec = "{name}"

class GovUnits_USFS_Query(Query):
	name = "GovUnits - National Forest"
	home = "https://carto.nationalmap.gov/arcgis/rest/services"
	service = "govunits"
	layer = 24
	fields = [("NAME", "name")]
	printSpec = "{name}"

class GovUnits_Wilderness_Query(Query):
	name = "GovUnits - National Wilderness"
	home = "https://carto.nationalmap.gov/arcgis/rest/services"
	service = "govunits"
	layer = 25
	fields = [("NAME", "name"), ("OWNERORMANAGINGAGENCY", "agency")]
	printSpec = "{name} ({agency})"

	@classmethod
	def processFields(self, fields):
		agency = GovUnits_AgencyLookup.get(fields["agency"])
		if agency:
			fields["agency"] = agency

def processGroupBy(spec):
	# python3 lama.py -q geomac_2000_2018 -w fireyear=2018
	#                 -g fireyear:6/agency:16//count:fireyear:4/sum:gisacres:14,.2f none

	pattern = re.compile("^{field}(?:/{field})*//{stat}:{field}(?:/{stat}:{field})*$".format(
		field="[_0-9A-Za-z]+(?::[<>]?[0-9]*,?(\\.[0-9]+)?[A-Za-z]?)?",
		stat="(?:avg|count|min|max|stddev|sum|var)"))

	if not pattern.match(spec):
		print("Group-by expression doesn't match pattern!")
		return None

	pattern = re.compile("^[<>]?[0-9]*")

	def splitField(field):
		if ":" in field:
			field, printSpec = field.split(":")
			nullSpec = pattern.match(printSpec).group(0)
			return (field, (printSpec, nullSpec))
		return (field, ("", ""))

	groupFields, spec = spec.split("//")
	printFields = [splitField(field) for field in groupFields.split("/")]
	groupFields = ",".join([field for field, printSpec in printFields])
	stats = []

	for spec in spec.split("/"):
		stat, field = spec.split(":", 1)
		field, spec = splitField(field)
		statField = "{}_{}".format(field, stat)
		printFields.append((statField, spec))

		stats.append("%7B{}%7D".format(",".join(["%22{}%22:%22{}%22".format(k, v) for k, v in (
			("statisticType", stat),
			("onStatisticField", field),
			("outStatisticFieldName", statField))])))

	stats = "%5B{}%5D".format(",".join(stats))

	return (groupFields, stats, printFields)

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
	parser.add_argument("-a", "--area", action="store_true")
	parser.add_argument("--count", action="store_true")
	parser.add_argument("--curl")
	parser.add_argument("-d", "--distance", type=float, default=20)
	parser.add_argument("--fields", action="store_true")
	parser.add_argument("--geojson", action="store_true")
	parser.add_argument("--geometry", action="store_true")
	parser.add_argument("-g", "--group-by")
	parser.add_argument("-p", "--precision", type=int, default=5, choices=(4,5,6))
	parser.add_argument("-q", "--query", default="state,county,zip_ca,topo,nps,rd,nlcs,blm,sma,w,wsa")
	parser.add_argument("--raw", action="store_true")
	parser.add_argument("--reprocess", action="store_true")
	parser.add_argument("-v", "--verbose", action="store_true")
	parser.add_argument("-w", "--where")
	parser.add_argument("-x", "--extent", action="store_true")
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

	if args.curl:
		global CURL
		CURL = args.curl

	if args.geometry:
		if args.count:
			print("returnCountOnly and returnGeometry should not both be true!")
			return
		if args.extent:
			print("returnExtentOnly and returnGeometry should not both be true!")
			return

	if args.group_by:
		groupBy = processGroupBy(args.group_by)
		if not groupBy:
			return
	else:
		groupBy = None

	kwargs = {
		"computeArea":          args.area,
		"distance":             args.distance,
		"fieldsOnly":           args.fields,
		"geojson":              args.geojson,
		"groupBy":              groupBy,
		"precision":            args.precision,
		"raw":                  args.raw,
		"reprocess":            args.reprocess,
		"returnCountOnly":      args.count,
		"returnExtentOnly":     args.extent,
		"returnGeometry":       args.geometry,
		"verbose":              args.verbose,
		"where":                args.where,
	}

	queryMap = {
		"aiannh": AIANNH_Query,
		"airnow": AirNow_Query,
		"airnow_contours_combined": AirNowContours_Combined_Query,
		"airnow_contours_ozone": AirNowContours_Ozone_Query,
		"airnow_contours_pm25": AirNowContours_PM25_Query,
		"airnow_current": AirNow_Current_Query,
		"airnow_ozpm": AirNowOzonePM_Query,
		"airnow_ozpm_current": AirNowOzonePM_Current_Query,
		"blm": BLM_Query,
		"ca_parks": CA_StateParksQuery,
		"calfire": CalFire_UnitsQuery,
		"calfire_czu_evac": CalFireCZU_EvacQuery,
		"cnra_conservancy": CNRA_ConservancyQuery,
		"county": TigerCountyQuery,
		"county_census": CensusCountyQuery,
		"county_usfs": USFS_CountyQuery,
		"county_usgs": USGS_CountyQuery,
		"cpad_holdings": CPAD_HoldingsQuery,
		"fire_incidents": USA_WildfireIncidentsQuery,
		"fire_perimeters": USA_WildfirePerimetersQuery,
		"fires_current": NIFC_CurrentPerimetersQuery,
		"fires_current_incidents": NIFC_CurrentIncidentsQuery,
		"firis": FIRIS_Query,
		"fs": USFS_Query,
		"govunits_blm": GovUnits_BLM_Query,
		"govunits_nps": GovUnits_NPS_Query,
		"govunits_usfs": GovUnits_USFS_Query,
		"govunits_w": GovUnits_Wilderness_Query,
		"irwin_inciweb": IRWIN_InciWebQuery,
		"nasa_modis": NASA_MODIS_Query,
		"nasa_viirs": NASA_VIIRS_Query,
		"nlcs": BLM_NLCS_Query,
		"nps": NPS_Query,
		"nps_irma": NPS_IRMA_Query,
		"nv_parks": NV_StateParksQuery,
		"nwr": NWR_Query,
		"rd": USFS_RangerDistrictQuery,
		"scc_parks": SCC_ParksQuery,
		"scc_protected": SCC_ProtectedLandsQuery,
		"slo": SLO_OpenSpaceQuery,
		"sma": BLM_SMA_Query,
		"sonoma_evac_areas": SonomaEvacAreasQuery,
		"sonoma_evac_zones": SonomaEvacZonesQuery,
		"state": TigerStateQuery,
		"topo": USGS_TopoQuery,
		"topoview": USGS_TopoViewQuery,
		"usfs_onda": USFS_OtherNationalDesignatedArea_Query,
		"usfs_sima": USFS_SpecialInterestManagementArea_Query,
		"usfs_w": USFS_Wilderness_Query,
		"w": WildernessQuery,
		"wsa": BLM_WSA_Query,
		"zip_ca": CA_ZIP_Code_Query,
	}

	addFireHistoryQueries(queryMap)
	addGeomacQueries(queryMap)

	for k in args.query.split(","):
		q = queryMap.get(k)
		if q:
			q.query(geometry, **kwargs)
		else:
			print("Unknown query: \"{}\"".format(k))

if __name__ == "__main__":
	main()
