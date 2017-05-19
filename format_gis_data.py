#!/usr/bin/python
import json
import re
import sys

def Feature(name2, id2, **kwargs):
	kwargs.update({'name2': name2, 'id2': id2})
	return {'type': 'Feature',
		'properties': kwargs,
		'geometry': {'type': 'MultiPolygon', 'coordinates': []}}

FeatureFlag_SetBounds   = 0x0001 # has partial subunits; set/extend item.bounds for this feature
FeatureFlag_SkipBounds  = 0x0002 # don't extend parent/ancestor bounds for this feature

NPS_NezPerce_BuffaloEddy = Feature('Buffalo Eddy', 'be')
NPS_NezPerce_Spalding = Feature('Spalding', 'sp', W2='Spalding,_Idaho')

G = None
XY2LL = None
SecondPoints = set()
HolesToRemove = ()
PolygonsToRemove = {
'nps_ca': (
#
# Golden Gate National Recreation Area
#
(-122.519694, 37.533448), # coastal area including Fitzgerald Marine Reserve
(-122.519702, 37.533489), # coastal area including Point Montara Light
(-122.517480, 37.539958), # small area near Montara
(-122.509973, 37.584858), # small area near Devil's Slide
(-122.513501, 37.594477), # Pedro Point Headlands
(-122.499031, 37.600852), # Pacifica State Beach
(-122.425814, 37.874280), # Angel Island State Park
#
# Lassen Volcanic National Park
#
(-121.600877, 40.348154), # Headquarters in Mineral, CA
#
# World War II Valor in the Pacific National Monument
#
(-157.954368, 21.363719), # HI
(-157.954916, 21.363748), # HI
(-157.949648, 21.364684), # HI
(-157.937538, 21.366363), # HI
(-157.936582, 21.367199), # HI
(-157.937516, 21.369237), # HI
),
'nps_hi': (
#
# World War II Valor in the Pacific National Monument
#
(-121.378507, 41.887758), # Tule Lake Unit (CA)
),
'nps_id': (
#
# Nez Perce National Historical Park
#
(-109.206051, 48.373056), # MT
(-117.224839, 45.337427), # OR
(-117.520354, 45.570223), # OR
#
# Minidoka National Historic Site
#
(-122.507464, 47.614825), # Bainbridge Island Japanese American Exclusion Memorial (WA)
),
'nps_mt': (
#
# Nez Perce National Historical Park
#
(-116.267642, 45.803354), # ID
(-115.959301, 46.076778), # ID
(-116.918370, 46.170823), # ID
(-116.935269, 46.173151), # ID
(-116.004092, 46.203655), # ID
(-116.818266, 46.445164), # ID
(-116.818326, 46.446846), # ID
(-116.817829, 46.446914), # ID
(-116.814847, 46.448688), # ID
(-116.810456, 46.449968), # ID
(-116.329538, 46.500551), # ID
(-117.224839, 45.337427), # OR
(-117.520354, 45.570223), # OR
),
'nps_nm': (
#
# Manhattan Project National Historical Park
#
(-84.317198, 35.928011), # Oak Ridge, TN: X-10 Graphite Reactor
(-84.394445, 35.938672), # Oak Ridge, TN: K-25 Building
(-84.256801, 35.984691), # Oak Ridge, TN: Y-12 Building 9204-3
(-84.255495, 35.985871), # Oak Ridge, TN: Y-12 Building 9731
(-119.387098, 46.587399), # Hanford, WA: Hanford High School
(-119.646295, 46.628954), # Hanford, WA: B Reactor
(-119.715131, 46.638641), # Hanford, WA: Bruggemann's Warehouse
(-119.618684, 46.644369), # Hanford, WA: Allard Pump House
(-119.478732, 46.660534), # Hanford, WA: White Bluffs Bank
),
'nps_or': (
#
# Nez Perce National Historical Park
#
(-116.267642, 45.803354), # ID
(-115.959301, 46.076778), # ID
(-116.918370, 46.170823), # ID
(-116.935269, 46.173151), # ID
(-116.004092, 46.203655), # ID
(-116.818266, 46.445164), # ID
(-116.818326, 46.446846), # ID
(-116.817829, 46.446914), # ID
(-116.814847, 46.448688), # ID
(-116.810456, 46.449968), # ID
(-116.329538, 46.500551), # ID
(-109.206051, 48.373056), # MT
),
'nps_wa': (
#
# Manhattan Project National Historical Park
#
(-84.317198, 35.928011), # Oak Ridge, TN: X-10 Graphite Reactor
(-84.394445, 35.938672), # Oak Ridge, TN: K-25 Building
(-84.256801, 35.984691), # Oak Ridge, TN: Y-12 Building 9204-3
(-84.255495, 35.985871), # Oak Ridge, TN: Y-12 Building 9731
(-106.264959, 35.840842), # Los Alamos, NM: Pajarito Site
(-106.345095, 35.843839), # Los Alamos, NM: V-Site
(-106.347393, 35.855718), # Los Alamos, NM: Gun Site
#
# Minidoka National Historic Site
#
(-114.239971, 42.678247), # ID
(-114.249704, 42.692788), # ID
#
# Nez Perce National Historical Park
#
(-116.267642, 45.803354), # ID
(-115.959301, 46.076778), # ID
(-116.918370, 46.170823), # ID
(-116.935269, 46.173151), # ID
(-116.004092, 46.203655), # ID
(-116.818266, 46.445164), # ID
(-116.818326, 46.446846), # ID
(-116.817829, 46.446914), # ID
(-116.814847, 46.448688), # ID
(-116.810456, 46.449968), # ID
(-116.329538, 46.500551), # ID
(-109.206051, 48.373056), # MT
(-117.224839, 45.337427), # OR
(-117.520354, 45.570223), # OR
),
}
SeparateFeatures = {
#
# NPS -> AZ -> Montezuma Castle National Monument
#
(-111.825721, 34.613346): Feature('Montezuma Castle', 'castle'),
(-111.749979, 34.645673): Feature('Montezuma Well', 'well', W2='Montezuma_Well', flags=FeatureFlag_SkipBounds),
#
# NPS -> AZ -> Navajo National Monument
#
(-110.817732, 36.670105): Feature('Inscription House', 'ih', flags=FeatureFlag_SkipBounds),
(-110.537306, 36.689120): Feature('Betatakin', 'bt'),
(-110.501645, 36.764945): Feature('Keet Seel', 'ks', flags=FeatureFlag_SkipBounds),
#
# NPS -> AZ -> Saguaro National Park
#
(-110.498832, 32.230070): Feature('Rincon Mountain District', 'rmd'),
(-111.113908, 32.315900): Feature('Tucson Mountain District', 'tmd'),
#
# NPS -> AZ -> Tumacacori National Historical Park
#
(-110.901675, 31.408678): Feature('Los Santos Angeles de Guevavi', 'g',
	W2='Mission_Los_Santos_%C3%81ngeles_de_Guevavi', flags=FeatureFlag_SkipBounds),
(-110.959223, 31.454015): Feature('San Cayetano de Calabazas', 'c',
	W2='Mission_San_Cayetano_de_Calabazas', flags=FeatureFlag_SkipBounds),
(-111.043785, 31.569337): Feature('San Jose de Tumacacori', 't',
	W2='Mission_San_Jos%C3%A9_de_Tumac%C3%A1cori'),
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
#
# NPS -> CA -> World War II Valor in the Pacific National Monument
#
(-121.378507, 41.887758): Feature('Tule Lake Unit', 'tule',
	W2='Tule_Lake_Unit,_World_War_II_Valor_in_the_Pacific_National_Monument'),
#
# NPS -> ID -> Nez Perce National Historical Park
#
(-116.267642, 45.803354): Feature('White Bird Battlefield', 'wb', W2='Battle_of_White_Bird_Canyon'),
(-115.959301, 46.076778): Feature('Clearwater Battlefield', 'cw', W2='Battle_of_the_Clearwater'),
(-116.918370, 46.170823): NPS_NezPerce_BuffaloEddy,
(-116.935269, 46.173151): NPS_NezPerce_BuffaloEddy,
(-116.004092, 46.203655): Feature('Heart of the Monster', 'hm'),
(-116.818266, 46.445164): NPS_NezPerce_Spalding,
(-116.818326, 46.446846): NPS_NezPerce_Spalding,
(-116.817829, 46.446914): NPS_NezPerce_Spalding,
(-116.814847, 46.448688): NPS_NezPerce_Spalding,
(-116.810456, 46.449968): NPS_NezPerce_Spalding,
(-116.329538, 46.500551): Feature('Canoe Camp', 'cc'),
#
# NPS -> MT -> Little Bighorn Battlefield National Monument
#
(-107.384146, 45.521082): Feature('Reno-Benteen Battlefield', 'rb'),
(-107.443667, 45.564359): Feature('Custer Battlefield', 'c'),
#
# NPS -> MT -> Nez Perce National Historical Park
#
(-109.206051, 48.373056): Feature('Bear Paw Battlefield', 'bp', W2='Battle_of_Bear_Paw'),
#
# NPS -> NM -> Bandelier National Monument
#
(-106.206648, 35.867916): Feature('Tsankawi Section', 't', W2='Tsankawi'),
#
# NPS -> NM -> Carlsbad Caverns National Park
#
(-104.460401, 32.109626): Feature('Rattlesnake Springs', 'rs', W2='Rattlesnake_Springs_Historic_District'),
#
# NPS -> NM -> Chaco Culture National Historical Park
#
(-108.109815, 35.674474): Feature("Kin Ya'a", 'ky', W2='Kin_Ya%27a', flags=FeatureFlag_SkipBounds),
(-107.681287, 35.972367): Feature('Pueblo Pintado', 'pp', flags=FeatureFlag_SkipBounds),
(-108.145752, 35.979813): Feature('Kin Bineola', 'kb', W2='Kin_Bineola', flags=FeatureFlag_SkipBounds),
#
# NPS -> NM -> El Malpais National Monument
#
(-107.819072, 35.096448): Feature('Northwest New Mexico Visitor Center', 'v', flags=FeatureFlag_SkipBounds),
#
# NPS -> NM -> Manhattan Project National Historical Park -> Los Alamos Unit
#
(-106.264959, 35.840842): Feature('Pajarito Site', 'p'),
(-106.345095, 35.843839): Feature('V-Site', 'v'),
(-106.347393, 35.855718): Feature('Gun Site', 'g'),
#
# NPS -> NM -> Pecos National Historical Park
#
(-105.817663, 35.539247): Feature('Glorieta Unit (Canoncito)', 'gwest', W2='Glorieta_Pass_Battlefield'),
(-105.683200, 35.565951): Feature('Main Unit', 'main'),
(-105.755533, 35.577073): Feature("Glorieta Unit (Pigeon's Ranch)", 'geast', W2='Glorieta_Pass_Battlefield'),
#
# NPS -> NM -> Petroglyph National Monument
#
(-106.749622, 35.153536): Feature('Southern Geologic Window', 'sgw'),
(-106.758586, 35.174355): Feature('Northern Geologic Window', 'ngw'),
(-106.688781, 35.189383): Feature('Piedras Marcadas Canyon', 'pmc'),
#
# NPS -> NM -> Salinas Pueblo Missions National Monument
#
(-106.075920, 34.260079): Feature('Gran Quivira Ruins', 'gq'),
(-106.364623, 34.451208): Feature('Abo Ruins', 'a', W2='Abo_(historic_place)'),
(-106.292308, 34.591781): Feature('Quarai Ruins', 'q', W2='Quarai'),
#
# NPS -> OR -> John Day Fossil Beds National Monument
#
(-119.618141, 44.596444): Feature('Sheep Rock Unit', 'sr'),
(-119.643497, 44.629640): Feature('Sheep Rock Unit (Cathedral Rock)', 'cr'),
(-119.632783, 44.659439): Feature('Sheep Rock Unit (Foree Area)', 'foree'),
(-120.263931, 44.663927): Feature('Painted Hills Unit', 'ph'),
(-120.402547, 44.929289): Feature('Clarno Unit', 'clarno'),
#
# NPS -> OR -> Oregon Caves National Monument and Preserve
#
(-123.644339, 42.160947): Feature('Illinois Valley Visitors Center', 'ivvc', flags=FeatureFlag_SkipBounds),
#
# NPS -> OR -> Nez Perce National Historical Park
#
(-117.224839, 45.337427): Feature('Old Chief Joseph Gravesite', 'cj', W2='Old_Chief_Joseph_Gravesite'),
(-117.520354, 45.570223): Feature('Lostine Homesite', 'lost'),
#
# NPS -> TN -> Manhattan Project National Historical Park -> Oak Ridge Unit
#
(-84.317198, 35.928011): Feature('X-10 Graphite Reactor', 'x10',
	W2='X-10_Graphite_Reactor'),
(-84.394445, 35.938672): Feature('K-25 Building', 'k25',
	W2='K-25'),
(-84.256801, 35.984691): Feature('Y-12 Building 9204-3', 'y9204',
	W2='Clinton_Engineer_Works#Y-12_electromagnetic_separation_plant'),
(-84.255495, 35.985871): Feature('Y-12 Building 9731', 'y9731',
	W2='Clinton_Engineer_Works#Y-12_electromagnetic_separation_plant'),
#
# NPS -> UT -> Canyonlands National Park
#
(-110.189552, 38.441484): Feature('Horseshoe Canyon Unit', 'hc', W2='Horseshoe_Canyon_(Utah)'),
#
# NPS -> UT -> Hovenweep National Monument
#
(-109.186458, 37.302006): Feature('Cajon', 'cajon'),
(-109.082068, 37.388997): Feature('Square Tower', 'st'),
(-109.038125, 37.397360): Feature('Holly', 'holly'),
(-109.033020, 37.405043): Feature('Horseshoe and Hackberry', 'hh'),
(-108.722510, 37.413030): Feature('Goodman Point', 'gp'),
(-108.983395, 37.444011): Feature('Cutthroat Castle', 'cc'),
#
# NPS -> WA -> Manhattan Project National Historical Park -> Hanford Unit
#
(-119.387098, 46.587399): Feature('Hanford High School', 'hh', W2='Hanford_Site'),
(-119.646295, 46.628954): Feature('B Reactor', 'br', W2='B_Reactor'),
(-119.715131, 46.638641): Feature("Bruggemann's Warehouse", 'bw'),
(-119.618684, 46.644369): Feature('Allard Pump House', 'ap'),
(-119.478732, 46.660534): Feature('White Bluffs Bank', 'wb', W2='White_Bluffs,_Washington'),
#
# NPS -> WA -> Minidoka National Historic Site
#
(-122.507464, 47.614825): Feature('Bainbridge Island|Japanese American|Exclusion Memorial', 'jam',
	W2='Bainbridge_Island_Japanese_American_Exclusion_Memorial'),
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
	assert len(NPS_ParkAndPreserve) == 0

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
		id = p.pop('id')
		id2 = p.pop('id2', None)
		name = p['name']
		name2 = p.get('name2')
		if name != prevName:
			prevName = name
			log('\t\t{} ={}', name, id)
		else:
			assert name2 is not None
		if name2 is not None:
			assert id2 is not None
			log('\t\t\t{} ={}', name2, id2)

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
	'alag': 'Alagnak_River',
	'ania': 'Aniakchak_National_Monument_and_Preserve',
	'crmo': 'Craters_of_the_Moon_National_Monument_and_Preserve',
	'dena': 'Denali_National_Park_and_Preserve',
	'deto': 'Devils_Tower',
	'fobo': 'Fort_Bowie',
	'fopo': 'Fort_Point,_San_Francisco',
	'gaar': 'Gates_of_the_Arctic_National_Park_and_Preserve',
	'glac': 'Glacier_National_Park_(U.S.)',
	'glba': 'Glacier_Bay_National_Park_and_Preserve',
	'grsa': 'Great_Sand_Dunes_National_Park_and_Preserve',
	'hale': 'Haleakal%C4%81_National_Park',
	'havo': 'Hawai%CA%BBi_Volcanoes_National_Park',
	'hono': 'Honouliuli_Internment_Camp',
	'kaho': 'Honok%C5%8Dhau_Settlement_and_Kaloko-Honok%C5%8Dhau_National_Historical_Park',
	'kala': 'Kalaupapa_Leprosy_Settlement_and_National_Historical_Park',
	'katm': 'Katmai_National_Park_and_Preserve',
	'lacl': 'Lake_Clark_National_Park_and_Preserve',
	'lewi': 'Lewis_and_Clark_National_and_State_Historical_Parks',
	'manz': 'Manzanar',
	'puhe': 'Pu%CA%BBukohol%C4%81_Heiau_National_Historic_Site',
	'puho': 'Pu%CA%BBuhonua_o_H%C5%8Dnaunau_National_Historical_Park',
	'redw': 'Redwood_National_and_State_Parks',
	'rori': 'Rosie_the_Riveter/World_War_II_Home_Front_National_Historical_Park',
	'sucr': 'Sunset_Crater#Sunset_Crater_Volcano_National_Monument',
	'tuma': 'Tumac%C3%A1cori_National_Historical_Park',
	'whis': 'Whiskeytown%E2%80%93Shasta%E2%80%93Trinity_National_Recreation_Area',
	'wrst': 'Wrangell%E2%80%93St._Elias_National_Park_and_Preserve',
	'yuch': 'Yukon%E2%80%93Charley_Rivers_National_Preserve',
}
class ParkAndPreserve(object):
	def __init__(self, state, name, parkType='Park'):
		self.state = state
		self.name = name
		self.parkType = parkType
		self.gotPark = False
		self.gotPreserve = False

NPS_ParkAndPreserve = {
	'ania': ParkAndPreserve('AK', 'Aniakchak', 'Monument'),
	'dena': ParkAndPreserve('AK', 'Denali'),
	'gaar': ParkAndPreserve('AK', 'Gates of the Arctic'),
	'glba': ParkAndPreserve('AK', 'Glacier Bay'),
	'grsa': ParkAndPreserve('CO', 'Great Sand Dunes'),
	'katm': ParkAndPreserve('AK', 'Katmai'),
	'lacl': ParkAndPreserve('AK', 'Lake Clark'),
	'wrst': ParkAndPreserve('AK', 'Wrangell-St. Elias'),
}
NPS_Names = {
	'cech': 'Cesar E. Chavez National Monument',
	'jodr': 'John D. Rockefeller Jr.|Memorial Parkway',
	'libi': 'Little Bighorn Battlefield|National Monument',
	'poch': 'Port Chicago Naval Magazine|National Memorial',
	'rori': 'Rosie the Riveter|World War II Home Front|National Historical Park',
	'safr': 'San Francisco Maritime|National Historical Park',
	'samo': 'Santa Monica Mountains|National Recreation Area',
	'valr': 'World War II Valor in the Pacific|National Monument',
	'whis': 'Whiskeytown-Shasta-Trinity|National Recreation Area|(Whiskeytown Unit)',
}
NPS_Codes = {
	'kica': 'seki',
	'sequ': 'seki',
}
NPS_MultiState = {
	'mapr': ('NM', 'TN', 'WA'),             # Manhattan Project National Historical Park
	'miin': ('ID', 'WA'),                   # Minidoka National Historic Site
	'nepe': ('ID', 'MT', 'OR', 'WA'),       # Nez Perce National Historical Park
	'valr': ('CA', 'HI'),                   # World War II Valor in the Pacific National Monument
}
NPS_StatePattern = re.compile('^[A-Z]{2}$')
NPS_CodePattern = re.compile('^[A-Z]{4}$')
NPS_ID_Set = set()

def nps_split_name(name):
	if name.endswith(' National Park'):
		return name[:-14], 'Park'
	if name.endswith(' National Preserve'):
		return name[:-18], 'Preserve'
	if name.endswith(' National Monument'):
		return name[:-18], 'Monument'
	err('"{}" is not a national park, preserve, or monument!', name)

@staticmethod
def stripPropertiesNPS(o):
	name = o['UNIT_NAME']
	code = o['UNIT_CODE']
	if NPS_CodePattern.match(code) is None:
		err('Code "{}" doesn\'t match pattern!', code)
	state = o['STATE']
	if NPS_StatePattern.match(state) is None:
		err('State "{}" doesn\'t match pattern!', state)

	id = code.lower()
	code = NPS_Codes.get(id, id)
	displayName = NPS_Names.get(id, name)
	w = NPS_Wikipedia.get(id)
	pp = NPS_ParkAndPreserve.get(id)

	if pp is not None:
		assert pp.state == state
		name, parkType = nps_split_name(name)
		assert pp.name == name
		if parkType == 'Preserve':
			if pp.gotPark:
				del NPS_ParkAndPreserve[id]
			else:
				pp.gotPreserve = True
			id += 'pr'
		else:
			assert pp.parkType == parkType
			if pp.gotPreserve:
				del NPS_ParkAndPreserve[id]
			else:
				pp.gotPark = True

	if id in NPS_ID_Set:
		err('NPS ID "{}" for "{}" is not unique!', id, displayName)

	NPS_ID_Set.add(id)

	if state != G.state and G.state not in NPS_MultiState.get(id, ()):
		return None

	p = {'name': displayName, 'code': code, 'id': id}
	if w is not None:
		p['W'] = w

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
	global PolygonsToRemove

	modeMap = {
		'uc/granites':          UC_GRANITES,
	}

	for state in ('ak', 'az', 'ca', 'co', 'hi', 'id', 'mt', 'nm', 'nv', 'or', 'ut', 'wa', 'wy'):
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

	PolygonsToRemove = PolygonsToRemove.get(G.id, ())

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
