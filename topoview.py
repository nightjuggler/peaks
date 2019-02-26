from __future__ import print_function
import json
import random
import re
import subprocess
import time

class TopoError(Exception):
	def __init__(self, message, *formatArgs):
		self.message = message.format(*formatArgs)

class TopoView(object):
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
		('gnis_cell_id',        '[1-9][0-9]{1,5}'),
	)
	def __init__(self, values):
		for (name, pattern), value in zip(self.FIELDS, values):
			setattr(self, name, value)

def query(bin_num, topo_id, longitude, latitude):
	params = [
		'f=json',
		'geometry={},{}'.format(longitude, latitude),
		'geometryType=esriGeometryPoint',
		'inSR=4326',
		'spatialRel=esriSpatialRelIntersects',
		'distance=20',
		'units=esriSRUnit_Meter',
		'outFields=*',
		'returnGeometry=true',
		'geometryPrecision=5',
		'outSR=4326',
		'where=' + '%20AND%20'.join([
			'bin_num={}'.format(bin_num),
			'series=\'HTMC\'',
			'md5=\'{}\''.format(topo_id),
		]),
	]

	url = 'https://ngmdb.usgs.gov/arcgis/rest/services/topoView/ustOverlay/MapServer/0/query?' + '&'.join(params)

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

	with open(CSV_FILENAME, 'a', 1) as f:
		for topo_id, topo in sorted(sources.iteritems()):
			if topo_id in topos:
				continue
			bin_num = scale_to_bin_num.get(topo.scale)
			if bin_num is None:
				print("Can't get bin_num for topo {}!".format(topo_id))
				break
			peak = topo.peaks[0]
			response = query(bin_num, topo_id, peak.longitude, peak.latitude)
			if response is None:
				break
			f.write(','.join([str(response[name]) for name, pattern in TopoView.FIELDS]))
			f.write('\n')

			sleep_time = int(random.random() * 5 + 5.5)
			print('Sleeping for', sleep_time, 'seconds')
			time.sleep(sleep_time)

def compare(sources):
	topos = read_csv()
	if topos is None:
		return

	for topo_id, topoview in sorted(topos.iteritems()):
		topo = sources.get(topo_id)
		if topo is None:
			print(topo_id, "Not used in the HTML")
			continue

		if topo.scale[:-4] + topo.scale[-3:] != topoview.map_scale:
			print(topo_id, "Scale doesn't match")
		if topo.state != topoview.primary_state:
			print(topo_id, "Primary state doesn't match")
		if topo.name.replace('.', '') != topoview.map_name:
			print(topo_id, "Name doesn't match")
		if topo.year[:4] != topoview.date_on_map:
			print(topo_id, "Year doesn't match")
		if len(topo.year) == 4:
			if topoview.date_on_map != topoview.imprint_year:
				print(topo_id, "Imprint year isn't specified")
		else:
			if topo.year[5:] != topoview.imprint_year:
				print(topo_id, "Imprint year doesn't match")
