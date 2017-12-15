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
	columnNames = (
		'# in list',
		'Name',
		'Elevation',
		'Saddle',
		'Prominence',
		'Line Parent',
		'Isolation',
		'Proximate Parent',
		'State',
		'Counties',
		'Quadrangle',
		'Section',
	)
	peakNamePattern = ('('
		'(?:[A-Z][- 0-9A-Za-z]+(?:, [A-Z][a-z]+)?(?:-[A-Z][ A-Za-z]+)?(?: \\(HP\\))?)|'
		'(?:"[A-Z][- 0-9A-Za-z]+")|'
		'(?:[1-9][0-9]+(?:-[A-Z][ A-Za-z]+)?))'
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
		(re.compile('^<a href="/quad\\?q=([0-9]+)" target="_blank">([A-Za-z]+(?: [A-Za-z]+)*)</a>'
			' - <a href="/qmap\\?Q=\\1" target="_blank">Map</a>$'),
			('quadId', 'quadName')),
		(re.compile('^([1-9][0-9]?)\\. ([A-Z][a-z]+(?:[- ][A-Z][a-z]+)+)$'),
			('sectionNumber', 'sectionName')),
	)
	numPeaks = {
		'DPS':   95, # The four Mexican peaks are missing from the LoJ DPS list.
		'GBP':  115,
		'NPC':   73,
		'SPS':  246, # Pilot Knob (North) is missing from the LoJ SPS list.
	}
	@classmethod
	def getPeaks(self, id):
		return loadListLoJ(id, self.numPeaks[id])

	def check(self, peak, peakListId):
		assert self.id == peak.listsOfJohnId
		if peakListId == 'NPC':
			assert self.state == 'NV'

	# Errata for the LoJ SPS list (https://listsofjohn.com/customlists?lid=60):
	#
	# - Mount Morgan (13,001') (known as Mount Morgan (North) on the SPS list) is listed in
	#   section 17 (Bear Creek Spire Area). It should be in section 18 (Mono Creek to Mammoth).
	#
	# - Pilot Knob (12,245') (known as Pilot Knob (North) on the SPS list) is entirely omitted.
	#   It should be in section 16 (Humphreys Basin and West).
	#
	nameMap = {
	# Desert Peaks Section:
		('Avawatz Mountains HP', 6154):                 'Avawatz Peak',
		('Canyon Benchmark', 5890):                     'Canyon Point',
		('Eagle Benchmark', 5350):                      'Eagle Mountains HP',
		('Glass Mountain HP', 11180):                   'Glass Mountain',
		('Jacumba Benchmark', 4512):                    'Jacumba Mountain',
		('Mitchell Benchmark', 7047):                   'Mitchell Point',
		('Mopah Peaks, East', 3530):                    'Mopah Point',
		('New York Two Benchmark', 7532):               'New York Mountains HP',
		('Nopah Benchmark', 6394):                      'Nopah Range HP',
		('Pahrump Benchmark', 5740):                    'Pahrump Point',
		('Resting Spring Range HP', 5264):              'Stewart Point',
		('Rosa Benchmark', 5020):                       'Rosa Point',
		('Sandy Benchmark', 7062):                      'Sandy Point',
		('Spectre Benchmark', 4483):                    'Spectre Point',
		('Superstition Peak', 5057):                    'Superstition Mountain',
	# Nevada Peaks Club:
		('Mount Jefferson-South Summit', 11941):        'Mount Jefferson',
		('Muddy Mountains HP', 5431):                   'Muddy Benchmark',
	# Sierra Peaks Section:
		('Coyote Peaks, East', 10892):  'Coyote Peaks',
		('Devils Crags', 12420):        'Devil\'s Crag #1',
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
		elif name[0] in '123456789':
			name = 'Peak ' + name
		i = name.find(', Mount')
		if i > 0:
			if i + 7 == len(name):
				name = 'Mount ' + name[:-7]
			elif name[i + 7] in ' -':
				name = 'Mount ' + name[:i] + name[i + 7:]
		elif name.endswith(', The'):
			name = 'The ' + name[:-5]
		if name.endswith(' (HP)'):
			name = name[:-4] + 'HP'
		return self.nameMap.get((name, elevation), name)

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
		('Mount Morrison', 12296): 12276,
		('Seven Gables', 13074): 13075,

	# LoJ DPS Elevation Adjustments:
	#
	# - Boundary Peak
	#   The 7.5' and 15' topos show a spot elevation of 13,140'.
	#   The 1:250,000 topos show either a spot elevation of 13,145' or no spot elevation.
	#   The 1:100,000 topos show a spot elevation of 4005m (13,140').
	#   So how does LoJ get 13,143'?
	#
	# - Stepladder Mountains HP
	#   "This location is higher than contour with spot elevation 892m. Elevation is interpolation of
	#    spot elevation and next higher contour." (892m + 900m) / 2 / 0.3048 m/ft = 2939.6 ft
	#   [https://listsofjohn.com/peak/65349]
	#
		('Boundary Peak', 13143): 13140,
		('East Ord Mountain', 6169): 6168,
		('Needle Peak', 5802): 5803,
		('Old Woman Mountains HP', 5325): 5324,
		('Spectre Point', 4483): 4482,
		('Stepladder Mountains HP', 2939): 2936,

	# LoJ GBP Elevation Adjustments:
	#
	# - Eagle Peak
	#   All the 7.5' topos on topoView show a spot elevation of 9,892'.
	#   There aren't any 15' topos available on topoView for that area.
	#   The 1:250,000 topos show a spot elevation of either 9,892' or 9,883'.
	#   The 1:100,000 topo doesn't show a spot elevation. It doesn't even name the peak.
	#   The highest contour is at 3000m, and the interval is 50m.
	#   So the average is 3025m which is 9,924' rounded down.
	#   I'm guessing there's a 7.5' topo that doesn't show a spot elevation?
	#   In that case the highest contour is at 9880', and the interval is 40'.
	#   So the average would be 9900'.
	#
		('Eagle Peak', 9900): 9892,
	}
	def postProcess(self):
		self.elevation = feetStr2Int(self.elevation, 'Elevation', self.name)
		self.saddleElev = feetStr2Int(self.saddleElev, 'Saddle elevation', self.name)
		self.prominence = feetStr2Int(self.prominence, 'Prominence', self.name)

		self.isolation = float(self.isolation)

		self.name = self.normalizeName(self.name, self.elevation)
		self.lineParent = self.normalizeName(self.lineParent)
		self.proximateParent = self.normalizeName(self.proximateParent)

		mappedElevation = self.elevationMap.get((self.name, self.elevation))
		if mappedElevation is not None:
			self.elevation = mappedElevation

def extractColumns(peak, row, rowNum, numCols):
	for colNum, (regexp, attributes) in enumerate(peak.re_columns[:numCols]):
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
		err("End of row {} expected after column {}", rowNum, colNum + 1)

def loadListLoJ(listId, numPeaks):
	f = open("extract/data/{}/loj.html".format(listId.lower()))

	row, bytes = readUntil(f, '', '<tr>')
	if bytes is None:
		err("Can't find <tr> for header row")
	row, bytes = readUntil(f, bytes, '</tr>')
	if bytes is None:
		err("Can't find </tr> for header row")

	numCols = 1
	maxCols = len(PeakLoJ.columnNames)

	while True:
		i = row.find('<td class="one">')
		if i < 0:
			err("Can't find <td> for header row, column {}", numCols)
		assert row[:i].strip() == ''
		row = row[i + 16:]
		i = row.find('</td>')
		if i < 0:
			err("Missing </td> for header row, column {}", numCols)
		col = row[:i]
		row = row[i + 5:]
		assert col == PeakLoJ.columnNames[numCols - 1]
		if row == '':
			break
		if numCols == maxCols:
			err("End of header row expected after column {}", maxCols)
		numCols += 1

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
		extractColumns(peak, row, rowNum, numCols)
		peak.postProcess()
		peaks.append(peak)

	f.close()
	assert len(peaks) == numPeaks
	return peaks

def matchElevation(peak, feet, isRange=None):
	line = '{:5} {:24} {:7} {{:7}} {{}}'.format(peak.id, peak.name,
		'{},{:03}'.format(*divmod(feet, 1000)) + ('+' if isRange else ' '))

	exactMatches, otherMatches = peak.matchElevation(feet, isRange)

	if exactMatches:
		return
	if otherMatches:
		for e, result in otherMatches:
			print line.format(e.getElevation(), result)
	else:
		for e in peak.elevations:
			print line.format(e.getElevation(), 'No match ({}){}'.format(feet - e.elevationFeet,
				'' if isRange is None or isRange == e.isRange else ' and range mismatch'))

class MatchByName(object):
	def __init__(self, pl):
		name2peak = {}

		def put(name, peak):
			if name in name2peak:
				item = name2peak[name]
				if isinstance(item, list):
					item.append(peak)
				else:
					name2peak[name] = [item, peak]
			else:
				name2peak[name] = peak

		for peaks in pl.peaks:
			for peak in peaks:
				name = peak.name
				if peak.isHighPoint:
					name += ' HP'
				put(name, peak)
				if peak.otherName is not None:
					put(peak.otherName, peak)

		self.name2peak = name2peak

	def get(self, peak2):
		peak = self.name2peak.get(peak2.name)
		if peak is not None:
			if not isinstance(peak, list):
				return peak
			log("Peak name '{}' is not unique!", peak2.name)
		return None

def checkElevation(peakList, peak2Class):
	peakMap = MatchByName(peakList)
	peakList2 = peak2Class.getPeaks(peakList.id)

	matchedPeaks = []
	for peak2 in peakList2:
		peak = peakMap.get(peak2)
		if peak is None:
			log("Cannot map '{}' ({})", peak2.name, peak2.elevation)
		else:
			matchedPeaks.append((peak, peak2))

	for peak, peak2 in matchedPeaks:
		peak2.check(peak, peakList.id)
		matchElevation(peak, peak2.elevation)

def checkData(pl):
	checkElevation(pl, PeakLoJ)
