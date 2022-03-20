import json
import random
import re
import subprocess
import time

class TopoError(Exception):
	def __init__(self, message, *formatArgs):
		self.message = message.format(*formatArgs)

class TopoView(object):

	# Note (2020-09-30):
	# The old 'gnis_cell_id' field had 2-6 digits.
	# The new 'gda_item_id' field has 7-8 digits.
	# GDA = Geospatial Data Act of 2018 ?

	FIELDS = (
		('scan_id',             '[0-9]{6}'),
		('md5',                 '[0-9a-f]{32}'),
		('map_scale',           '[012456]{5,6}'),
		('date_on_map',         '[0-9]{4}'),
		('imprint_year',        '[0-9]{4}'),
		('primary_state',       '[A-Z]{2}'),
		('map_state',           '[A-Z]{2}'),
		('map_name',            '[ A-Za-z]+'),
		('min_longitude',       '-?[0-9]{1,3}(?:\.[0-9]{1,5})?'),
		('min_latitude',        '-?[0-9]{1,3}(?:\.[0-9]{1,5})?'),
		('max_longitude',       '-?[0-9]{1,3}(?:\.[0-9]{1,5})?'),
		('max_latitude',        '-?[0-9]{1,3}(?:\.[0-9]{1,5})?'),
		('OBJECTID',            '[1-9][0-9]{3,5}'),
		('datum',               'NAD(?:27|83)'),
		('gda_item_id',         '[1-9][0-9]{1,7}'),
	)
	CORRECTIONS = {
		'290045': (
			# Extend the 1995/2000 Drakes Bay, CA 7.5' map 1 minute south and 1 minute west
			# to include Point Reyes Head (the high point near the lighthouse).
			('min_latitude', '37.98333'), # 37 59 00
			('max_latitude', '38.12500'), # 38 07 30
			('min_longitude', '-123.01667'), # -123 01 00
			('max_longitude', '-122.87500'), # -122 52 30
		),
		'293349': (
			# The map name is "Mount Ritter" - not "Mt Ritter".
			('map_name', 'Mount Ritter'),
		),
		'296876': (
			# The pdf (CA_Borrego_296876_1959_62500_geo.pdf) clearly shows 1978 (not 1976)
			# for the imprint year.
			('imprint_year', '1978'),
		),
		'296969': (
			# The map name is "Caliente Mtn." - not "Caliente Mountain".
			('map_name', 'Caliente Mtn'),
		),
		'297086': (
			# The pdf (CA_Chilcoot_297086_1950_62500_geo.pdf) clearly shows 1983 (not 1993)
			# for the imprint year.
			('imprint_year', '1983'),
		),
		'298788': (
			# The pdf (CA_Robbs Peak_298788_1952_62500_geo.pdf) clearly shows 1978 (not 1976)
			# for the imprint year.
			('imprint_year', '1978'),
		),
		'299952': (
			# The map name is "Bloody Mtn." - not "Bloody Mountain".
			('map_name', 'Bloody Mtn'),
		),
		'301726': (
			# Shift the min and max longitude for the 1956/1981 Silver Lake, CA 15' map
			# by 0.00001 degrees east.
			# The summit of Round Top is right on the eastern edge of this map.
			('min_longitude', '-120.251'),
			('max_longitude', '-120.001'),
		),
		'321701': (
			# I don't see 1976 (or any imprint year) anywhere on this map. So I'm going to
			# use the most recent year printed on the map (1969).
			('imprint_year', '1969'),
		),
	}
	def __init__(self, values):
		for (name, pattern), value in zip(self.FIELDS, values):
			setattr(self, name, value)

def query(*params):
	url = 'https://ngmdb.usgs.gov/arcgis/rest/services/topoview/ustOverlay/MapServer/0/query?' + '&'.join(params)

	response_filename = 'topoview.out'

	command = ['/usr/local/opt/curl/bin/curl',
		'-o', response_filename,
		'--connect-timeout', '6',
		'--max-time', '12',
		'--retry', '2',
		url]

	print(*command)

	try:
		rc = subprocess.call(command)
		if rc != 0:
			raise TopoError('Exit code {}', rc)

		with open(response_filename) as f:
			response = json.load(f)

		features = response.get('features')
		if features is None:
			raise TopoError("Response doesn't have the 'features' property!")
		if len(features) != 1:
			raise TopoError("Number of features != 1")

		feature = features[0]
		response = feature.get('attributes')
		if response is None:
			raise TopoError("Feature doesn't have the 'attributes' property!")

		geometry = feature.get('geometry')
		if geometry is None:
			raise TopoError("Feature doesn't have the 'geometry' property!")
		geometry = geometry.get('rings')
		if geometry is None:
			raise TopoError("Geometry doesn't have the 'rings' property!")
		if len(geometry) != 1:
			raise TopoError("Number of polygons != 1")
		geometry = geometry[0]
		if len(geometry) != 5:
			raise TopoError("Number of polygon points != 5")
		if geometry[0] != geometry[4]:
			raise TopoError("First point != last point")

		min_longitude, min_latitude = geometry[0]
		max_longitude, max_latitude = geometry[2]

		if not (min_longitude < max_longitude):
			raise TopoError("min_longitude !< max_longitude")
		if not (min_latitude < max_latitude):
			raise TopoError("min_latitude !< max_latitude")
		x, y = geometry[1]
		if round(abs(x - min_longitude), 5) > 2e-5 or round(abs(y - max_latitude), 5) > 2e-5:
			raise TopoError("Second point [{},{}] != [{},{}]", x, y, min_longitude, max_latitude)
		x, y = geometry[3]
		if round(abs(x - max_longitude), 5) > 2e-5 or round(abs(y - min_latitude), 5) > 2e-5:
			raise TopoError("Fourth point [{},{}] != [{},{}]", x, y, max_longitude, min_latitude)

	except TopoError as e:
		print(e.message)
		return None

	response['min_longitude'] = min_longitude
	response['min_latitude'] = min_latitude
	response['max_longitude'] = max_longitude
	response['max_latitude'] = max_latitude
	return response

def loadQuery(bin_num, topo_id, longitude, latitude):
	return query(
		'f=json',
#		'geometry={},{}'.format(longitude, latitude),
#		'geometryType=esriGeometryPoint',
#		'inSR=4326',
#		'spatialRel=esriSpatialRelIntersects',
#		'distance=20',
#		'units=esriSRUnit_Meter',
		'outFields=*',
		'returnGeometry=true',
		'geometryPrecision=5',
		'outSR=4326',
		'where=' + '%20AND%20'.join([
			'bin_num={}'.format(bin_num),
			'series=\'HTMC\'',
			'md5=\'{}\''.format(topo_id),
		]))

def reloadQuery(scan_id):
	return query(
		'f=json',
		'outFields=*',
		'returnGeometry=true',
		'geometryPrecision=5',
		'outSR=4326',
		'where=scan_id=' + scan_id)

CSV_FILENAME = 'topoview.txt'

def read_csv():
	line_pattern = re.compile('^' + ','.join([pattern for name, pattern in TopoView.FIELDS]) + '$')
	line_number = 0
	topos = {}

	with open(CSV_FILENAME) as f:
		try:
			for line in f:
				line_number += 1
				if not line_pattern.match(line):
					raise TopoError("Doesn't match expected pattern")

				topo = TopoView(line.split(','))
				topo_id = topo.md5
				if topo_id in topos:
					raise TopoError("Duplicate ID {}", topo_id)
				topos[topo_id] = topo

		except TopoError as e:
			print("{}, line {} {}!".format(CSV_FILENAME, line_number, e.message))
			return None
	return topos

def load(sources):
	topos = read_csv()
	if topos is None:
		return

	scale_to_bin_num = {
		'24,000': 5,
		'25,000': 5,
		'62,500': 3,
		'125,000': 2,
		'250,000': 1,
	}

	response = None
	with open(CSV_FILENAME, 'a', 1) as f:
		for topo_id, topo in sorted(sources.items()):
			if topo_id in topos:
				continue
			bin_num = scale_to_bin_num.get(topo.scale)
			if bin_num is None:
				print("Can't get bin_num for topo {}!".format(topo_id))
				break
			peak = topo.peaks[0]
			if response:
				sleep_time = int(random.random() * 5 + 5.5)
				print('Sleeping for', sleep_time, 'seconds')
				time.sleep(sleep_time)
			response = loadQuery(bin_num, topo_id, peak.longitude, peak.latitude)
			if response is None:
				break
			print(','.join([str(response[name]) for name, pattern in TopoView.FIELDS]), file=f)

def read_new():
	topos = {}
	with open('topoview.new') as new:
		for line in new:
			topo = TopoView(line.split(','))
			topos[topo.scan_id] = topo
	return topos

def reload():
	new_topos = read_new()
	response = None
	with open(CSV_FILENAME) as old, open('topoview.new', 'a', 1) as new:
		for line in old:
			scan_id = TopoView(line.split(',')).scan_id
			if scan_id in new_topos:
				continue
			if response:
				sleep_time = int(random.random() * 5 + 5.5)
				print('Sleeping for', sleep_time, 'seconds')
				time.sleep(sleep_time)
			response = reloadQuery(scan_id)
			if response is None:
				break
			print(','.join([str(response[name]) for name, pattern in TopoView.FIELDS]), file=new)

def compare(sources):
	topos = read_csv()
	if topos is None:
		return

	scans = {topo.scan_id: topo for topo in topos.values()}

	for scan_id, corrections in TopoView.CORRECTIONS.items():
		topo = scans.get(scan_id)
		if not topo:
			print("Skipping corrections for", scan_id, "- not in", CSV_FILENAME)
			continue
		for name, value in corrections:
			setattr(topo, name, value)

	for topo_id, topoview in sorted(topos.items()):
		topo = sources.get(topo_id)
		if topo is None:
			print(topo_id, "Not used in the HTML")
			continue

		diffs = []

		if topo.scale[:-4] + topo.scale[-3:] != topoview.map_scale:
			diffs.append("Scale doesn't match")
		if topo.state != topoview.primary_state:
			diffs.append("Primary state doesn't match")
		if topo.name.replace('.', '') != topoview.map_name:
			diffs.append("Name doesn't match")
		if topo.year[:4] != topoview.date_on_map:
			diffs.append("Year doesn't match")
		if len(topo.year) == 4:
			if topoview.date_on_map != topoview.imprint_year:
				diffs.append("Imprint year isn't specified ({})".format(topoview.imprint_year))
		else:
			if topo.year[5:] != topoview.imprint_year:
				diffs.append("Imprint year doesn't match ({} != {})".format(
					topo.year[5:], topoview.imprint_year))

		min_lng = float(topoview.min_longitude)
		max_lng = float(topoview.max_longitude)
		min_lat = float(topoview.min_latitude)
		max_lat = float(topoview.max_latitude)

		for peak in topo.peaks:
			lng = float(peak.longitude)
			lat = float(peak.latitude)

			if not (min_lng <= lng <= max_lng and min_lat <= lat <= max_lat):
				diffs.append("{} {},{} not in {},{},{},{}".format(
					peak.name.replace('&quot;', '"'),
					lng, lat, min_lng, min_lat, max_lng, max_lat))

		if diffs:
			peak_lists = set()
			for peak in topo.peaks:
				peak_lists.add(peak.peakList.id)
				for other in peak.dataAlsoPeaks:
					peak_lists.add(other.peakList.id)

			num_peaks = len(topo.peaks)
			print(topo.linkPrefix + topo_id, '|', ', '.join(sorted(peak_lists)),
				'({} peak{})'.format(num_peaks, '' if num_peaks == 1 else 's'))
			for diff in diffs:
				print('--', diff)
			print()

if __name__ == '__main__':
	import sys
	if len(sys.argv) == 2 and sys.argv[1] == 'reload':
		reload()
