#!/usr/bin/python
import re
import sys

class FormatError(Exception):
	def __init__(self, message, *formatArgs):
		self.message = message.format(*formatArgs)

class InputFile(file):
	def __init__(self, fileName):
		self.lineNumber = 0
		super(InputFile, self).__init__(fileName)

	def next(self):
		line = super(InputFile, self).next()
		self.lineNumber += 1
		return line

peakLists = {}
peakListParams = {
	'sps': {
		'geojsonTitle': 'Sierra Peaks',
		'numColumns': 14,
		'numPeaks': 248,
		'numSections': 24,
	},
	'dps': {
		'geojsonTitle': 'Desert Peaks',
		'numColumns': 13,
		'numPeaks': 99,
		'numSections': 9,
	},
	'gbp': {
		'geojsonTitle': 'Great Basin Peaks',
		'numColumns': 13,
		'numPeaks': 15,
		'numSections': 12,
	},
	'npc': {
		'geojsonTitle': 'Nevada Peaks Club',
		'numColumns': 13,
		'numPeaks': 19,
		'numSections': 6,
	},
}

class PeakList(object):
	def __init__(self, id):
		self.__dict__.update(peakListParams[id])

		self.id = id.upper()
		self.htmlFilename = id + '.html'
		self.colspan = str(self.numColumns)
		self.colspanMinus1 = str(self.numColumns - 1)
		self.peaks = []
		self.sections = []
		self.landMgmtAreas = {}

		peakLists[self.id] = self

	def sps(self):
		return self.id == 'SPS'

	def readHTML(self):
		try:
			readHTML(self)
		except FormatError as err:
			sys.exit("[{}:{}] {}!".format(self.htmlFilename, self.htmlFile.lineNumber, err.message))

class Peak(object):
	def __init__(self):
		self.id = ''
		self.name = ''
		self.otherName = None
		self.latitude = ''
		self.longitude = ''
		self.zoom = ''
		self.baseLayer = ''
		self.elevations = []
		self.prominence = ''
		self.prominenceLink = None
		self.grade = ''
		self.summitpostId = None
		self.summitpostName = None
		self.wikipediaLink = None
		self.bobBurdId = None
		self.listsOfJohnId = None
		self.peakbaggerId = None
		self.peteYamagataId = None
		self.climbDate = None
		self.climbPhotos = None
		self.climbWith = None
		self.extraRow = None
		self.dataFrom = None
		self.nonUS = False
		self.hasHtmlId = False
		self.isClimbed = False
		self.isEmblem = False
		self.isMtneer = False
		self.isHighPoint = False
		self.landClass = None
		self.landManagement = None
		self.suspended = False

	def elevationHTML(self):
		return '<br>'.join([e.html() for e in self.elevations])

	def copyFrom(self, other):
		doNotCopy = ('id', 'dataFrom', 'hasHtmlId', 'isEmblem', 'isMtneer', 'suspended')

		if other.dataFrom is not None:
			sys.exit("{} should not have the data-from attribute!".format(self.dataFrom))

		for k, v in vars(other).iteritems():
			if not (k[0] == '_' or k in doNotCopy):
				setattr(self, k, v)

def badLine():
	raise FormatError("Line doesn't match expected pattern")

def badSuffix():
	raise FormatError("Suffix and class don't match")

def badClimbed():
	raise FormatError("Climbed column doesn't match class")

def parseClasses(peak, classNames):
	if classNames is None:
		return True

	classNames = classNames.split()
	className = classNames.pop(0)

	if className == 'climbed':
		peak.isClimbed = True
		if not classNames:
			return True
		className = classNames.pop(0)

	if className == 'emblem':
		peak.isEmblem = True
		if not classNames:
			return True
		className = classNames.pop(0)
	elif className == 'mtneer':
		peak.isMtneer = True
		if not classNames:
			return True
		className = classNames.pop(0)

	if className.startswith('land'):
		peak.landClass = className
		if not classNames:
			return True
		className = classNames.pop(0)

	if className == 'suspended':
		peak.suspended = True
		if not classNames:
			return True

	return False

class LandMgmtArea(object):
	def __init__(self, peak, url, highPoint):
		self.count = 1
		self.url = url
		self.highPoint = peak if highPoint else None
		self.highestPoint = peak

	def add(self, peak, url, highPoint):
		self.count += 1
		if url != self.url:
			if self.url is None:
				self.url = url
			elif url is not None:
				return "URL doesn't match previous URL"
		if highPoint:
			if self.highPoint is not None:
				return "Duplicate high point"
			self.highPoint = peak
		return None

landNameLookup = {
	"Giant Sequoia National Monument":      'Sequoia National Forest',
	"Harvey Monroe Hall RNA":               'Hoover Wilderness',
	"Lake Mead NRA":                        'landNPS',
	"Lake Tahoe Basin Management Unit":     'landFS',
	"Mono Basin Scenic Area":               'Inyo National Forest',
	"Navajo Nation":                        'landRez',
	"NAWS China Lake":                      'landDOD',
	"Organ Pipe Cactus NM":                 'landNPS',
	"Providence Mountains SRA":             'landSP',
	"Red Rock Canyon NCA":                  'landBLM',
	"Spring Mountains NRA":                 'Humboldt-Toiyabe National Forest',
	"Tohono O'odham Indian Reservation":    'landRez',
	"Virgin Peak Instant Study Area":       'landBLM',
}
landNameSuffixes = [
	(' National Forest',            'landFS'),
	(' National Park',              'landNPS'),
	(' National Preserve',          'landNPS'),
	(' National Wildlife Refuge',   'landFWS'),
	(' State Park',                 'landSP'),
]
landNamePrefixes = [
	('BLM ',                        'landBLM'),
]
landMgmtPattern = re.compile('^(?:<a href="([^"]+)">([- A-Za-z]+)</a>( HP)?)|([- \'A-Za-z]+)')
fsLinkPattern = re.compile('^https://www\\.fs\\.usda\\.gov/[a-z]+$')
fwsLinkPattern = re.compile('^https://www\\.fws\\.gov/refuge/[a-z]+/$')
npsLinkPattern = re.compile('^https://www\\.nps\\.gov/[a-z]{4}/index\\.htm$')
stateParkPattern = re.compile('^https://www\\.parks\\.ca\\.gov/\\?page_id=[0-9]+$')
wildernessPattern = re.compile('^http://www\\.wilderness\\.net/NWPS/wildView\\?WID=[0-9]+$')
landLinkPattern = {
	'landFS':       fsLinkPattern,
	'landFWS':      fwsLinkPattern,
	'landNPS':      npsLinkPattern,
	'landSP':       stateParkPattern,
}
landOrder = {
	'landDOD':      0,
	'landRez':      1,
	'landFWS':      2,
	'landBLM':      3,
	'landFS':       4,
	'landBLMW':     5,
	'landFSW':      6,
	'landSP':       7,
	'landNPS':      8,
}

def parseLandManagement(pl, peak):
	line = pl.htmlFile.next()

	if line[:4] != '<td>' or line[-6:] != '</td>\n':
		badLine()
	line = line[4:-6]

	if peak.nonUS:
		if line == '&nbsp;':
			return
		badLine()

	landList = []
	landClass = None

	while True:
		m = landMgmtPattern.match(line)
		if m is None:
			badLine()

		landLink, landName, landHP, landName2 = m.groups()
		line = line[m.end():]

		if landName2 is not None:
			landName = landName2
			if landName[-3:] == ' HP':
				landHP = landName[-3:]
				landName = landName[:-3]

		if landName.endswith(' Wilderness'):
			if landClass == 'landFS':
				landClass = 'landFSW'
			elif landClass is None or landClass == 'landBLM':
				landClass = 'landBLMW'
			if landLink is not None and wildernessPattern.match(landLink) is None:
				raise FormatError("Wilderness URL doesn't match expected pattern")
		else:
			currentClass = landNameLookup.get(landName)
			if currentClass is None:
				for suffix, suffixClass in landNameSuffixes:
					if landName.endswith(suffix):
						currentClass = suffixClass
						break
				else:
					for prefix, prefixClass in landNamePrefixes:
						if landName.startswith(prefix):
							currentClass = prefixClass
							break
					else:
						raise FormatError("Unrecognized land management name")

			if currentClass.startswith('land'):
				linkPattern = landLinkPattern.get(currentClass)
				if linkPattern is not None:
					if landLink is None or linkPattern.match(landLink) is None:
						raise FormatError("Land management URL doesn't match expected pattern")

				if landClass is None:
					landClass = currentClass
				elif landOrder[landClass] < landOrder[currentClass]:
					raise FormatError("Unexpected order of land management areas")

			elif not (landList and currentClass == landList[-1][1]):
				raise FormatError('"{}" must follow "{}"', landName, currentClass)

		if landName in pl.landMgmtAreas:
			errorMsg = pl.landMgmtAreas[landName].add(peak, landLink, landHP is not None)
			if errorMsg:
				raise FormatError("{} for {}", errorMsg, landName)
		else:
			pl.landMgmtAreas[landName] = LandMgmtArea(peak, landLink, landHP is not None)

		if landHP is None:
			landHP = ''
		landList.append((landLink, landName, landHP))
		if line == '':
			break
		if line[:4] != '<br>':
			badLine()
		line = line[4:]

	if peak.landClass != landClass:
		raise FormatError("Land management column doesn't match class")
	peak.landManagement = '<br>'.join([
		'<a href="{}">{}</a>{}'.format(landLink, landName, landHP) if landLink
		else landName + landHP
		for (landLink, landName, landHP) in landList])

def printLandManagementAreas(pl):
	for name, area in sorted(pl.landMgmtAreas.iteritems()):
		print '{:35}{: 3}  {:22} {}'.format(name,
			area.count,
			area.highPoint.name if area.highPoint else '-',
			area.url if area.url else '-')

def toFeet(meters, delta=0.5):
	return int(meters / 0.3048 + delta)

class NGSDataSheet(object):
	sources = {}
	toFeetDelta = 0.488
	linkPrefix = 'https://www.ngs.noaa.gov/cgi-bin/ds_mark.prl?PidBox='
	tooltipPattern = re.compile('^([0-9]{4}(?:\\.[0-9]{1,2})?m) \\(NAVD 88\\) NGS Data Sheet &quot;([A-Z][a-z]+(?: [A-Z][a-z]+)*(?: [0-9]+)?)&quot; \\(([A-Z]{2}[0-9]{4})\\)$')

	def __init__(self, name, id):
		self.id = id
		self.name = name
		self.vdatum = 'NAVD 88'
		self.linkSuffix = id

	def __str__(self):
		return "NGS Data Sheet &quot;{}&quot; ({})".format(self.name, self.id)

	def setMeters(self):
		self.inMeters = True

class USGSTopo(object):
	sources = {}
	toFeetDelta = 0.5
	linkPrefix = 'https://ngmdb.usgs.gov/img4/ht_icons/Browse/'
	linkPattern = re.compile('^([A-Z]{2})/\\1_([A-Z][a-z]+(?:%20[A-Z][a-z]+)*)_([0-9]{6})_([0-9]{4})_(24000|62500|250000)\\.jpg$')
	tooltipPattern = re.compile('^((?:[0-9]{4}(?:(?:\\.[0-9])|(?:-[0-9]{4}))?m)|(?:[0-9]{4,5}(?:-[0-9]{4,5})?\'))(?: \\((MSL|NGVD 29)\\))? USGS (7\\.5|15|60)\' Quad \\(1:(24,000|62,500|250,000)\\) &quot;([\\. A-Za-z]+), ([A-Z]{2})&quot; \\(([0-9]{4}(?:/[0-9]{4})?)\\)$')

	quadScale = {'7.5': '24,000', '15': '62,500', '60': '250,000'}
	quadVDatum = {'7.5': ('NGVD 29',), '15': ('MSL', 'NGVD 29'), '60': (None,)}

	def __init__(self, vdatum, series, scale, name, state, year):
		self.vdatum = vdatum
		self.series = series
		self.scale = scale
		self.name = name
		self.state = state
		self.year = year

		if scale != self.quadScale[series]:
			raise FormatError("Scale doesn't match {}' quad", series)
		if vdatum not in self.quadVDatum[series]:
			if vdatum is None:
				raise FormatError("Missing vertical datum for {}' quad", series)
			raise FormatError("Unexpected vertical datum ({}) for {}' quad", vdatum, series)

		self.linkSuffix = None
		self.inMeters = False
		self.contourInterval = None

	def setLinkSuffix(self, linkSuffix):
		m = self.linkPattern.match(linkSuffix)
		if m is None:
			raise FormatError("Elevation link suffix doesn't match expected pattern")
		self.id = m.group(3)

		self.linkSuffix = "{0}/{0}_{1}_{2}_{3}_{4}{5}.jpg".format(
			self.state,
			self.name.replace('.', '').replace(' ', '%20'),
			self.id,
			self.year[:4],
			self.scale[:-4],
			self.scale[-3:])

	def __str__(self):
		return "USGS {}' Quad (1:{}) &quot;{}, {}&quot; ({})".format(
			self.series, self.scale, self.name, self.state, self.year)

	def setMeters(self):
		if self.series != '7.5':
			raise FormatError("Unexpected elevation in meters on {}' quad", self.series)
		self.inMeters = True

	def setContourInterval(self, interval):
		if self.series != '7.5':
			raise FormatError("Unexpected elevation range on {}' quad", self.series)
		self.contourInterval = interval

def parseElevationTooltip(e, link, tooltip):
	for sourceClass in (NGSDataSheet, USGSTopo):
		if link.startswith(sourceClass.linkPrefix):
			m = sourceClass.tooltipPattern.match(tooltip)
			if m is None:
				raise FormatError("Tooltip doesn't match expected pattern")
			e.source = sourceClass(*m.groups()[1:])
			linkSuffix = link[len(sourceClass.linkPrefix):]
			if e.source.linkSuffix is None:
				e.source.setLinkSuffix(linkSuffix)
			if linkSuffix != e.source.linkSuffix:
				raise FormatError("Elevation link suffix doesn't match")
			if not e.checkTooltipElevation(m.group(1)):
				raise FormatError("Elevation in tooltip doesn't match")
			return

	raise FormatError("Unrecognized elevation link")

class Elevation(object):
	pattern1 = re.compile('^([0-9]{1,2},[0-9]{3}\\+?)')
	pattern2 = re.compile('^<span><a href="([^"]+)">([0-9]{1,2},[0-9]{3}\\+?)</a><div class="tooltip">([- &\'(),\\.:;/0-9A-Za-z]+)(?:(</div></span>)|$)')

	def __init__(self, elevation):
		self.isRange = elevation[-1] == '+'
		if self.isRange:
			elevation = elevation[:-1]
		self.elevationFeet = int(elevation[:-4] + elevation[-3:])
		self.elevationMeters = None
		self.extraLines = ''
		self.source = None

	def getElevation(self):
		return '{},{:03}'.format(*divmod(self.elevationFeet, 1000)) + ('+' if self.isRange else '')

	def getTooltip(self):
		src = self.source

		if self.elevationMeters is None:
			elevation, suffix = self.elevationFeet, "'"
		else:
			elevation, suffix = self.elevationMeters, "m"

		tooltip = [str(elevation), suffix, " ", str(src)]

		if src.vdatum is not None:
			tooltip[2:2] = [" (", src.vdatum, ")"]
		if self.isRange:
			tooltip[1:1] = ["-", str(elevation + src.contourInterval - 1)]

		return ''.join(tooltip)

	def html(self):
		if self.source is None:
			return self.getElevation()

		return '<span><a href="{}{}">{}</a><div class="tooltip">{}{}</div></span>'.format(
			self.source.linkPrefix,
			self.source.linkSuffix,
			self.getElevation(), self.getTooltip(), self.extraLines)

	def checkTooltipElevation(self, elevation):
		inMeters = elevation[-1] == 'm'
		elevation = elevation[:-1]
		isRange = '-' in elevation
		if isRange:
			elevation, elevationMax = elevation.split('-')
			elevationMin = int(elevation)
			elevationMax = int(elevationMax)
			interval = elevationMax - elevationMin + 1
			contourIntervals = (10, 20) if inMeters else (20, 40)
			if interval not in contourIntervals or elevationMin % interval != 0:
				raise FormatError("Elevation range in tooltip not valid")
			self.source.setContourInterval(interval)
		if inMeters:
			self.source.setMeters()
			self.elevationMeters = float(elevation) if '.' in elevation else int(elevation)
			elevation = toFeet(self.elevationMeters, self.source.toFeetDelta)
		else:
			elevation = int(elevation)

		return elevation == self.elevationFeet and isRange == self.isRange

def parseElevation(pl, peak):
	line = pl.htmlFile.next()

	if line[:4] != '<td>':
		badLine()
	line = line[4:]

	while True:
		m = Elevation.pattern1.match(line)
		if m is not None:
			e = Elevation(m.group(1))
			line = line[m.end():]
		else:
			m = Elevation.pattern2.match(line)
			if m is None:
				badLine()

			e = Elevation(m.group(2))
			parseElevationTooltip(e, m.group(1), m.group(3))

			if m.group(4) is None:
				e.extraLines = '\n'
				for line in pl.htmlFile:
					if line.startswith('</div></span>'):
						line = line[13:]
						break
					e.extraLines += line
			else:
				line = line[m.end():]

		peak.elevations.append(e)

		if line == '</td>\n':
			break
		if line[:4] != '<br>':
			badLine()
		line = line[4:]

tableLine = '<p><table id="peakTable" class="land landColumn">\n'

def readHTML(pl):
	sectionRowPattern = re.compile('^<tr class="section"><td id="' + pl.id + '([0-9]+)" colspan="' + pl.colspan + '">\\1\\. ([- &,;A-Za-z]+)</td></tr>$')
	peakRowPattern = re.compile('^<tr(?: class="([A-Za-z]+(?: [A-Za-z]+)*)")?(?: data-from="(([A-Z]+)([0-9]+)\\.([0-9]+))")?>$')
	column1Pattern = re.compile('^<td(?: id="' + pl.id + '([0-9]+\\.[0-9]+)")?( rowspan="2")?>([0-9]+\\.[0-9]+)</td>$')
	column2Pattern = re.compile('^<td><a href="https://mappingsupport\\.com/p/gmap4\\.php\\?ll=([0-9]+\\.[0-9]+),-([0-9]+\\.[0-9]+)&z=([0-9]+)&t=(t[14])">([ \'#()0-9A-Za-z]+)</a>( \\*{1,2}| HP)?(?:<br>\\(([ A-Za-z]+)\\))?</td>$')
	gradePattern = re.compile('^<td>Class ([123456](?:s[23456]\\+?)?)</td>$')
	prominencePattern1 = re.compile('^<td>((?:[0-9]{1,2},)?[0-9]{3})</td>$')
	prominencePattern2 = re.compile('^<td><a href="([^"]+)">((?:[0-9]{1,2},)?[0-9]{3})</a></td>$')
	summitpostPattern = re.compile('^<td><a href="http://www\\.summitpost\\.org/([-a-z]+)/([0-9]+)">SP</a></td>$')
	wikipediaPattern = re.compile('^<td><a href="https://en\\.wikipedia\\.org/wiki/([_,()%0-9A-Za-z]+)">W</a></td>$')
	bobBurdPattern = re.compile('^<td><a href="http://www\\.snwburd\\.com/dayhikes/peak/([0-9]+)">BB</a></td>$')
	listsOfJohnPattern = re.compile('^<td><a href="https://listsofjohn\\.com/peak/([0-9]+)">LoJ</a></td>$')
	peakbaggerPattern = re.compile('^<td><a href="http://peakbagger\\.com/peak.aspx\\?pid=([0-9]+)">Pb</a></td>$')
	peteYamagataPattern = re.compile('^<td><a href="http://www\\.petesthousandpeaks\\.com/Captions/nspg/([a-z]+)\\.html">PY</a></td>$')
	weatherPattern = re.compile('^<td><a href="http://forecast\\.weather\\.gov/MapClick\\.php\\?lon=-([0-9]+\\.[0-9]+)&lat=([0-9]+\\.[0-9]+)">WX</a></td>$')
	climbedPattern = re.compile('^<td>(?:([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})|(?:<a href="/photos/([0-9A-Za-z]+(?:/best)?/(?:index[0-9][0-9]\\.html)?)">([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})</a>))(?: (solo|(?:with .+)))</td>$')
	emptyCell = '<td>&nbsp;</td>\n'
	extraRowFirstLine = '<tr><td colspan="{}"><ul>\n'.format(pl.colspanMinus1)
	extraRowLastLine = '</ul></td></tr>\n'
	dataFromList = []

	pl.htmlFile = htmlFile = InputFile(pl.htmlFilename)
	for line in htmlFile:
		if line == tableLine:
			break
	for line in htmlFile:
		m = sectionRowPattern.match(line)
		if m is not None:
			pl.sections.append(m.group(2))
			if int(m.group(1)) != len(pl.sections):
				raise FormatError("Unexpected section number")
			pl.peaks.append([])
			break
	for line in htmlFile:
		m = peakRowPattern.match(line)
		if m is not None:
			peak = Peak()
			if m.group(2) is not None:
				peak.dataFrom = m.group(2)
				dataFromList.append([peak, m.group(3), int(m.group(4)), int(m.group(5))])
			if not parseClasses(peak, m.group(1)):
				raise FormatError("Bad class names")

			line = htmlFile.next()
			m = column1Pattern.match(line)
			if m is None:
				badLine()
			if m.group(2) is not None:
				peak.extraRow = ''
			peak.id = m.group(3)
			if m.group(1) is not None:
				if peak.id != m.group(1):
					raise FormatError("HTML ID doesn't match peak ID")
				peak.hasHtmlId = True

			sectionNumber, peakNumber = peak.id.split('.')
			sectionNumber, peakNumber = int(sectionNumber), int(peakNumber)
			if sectionNumber != len(pl.sections):
				raise FormatError("Peak ID doesn't match section number")
			if peakNumber != len(pl.peaks[-1]) + 1:
				raise FormatError("Peak ID doesn't match peak number")
			if pl.id == 'DPS' and sectionNumber == 9:
				peak.nonUS = True

			line = htmlFile.next()
			m = column2Pattern.match(line)
			if m is None:
				badLine()
			peak.latitude = m.group(1)
			peak.longitude = m.group(2)
			peak.zoom = m.group(3)
			peak.baseLayer = m.group(4)
			peak.name = m.group(5)
			suffix = m.group(6)
			peak.otherName = m.group(7)

			if peak.nonUS:
				if peak.baseLayer != 't1':
					badLine()
			else:
				if peak.baseLayer != 't4':
					badLine()

			if suffix is None:
				if peak.isEmblem or peak.isMtneer:
					badSuffix()
			elif suffix == ' *':
				if not peak.isMtneer:
					badSuffix()
			elif suffix == ' **':
				if not peak.isEmblem:
					badSuffix()
			else:
				peak.isHighPoint = True

			parseLandManagement(pl, peak)
			parseElevation(pl, peak)

			line = htmlFile.next()
			m = gradePattern.match(line)
			if m is None:
				badLine()
			peak.grade = m.group(1)
			if len(peak.grade) > 1:
				approachGrade, summitGrade = int(peak.grade[0]), int(peak.grade[2])
				if approachGrade >= summitGrade:
					raise FormatError("Summit grade must be greater than approach grade")
				if summitGrade == 6 and peak.grade[-1] == '+':
					raise FormatError("Summit grade 6+ doesn't make sense")

			line = htmlFile.next()
			m = prominencePattern1.match(line)
			if m is not None:
				peak.prominence = m.group(1)
			else:
				m = prominencePattern2.match(line)
				if m is None:
					badLine()
				peak.prominenceLink = m.group(1)
				peak.prominence = m.group(2)

			line = htmlFile.next()
			if line != emptyCell:
				m = summitpostPattern.match(line)
				if m is None:
					badLine()
				peak.summitpostName = m.group(1)
				peak.summitpostId = int(m.group(2))

			line = htmlFile.next()
			if line != emptyCell:
				m = wikipediaPattern.match(line)
				if m is None:
					badLine()
				peak.wikipediaLink = m.group(1)

			line = htmlFile.next()
			m = bobBurdPattern.match(line)
			if m is None:
				if pl.id in ('DPS', 'SPS') or line != emptyCell:
					badLine()
			else:
				peak.bobBurdId = m.group(1)

			line = htmlFile.next()
			m = listsOfJohnPattern.match(line)
			if m is None:
				if not (peak.nonUS and line == emptyCell):
					badLine()
			else:
				peak.listsOfJohnId = m.group(1)

			line = htmlFile.next()
			m = peakbaggerPattern.match(line)
			if m is None:
				badLine()
			peak.peakbaggerId = m.group(1)

			if pl.sps():
				line = htmlFile.next()
				if line != emptyCell:
					m = peteYamagataPattern.match(line)
					if m is None:
						badLine()
					peak.peteYamagataId = m.group(1)

			line = htmlFile.next()
			m = weatherPattern.match(line)
			if m is None:
				if not (peak.nonUS and line == emptyCell):
					badLine()
			else:
				wxLatitude = m.group(2)
				wxLongitude = m.group(1)
				if wxLatitude != peak.latitude or wxLongitude != peak.longitude:
					raise FormatError("Peak lat/long doesn't match WX lat/long")

			line = htmlFile.next()
			if line == emptyCell:
				if peak.isClimbed:
					badClimbed()
			else:
				m = climbedPattern.match(line)
				if m is None:
					badLine()
				if not peak.isClimbed:
					badClimbed()
				climbDate, peak.climbPhotos, peak.climbDate, peak.climbWith = m.groups()
				if peak.climbDate is None:
					peak.climbDate = climbDate

			line = htmlFile.next()
			if line != '</tr>\n':
				badLine()
			if peak.extraRow is not None:
				line = htmlFile.next()
				if line != extraRowFirstLine:
					badLine()
				for line in htmlFile:
					if line == extraRowLastLine:
						break
					peak.extraRow += line

			pl.peaks[-1].append(peak)
		else:
			m = sectionRowPattern.match(line)
			if m is not None:
				pl.sections.append(m.group(2))
				if int(m.group(1)) != len(pl.sections):
					raise FormatError("Unexpected section number")
				pl.peaks.append([])
			elif line == '</table>\n':
				break
			else:
				badLine()
	htmlFile.close()
	if sum([len(peaks) for peaks in pl.peaks]) != pl.numPeaks:
		raise FormatError("Number of peaks in HTML file is not {}", pl.numPeaks)
	if len(pl.sections) != pl.numSections:
		raise FormatError("Number of sections in HTML file is not {}", pl.numSections)

	for peak, pl2Id, numSection, numPeak in dataFromList:
		pl2 = peakLists.get(pl2Id)
		if pl2 is None:
			pl2 = PeakList(pl2Id.lower())
			pl2.readHTML()
		peak.copyFrom(pl2.peaks[numSection - 1][numPeak - 1])

def writeHTML(pl):
	oldColspan = ' colspan="' + pl.colspan + '"'
	newColspan = ' colspan="' + pl.colspan + '"'
	sectionFormat = '<tr class="section"><td id="{0}{1}"' + newColspan + '>{1}. {2}</td></tr>'
	column2Format = '<td><a href="https://mappingsupport.com/p/gmap4.php?ll={},-{}&z={}&t={}">{}</a>{}{}</td>'
	summitpostFormat = '<td><a href="http://www.summitpost.org/{0}/{1}">SP</a></td>'
	wikipediaFormat = '<td><a href="https://en.wikipedia.org/wiki/{0}">W</a></td>'
	bobBurdFormat = '<td><a href="http://www.snwburd.com/dayhikes/peak/{0}">BB</a></td>'
	listsOfJohnFormat = '<td><a href="https://listsofjohn.com/peak/{0}">LoJ</a></td>'
	peakbaggerFormat = '<td><a href="http://peakbagger.com/peak.aspx?pid={0}">Pb</a></td>'
	peteYamagataFormat = '<td><a href="http://www.petesthousandpeaks.com/Captions/nspg/{0}.html">PY</a></td>'
	weatherFormat = '<td><a href="http://forecast.weather.gov/MapClick.php?lon=-{0}&lat={1}">WX</a></td>'
	emptyCell = '<td>&nbsp;</td>'
	extraRowFirstLine = '<tr><td colspan="{}"><ul>'.format(pl.colspanMinus1)
	extraRowLastLine = '</ul></td></tr>'
	section1Line = sectionFormat.format(pl.id, 1, pl.sections[0]) + '\n'

	htmlFile = open(pl.htmlFilename)
	for line in htmlFile:
		print line,
		if line == tableLine:
			break
	for line in htmlFile:
		if line == section1Line:
			break
		line = line.replace(oldColspan, newColspan)
		print line,

	for sectionNumber, (sectionName, peaks) in enumerate(zip(pl.sections, pl.peaks)):
		print sectionFormat.format(pl.id, sectionNumber + 1, sectionName)

		for peak in peaks:
			suffix = ''
			classNames = []

			if peak.isClimbed:
				classNames.append('climbed')
			if peak.isHighPoint:
				suffix = ' HP'
			elif peak.isMtneer:
				suffix = ' *'
				classNames.append('mtneer')
			elif peak.isEmblem:
				suffix = ' **'
				classNames.append('emblem')
			if peak.landClass is not None:
				classNames.append(peak.landClass)
			if peak.suspended:
				classNames.append('suspended')

			attr = ''
			if classNames:
				attr += ' class="{}"'.format(' '.join(classNames))
			if peak.dataFrom is not None:
				attr += ' data-from="{}"'.format(peak.dataFrom)
			print '<tr{}>'.format(attr)

			attr = ''
			if peak.hasHtmlId:
				attr += ' id="{}{}"'.format(pl.id, peak.id)
			if peak.extraRow is not None:
				attr += ' rowspan="2"'
			print '<td{}>{}</td>'.format(attr, peak.id)

			otherName = '' if peak.otherName is None else '<br>({})'.format(peak.otherName)

			print column2Format.format(peak.latitude, peak.longitude, peak.zoom, peak.baseLayer,
				peak.name, suffix, otherName)

			if peak.landManagement is None:
				print emptyCell
			else:
				print '<td>{}</td>'.format(peak.landManagement)

			print '<td>{}</td>'.format(peak.elevationHTML())
			print '<td>Class {}</td>'.format(peak.grade)

			if peak.prominenceLink is None:
				print '<td>{}</td>'.format(peak.prominence)
			else:
				print '<td><a href="{}">{}</a></td>'.format(peak.prominenceLink, peak.prominence)

			if peak.summitpostId is None:
				print emptyCell
			else:
				print summitpostFormat.format(peak.summitpostName, peak.summitpostId)

			if peak.wikipediaLink is None:
				print emptyCell
			else:
				print wikipediaFormat.format(peak.wikipediaLink)

			if peak.bobBurdId is None:
				print emptyCell
			else:
				print bobBurdFormat.format(peak.bobBurdId)

			if peak.listsOfJohnId is None:
				print emptyCell
			else:
				print listsOfJohnFormat.format(peak.listsOfJohnId)

			print peakbaggerFormat.format(peak.peakbaggerId)

			if pl.sps():
				if peak.peteYamagataId is None:
					print emptyCell
				else:
					print peteYamagataFormat.format(peak.peteYamagataId)

			if peak.nonUS:
				print emptyCell
			else:
				print weatherFormat.format(peak.longitude, peak.latitude)

			if peak.isClimbed:
				if peak.climbPhotos is None:
					print '<td>{} {}</td>'.format(peak.climbDate, peak.climbWith)
				else:
					print '<td><a href="/photos/{}">{}</a> {}</td>'.format(
						peak.climbPhotos, peak.climbDate, peak.climbWith)
			else:
				print emptyCell

			print '</tr>'
			if peak.extraRow is not None:
				print extraRowFirstLine
				print peak.extraRow,
				print extraRowLastLine

	for line in htmlFile:
		if line == '</table>\n':
			print line,
			break
	for line in htmlFile:
		print line,
	htmlFile.close()

def writePeakJSON(f, peak):
	f('{\n')
	f('\t\t"type": "Feature",\n')
	f('\t\t"geometry": {"type": "Point", "coordinates": [-')
	f(peak.longitude)
	f(',')
	f(peak.latitude)
	f(']},\n')
	f('\t\t"properties": {\n')

	p = [('id', peak.id), ('name', peak.name)]
	if peak.otherName is not None:
		p.append(('name2', peak.otherName))

	p.append(('prom', peak.prominence))
	p.append(('YDS', peak.grade))
	p.append(('G4', 'z={}&t={}'.format(peak.zoom, peak.baseLayer)))
	if peak.bobBurdId is not None:
		p.append(('BB', peak.bobBurdId))
	if peak.listsOfJohnId is not None:
		p.append(('LoJ', peak.listsOfJohnId))
	if peak.peakbaggerId is not None:
		p.append(('Pb', peak.peakbaggerId))
	if peak.summitpostId is not None:
		p.append(('SP', '{}/{}'.format(peak.summitpostName, peak.summitpostId)))
	if peak.wikipediaLink is not None:
		p.append(('W', peak.wikipediaLink))
	if peak.isClimbed:
		if peak.climbPhotos is None:
			p.append(('climbed', peak.climbDate))
		else:
			p.append(('climbed', '<a href=\\"https://nightjuggler.com/photos/{}\\">{}</a>'.format(
				peak.climbPhotos, peak.climbDate)))

	for k, v in p:
		f('\t\t\t"')
		f(k)
		f('": "')
		f(v)
		f('",\n')

	if peak.isHighPoint:
		f('\t\t\t"HP": true,\n')
	elif peak.isEmblem:
		f('\t\t\t"emblem": true,\n')
	elif peak.isMtneer:
		f('\t\t\t"mtneer": true,\n')
	if peak.nonUS:
		f('\t\t\t"noWX": true,\n')

	f('\t\t\t"elev": "')
	f(peak.elevationHTML().replace('"', '\\"').replace('\n', '\\n'))
	f('"\n\t\t}}')

def writeJSON(pl):
	f = sys.stdout.write
	firstPeak = True

	f('{\n')
	f('\t"id": "')
	f(pl.id)
	f('",\n\t"name": "')
	f(pl.geojsonTitle)
	f('",\n')
	f('\t"type": "FeatureCollection",\n')
	f('\t"features": [')
	for peaks in pl.peaks:
		for peak in peaks:
			if not peak.suspended:
				if firstPeak:
					firstPeak = False
				else:
					f(',')
				writePeakJSON(f, peak)
	f(']\n')
	f('}\n')

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('inputMode', nargs='?', default='sps', choices=sorted(peakListParams.keys()))
	parser.add_argument('outputMode', nargs='?', default='html', choices=['html', 'json', 'land'])
	args = parser.parse_args()

	pl = PeakList(args.inputMode)
	pl.readHTML()

	if args.outputMode == 'html':
		writeHTML(pl)
	elif args.outputMode == 'json':
		writeJSON(pl)
	elif args.outputMode == 'land':
		printLandManagementAreas(pl)

if __name__ == '__main__':
	main()
