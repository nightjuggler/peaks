#!/usr/bin/python
import json
import sys

XY2LL = None

PalmSpringsFO = 'Palm Springs Field Office'
PiedrasBlancas = 'Piedras Blancas Light Station<br>Outstanding Natural Area'
SantaRosaSanJacintoNM = 'Santa Rosa and San Jacinto Mountains<br>National Monument'

nameMap = {
	'BAKERSFIELD FIELD OFFICE':                     'Bakersfield Field Office',
	'Headwaters Forest Preserve':                   'Headwaters Forest Reserve',
	'Palm Springs S. Coast Field Office':           PalmSpringsFO,
	'Palm Springs/S. Coast Field Office':           PalmSpringsFO,
	'Palm Springs/SouthCoast Field Office':         PalmSpringsFO,
	'Piedras Blancas Light Station ONA':            PiedrasBlancas,
	'Santa Rosa National Monument':                 SantaRosaSanJacintoNM,
	'Santa Rosa and San Jacinto Mountains NM':      SantaRosaSanJacintoNM,
}
BLM_CA_Districts = (
	'Northern California',
	'Central California',
	'California Desert',
)
BLM_CA_FieldOffices = (
	'Applegate',
	'Arcata',
	'Bakersfield',
	'Barstow',
	'Bishop',
	'Central Coast',
	'Eagle Lake',
	'El Centro',
	'Mother Lode',
	'Needles',
	'Palm Springs',
	'Redding',
	'Ridgecrest',
	'Ukiah',
)
BLM_CA_OtherOffices = (
	'California State Office',
	'Surprise Field Station',
)
BLM_CA_NLCS_Prefix = 'https://www.blm.gov/nlcs_web/sites/ca/st/en/prog/nlcs/'
BLM_CA_OtherAreas = {
	'Berryessa Snow Mountain National Monument': {
		'BLM': 'Berryessa_Snow_Mountain.html',
		'W': 'Berryessa_Snow_Mountain_National_Monument',
	},
	'Carrizo Plain National Monument': {
		'BLM': 'Carrizo_Plain_NM.html',
		'W': 'Carrizo_Plain',
	},
	'Fort Ord National Monument': {
		'BLM': 'Fort_Ord_NM.html',
		'W': 'Fort_Ord',
	},
	'Headwaters Forest Reserve': {
		'BLM': 'Headwaters_ForestReserve.html',
		'W': 'Headwaters_Forest_Reserve',
	},
	'King Range National Conservation Area': {
		'BLM': 'King_Range_NCA.html',
		'W': 'King_Range_(California)',
	},
	'Mojave Trails National Monument': {
		'BLM': 'Mojave_Trails.html',
		'W': 'Mojave_Trails_National_Monument',
	},
	PiedrasBlancas: {
		'BLM': 'PBLS.html',
		'W': 'Piedras_Blancas_Light_Station',
	},
	'Sand to Snow National Monument': {
		'BLM': 'Sand-to-Snow.html',
		'W': 'Sand_to_Snow_National_Monument',
	},
	SantaRosaSanJacintoNM: {
		'BLM': 'SantaRosa_SanJacintoMtns_NM.html',
		'W': 'Santa_Rosa_and_San_Jacinto_Mountains_National_Monument',
	},
}

HolesToRemove = (
	((-119.767215, 35.250725), (-119.76721, 35.250549), (-119.766644, 35.250555), (-119.766648, 35.250732)),
)

def log(message, *formatArgs):
	print >>sys.stderr, message.format(*formatArgs)

def featureKey(feature):
	return feature['properties']['name']

@staticmethod
def stripHoles(geojson):
	for feature in geojson['features']:
		name = feature['properties']['name']
		coordinates = feature['geometry']['coordinates']

		for polygon in coordinates:
			for subpolygon in polygon:
				assert subpolygon[0] == subpolygon[-1]
			if len(polygon) > 1:
				holes = []
				for subpolygon in polygon[1:]:
					hole = tuple([tuple(point) for point in subpolygon[:-1]])
					if hole in HolesToRemove:
						log('Removing the following hole for "{}": {}', name, hole)
					else:
						log('Keeping the {}-point hole starting/ending at {} for "{}"',
							len(subpolygon) - 1, subpolygon[0], name)
						holes.append(subpolygon)
				polygon[1:] = holes

	geojson['features'].sort(key=featureKey)

def nameRank(name):
	if name.endswith(' Field Office'):
		return 0
	if name.endswith(' Field Station'):
		return 1
	if name.endswith(' State Office'):
		return 2
	if name.endswith(' District Office'):
		return 3
	return 4

@staticmethod
def stripDuplicates(geojson):
	points = {}
	sep = ' &amp;<br>'
	for feature in geojson['features']:
		name = feature['properties']['name']
		point = tuple(feature['geometry']['coordinates'])
		if point in points:
			props = points[point]['properties']
			log('"{}" has the same location as "{}"', name, props['name'])
			nameList = [(nameRank(n), n) for n in props['name'].split(sep)]
			nameList.append((nameRank(name), name))
			nameList.sort()
			if nameList[0][0] < 4:
				while nameList[-1][0] >= 4:
					del nameList[-1]
			props['name'] = sep.join([n for rank, n in nameList])
			log('Changing name to "{}"', props['name'])
		else:
			points[point] = feature

	geojson['features'] = points.values()

@staticmethod
def stripMultiPolygon(geoType, coordinates):
	if geoType != 'MultiPolygon':
		sys.exit('Unexpected geometry type: "{}"'.format(geoType))

	if XY2LL:
		coordinates = [[[[round(c, 6) for c in XY2LL(x, y)] for x, y in subpolygon]
			for subpolygon in polygon]
			for polygon in coordinates]
	else:
		coordinates = [[[(round(x, 6), round(y, 6)) for x, y in subpolygon]
			for subpolygon in polygon]
			for polygon in coordinates]

	return {'type': 'MultiPolygon', 'coordinates': coordinates}

@staticmethod
def stripPoint(geoType, coordinates):
	if geoType != 'Point':
		sys.exit('Unexpected geometry type: "{}"'.format(geoType))

	if XY2LL:
		coordinates = [round(c, 6) for c in XY2LL(*coordinates)]
	else:
		coordinates = [round(c, 6) for c in coordinates]

	return {'type': 'Point', 'coordinates': coordinates}

@staticmethod
def stripPropertiesAA(o):
	name, parent = o['ADMU_NAME'], o['PARENT_NAME']
	if name in nameMap:
		name = nameMap[name]
	if parent in nameMap:
		parent = nameMap[parent]
	if name.endswith(' Field Office'):
		assert name[:-13] in BLM_CA_FieldOffices
		assert parent.endswith(' District')
		assert parent[:-9] in BLM_CA_Districts
	else:
		assert name in BLM_CA_OtherAreas
		if parent.endswith(' Field Office'):
			assert parent[:-13] in BLM_CA_FieldOffices
		elif parent.endswith(' District'):
			assert parent[:-9] in BLM_CA_Districts
		else:
			sys.exit('Parent for "{}" must be a Field Office or District'.format(name))
		return None
	return {'name': name, 'parent': parent}

@staticmethod
def stripPropertiesSA(o):
	name, parent = o['ADMU_NAME'], o['PARENT_NAME']
	if name in nameMap:
		name = nameMap[name]
	if parent in nameMap:
		parent = nameMap[parent]
	if name.endswith(' Field Office'):
		assert name[:-13] in BLM_CA_FieldOffices
		assert parent.endswith(' District')
		assert parent[:-9] in BLM_CA_Districts
		return None
	else:
		assert name in BLM_CA_OtherAreas
		if parent.endswith(' Field Office'):
			assert parent[:-13] in BLM_CA_FieldOffices
		elif parent.endswith(' District'):
			assert parent[:-9] in BLM_CA_Districts
		else:
			sys.exit('Parent for "{}" must be a Field Office or District'.format(name))
	o = {'name': name, 'parent': parent}
	o.update(BLM_CA_OtherAreas[name])
	return o

@staticmethod
def stripPropertiesFO(o):
	name = o['ADMU_NAME']
	if name in nameMap:
		name = nameMap[name]
	if name.endswith(' Field Office'):
		assert name[:-13] in BLM_CA_FieldOffices
	elif name.endswith(' District Office'):
		assert name[:-16] in BLM_CA_Districts
	else:
		assert name in BLM_CA_OtherAreas or name in BLM_CA_OtherOffices

	return {'name': name}

class BLM_CA_AA(object):
	#
	# Administrative Areas (Field Office boundaries)
	#
	filename = 'blm/ca/admu_ofc_poly'
	stripGeometry = stripMultiPolygon
	stripProperties = stripPropertiesAA
	postprocess = stripHoles

class BLM_CA_SA(object):
	#
	# Special Areas (e.g. National Monument boundaries)
	#
	filename = 'blm/ca/admu_ofc_poly'
	stripGeometry = stripMultiPolygon
	stripProperties = stripPropertiesSA
	postprocess = stripHoles

class BLM_CA_FO(object):
	#
	# Field Offices (Field Office locations)
	#
	filename = 'blm/ca/admu_ofc_pt'
	stripGeometry = stripPoint
	stripProperties = stripPropertiesFO
	postprocess = stripDuplicates

G = None

def stripHook(o):
	if 'coordinates' in o:
		return G.stripGeometry(o['type'], o['coordinates'])

	if 'ADMU_NAME' in o:
		return G.stripProperties(o)

	if 'properties' in o:
		oType = o['type']
		if oType == 'Feature':
			oProperties = o['properties']
			if oProperties is None:
				return None
			return {'type': oType, 'properties': oProperties, 'geometry': o['geometry']}
		if oType == 'name':
			return None
		sys.exit('Unexpected object with properties has type "{}"'.format(oType))

	if 'features' in o:
		oType = o['type']
		if oType == 'FeatureCollection':
			return {'type': oType, 'features': [f for f in o['features'] if f is not None]}
		sys.exit('Unexpected object with features has type "{}"'.format(oType))

	if 'name' in o:
		return None

	sys.exit('Unexpected object has the following keys: {}'.format(', '.join(
		['"{}"'.format(k) for k in o.iterkeys()])))

def strip():
	filename = 'data/{}_{}.json'.format(G.filename, 'xy' if XY2LL else 'll')
	log('Opening {}', filename)

	jsonFile = open(filename)
	data = json.load(jsonFile, object_hook=stripHook)
	jsonFile.close()

	G.postprocess(data)
	json.dump(data, sys.stdout, separators=(',', ':'))

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('mode', choices=('blm_ca_aa', 'blm_ca_sa', 'blm_ca_fo'))
	parser.add_argument('--xy2ll', choices=('ca', 'sca'))
	args = parser.parse_args()

	if args.mode == 'blm_ca_aa':
		G = BLM_CA_AA
	elif args.mode == 'blm_ca_sa':
		G = BLM_CA_SA
	elif args.mode == 'blm_ca_fo':
		G = BLM_CA_FO

	if args.xy2ll:
		import geo
		if args.xy2ll == 'ca':
			XY2LL = geo.CaliforniaAlbers().inverse
		elif args.xy2ll == 'sca':
			R = geo.GRS_1980_Ellipsoid.a
			XY2LL = geo.AlbersSphere(-120.0, 0.0, 34.0, 40.5, R).setFalseNorthing(-4000000.0).inverse
	strip()
