#!/usr/bin/python
import json
import sys

def Feature(name2, id, **kwargs):
	kwargs.update({'name2': name2, 'id': id})
	return {'type': 'Feature',
		'properties': kwargs,
		'geometry': {'type': 'MultiPolygon', 'coordinates': []}}

FeatureFlag_SetBounds   = 0x0001 # has partial subunits; set/extend item.bounds for this feature
FeatureFlag_SkipBounds  = 0x0002 # don't extend parent/ancestor bounds for this feature

G = None
XY2LL = None
SecondPoints = set()
HolesToRemove = ()
PolygonsToRemove = (
#
# Why are the following areas included as part of the Golden Gate National Recreation Area?
#
(-122.519694, 37.533448), # includes Montara SMR and Pillar Point SMCA
(-122.519702, 37.533489), # includes Point Montara Light
(-122.517480, 37.539958), # small part of the coast near Montara
(-122.509973, 37.584858), # near Devil's Slide
(-122.513501, 37.594477), # Pedro Point Headlands (http://pedropointheadlands.org/)
(-122.499031, 37.600852), # Pacifica State Beach
(-122.425814, 37.874280), # Angel Island State Park
#
(-121.600877, 40.348154), # Lassen Volcanic National Park Headquarters in Mineral, CA
)
SeparateFeatures = {
#
# NPS -> CA -> Channel Islands National Park
#
(-119.037070, 33.448103): Feature('Santa Barbara Island', 'sb', W2='Santa_Barbara_Island'),
(-120.270728, 34.001945): Feature('Santa Rosa Island', 'sr', W2='Santa_Rosa_Island_(California)'),
(-119.339176, 34.022787): Feature('Anacapa Island', 'ac', W2='Anacapa_Island'),
(-120.472997, 34.030254): Feature('San Miguel Island', 'sm', W2='San_Miguel_Island'),
(-119.949952, 34.060441): Feature('Santa Cruz Island', 'sc', W2='Santa_Cruz_Island'),
(-119.266819, 34.248069): Feature('Headquarters', 'hq', flags=FeatureFlag_SkipBounds),
#
# NPS -> CA -> Golden Gate National Recreation Area
#
(-122.486926, 37.642721): Feature('Milagra Ridge', 'mr', W2='Milagra_Ridge'),
(-122.509305, 37.776285): Feature('Sutro Heights Park', 'sh', W2='Sutro_Heights_Park'),
(-122.424849, 37.832023): Feature('Alcatraz Island', 'az', W2='Alcatraz_Island'),
#
# NPS -> CA -> Lava Beds National Monument
#
(-121.394089, 41.851072): Feature('Petroglyph Section', 'p', W2='Petroglyph_Point_Archeological_Site'),
}

def log(message, *formatArgs):
	print >>sys.stderr, message.format(*formatArgs)

def err(*args):
	log(*args)
	sys.exit()

def getMapLink(point, numPoints):
	return 'pmap.html?o={}&ll={:f},{:f} {:>14}'.format(G.id, point[1], point[0],
		'({} points)'.format(numPoints))

def featureKey(feature):
	return feature['properties']['name']

def getBounds(points):
	minLng, minLat = maxLng, maxLat = points[0]

	for lng, lat in points[1:-1]:
		if lng < minLng:
			minLng = lng
		elif lng > maxLng:
			maxLng = lng
		if lat < minLat:
			minLat = lat
		elif lat > maxLat:
			maxLat = lat

	return minLng, minLat, maxLng, maxLat

def stripHoles(geojson):
	strippedFeatures = []
	geojson['features'].sort(key=featureKey)

	for feature in geojson['features']:
		name = feature['properties']['name']
		coordinates = feature['geometry']['coordinates']

		numPolygons = len(coordinates)
		log('> "{}" has {} polygon{}', featureKey(feature), numPolygons, '' if numPolygons == 1 else 's')

		polygons = []
		numSmallPolygons = 0
		separateFeatures = []

		for polygon in coordinates:
			numPoints = len(polygon[0]) - 1
			for subpolygon in polygon:
				assert subpolygon[0] == subpolygon[-1]

			minLng, minLat, maxLng, maxLat = getBounds(polygon[0])
			if maxLng - minLng < 0.00025 and maxLat - minLat < 0.00025:
				log('\tRemoving small polygon with bounds {:f},{:f}, {:f},{:f} ({} points)',
					minLat, minLng, maxLat, maxLng, numPoints)
				numSmallPolygons += 1
				continue

			secondPoint = tuple(polygon[0][1])
			if secondPoint in SecondPoints:
				err('2nd point {} not unique!', secondPoint)
			SecondPoints.add(secondPoint)

			mapLink = getMapLink(secondPoint, numPoints)

			if secondPoint in PolygonsToRemove:
				log('\t{} REMOVING', mapLink)
				continue

			if secondPoint in SeparateFeatures:
				f = SeparateFeatures[secondPoint]
				p = f['properties']
				log('\t{} ADDING to "{}"', mapLink, p['name2'])
				p.update(feature['properties'])
				c = f['geometry']['coordinates']
				c.append(polygon)
				if len(c) == 1:
					separateFeatures.append(f)
				secondPoint = None
			else:
				log('\t{}', mapLink)

			if len(polygon) > 1:
				holes = []
				for subpolygon in polygon[1:]:
					firstPoint = tuple(subpolygon[0])
					mapLink = getMapLink(firstPoint, len(subpolygon) - 1)
					if firstPoint in HolesToRemove:
						log('\t\tHole at {} REMOVING', mapLink)
					else:
						log('\t\tHole at {}', mapLink)
						holes.append(subpolygon)
				polygon[1:] = holes

			if secondPoint is not None:
				polygons.append(polygon)

		if numSmallPolygons > 0:
			log('\tRemoved {} small polygon{}', numSmallPolygons, '' if numSmallPolygons == 1 else 's')

		coordinates[:] = polygons

		if polygons:
			strippedFeatures.append(feature)
			if separateFeatures:
				flags = feature['properties'].get('flags', 0) | FeatureFlag_SetBounds
				log('\tSetting flags to {}', flags)
				feature['properties']['flags'] = flags

		strippedFeatures.extend(separateFeatures)

	geojson['features'] = strippedFeatures

@staticmethod
def postprocessNPS(geojson):
	featureMap = {}

	for feature in geojson['features']:
		properties = feature['properties']
		name = properties['name']
		geometry = feature['geometry']

		if name in featureMap:
			log('Duplicate feature for "{}"', name)
			continue

		featureMap[name] = feature
		if geometry['type'] == 'Polygon':
			polygon = geometry['coordinates']
			geometry['type'] = 'MultiPolygon'
			geometry['coordinates'] = [polygon]

	stripHoles(geojson)

	prevName = None
	for feature in geojson['features']:
		p = feature['properties']
		name = p['name']
		code = p['code']
		hasName2 = 'name2' in p
		if code in NPS_Codes:
			p['code'] = NPS_Codes[code]
		if name != prevName:
			log('\t\t{} ={}', name, code)
			prevName = name
		else:
			assert hasName2
		if hasName2:
			log('\t\t\t{} ={}', p['name2'], p['id'])
			del p['id']

@staticmethod
def mergePolygons(geojson):
	featureMap = {}
	featureList = []

	for feature in geojson['features']:
		properties = feature['properties']
		name = properties['name']
		geometry = feature['geometry']
		assert geometry['type'] == 'Polygon'
		polygon = geometry['coordinates']

		if name in featureMap:
			feature = featureMap[name]
			assert properties == feature['properties']
			geometry = feature['geometry']
			assert geometry['type'] == 'MultiPolygon'
			geometry['coordinates'].append(polygon)
		else:
			featureList.append(feature)
			featureMap[name] = feature
			geometry['type'] = 'MultiPolygon'
			geometry['coordinates'] = [polygon]

	geojson['features'] = featureList
	stripHoles(geojson)

@staticmethod
def stripPolygon(geoType, coordinates):
	if geoType == 'Polygon':
		if XY2LL:
			coordinates = [[[round(c, 6) for c in XY2LL(x, y)] for x, y in subpolygon]
				for subpolygon in coordinates]
		else:
			coordinates = [[(round(x, 6), round(y, 6)) for x, y in subpolygon]
				for subpolygon in coordinates]
	elif geoType == 'MultiPolygon':
		if XY2LL:
			coordinates = [[[[round(c, 6) for c in XY2LL(x, y)] for x, y in subpolygon]
				for subpolygon in polygon]
				for polygon in coordinates]
		else:
			coordinates = [[[(round(x, 6), round(y, 6)) for x, y in subpolygon]
				for subpolygon in polygon]
				for polygon in coordinates]
	else:
		sys.exit('Unexpected geometry type: "{}"'.format(geoType))

	return {'type': geoType, 'coordinates': coordinates}

NPS_Wikipedia = {
	'fopo': 'Fort_Point,_San_Francisco',
	'manz': 'Manzanar',
	'redw': 'Redwood_National_and_State_Parks',
	'rori': 'Rosie_the_Riveter/World_War_II_Home_Front_National_Historical_Park',
	'whis': 'Whiskeytown%E2%80%93Shasta%E2%80%93Trinity_National_Recreation_Area',
}
NPS_Names = {
	'cech': 'Cesar E. Chavez National Monument',
	'jodr': 'John D. Rockefeller Jr.|Memorial Parkway',
	'libi': 'Little Bighorn Battlefield|National Monument',
	'poch': 'Port Chicago Naval Magazine|National Memorial',
	'rori': 'Rosie the Riveter|World War II Home Front|National Historical Park',
	'safr': 'San Francisco Maritime|National Historical Park',
	'samo': 'Santa Monica Mountains|National Recreation Area',
	'whis': 'Whiskeytown-Shasta-Trinity|National Recreation Area|(Whiskeytown Unit)',
}
NPS_Codes = {
	'gsdp': 'grsa',
	'kica': 'seki',
	'sequ': 'seki',
}

@staticmethod
def stripPropertiesNPS(o):
	if o['STATE'] != G.state:
		return None

	name = o['UNIT_NAME']
	code = o['UNIT_CODE'].lower()

	if name == 'Great Sand Dunes National Preserve':
		code = 'gsdp'
	if code in NPS_Names:
		name = NPS_Names[code]

	p = {'name': name, 'code': code}

	if code in NPS_Wikipedia:
		p['W'] = NPS_Wikipedia[code]

	return p

UC_Names = (
	'Sweeney Granite Mountains Desert Research Center',
)
UC_LongNames = {
	'Sweeney Granite Mountains Desert Research Center':
		('Sweeney Granite Mountains', 'Desert Research Center'),
}
UC_Campuses = (
	'UC Riverside',
)
UC_Counties = (
	'San Bernardino County',
)

@staticmethod
def stripPropertiesUC(o):
	name = o['Name']
	campus = o['Campus']
	county = o['County']

	assert name in UC_Names
	assert campus in UC_Campuses
	assert county in UC_Counties

	p = {'campus': campus}
	if name in UC_LongNames:
		p['name'], p['name2'] = UC_LongNames[name]
	else:
		p['name'] = name

	return p

class NPS(object):
	#
	# Boundaries for land managed by the National Park Service
	#
	filename = 'nps_boundary'
	nameField = 'UNIT_NAME'
	stripGeometry = stripPolygon
	stripProperties = stripPropertiesNPS
	postprocess = postprocessNPS

class UC_GRANITES(object):
	#
	# Boundary for the Sweeney Granite Mountains Desert Research Center
	#
	filename = 'uc/Sweeney_Granite_Mountains_Boundary'
	nameField = 'Campus'
	stripGeometry = stripPolygon
	stripProperties = stripPropertiesUC
	postprocess = mergePolygons

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
		'uc/granites':          UC_GRANITES,
	}

	for state in ('az', 'ca', 'co', 'id', 'mt', 'nm', 'nv', 'or', 'ut', 'wa', 'wy'):
		modeMap['nps/' + state] = NPS

	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('mode', choices=sorted(modeMap.keys()))
	parser.add_argument('--xy2ll', choices=('ca', 'sca'))
	args = parser.parse_args()

	G = modeMap[args.mode]
	G.id = args.mode.replace('/', '_')
	if G is NPS:
		G.state = args.mode[-2:].upper()

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
