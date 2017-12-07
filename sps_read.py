#!/usr/bin/python
import re
import sys
import vertcon

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
		'numPeaks': 248,
		'numSections': 24,
	},
	'dps': {
		'geojsonTitle': 'Desert Peaks',
		'numPeaks': 99,
		'numSections': 9,
	},
	'gbp': {
		'geojsonTitle': 'Great Basin Peaks',
		'numPeaks': 15,
		'numSections': 12,
	},
	'npc': {
		'geojsonTitle': 'Nevada Peaks Club',
		'numPeaks': 19,
		'numSections': 6,
	},
	'osp': {
		'geojsonTitle': 'Other Sierra Peaks',
		'numPeaks': 20,
		'numSections': 24,
	},
}

class PeakList(object):
	def __init__(self, id):
		self.__dict__.update(peakListParams[id])

		self.id = id.upper()
		self.htmlFilename = getattr(self, 'baseFilename', id) + '.html'
		self.sierraPeaks = id in ('osp', 'sps')
		self.numColumns = 14 if self.sierraPeaks else 13
		self.peaks = []
		self.sections = []
		self.landMgmtAreas = {}

		peakLists[self.id] = self

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
		self.prominences = []
		self.grade = ''
		self.summitpostId = None
		self.summitpostName = None
		self.wikipediaLink = None
		self.bobBurdId = None
		self.listsOfJohnId = None
		self.peakbaggerId = None
		self.sierraColumn12 = None
		self.climbed = None
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

	def matchElevation(self, *args):
		results = []
		for e in self.elevations:
			result = e.match(*args)
			if result:
				results.append((e, result))
		return results

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
	tooltipPattern = re.compile(
		'^([0-9]{4}(?:\\.[0-9]{1,2})?m) \\(NAVD 88\\) NGS Data Sheet '
		'&quot;([A-Z][a-z]+(?: [A-Z][a-z]+)*(?: [0-9]+)?)&quot; \\(([A-Z]{2}[0-9]{4})\\)$')

	def __init__(self, name, id):
		self.id = id
		self.name = name
		self.vdatum = 'NAVD 88'
		self.linkSuffix = id
		self.inMeters = True

	def __str__(self):
		return "NGS Data Sheet &quot;{}&quot; ({})".format(self.name, self.id)

	def setUnits(self, inMeters):
		if not inMeters:
			raise FormatError("Elevation from NGS Data Sheet expected to be in meters")

	def addPeak(self, peak):
		src = self.sources.setdefault(self.id, self)
		if src is self:
			self.peak = peak
			return

		raise FormatError("NGS Data Sheet ID {} referenced {} peak", self.id,
			"more than once by the same" if src.peak is peak else "by more than one")

class USGSTopo(object):
	sources = {}
	toFeetDelta = 0.5
	linkPrefix = 'https://ngmdb.usgs.gov/img4/ht_icons/Browse/'
	linkPattern = re.compile(
		'^([A-Z]{2})/\\1_([A-Z][a-z]+(?:%20[A-Z][a-z]+)*)_'
		'([0-9]{6})_([0-9]{4})_(24000|62500|250000)\\.jpg$')
	tooltipPattern = re.compile(
		'^((?:[0-9]{4}(?:(?:\\.[0-9])|(?:-[0-9]{4}))?m)|(?:[0-9]{4,5}(?:-[0-9]{4,5})?\'))'
		'(?: \\((MSL|NGVD 29)\\))? USGS (7\\.5|15|60)\' Quad \\(1:(24,000|62,500|250,000)\\) '
		'&quot;([\\. A-Za-z]+), ([A-Z]{2})&quot; \\(([0-9]{4}(?:/[0-9]{4})?)\\)$')

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

	def setUnits(self, inMeters):
		if inMeters and self.series != '7.5':
			raise FormatError("Unexpected elevation in meters on {}' quad", self.series)
		self.inMeters = inMeters

	def setContourInterval(self, interval):
		if self.series != '7.5':
			raise FormatError("Unexpected elevation range on {}' quad", self.series)
		self.contourInterval = interval

	def addPeak(self, peak):
		src = self.sources.setdefault(self.id, self)
		if src is self:
			self.peaks = [peak]
			return

		if src.contourInterval is None:
			if self.contourInterval is not None:
				src.contourInterval = self.contourInterval
		elif self.contourInterval is None:
			self.contourInterval = src.contourInterval
		self.peaks = src.peaks

		if vars(self) != vars(src):
			raise FormatError("Topos with ID {} don't match", self.id)

		peak.elevations[-1].source = src
		src.peaks.append(peak)

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
	pattern2 = re.compile(
		'^<span><a href="([^"]+)">([0-9]{1,2},[0-9]{3}\\+?)</a>'
		'<div class="tooltip">([- &\'(),\\.:;/0-9A-Za-z]+)(?:(</div></span>)|$)')

	def __init__(self, elevation):
		self.isRange = elevation[-1] == '+'
		if self.isRange:
			elevation = elevation[:-1]
		self.elevationFeet = int(elevation[:-4] + elevation[-3:])
		self.source = None

	def getElevation(self):
		return '{},{:03}'.format(*divmod(self.elevationFeet, 1000)) + ('+' if self.isRange else '')

	def getTooltip(self):
		src = self.source

		if src.inMeters:
			elevation, suffix = self.elevationMeters, "m"
		else:
			elevation, suffix = self.elevationFeet, "'"

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
		self.source.setUnits(inMeters)
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
			self.elevationMeters = float(elevation) if '.' in elevation else int(elevation)
			elevation = toFeet(self.elevationMeters, self.source.toFeetDelta)
		else:
			elevation = int(elevation)

		return elevation == self.elevationFeet and isRange == self.isRange

	def match(self, feet, isRange=None):
		if feet == self.elevationFeet:
			if self.isRange:
				if not isRange:
					return "Range minimum (but not a range)"
			elif isRange:
				return "Range minimum (but not a range on my list)"
			return True

		if self.source is None:
			if not (self.isRange and isRange is None):
				return False

			result = "Range average{2} if contour interval is {0} {1}"
			for contour in (40, 20):
				if feet == self.elevationFeet + contour/2:
					return result.format(contour, "feet", "")

			meters = round(self.elevationFeet * 0.3048)
			for contour in (20, 10):
				average = meters + contour/2
				if feet == toFeet(average):
					return result.format(contour, "meters", "")
				if feet == toFeet(average, 0):
					return result.format(contour, "meters", " rounded down")
		elif self.isRange:
			if isRange is not None:
				return False

			if self.source.inMeters:
				average = self.elevationMeters + self.source.contourInterval/2
				if feet == toFeet(average):
					return True
				if feet == toFeet(average, 0):
					return "Range average rounded down"
			else:
				if feet == self.elevationFeet + self.source.contourInterval/2:
					return True
		elif self.source.inMeters:
			if isRange:
				return False

			meters = self.elevationMeters
			if isinstance(meters, float):
				m = "{:.2f}".format(meters)
				if m[-1] == '0' and m[-2] != '.':
					m = m[:-1]

				if feet == toFeet(round(meters)):
					return "round(round({})/0.3048)".format(m)
				if feet == toFeet(round(meters), 0):
					return "roundDown(round({})/0.3048)".format(m)

				if feet == toFeet(meters, 0):
					return "roundDown({}/0.3048)".format(m)

				if feet == toFeet(int(meters)):
					return "round(roundDown({})/0.3048)".format(m)
				if feet == toFeet(int(meters), 0):
					return "roundDown(roundDown({})/0.3048)".format(m)
			else:
				if feet == toFeet(meters, 0):
					return "roundDown({}/0.3048)".format(meters)
		return False

def parseElevation(pl, peak):
	line = pl.htmlFile.next()

	if line[:4] != '<td>':
		badLine()
	line = line[4:]

	while True:
		m = Elevation.pattern1.match(line)
		if m is not None:
			e = Elevation(m.group(1))
			peak.elevations.append(e)
			line = line[m.end():]
		else:
			m = Elevation.pattern2.match(line)
			if m is None:
				badLine()

			e = Elevation(m.group(2))
			parseElevationTooltip(e, m.group(1), m.group(3))
			peak.elevations.append(e)
			if peak.dataFrom is None:
				e.source.addPeak(peak)

			if m.group(4) is None:
				e.extraLines = '\n'
				for line in pl.htmlFile:
					if line.startswith('</div></span>'):
						line = line[13:]
						break
					e.extraLines += line
			else:
				e.extraLines = ''
				line = line[m.end():]

		if line == '</td>\n':
			break
		if line[:4] != '<br>':
			badLine()
		line = line[4:]

def printElevationStats(pl):
	print '\n====== {} NGS Data Sheets\n'.format(len(NGSDataSheet.sources))

	for id, src in sorted(NGSDataSheet.sources.iteritems()):
		peak = src.peak
		name = peak.name
		if peak.isHighPoint:
			name += ' HP'
		if peak.otherName is not None:
			name += ' ({})'.format(peak.otherName)
		print '{} ({}) {}'.format(id, src.name, name)

	print '\n====== {} USGS Topo Maps\n'.format(len(USGSTopo.sources))

	for id, src in sorted(USGSTopo.sources.iteritems()):
		numRefs = len(src.peaks)
		numPeaks = len(set(src.peaks))

		print '{}  {:>3}  {:>7}  {} {:20} {:9}  {}/{}{}'.format(id,
			src.series, src.scale, src.state, src.name, src.year,
			numPeaks, numRefs, '' if numRefs == numPeaks else ' *')

RE_Escape = re.compile('[\\' + '\\'.join('$()*+.?[]^') + ']')

def toRegExp(spec, *args):
	return re.compile('^' + RE_Escape.sub('\\\\\\g<0>', spec[:-1]).format(*args) + '$')

class SimpleColumn(object):
	def __init__(self, id):
		self.id = id

	def __str__(self):
		return self.prefix + self.id + self.suffix

	@classmethod
	def match(self, line):
		prefixLen = len(self.prefix)
		suffixLen = len(self.suffix)

		if line[:prefixLen] != self.prefix:
			badLine()
		if line[-suffixLen:] != self.suffix:
			badLine()

		m = self.pattern.match(line[prefixLen:-suffixLen])
		if m is None:
			badLine()

		return self(m.group())

class ColumnHPS(SimpleColumn):
	prefix = '<td><a href="http://www.hundredpeaks.org/Peaks/'
	suffix = '.html">HPS</a></td>\n'
	pattern = re.compile('^[0-9]{2}[A-Z]$')

class ColumnPY(SimpleColumn):
	prefix = '<td><a href="http://www.petesthousandpeaks.com/Captions/nspg/'
	suffix = '.html">PY</a></td>\n'
	pattern = re.compile('^[a-z]+$')

class ColumnVR(object):
	spec = '<td><a href="http://vulgarianramblers.org/peak_detail.php?peak_name={}">{}</a></td>\n'
	pattern = toRegExp(spec, '([-%0-9A-Za-z]+)', '((?:#[1-9][0-9]{0,2})|VR)')

	def __init__(self, name, rank=None):
		self.name = name
		self.rank = rank

	def __str__(self):
		return self.spec.format(self.name,
			'VR' if self.rank is None else '#' + str(self.rank))

	@classmethod
	def match(self, line):
		m = self.pattern.match(line)
		if m is None:
			badLine()

		name, rank = m.groups()

		if rank == 'VR':
			rank = None
		else:
			rank = int(rank[1:])
			if rank > 147:
				raise FormatError("Thirteener rank expected to be between 1 and 147")

		return self(name, rank)

def addSection(pl, m):
	id, sectionNumber, colspan, sectionName = m.groups()
	if id != pl.id:
		raise FormatError('Expected id="{}{}" for section row', pl.id, len(pl.sections) + 1)
	if colspan != str(pl.numColumns):
		raise FormatError('Expected colspan="{}" for section row', pl.numColumns)

	pl.sections.append(sectionName)
	if int(sectionNumber) != len(pl.sections):
		raise FormatError("Unexpected section number")
	pl.peaks.append([])

class RE(object):
	sectionRow = re.compile(
		'^<tr class="section">'
		'<td id="([A-Z]+)([0-9]+)" colspan="(1[0-9])">'
		'\\2\\. ([- &,;A-Za-z]+)</td></tr>$'
	)
	peakRow = re.compile(
		'^<tr(?: class="([A-Za-z]+(?: [A-Za-z]+)*)")?'
		'(?: data-from="(([A-Z]+)([0-9]+)\\.([0-9]+))")?>$'
	)
	column1 = re.compile(
		'^<td(?: id="([A-Z]+)([0-9]+\\.[0-9]+)")?( rowspan="2")?>([0-9]+\\.[0-9]+)</td>$'
	)
	column2 = re.compile(
		'^<td><a href="https://mappingsupport\\.com/p/gmap4\\.php\\?'
		'll=([0-9]+\\.[0-9]+),-([0-9]+\\.[0-9]+)&z=([0-9]+)&t=(t[14])">'
		'([ #&\'()0-9;A-Za-z]+)</a>( \\*{1,2}| HP)?(?:<br>\\(([ A-Za-z]+)\\))?</td>$'
	)
	grade = re.compile(
		'^<td>Class ([123456](?:s[23456]\\+?)?)</td>$'
	)
	prominence = re.compile('^[,0-9]+')
	prominence1 = re.compile('^[1-9][0-9]{0,2}$')
	prominence2 = re.compile('^[1-9][0-9]?,[0-9]{3}$')
	prominenceTooltip = re.compile('^[- "&\'\\(\\)\\+,/0-9:;<=>A-Za-z]+$')
	summitpost = re.compile(
		'^<td><a href="http://www\\.summitpost\\.org/([-0-9a-z]+)/([0-9]+)">SP</a></td>$'
	)
	wikipedia = re.compile(
		'^<td><a href="https://en\\.wikipedia\\.org/wiki/([_,()%0-9A-Za-z]+)">W</a></td>$'
	)
	bobBurd = re.compile(
		'^<td><a href="http://www\\.snwburd\\.com/dayhikes/peak/([0-9]+)">BB</a></td>$'
	)
	listsOfJohn = re.compile(
		'^<td><a href="https://listsofjohn\\.com/peak/([0-9]+)">LoJ</a></td>$'
	)
	peakbagger = re.compile(
		'^<td><a href="http://peakbagger\\.com/peak.aspx\\?pid=([0-9]+)">Pb</a></td>$'
	)
	weather = re.compile(
		'^<td><a href="http://forecast\\.weather\\.gov/MapClick\\.php\\?'
		'lon=-([0-9]+\\.[0-9]+)&lat=([0-9]+\\.[0-9]+)">WX</a></td>$'
	)
	climbedDate = re.compile('^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}')
	climbedLink = re.compile('^/photos/([0-9A-Za-z]+(?:/best)?/(?:index[0-9][0-9]\\.html)?)">')
	climbedWithLink = re.compile('^(https?://[-\\./0-9A-Za-z]+)">')
	climbedWithName = re.compile('^[A-Z][a-z]+(?: [A-Z][a-z]+)*')

def parseClimbedWith(line):
	climbedWith = []
	lastName = False

	while True:
		photoLink = None
		if line.startswith('<a href="'):
			line = line[9:]
			m = RE.climbedWithLink.match(line)
			if m is None:
				raise FormatError("Climbed-with link doesn't match expected pattern")
			photoLink = m.group(1)
			line = line[m.end():]

		m = RE.climbedWithName.match(line)
		if m is None:
			raise FormatError("Climbed-with name doesn't match expected pattern")
		name = m.group()
		line = line[m.end():]
		if photoLink is None:
			climbedWith.append(name)
		else:
			if not line.startswith('</a>'):
				raise FormatError("Expected </a> after climbed-with name")
			line = line[4:]
			climbedWith.append((name, photoLink))
		if lastName:
			break

		if line.startswith(' and '):
			if len(climbedWith) != 1:
				badLine()
			lastName = True
			line = line[5:]
		elif line.startswith(', and '):
			if len(climbedWith) == 1:
				badLine()
			lastName = True
			line = line[6:]
		elif line.startswith(', '):
			line = line[2:]
		elif len(climbedWith) == 1:
			break
		else:
			badLine()

	return line, climbedWith

def parseClimbed(line, htmlFile):
	climbed = []

	if not line.startswith('<td>'):
		badLine()

	while True:
		line = line[4:]

		photoLink = None
		if line.startswith('<a href="'):
			line = line[9:]
			m = RE.climbedLink.match(line)
			if m is None:
				raise FormatError("Climbed date link doesn't match expected pattern")
			photoLink = m.group(1)
			line = line[m.end():]

		m = RE.climbedDate.match(line)
		if m is None:
			raise FormatError("Climbed date doesn't match expected pattern")
		date = m.group()
		line = line[m.end():]
		if photoLink is None:
			climbedDate = date
		else:
			if not line.startswith('</a>'):
				raise FormatErorr("Expected </a> after climbed date")
			line = line[4:]
			climbedDate = (date, photoLink)

		if line.startswith(' solo'):
			line = line[5:]
			climbed.append((climbedDate, []))
		elif line.startswith(' with '):
			line, climbedWith = parseClimbedWith(line[6:])
			climbed.append((climbedDate, climbedWith))
		else:
			raise FormatError("Expected 'solo' or 'with' after climbed date")

		if line == '</td>\n':
			break
		if line == '\n':
			line = htmlFile.next()
			if line.startswith('<br>'):
				continue
		badLine()

	return climbed

def climbed2Html(climbed):
	lines = []

	for date, climbedWith in climbed:
		line = []

		if isinstance(date, str):
			line.append(date)
		else:
			line.append('<a href="/photos/{1}">{0}</a>'.format(*date))

		if climbedWith:
			line.append('with')

			names = []
			for name in climbedWith:
				if isinstance(name, str):
					names.append(name)
				else:
					names.append('<a href="{1}">{0}</a>'.format(*name))
			if len(names) > 2:
				names = ', and '.join([', '.join(names[:-1]), names[-1]])
			else:
				names = ' and '.join(names)

			line.append(names)
		else:
			line.append('solo')

		lines.append(' '.join(line))

	return '\n<br>'.join(lines)

def parseProminence(line):
	if not line.startswith('<td>'):
		badLine()

	prominences = []

	while True:
		line = line[4:]
		tooltip = False
		if line.startswith('<span>'):
			line = line[6:]
			tooltip = True

		m = RE.prominence.match(line)
		if m is None:
			badLine()
		prom = m.group()
		line = line[m.end():]

		if len(prom) < 4:
			m = RE.prominence1.match(prom)
			if m is None:
				badLine()
			prom = int(prom)
		else:
			m = RE.prominence2.match(prom)
			if m is None:
				badLine()
			prom = int(prom[:-4]) * 1000 + int(prom[-3:])

		if tooltip:
			if not line.startswith('<div class="tooltip">'):
				raise FormatError('Expected <div class="tooltip">')
			line = line[21:]

			i = line.find('</div>')
			if i < 0:
				badLine()

			m = RE.prominenceTooltip.match(line[:i])
			if m is None:
				badLine()
			tooltip = m.group()
			line = line[m.end():]

			if not line.startswith('</div></span>'):
				raise FormatError('Expected </div></span>')
			line = line[13:]

			prominences.append((prom, tooltip))
		else:
			prominences.append(prom)

		if not line.startswith('<br>'):
			break

	if not line == '</td>\n':
		badLine()

	return prominences

def int2str(n):
	return str(n) if n < 1000 else '{},{:03}'.format(*divmod(n, 1000))

def prom2html(prominences):
	lines = []

	for prom in prominences:
		if isinstance(prom, int):
			html = int2str(prom)
		else:
			prom, tooltip = prom
			html = '<span>{}<div class="tooltip">{}</div></span>'.format(int2str(prom), tooltip)
		lines.append(html)

	return '<br>'.join(lines)

tableLine = '<p><table id="peakTable" class="land landColumn">\n'

def readHTML(pl):
	emptyCell = '<td>&nbsp;</td>\n'
	extraRowFirstLine = '<tr><td colspan="{}"><ul>\n'.format(pl.numColumns - 1)
	extraRowLastLine = '</ul></td></tr>\n'
	dataFromList = []

	pl.htmlFile = htmlFile = InputFile(pl.htmlFilename)
	for line in htmlFile:
		if line == tableLine:
			break
	for line in htmlFile:
		m = RE.sectionRow.match(line)
		if m is not None:
			addSection(pl, m)
			break
	for line in htmlFile:
		m = RE.peakRow.match(line)
		if m is not None:
			peak = Peak()
			if m.group(2) is not None:
				peak.dataFrom = m.group(2)
				dataFromList.append([peak, m.group(3), int(m.group(4)), int(m.group(5))])
			if not parseClasses(peak, m.group(1)):
				raise FormatError("Bad class names")

			line = htmlFile.next()
			m = RE.column1.match(line)
			if m is None:
				badLine()
			htmlListId, htmlPeakId, extraRow, peakId = m.groups()
			if extraRow is not None:
				peak.extraRow = ''
			peak.id = peakId
			if htmlPeakId is not None:
				if pl.id != htmlListId or peak.id != htmlPeakId:
					raise FormatError("HTML ID doesn't match peak ID and/or peak list ID")
				peak.hasHtmlId = True

			sectionNumber, peakNumber = map(int, peak.id.split('.'))
			if sectionNumber != len(pl.sections):
				raise FormatError("Peak ID doesn't match section number")
			if peakNumber != len(pl.peaks[-1]) + 1:
				raise FormatError("Peak ID doesn't match peak number")
			if pl.id == 'DPS' and sectionNumber == 9:
				peak.nonUS = True

			line = htmlFile.next()
			m = RE.column2.match(line)
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
			m = RE.grade.match(line)
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
			peak.prominences = parseProminence(line)

			line = htmlFile.next()
			if line != emptyCell:
				m = RE.summitpost.match(line)
				if m is None:
					badLine()
				peak.summitpostName = m.group(1)
				peak.summitpostId = int(m.group(2))

			line = htmlFile.next()
			if line != emptyCell:
				m = RE.wikipedia.match(line)
				if m is None:
					badLine()
				peak.wikipediaLink = m.group(1)

			line = htmlFile.next()
			m = RE.bobBurd.match(line)
			if m is None:
				if line != emptyCell or pl.id in ('DPS', 'SPS'):
					badLine()
			else:
				peak.bobBurdId = m.group(1)

			line = htmlFile.next()
			m = RE.listsOfJohn.match(line)
			if m is None:
				if line != emptyCell or not (peak.nonUS or pl.id in ('OSP',)):
					badLine()
			else:
				peak.listsOfJohnId = m.group(1)

			line = htmlFile.next()
			m = RE.peakbagger.match(line)
			if m is None:
				if line != emptyCell or pl.id not in ('OSP',):
					badLine()
			else:
				peak.peakbaggerId = m.group(1)

			if pl.sierraPeaks:
				line = htmlFile.next()
				if line != emptyCell:
					peak.sierraColumn12 = (ColumnHPS if sectionNumber == 1 else
						ColumnPY if sectionNumber > 22 else ColumnVR).match(line)

			line = htmlFile.next()
			m = RE.weather.match(line)
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
				peak.climbed = parseClimbed(line, htmlFile)
				if not peak.isClimbed:
					badClimbed()

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
			m = RE.sectionRow.match(line)
			if m is not None:
				addSection(pl, m)
			elif line == '</table>\n':
				break
			else:
				badLine()
	htmlFile.close()
	if sum([len(peaks) for peaks in pl.peaks]) != pl.numPeaks:
		raise FormatError("Number of peaks is not {}", pl.numPeaks)
	if len(pl.sections) != pl.numSections:
		raise FormatError("Number of sections is not {}", pl.numSections)

	for peak, pl2Id, sectionNumber, peakNumber in dataFromList:
		pl2 = peakLists.get(pl2Id)
		if pl2 is None:
			pl2 = PeakList(pl2Id.lower())
			pl2.readHTML()
		peak.copyFrom(pl2.peaks[sectionNumber - 1][peakNumber - 1])

def writeHTML(pl):
	sectionFormat = '<tr class="section"><td id="{0}{1}" colspan="{2}">{1}. {3}</td></tr>'
	column2Format = '<td><a href="https://mappingsupport.com/p/gmap4.php?ll={},-{}&z={}&t={}">{}</a>{}{}</td>'
	summitpostFormat = '<td><a href="http://www.summitpost.org/{0}/{1}">SP</a></td>'
	wikipediaFormat = '<td><a href="https://en.wikipedia.org/wiki/{0}">W</a></td>'
	bobBurdFormat = '<td><a href="http://www.snwburd.com/dayhikes/peak/{0}">BB</a></td>'
	listsOfJohnFormat = '<td><a href="https://listsofjohn.com/peak/{0}">LoJ</a></td>'
	peakbaggerFormat = '<td><a href="http://peakbagger.com/peak.aspx?pid={0}">Pb</a></td>'
	weatherFormat = '<td><a href="http://forecast.weather.gov/MapClick.php?lon=-{0}&lat={1}">WX</a></td>'

	emptyCell = '<td>&nbsp;</td>'
	extraRowFirstLine = '<tr><td colspan="{}"><ul>'.format(pl.numColumns - 1)
	extraRowLastLine = '</ul></td></tr>'
	section1Line = sectionFormat.format(pl.id, 1, pl.numColumns, pl.sections[0]) + '\n'

	htmlFile = open(pl.htmlFilename)
	for line in htmlFile:
		print line,
		if line == tableLine:
			break
	for line in htmlFile:
		if line == section1Line:
			break
		print line,

	for sectionNumber, (sectionName, peaks) in enumerate(zip(pl.sections, pl.peaks)):
		print sectionFormat.format(pl.id, sectionNumber + 1, pl.numColumns, sectionName)

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
			print '<td>{}</td>'.format(prom2html(peak.prominences))

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

			if peak.peakbaggerId is None:
				print emptyCell
			else:
				print peakbaggerFormat.format(peak.peakbaggerId)

			if pl.sierraPeaks:
				if peak.sierraColumn12 is None:
					print emptyCell
				else:
					print str(peak.sierraColumn12),

			if peak.nonUS:
				print emptyCell
			else:
				print weatherFormat.format(peak.longitude, peak.latitude)

			if peak.isClimbed:
				print '<td>{}</td>'.format(climbed2Html(peak.climbed))
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

	p.append(('prom', prom2html(peak.prominences)))
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
		p.append(('climbed', '<br>'.join([date if isinstance(date, str) else
			'<a href=\\"https://nightjuggler.com/photos/{1}\\">{0}</a>'.format(*date)
			for date, climbedWith in peak.climbed])))

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

def checkData(pl):
	import sps_check
	getattr(sps_check, 'check' + pl.id)(pl)

def main():
	outputFunction = {
		'check': checkData,
		'elev': printElevationStats,
		'html': writeHTML,
		'json': writeJSON,
		'land': printLandManagementAreas,
	}
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('inputMode', nargs='?', default='sps', choices=sorted(peakListParams.keys()))
	parser.add_argument('outputMode', nargs='?', default='html', choices=sorted(outputFunction.keys()))
	args = parser.parse_args()

	pl = PeakList(args.inputMode)
	pl.readHTML()
	outputFunction[args.outputMode](pl)

if __name__ == '__main__':
	main()
