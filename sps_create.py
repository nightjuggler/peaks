import re
import sys

def log(message, *formatArgs):
	print >>sys.stderr, message.format(*formatArgs)

def err(*args):
	log(*args)
	sys.exit()

def readUntil(f, bytes, untilStr):
	while True:
		i = bytes.find(untilStr)
		if i >= 0:
			return bytes[:i], bytes[i + len(untilStr):]
		newbytes = f.read(200)
		if newbytes == '':
			return bytes, None
		bytes += newbytes

class RE(object):
	numLT1k = re.compile('^[1-9][0-9]{0,2}$')
	numGE1k = re.compile('^[1-9][0-9]?,[0-9]{3}$')

	td = re.compile('^<td(?: align="(?:center|right)")?>')

def str2int(s):
	if len(s) < 4:
		if RE.numLT1k.match(s) is None:
			return None
		return int(s)

	if RE.numGE1k.match(s) is None:
		return None
	return int(s[:-4]) * 1000 + int(s[-3:])

def feetStr2Int(feetStr, description, peakName):
	feet = str2int(feetStr)
	if feet is None:
		err("{} '{}' ({}) doesn't match expected pattern", description, feetStr, peakName)
	return feet

class PeakLoJ(object):
	peakNamePattern = ('('
		'(?:[- A-Za-z]+(?:, [A-Z][a-z]+)?)|'
		'(?:"[- A-Za-z]+")|'
		'(?:[1-9][0-9]+))'
	)
	re_peakName = re.compile('^' + peakNamePattern + '$')
	re_columns = (
		(re.compile('^[1-9][0-9]*$'), None),
		(re.compile('^<b><a href="/peak/([1-9][0-9]*)" target="_blank">' + peakNamePattern + '</a></b>$'),
			('id', 'name')),
		(re.compile('^([,0-9]+)\'&nbsp;$'), ('elevation',)),
		(re.compile('^<b><a href="/qmap\\?'
			'lat=(-?[0-9]{1,2}\\.[0-9]{4})&amp;'
			'lon=(-?[0-9]{1,3}\\.[0-9]{4})&amp;z=15" target="_blank">([,0-9]+)\'</a>&nbsp;</b>$'),
			('saddleLat', 'saddleLng', 'saddleElev')),
		(re.compile('^([,0-9]+)\'&nbsp;$'), ('prominence',)),
		(re_peakName, ('lineParent',)),
		(re.compile('^([0-9]+\\.[0-9]{2})&nbsp;$'), ('isolation',)),
		(re_peakName, ('proximateParent',)),
		(re.compile('^([A-Z]{2})$'), ('state',)),
		(re.compile('^([A-Z][a-z]+(?: [A-Z][a-z]+)*(?: &amp; [A-Z][a-z]+(?: [A-Z][a-z]+)*)*)$'),
			('counties',)),
		(re.compile('^<a href="/quad\\?q=([0-9]+)" target="_blank">([A-Z][a-z]+(?: [A-Z][a-z]+)*)</a>'
			' - <a href="/qmap\\?Q=\\1" target="_blank">Map</a>$'),
			('quadId', 'quadName')),
		(re.compile('^([1-9][0-9]?)\\. ([A-Z][a-z]+(?:[- ][A-Z][a-z]+)+)$'),
			('sectionNumber', 'sectionName')),
	)
	# Errata for the LoJ SPS list (https://listsofjohn.com/customlists?lid=60):
	#
	# - Mount Morgan (13,001') (known as Mount Morgan (North) on the SPS list) is listed in
	#   section 17 (Bear Creek Spire Area). It should be in section 18 (Mono Creek to Mammoth).
	#
	# - Pilot Knob (12,245') (known as Pilot Knob (North) on the SPS list) is entirely omitted.
	#   It should be in section 16 (Humphreys Basin and West).
	#
	nameMap = {
		('Coyote Peaks, East', 10892):  'Coyote Peaks',
		('Mount Morgan', 13748):        'Mount Morgan (South)',
		('Mount Morgan', 13001):        'Mount Morgan (North)',
		('Mount Stanford', 13973):      'Mount Stanford (South)',
		('Mount Stanford', 12838):      'Mount Stanford (North)',
		('Pyramid Peak', 12778):        'Pyramid Peak (South)',
		('Pyramid Peak', 9983):         'Pyramid Peak (North)',
		('Sawtooth Peak', 8020):        'Sawtooth Peak (South)',
		('Sawtooth Peak', 12343):       'Sawtooth Peak (North)',
		('Sierra Buttes, North', 8591): 'Sierra Buttes',
		('Three Sisters, East', 10612): 'Three Sisters',
	}
	def normalizeName(self, name, elevation=None):
		if name[0] == '"':
			assert name[-1] == '"'
			name = name[1:-1]
		if name.endswith(', Mount'):
			name = 'Mount ' + name[:-7]
		elif name.endswith(', The'):
			name = 'The ' + name[:-5]
		mappedName = self.nameMap.get((name, elevation))
		if mappedName is not None:
			name = mappedName
		return name

	# LoJ SPS Elevation Adjustments:
	#
	# - Adams Peak (8,199) vs 8,197 (topo):
	#   "East Summit determined higher than west by 2 feet using photo pixel analysis."
	#   [https://listsofjohn.com/peak/17460]
	#
	# - Mount Agassiz (13,892) vs 13,893 (7.5' topo) or 13,891 (15' topo)
	#   Perhaps the average between the 7.5' and 15' topo spot elevations was taken?
	#
	# - Basin Mountain (13,190) vs 13,181 (topo):
	#   "East Summit is higher. Elevation is interpolation of spot 13181 and next highest contour at 13200."
	#   [https://listsofjohn.com/peak/32365]
	#
	# - Mount Baxter (13,140) vs 13,136 (4004m) (topo):
	#   "This location shown higher than 4004m spot elevation on historical maps and appears higher from
	#    photographs. Elevation is estimated."
	#   [https://listsofjohn.com/peak/32376]
	#
	# - Mount Morrison (12,296) vs 12,277 (3742m) (topo):
	#   Perhaps the 3742m spot elevation was misread as 3748m? The 3600m contour passes through
	#   the 2 in such a way that it may look like an 8 at first glance.
	#
	#   Or the 3742m spot elevation from the 1983 1:24k topo was converted to feet, rounded down,
	#   and then 20 feet (half of a typical 40-foot contour interval) were added because the more
	#   recent 1994 topo doesn't show the spot elevation (even though the contour interval is 20
	#   meters, not 40 feet, and, of course, the highest contour is 3740m, not 3742m).
	#
	elevationMap = {
		('Adams Peak', 8199): 8197,
		('Mount Agassiz', 13892): 13893,
		('Basin Mountain', 13190): 13181,
		('Mount Baxter', 13140): 13136,
		('Mount Morrison', 12296): 12277,
	}
	def postProcess(self):
		self.elevation = feetStr2Int(self.elevation, 'Elevation', self.name)
		self.saddleElev = feetStr2Int(self.saddleElev, 'Saddle elevation', self.name)
		self.prominence = feetStr2Int(self.prominence, 'Prominence', self.name)

		self.isolation = float(self.isolation)
		self.sectionNumber = int(self.sectionNumber)

		self.name = self.normalizeName(self.name, self.elevation)
		self.lineParent = self.normalizeName(self.lineParent)
		self.proximateParent = self.normalizeName(self.proximateParent)

		mappedElevation = self.elevationMap.get((self.name, self.elevation))
		if mappedElevation is not None:
			self.elevation = mappedElevation

def extractColumns(peak, row, rowNum):
	for colNum, (regexp, attributes) in enumerate(peak.re_columns):
		m = RE.td.match(row)
		if m is None:
			err("Beginning of row {}, column {} doesn't match expected pattern", rowNum, colNum + 1)
		row = row[m.end():]
		i = row.find('</td>')
		if i < 0:
			err("Missing </td> for row {}, column {}", rowNum, colNum + 1)
		col = row[:i]
		row = row[i + 5:]
		m = regexp.match(col)
		if m is None:
			err("Row {}, column {} doesn't match expected pattern:\n{}", rowNum, colNum + 1, col)
		if attributes is None:
			assert regexp.groups == 0
		else:
			values = m.groups()
			assert len(attributes) == len(values)
			for attr, value in zip(attributes, values):
				setattr(peak, attr, value)
	if row != '':
		err("End of row expected after column {}", colNum + 1)

def loadListLoJ(listId):
	f = open("extract/data/{}/loj.html".format(listId))

	row, bytes = readUntil(f, '', '<tr>')
	if bytes is None:
		err("Can't find <tr> for header row")
	row, bytes = readUntil(f, bytes, '</tr>')
	if bytes is None:
		err("Can't find </tr> for header row")

	rowNum = 0
	peaks = []

	while True:
		row, bytes = readUntil(f, bytes, '<tr>')
		if bytes is None:
			break
		rowNum += 1
		row, bytes = readUntil(f, bytes, '</tr>')
		if bytes is None:
			err("Can't find </tr> for row {}", rowNum)

		peak = PeakLoJ()
		extractColumns(peak, row, rowNum)
		peak.postProcess()
		peaks.append(peak)

	f.close()
	assert len(peaks) == 246
	return peaks

def matchElevation(peak, *args):

	def formatElevation(feet, isRange=False):
		feet1, feet2 = divmod(feet, 1000)
		return '{:2},{:03}{}'.format(feet1, feet2, '+' if isRange else ' ')

	def printNoMatch(feet1, isRange1, feet2, isRange2=False):
		print line.format(formatElevation(feet1, isRange1), 'No match'),
		print '({}){}'.format(feet2 - feet1, '' if isRange1 == isRange2 else ' and range mismatch')

	line = '{:5} {:24} {:7} {{:7}} {{}}'.format(peak.id, peak.name, formatElevation(*args))

	results = peak.matchElevation(*args)

	if not results:
		for e in peak.elevations:
			printNoMatch(e.elevationFeet, e.isRange, *args)
		return

	for e, result in results:
		elevation = formatElevation(e.elevationFeet, e.isRange)
		if result is True:
			result = 'Exact match'
		print line.format(elevation, result)

def checkElevation(pl, sectionNumber, peakNumber, *args):
	peak = pl.peaks[sectionNumber - 1][peakNumber - 1]
	matchElevation(peak, *args)

def spsMap(pl):
	name2peak = {}
	for peaks in pl.peaks:
		for peak in peaks:
			if peak.name == "Devil's Crag #1":
				name2peak["Devils Crags"] = peak
			else:
				name2peak[peak.name] = peak
	return name2peak

def checkSPS(pl):
	name2peak = spsMap(pl)
	peaksLoJ = loadListLoJ('sps')

	for peakLoJ in peaksLoJ:
		peak = name2peak[peakLoJ.name]
		assert peak.listsOfJohnId == peakLoJ.id
		matchElevation(peak, peakLoJ.elevation)

#	checkElevation(pl,5,4, 13553,False) # Pb
#	checkElevation(pl,18,8, 12276,True) # W
