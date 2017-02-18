#!/usr/bin/python
import json
import sys

G = None
XY2LL = None

NAME_SUFFIXES = [
	' Forest Preserve',
	' Forest Reserve',
	' National Conservation Area',
	' National Monument',
	' NM',
	' ONA',
	' Outstanding Natural Area',
]
BLM_CA_NAME_MAP = {
	'BAKERSFIELD FIELD OFFICE':                     'Bakersfield Field Office',
	'Palm Springs S. Coast Field Office':           'Palm Springs Field Office',
	'Palm Springs/S. Coast Field Office':           'Palm Springs Field Office',
	'Palm Springs/SouthCoast Field Office':         'Palm Springs Field Office',

	'Piedras Blancas':                              'Piedras Blancas Light Station',
	'Sand To Snow':                                 'Sand to Snow',
	'Santa Rosa':                                   'Santa Rosa and San Jacinto Mountains',
	'Santa Rosa-San Jacinto Mountains':             'Santa Rosa and San Jacinto Mountains',
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
BLM_CA_OtherAreas = {
	'Berryessa Snow Mountain': {
		'BLM': 'Berryessa_Snow_Mountain.html',
		'D': 'National Monument',
		'FS': 'berryessa-snow-mountain-national-monument',
		'NF': 'mendocino',
		'NFW': 'Mendocino_National_Forest',
		'W': 'Berryessa_Snow_Mountain_National_Monument',
	},
	'California Coastal': {
		'BLM': 'California_Coastal_NM.html',
		'D': 'National Monument',
		'W': 'California_Coastal_National_Monument',
	},
	'Carrizo Plain': {
		'BLM': 'Carrizo_Plain_NM.html',
		'D': 'National Monument',
		'W': 'Carrizo_Plain',
	},
	'Fort Ord': {
		'BLM': 'Fort_Ord_NM.html',
		'D': 'National Monument',
		'W': 'Fort_Ord',
	},
	'Headwaters': {
		'BLM': 'Headwaters_ForestReserve.html',
		'D': 'Forest Reserve',
		'W': 'Headwaters_Forest_Reserve',
	},
	'King Range': {
		'BLM': 'King_Range_NCA.html',
		'D': 'National Conservation Area',
		'W': 'King_Range_(California)',
	},
	'Mojave Trails': {
		'BLM': 'Mojave_Trails.html',
		'D': 'National Monument',
		'W': 'Mojave_Trails_National_Monument',
	},
	'Piedras Blancas Light Station': {
		'BLM': 'PBLS.html',
		'D': 'Outstanding Natural Area',
		'W': 'Piedras_Blancas_Light_Station',
	},
	'Sand to Snow': {
		'BLM': 'Sand-to-Snow.html',
		'D': 'National Monument',
		'FS': 'sand-to-snow-national-monument',
		'NF': 'sbnf',
		'NFW': 'San_Bernardino_National_Forest',
		'W': 'Sand_to_Snow_National_Monument',
	},
	'Santa Rosa and San Jacinto Mountains': {
		'BLM': 'SantaRosa_SanJacintoMtns_NM.html',
		'D': 'National Monument',
		'NF': 'sbnf',
		'NFW': 'San_Bernardino_National_Forest',
		'W': 'Santa_Rosa_and_San_Jacinto_Mountains_National_Monument',
	},
}

HolesToRemove = (
	((-119.767215, 35.250725), (-119.76721, 35.250549), (-119.766644, 35.250555), (-119.766648, 35.250732)),
)

def log(message, *formatArgs):
	print >>sys.stderr, message.format(*formatArgs)

def featureKey(feature):
	p = feature['properties']
	name = p['name']

	d = p.get('D')
	if d is not None:
		name += ' ' + d

		agency = p.get('agency')
		if agency is not None:
			name += ' (' + agency + ')'

	return name

@staticmethod
def stripHoles(geojson):
	geojson['features'].sort(key=featureKey)

	for feature in geojson['features']:
		name = feature['properties']['name']
		coordinates = feature['geometry']['coordinates']

		numPolygons = len(coordinates)
		log('> "{}" has {} polygon{}', featureKey(feature), numPolygons, '' if numPolygons == 1 else 's')

		for polygon in coordinates:
			for subpolygon in polygon:
				assert subpolygon[0] == subpolygon[-1]
			if len(polygon) > 1:
				holes = []
				for subpolygon in polygon[1:]:
					hole = tuple([tuple(point) for point in subpolygon[:-1]])
					if hole in HolesToRemove:
						log('\tRemoving the following hole: {}', hole)
					else:
						log('\tKeeping the {}-point hole starting/ending at {}',
							len(subpolygon) - 1, subpolygon[0])
						holes.append(subpolygon)
				polygon[1:] = holes

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

def getName(name):
	for suffix in NAME_SUFFIXES:
		if name.endswith(suffix):
			name = name[:-len(suffix)]
			break
	return BLM_CA_NAME_MAP.get(name, name)

@staticmethod
def stripPropertiesAA(o):
	name = getName(o[G.nameField])
	parent = getName(o['PARENT_NAME'])

	if name.endswith(' Field Office'):
		assert name[:-13] in BLM_CA_FieldOffices
		assert parent.endswith(' District')
		assert parent[:-9] in BLM_CA_Districts
		if G is BLM_CA_SA:
			return None
	else:
		assert name in BLM_CA_OtherAreas
		if parent.endswith(' Field Office'):
			assert parent[:-13] in BLM_CA_FieldOffices
		elif parent.endswith(' District'):
			assert parent[:-9] in BLM_CA_Districts
		else:
			sys.exit('Parent for "{}" must be a Field Office or District'.format(name))
		if G is BLM_CA_AA:
			return None

	p = {'name': name, 'parent': parent}
	if G is BLM_CA_SA:
		p.update(BLM_CA_OtherAreas[name])
	return p

@staticmethod
def stripPropertiesFO(o):
	name = getName(o[G.nameField])

	if name.endswith(' Field Office'):
		assert name[:-13] in BLM_CA_FieldOffices
	elif name.endswith(' District Office'):
		assert name[:-16] in BLM_CA_Districts
	else:
		if name in BLM_CA_OtherAreas:
			landType = BLM_CA_OtherAreas[name]['D']
			sep = ' ' if len(name) < 23 else '<br>'
			name = '{}{}{}'.format(name, sep, landType)
		else:
			assert name in BLM_CA_OtherOffices

	return {'name': name}

@staticmethod
def stripPropertiesNM(o):
	name = getName(o[G.nameField])

	assert name in BLM_CA_OtherAreas

	p = {'name': name}
	p.update(BLM_CA_OtherAreas[name])

	agency = o.get('AGENCY_CODE_ca')
	if 'NF' in p:
		assert agency == 'BLM' or agency == 'USFS'
		p['agency'] = agency
	else:
		assert agency == 'BLM'

	subunit = o.get('NLCS_SUBUNIT_ID_ca')
	assert subunit in (0, 1, 2)
	if subunit != 0:
		p['subunit'] = subunit

	if name == 'California Coastal' and subunit == 1:
		return p if G is BLM_CA_CCNM else None

	return p if G is BLM_CA_NM else None

class BLM_CA_AA(object):
	#
	# Administrative Areas (Field Office boundaries)
	#
	filename = 'blm/ca/admu_ofc_poly'
	nameField = 'ADMU_NAME'
	stripGeometry = stripMultiPolygon
	stripProperties = stripPropertiesAA
	postprocess = stripHoles

class BLM_CA_SA(BLM_CA_AA):
	#
	# Conservation Lands (e.g. National Monument boundaries)
	# Not as correct or complete as BLM_CA_NM
	#
	pass

class BLM_CA_FO(object):
	#
	# Field Offices (Field/District/State Office locations)
	#
	filename = 'blm/ca/admu_ofc_pt'
	nameField = 'ADMU_NAME'
	stripGeometry = stripPoint
	stripProperties = stripPropertiesFO
	postprocess = stripDuplicates

class BLM_CA_NM(object):
	#
	# Conservation Lands (e.g. National Monument boundaries)
	# More correct and complete than BLM_CA_SA
	#
	filename = 'blm/ca/nlcs_nm_nca_poly'
	nameField = 'NLCS_NAME'
	stripGeometry = stripMultiPolygon
	stripProperties = stripPropertiesNM
	postprocess = stripHoles

class BLM_CA_CCNM(BLM_CA_NM):
	#
	# California Coastal National Monument, Subunit 1
	# Thousands of small polygons all along the coast!
	#
	pass

def stripHook(o):
	if 'coordinates' in o:
		return G.stripGeometry(o['type'], o['coordinates'])

	if G.nameField in o:
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

def parseArgs():
	global G, XY2LL

	modeMap = {
		'blm/ca/aa':    BLM_CA_AA,
		'blm/ca/sa':    BLM_CA_SA,
		'blm/ca/fo':    BLM_CA_FO,
		'blm/ca/nm':    BLM_CA_NM,
		'blm/ca/ccnm':  BLM_CA_CCNM,
	}

	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('mode', choices=sorted(modeMap.keys()))
	parser.add_argument('--xy2ll', choices=('ca', 'sca'))
	args = parser.parse_args()

	G = modeMap[args.mode]

	if args.xy2ll:
		import geo
		if args.xy2ll == 'ca':
			XY2LL = geo.CaliforniaAlbers().inverse
		elif args.xy2ll == 'sca':
			R = geo.GRS_1980_Ellipsoid.a
			XY2LL = geo.AlbersSphere(-120.0, 0.0, 34.0, 40.5, R).setFalseNorthing(-4000000.0).inverse

if __name__ == '__main__':
	parseArgs()
	strip()
