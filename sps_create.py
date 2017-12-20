import re
import sys

def log(message, *args, **kwargs):
	print >>sys.stderr, message.format(*args, **kwargs)

def err(*args, **kwargs):
	log(*args, **kwargs)
	sys.exit()

class TableReader(object):
	def err(self, message, *args, **kwargs):
		self.fileObj.close()

		if self.rowNum == 0:
			prevTag = "<{}>".format(self.TABLE)
		elif self.colNum == 0:
			prevTag = self.endTag_TR
		elif self.colNum == 1:
			prevTag = self.tag_TR
		else:
			prevTag = self.colEndTag

		prefix = self.fileObj.name
		i = prefix.rfind("/")
		if i >= 0:
			prefix = prefix[i + 1:]
		if self.rowNum > 0:
			prefix += ", row " + str(self.rowNum)
		if self.colNum > 0:
			prefix += ", column " + str(self.colNum)
		prefix += ": "

		err(prefix + message, prevTag=prevTag, *args, **kwargs)

	def __init__(self, fileObj, upper=False, tableAttributes=None):
		self.bytes = ""
		self.rowNum = 0
		self.colNum = 0
		self.fileObj = fileObj

		if upper:
			self.TABLE, self.TR, self.TD, self.TH = ("TABLE", "TR", "TD", "TH")
		else:
			self.TABLE, self.TR, self.TD, self.TH = ("table", "tr", "td", "th")

		self.tag_TR = "<" + self.TR + ">"
		self.endTag_TR = "</" + self.TR + ">"
		self.endTag_TD = "</" + self.TD + ">"
		self.endTag_TH = "</" + self.TH + ">"

		while True:
			self.readUntil("<" + self.TABLE)
			b = self.readUntil(">", errMsg="Can't find '>' for {prevTag}").rstrip()
			if tableAttributes is None:
				break
			if len(b) == 0:
				if tableAttributes == "":
					break
			elif b[0] in " \n\r\t":
				if tableAttributes == b.lstrip():
					break

	def __iter__(self):
		return self

	def readUntil(self, untilStr, errMsg="Can't find '{untilStr}'"):
		bytes = self.bytes
		while True:
			i = bytes.find(untilStr)
			if i >= 0:
				self.bytes = bytes[i + len(untilStr):]
				return bytes[:i]
			newbytes = self.fileObj.read(1000)
			if newbytes == "":
				self.err(errMsg, untilStr=untilStr)
			bytes += newbytes

	def next(self):
		if self.fileObj is None:
			raise StopIteration()

		b = self.readUntil("<", errMsg="Can't find '<' for next tag after {prevTag}")

		if b.strip() != "":
			self.err("Expected only whitespace between {prevTag} and next tag")

		b = self.readUntil(">", errMsg="Can't find '>' for next tag after {prevTag}")

		if b == self.TR:
			self.rowNum += 1
		elif b == "/" + self.TABLE:
			self.fileObj.close()
			self.fileObj = None
			raise StopIteration()
		else:
			self.err("Expected either {} or </{}> after {prevTag}", self.tag_TR, self.TABLE)

		row = self.readUntil(self.endTag_TR).strip()

		while row.startswith(self.tag_TR):
			row = row[len(self.tag_TR):].lstrip()

		columns = []

		while row != "":
			self.colNum += 1

			i = row.find("<")
			if i < 0:
				self.err("Can't find '<' for next tag after {prevTag}")
			if row[:i].strip() != "":
				self.err("Expected only whitespace between {prevTag} and next tag")
			row = row[i + 1:]
			i = row.find(">")
			if i < 0:
				self.err("Can't find '>' for next tag after {prevTag}")

			tag = row[:i]
			row = row[i + 1:]
			i = tag.find(" ")
			if i >= 0:
				tag = tag[:i]

			if tag == self.TD:
				endTag = self.endTag_TD
			elif tag == self.TH:
				endTag = self.endTag_TH
			else:
				self.err("Expected either <{}> or <{}> after {prevTag}", self.TD, self.TH)

			i = row.find(endTag)
			if i < 0:
				self.err("Can't find {}", endTag)

			self.colEndTag = endTag

			col = row[:i]
			row = row[i + 5:]
			while col.startswith("&nbsp;"):
				col = col[6:]
			while col.endswith("&nbsp;"):
				col = col[:-6]
			columns.append(col)

		self.colNum = 0
		return columns

class RE(object):
	numLT1k = re.compile('^[1-9][0-9]{0,2}$')
	numGE1k = re.compile('^[1-9][0-9]?,[0-9]{3}$')
	htmlTag = re.compile('<[^>]*>')

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

class ObjectDiff(object):
	def __init__(self, a, b, allowNotEq=()):
		a = vars(a)
		b = vars(b)

		self.notEq = []
		self.onlyA = []
		self.onlyB = [k for k in b.iterkeys() if k not in a]

		for k, v in a.iteritems():
			if k in b:
				if v != b[k] and k not in allowNotEq:
					self.notEq.append(k)
			else:
				self.onlyA.append(k)

	def __nonzero__(self):
		return bool(self.notEq or self.onlyA or self.onlyB)

	def message(self, nameA, nameB, suffix=""):
		if not self:
			return "Objects {} and {} are the same{}".format(nameA, nameB, suffix)

		lines = ["Objects {} and {} are different{}".format(nameA, nameB, suffix)]
		if self.onlyA:
			lines.append("Only {} has these attributes: {}".format(nameA, ", ".join(self.onlyA)))
		if self.onlyB:
			lines.append("Only {} has these attributes: {}".format(nameB, ", ".join(self.onlyB)))
		if self.notEq:
			lines.append("These attributes have different values: " + ", ".join(self.notEq))
		return "\n".join(lines)

class ElevationPb(object):
	classId = "Pb"

	def __init__(self, minFeet, maxFeet):
		self.feet = minFeet
		self.isRange = minFeet < maxFeet

	def __str__(self):
		return "{},{:03}".format(*divmod(self.feet, 1000)) + ("+" if self.isRange else "")

	def diff(self, e):
		return "({}){}".format(self.feet - e.elevationFeet,
			"" if self.isRange == e.isRange else " and range mismatch")

class ElevationLoJ(object):
	classId = "LoJ"

	def __init__(self, feet):
		self.feet = feet

	def __str__(self):
		return "{},{:03}".format(*divmod(self.feet, 1000))

	def diff(self, e):
		return "({})".format(self.feet - e.elevationFeet)

class TablePeak(object):
	@classmethod
	def getPeaks(self, peakListId, fileNameSuffix=""):
		htmlFile = open("extract/data/{}/{}{}.html".format(
			peakListId.lower(), self.classId.lower(), fileNameSuffix))

		table = TableReader(htmlFile, **getattr(self, "tableReaderArgs", {}))
		row = table.next()

		columns = []
		for colNum, colStr in enumerate(row):
			colStr = RE.htmlTag.sub("", colStr)
			col = self.columnMap.get(colStr, None)
			if col is None:
				table.colNum = colNum + 1
				table.err("Unrecognized column name:\n{}", colStr)
			columns.append(col)

		peaks = []
		for row in table:
			if len(row) != len(columns):
				table.err("Unexpected number of columns")
			peak = self()
			for colNum, (colStr, (regexp, attributes)) in enumerate(zip(row, columns)):
				m = regexp.match(colStr)
				if m is None:
					table.colNum = colNum + 1
					table.err("Doesn't match expected pattern:\n{}", colStr)
				if attributes is None:
					assert regexp.groups == 0
				else:
					values = m.groups()
					assert len(attributes) == len(values)
					for attr, value in zip(attributes, values):
						setattr(peak, attr, value)
			peak.postProcess()
			peaks.append(peak)

		assert len(peaks) == self.numPeaks[peakListId]
		return peaks

class PeakPb(TablePeak):
	classId = 'Pb'
	tableReaderArgs = dict(tableAttributes='class="gray"')
	columnMap = {
		'Rank': (
			re.compile('^(?:[1-9][0-9]*\\.)?$'),
			None
		),
		'Peak': (
			re.compile('^<a href=peak\\.aspx\\?pid=([1-9][0-9]*)>([- A-Za-z]+)</a>$'),
			('id', 'name')
		),
		'Section': (
			re.compile('^([1-9]|[0-9]{2})(?:\\.| -) ([- A-Za-z]+)$'),
			('sectionNumber', 'sectionName')
		),
		'Elev-Ft': (
			re.compile('^((?:[1-9][0-9],[0-9]{3})|(?:[1-9][0-9]{3}))$'),
			('elevation',)
		),
		'Range (Level 5)': (
			re.compile('^<a href=range\\.aspx\\?rid=([1-9][0-9]*)>([- A-Za-z]+)</a>$'),
			('rangeId', 'rangeName')
		),
		'Prom-Ft': (
			re.compile('^((?:[1-9][0-9],[0-9]{3})|(?:[1-9][0-9]{1,3}))$'),
			('prominence',)
		),
	}
	columnMap['Elev-Ft(Opt)'] = columnMap['Elev-Ft']
	columnMap['Prom-Ft(Opt)'] = columnMap['Prom-Ft']
	numPeaks = {
		'DPS':   99,
		'GBP':  115,
		'NPC':   73,
		'SPS':  247,
	}
	def check(self, peak, peakListId):
		if self.id != peak.peakbaggerId:
			err("ID ({}) doesn't match Pb ID ({}) for {}", self.id, peak.peakbaggerId, self.name)

	nameMap = {
	# Desert Peaks Section:
		('Chuckwalla Mountains HP', 3446):      'Bunch Benchmark',
		('Eagle Mountain', 5350):               'Eagle Mountains HP',
		('Granite Mountain', 6762):             'Granite Peak',
		('Granite Mountain', 4331):             'Granite Benchmark',
		('Old Woman Mountain', 5325):           'Old Woman Mountains HP',
		('Spectre Peak', 4482):                 'Spectre Point',
		('Stepladder Mountains', 2940):         'Stepladder Mountains HP',
		('Superstition Benchmark', 5057):       'Superstition Mountain',
	# Sierra Peaks Section:
		('Devils Crags', 12400):                'Devil\'s Crag #1',
		('Mount Morgan', 13748):                'Mount Morgan (South)',
		('Mount Morgan', 12992):                'Mount Morgan (North)',
		('Mount Stanford', 13973):              'Mount Stanford (South)',
		('Mount Stanford', 12838):              'Mount Stanford (North)',
		('Pilot Knob', 12245):                  'Pilot Knob (North)',
		('Pyramid Peak', 12779):                'Pyramid Peak (South)',
		('Pyramid Peak', 9983):                 'Pyramid Peak (North)',
		('Sawtooth Peak', 8000):                'Sawtooth Peak (South)',
		('Sawtooth Peak', 12343):               'Sawtooth Peak (North)',
		('Sierra Buttes Lookout', 8590):        'Sierra Buttes',
	}
	@classmethod
	def normalizeName(self, name, elevation=None):
		if name.endswith(' High Point'):
			name = name[:-10] + 'HP'
		return self.nameMap.get((name, elevation), name)

	def postProcess(self):
		def str2int(s):
			return int(s) if len(s) <= 4 else int(s[:-4]) * 1000 + int(s[-3:])

		self.elevation = str2int(self.elevation)
		self.prominence = str2int(self.prominence)

	@classmethod
	def getPeaks(self, peakListId):
		super_getPeaks = super(PeakPb, self).getPeaks
		minPeaks = super_getPeaks(peakListId)
		maxPeaks = super_getPeaks(peakListId, fileNameSuffix='-max')
		maxPeaks = {p.id: p for p in maxPeaks}

		for peak in minPeaks:
			maxPeak = maxPeaks[peak.id]

			diff = ObjectDiff(peak, maxPeak, allowNotEq=("elevation", "prominence"))
			if diff:
				err(diff.message("minPeak", "maxPeak",
					" for Pb ID {} ({})".format(peak.id, peak.name)))

			peak.name = peak.normalizeName(peak.name, peak.elevation)

			if peak.elevation > maxPeak.elevation:
				err("Pb: Max elevation ({}) must be >= min elevation ({}) for {}",
					maxPeak.elevation, peak.elevation, peak.name)
			if peak.prominence > maxPeak.prominence:
				err("Pb: Max prominence ({}) must be >= min prominence ({}) for {}",
					maxPeak.prominence, peak.prominence, peak.name)

			peak.elevation = ElevationPb(peak.elevation, maxPeak.elevation)

		return minPeaks

class PeakLoJ(TablePeak):
	classId = 'LoJ'
	peakNamePattern = ('('
		'(?:[A-Z][- 0-9A-Za-z]+(?:, [A-Z][a-z]+)?(?:-[A-Z][ A-Za-z]+)?(?: \\(HP\\))?)|'
		'(?:"[A-Z][- 0-9A-Za-z]+")|'
		'(?:[1-9][0-9]+(?:-[A-Z][ A-Za-z]+)?))'
	)
	peakNameRegExp = re.compile('^' + peakNamePattern + '$')
	columnMap = {
		'# in list': (
			re.compile('^[1-9][0-9]*$'),
			None
		),
		'Name': (
			re.compile(
				'^<b><a href="/peak/([1-9][0-9]*)" target="_blank">' +
				peakNamePattern + '</a></b>$'
			),
			('id', 'name')
		),
		'Elevation': (
			re.compile('^([,0-9]+)\'$'),
			('elevation',)
		),
		'Saddle': (
			re.compile(
				'^<b><a href="/qmap\\?'
				'lat=(-?[0-9]{1,2}\\.[0-9]{4})&amp;'
				'lon=(-?[0-9]{1,3}\\.[0-9]{4})&amp;z=15" '
				'target="_blank">([,0-9]+)\'</a>&nbsp;</b>$'
			),
			('saddleLat', 'saddleLng', 'saddleElev')
		),
		'Prominence': (
			re.compile('^([,0-9]+)\'$'),
			('prominence',)
		),
		'Line Parent': (
			peakNameRegExp,
			('lineParent',)
		),
		'Isolation': (
			re.compile('^([0-9]+\\.[0-9]{2})$'),
			('isolation',)
		),
		'Proximate Parent': (
			peakNameRegExp,
			('proximateParent',)
		),
		'State': (
			re.compile('^([A-Z]{2})$'),
			('state',)
		),
		'Counties': (
			re.compile(
				'^([A-Z][a-z]+(?: [A-Z][a-z]+)*(?: &amp;'
				' [A-Z][a-z]+(?: [A-Z][a-z]+)*)*)$'
			),
			('counties',)
		),
		'Quadrangle': (
			re.compile(
				'^<a href="/quad\\?q=([0-9]+)" target="_blank">([A-Za-z]+(?: [A-Za-z]+)*)</a>'
				' - <a href="/qmap\\?Q=\\1" target="_blank">Map</a>$'
			),
			('quadId', 'quadName')
		),
		'Section': (
			re.compile('^([1-9][0-9]?)\\. ([A-Z][a-z]+(?:[- ][A-Z][a-z]+)+)$'),
			('sectionNumber', 'sectionName')
		),
	}
	numPeaks = {
		'DPS':   95, # The four Mexican peaks are missing from the LoJ DPS list.
		'GBP':  115,
		'NPC':   73,
		'SPS':  246, # Pilot Knob (North) is missing from the LoJ SPS list.
	}
	def check(self, peak, peakListId):
		if self.id != peak.listsOfJohnId:
			err("ID ({}) doesn't match LoJ ID ({}) for {}", self.id, peak.listsOfJohnId, self.name)
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
	@classmethod
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

		self.elevation = ElevationLoJ(self.elevationMap.get(
			(self.name, self.elevation), self.elevation))

def matchElevation(peak, elevation):
	line = "{:5} {:24} {:7} {{:7}}".format(peak.id, peak.name, elevation)

	exactMatches, otherMatches = peak.matchElevation(elevation)

	if exactMatches:
		return
	if otherMatches:
		for e, result in otherMatches:
			print line.format(e.getElevation()), result
	else:
		for e in peak.elevations:
			print line.format(e.getElevation()), "No match", elevation.diff(e)

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
	print "+--------------------------------------+"
	print "| Lists of John                        |"
	print "+--------------------------------------+"
	checkElevation(pl, PeakLoJ)

	print "+--------------------------------------+"
	print "| Peakbagger                           |"
	print "+--------------------------------------+"
	checkElevation(pl, PeakPb)
