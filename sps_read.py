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

def int2str(n):
	return str(n) if n < 1000 else '{},{:03}'.format(*divmod(n, 1000))

peakLists = {}
peakListParams = {
	'sps': {
		'geojsonTitle': 'Sierra Peaks Section',
		'numPeaks': 248,
		'numSections': 24,
	},
	'dps': {
		'geojsonTitle': 'Desert Peaks Section',
		'numPeaks': 99,
		'numSections': 9,
	},
	'gbp': {
		'geojsonTitle': 'Great Basin Peaks',
		'numPeaks': 15,
		'numSections': 12,
	},
	'hps': {
		'geojsonTitle': 'Hundred Peaks Section',
		'numPeaks': 23,
		'numSections': 32,
	},
	'npc': {
		'geojsonTitle': 'Nevada Peaks Club',
		'numPeaks': 24,
		'numSections': 6,
	},
	'ogul': {
		'geojsonTitle': 'Tahoe Ogul Peaks',
		'numPeaks': 63,
		'numSections': 15,
	},
	'odp': {
		'geojsonTitle': 'Other Desert Peaks',
		'numPeaks': 4,
		'numSections': 8,
	},
	'osp': {
		'geojsonTitle': 'Other Sierra Peaks',
		'numPeaks': 25,
		'numSections': 24,
	},
}

class PeakList(object):
	def __init__(self, id):
		self.__dict__.update(peakListParams[id])

		self.id = id.upper()
		self.htmlFilename = getattr(self, 'baseFilename', id) + '.html'
		self.column12 = globals().get('column12_' + self.id)
		self.numColumns = 13 if self.column12 is None else 14
		self.peaks = []
		self.sections = []

		peakLists[id] = self
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
		self.column12 = None
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
		self.delisted = False
		self.suspended = False

	def elevationHTML(self):
		return '<br>'.join([e.html() for e in self.elevations])

	def prominenceHTML(self):
		return '<br>'.join([int2str(prom) if isinstance(prom, int) else prom.html()
			for prom in self.prominences])

	def landManagementHTML(self):
		return '<br>'.join([land.html(self) for land in self.landManagement])

	def matchElevation(self, elevation):
		exactMatches = []
		otherMatches = []
		matchMethod = 'match' + elevation.classId

		for e in self.elevations:
			result = getattr(e, matchMethod)(elevation)
			if result is True:
				exactMatches.append(e)
			elif result:
				otherMatches.append((e, result))

		return exactMatches, otherMatches

	def copyFrom(self, other):
		doNotCopy = ('id', 'column12', 'dataFrom', 'hasHtmlId',
			'isEmblem', 'isMtneer', 'delisted', 'suspended')

		if other.dataFrom is not None:
			sys.exit("{} should not have the data-from attribute!".format(self.dataFrom))

		for k, v in vars(other).iteritems():
			if not (k[0] == '_' or k in doNotCopy):
				setattr(self, k, v)

		if other.column12 is not None:
			self.column12 = other.column12

		self.dataFromPeak = other

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

	if className in ('delisted', 'suspended'):
		setattr(peak, className, True)
		if not classNames:
			return True

	return False

class LandMgmtArea(object):
	name2area = {}

	def __init__(self, name, link):
		self.count = 0
		self.name = name
		self.link = link
		self.highPoint = None
		self.highestPoint = None

	def err(self, message):
		raise FormatError("{} for {}", message, self.name)

	def isHighPoint(self, peak):
		if peak.dataFrom is not None:
			peak = peak.dataFromPeak

		return self.highPoint == peak

	def html(self, peak):
		highPoint = " HP" if self.isHighPoint(peak) else ""

		if self.link is None:
			return self.name + highPoint

		return "<a href=\"{}\">{}</a>{}".format(self.link, self.name, highPoint)

	@classmethod
	def add(self, peak, name, link, isHighPoint):
		area = self.name2area.get(name)
		if area is None:
			self.name2area[name] = area = self(name, link)

		if peak.dataFrom is not None:
			return area

		area.count += 1
		if link != area.link:
			if area.link is None:
				area.link = link
			elif link is not None:
				area.err("URL doesn't match previous URL")
		if isHighPoint:
			if area.highPoint is not None:
				area.err("Duplicate high point")
			area.highPoint = peak

		return area

landNameLookup = {
	"Carrizo Plain National Monument":      'landBLM',
	"Giant Sequoia National Monument":      'Sequoia National Forest',
	"Gold Butte National Monument":         'landBLM',
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
wildernessPattern = re.compile('^https://www\\.wilderness\\.net/NWPS/wildView\\?WID=[0-9]+$')
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

			elif not (landList and currentClass == landList[-1].name):
				raise FormatError('"{}" must follow "{}"', landName, currentClass)

		landList.append(LandMgmtArea.add(peak, landName, landLink, landHP is not None))

		if line == '':
			break
		if line[:4] != '<br>':
			badLine()
		line = line[4:]

	if peak.landClass != landClass:
		raise FormatError("Land management column doesn't match class")

	peak.landManagement = landList

def printLandManagementAreas(pl):
	readAllHTML()

	for name, area in sorted(LandMgmtArea.name2area.iteritems()):
		print '{:35}{:4}  {:22} {}'.format(name,
			area.count,
			area.highPoint.name if area.highPoint else '-',
			area.link if area.link else '-')

def toSurveyFeet(meters, delta=0.5):
	return int(meters * 39.37/12 + delta)

def toFeet(meters, delta=0.5):
	return int(meters / 0.3048 + delta)

def toMeters(feet, delta=0.5):
	return int(feet * 12/39.37 + delta)

class NGSDataSheet(object):
	sources = {}
	linkPrefix = 'https://www.ngs.noaa.gov/cgi-bin/ds_mark.prl?PidBox='
	tooltipPattern = re.compile(
		'^([0-9]{4}(?:\\.[0-9]{1,2})?m) \\(NAVD 88\\) NGS Data Sheet '
		'&quot;((?:Mc)?[A-Z][a-z]+(?: [A-Z][a-z]+)*(?: 2)?(?: VABM)?(?: [1-9][0-9]{3})?)&quot; '
		'\\(([A-Z]{2}[0-9]{4})\\)$')

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
	linkPrefix = 'https://ngmdb.usgs.gov/img4/ht_icons/Browse/'
	linkPattern = re.compile(
		'^[A-Z]{2}/[A-Z]{2}_(?:Mc)?[A-Z][a-z]+(?:%20[A-Z][a-z]+)*(?:%20(?:[SN][WE]))?_'
		'([0-9]{6})_[0-9]{4}_(?:24000|62500|125000|250000)\\.jpg$')
	tooltipPattern = re.compile(
		'^((?:[0-9]{3,4}(?:(?:\\.[0-9])|(?:-[0-9]{3,4}))?m)|(?:[0-9]{4,5}(?:-[0-9]{4,5})?\'))'
		'(?: \\((MSL|NGVD 29)\\))? USGS (7\\.5|15|30|60)\' Quad \\(1:(24,000|62,500|125,000|250,000)\\) '
		'&quot;([\\. A-Za-z]+), ([A-Z]{2})&quot; \\(([0-9]{4}(?:/[0-9]{4})?)\\)$')

	quadScale = {'7.5': '24,000', '15': '62,500', '30': '125,000', '60': '250,000'}
	quadVDatum = {'7.5': ('MSL', 'NGVD 29'), '15': ('MSL', 'NGVD 29'), '30': ('MSL',), '60': ('MSL', None)}

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
		self.id = m.group(1)

		state2 = self.state
		# Special case for the 1962 15' (1:62,500) Benton, NV-CA quad:
		# The JPG filename prefix is NV, but it's in the CA directory.
		if self.id == '320710':
			state2 = 'NV'

		self.linkSuffix = "{0}/{1}_{2}_{3}_{4}_{5}{6}.jpg".format(
			self.state,
			state2,
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
			e.checkTooltipElevation(m.group(1))
			return

	raise FormatError("Unrecognized elevation link")

class Elevation(object):
	pattern1 = re.compile('^([0-9]{1,2},[0-9]{3}\\+?)')
	pattern2 = re.compile(
		'^<span><a href="([^"]+)">([0-9]{1,2},[0-9]{3}\\+?)</a>'
		'<div class="tooltip">([- &\'(),\\.:;/0-9A-Za-z]+)(?:(</div></span>)|$)')

	def __init__(self, elevation, latlng):
		self.isRange = elevation[-1] == '+'
		if self.isRange:
			elevation = elevation[:-1]
		self.elevationFeet = int(elevation[:-4] + elevation[-3:])
		self.source = None
		self.latlng = latlng

	def getElevation(self):
		return '{},{:03}'.format(*divmod(self.elevationFeet, 1000)) + ('+' if self.isRange else '')

	def sortkey(self):
		src = self.source
		if src is None:
			return (80, not self.isRange, self.elevationFeet)
		if isinstance(src, NGSDataSheet):
			return (90, self.elevationFeet, src.id)
		if isinstance(src, USGSTopo):
			scale = int(src.scale[-3:]) + int(src.scale[:-4]) * 1000
			return (60, -scale, not self.isRange, src.year, src.id)
		return (0,)

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
			elevation = toSurveyFeet(self.elevationMeters)
		else:
			elevation = int(elevation)

		if isRange != self.isRange:
			raise FormatError("Elevation range doesn't match tooltip")
		if elevation != self.elevationFeet:
			raise FormatError("Elevation doesn't match tooltip")

	def matchLoJ(self, elevation):
		feet = elevation.feet

		if self.source is None:
			if not self.isRange:
				return feet == self.elevationFeet

			result = "Range average if contour interval is {0} {1}"
			for contour in (40, 20):
				if self.elevationFeet % contour == 0:
					if feet == self.elevationFeet + contour/2:
						return result.format(contour, "feet")

			meters = toMeters(self.elevationFeet)
			for contour in (20, 10):
				if meters % contour == 0:
					if feet == toFeet(meters + contour/2, 0):
						return result.format(contour, "meters")
			return False

		if not isinstance(self.source, USGSTopo):
			return False

		if self.isRange:
			if self.source.inMeters:
				return feet == toFeet(self.elevationMeters + self.source.contourInterval/2, 0)

			return feet == self.elevationFeet + self.source.contourInterval/2

		if self.source.inMeters:
			return feet == toFeet(self.elevationMeters, 0)

		return feet == self.elevationFeet

	def matchPb(self, elevation):
		feet = elevation.feet
		isRange = elevation.isRange

		if self.source is None:
			if feet == self.elevationFeet:
				if isRange == self.isRange:
					return True
				return "Range mismatch"

			if not isRange:
				meters = toMeters(self.elevationFeet)
				if feet == toFeet(meters):
					return "Would match if spot elevation is {}m".format(meters)
			return False

		if self.isRange:
			# Source must be USGSTopo
			if self.source.inMeters:
				elevationFeet = toFeet(self.elevationMeters)
				maxElevation = toFeet(self.elevationMeters + self.source.contourInterval)
			else:
				elevationFeet = self.elevationFeet
				maxElevation = elevationFeet + self.source.contourInterval
			if feet == elevationFeet:
				if not isRange:
					return "Range mismatch"
				if elevation.maxFeet == maxElevation:
					return True
				return "Max elevation mismatch"
			return False

		if self.source.vdatum == "NAVD 88":
			assert self.source.inMeters

			if feet == toFeet(self.elevationMeters - vertcon.getShift(*self.latlng)):
				if not isRange:
					return True
				return "Range mismatch"
			return False

		if self.source.inMeters:
			if feet == toFeet(round(self.elevationMeters)):
				if not isRange:
					return True
				return "Range mismatch"
			return False

		if feet == self.elevationFeet:
			if not isRange:
				return True
			return "Range mismatch"
		return False

	def matchVR(self, elevation):
		feet = elevation.feet

		if not self.isRange:
			return feet == self.elevationFeet

		assert self.source is not None

		if self.source.inMeters:
			maxFeet = toFeet(self.elevationMeters + self.source.contourInterval)
		else:
			maxFeet = self.elevationFeet + self.source.contourInterval

		return self.elevationFeet <= feet < maxFeet

def parseElevation(pl, peak):
	line = pl.htmlFile.next()

	if line[:4] != '<td>':
		badLine()

	latlng = (float(peak.latitude), float(peak.longitude))

	while True:
		line = line[4:]
		m = Elevation.pattern1.match(line)
		if m is not None:
			e = Elevation(m.group(1), latlng)
			peak.elevations.append(e)
			line = line[m.end():]
		else:
			m = Elevation.pattern2.match(line)
			if m is None:
				badLine()

			e = Elevation(m.group(2), latlng)
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

	e1 = peak.elevations[0]
	k1 = e1.sortkey()
	for e2 in peak.elevations[1:]:
		k2 = e2.sortkey()
		if k2 > k1:
			raise FormatError("Elevations are not in the expected order")
		e1 = e2
		k1 = k2

def printElevationStats(pl):
	readAllHTML()

	numAllSourced = 0
	numSomeSourced = 0
	for section in pl.peaks:
		for peak in section:
			numSources = 0
			for e in peak.elevations:
				if e.source is not None:
					numSources += 1
			if numSources == len(peak.elevations):
				numAllSourced += 1
			elif numSources > 0:
				numSomeSourced += 1

	print "Number of peaks with all elevations sourced: {}/{}".format(numAllSourced, pl.numPeaks)
	print "Number of peaks with some elevations sourced: {}/{}".format(numSomeSourced, pl.numPeaks)

	print '\n====== {} NGS Data Sheets\n'.format(len(NGSDataSheet.sources))

	for id, src in sorted(NGSDataSheet.sources.iteritems()):
		peak = src.peak
		print id, "({})".format(src.name), peak.name,
		if peak.isHighPoint:
			print "HP",
		if peak.otherName is not None:
			print "({})".format(peak.otherName),
		print

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
	prefix = '<td><a href="http://www.hundredpeaks.org/guides/'
	suffix = '.htm">HPS</a></td>\n'
	pattern = re.compile('^[0-9]{2}[a-z]$')

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

def column12_HPS(sectionNumber, peakNumber):
	return ColumnHPS, False

def column12_OGUL(sectionNumber, peakNumber):
	return ColumnPY, (sectionNumber, peakNumber) == (4, 2)

def column12_OSP(sectionNumber, peakNumber):
	if sectionNumber == 1:
		return ColumnHPS, True
	if sectionNumber >= 23:
		return ColumnPY, True
	return ColumnVR, True

def column12_SPS(sectionNumber, peakNumber):
	if sectionNumber == 1:
		return ColumnHPS, True
	if sectionNumber >= 23:
		return ColumnPY, False
	return ColumnVR, True

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
		'\\2\\. ([- &,;0-9A-Za-z]+)</td></tr>$'
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
		'll=([0-9]{1,2}\\.[0-9]{1,6}),(-[0-9]{1,3}\\.[0-9]{1,6})&z=(1[0-9])&t=(t[14])">'
		'([ #&\'()0-9;A-Za-z]+)</a>( \\*{1,2}| HP)?(?:<br>\\(([ A-Za-z]+)\\))?</td>$'
	)
	grade = re.compile(
		'^<td>Class ([123456](?:s[23456]\\+?)?)</td>$'
	)
	numLT1k = re.compile('^[1-9][0-9]{0,2}$')
	numGE1k = re.compile('^[1-9][0-9]?,[0-9]{3}$')
	numMeters = re.compile('^[1-9][0-9]{0,3}(?:\\.[0-9])?$')
	prominence = re.compile('^[,0-9]+')
	prominenceTooltip = re.compile(
		'^(?:\\(([,0-9]+m?) \\+ ([124]0m?)/2\\)|([,0-9]+(?:(?:\\.[0-9])?m)?))'
		' - (?:\\(([,0-9]+m?) - ([124]0m?)/2\\)|([,0-9]+(?:(?:\\.[0-9])?m)?))'
		' \\(([A-Z][A-Za-z]+(?:/[A-Z][A-Za-z]+)*)\\)(<br>Line Parent: '
		'[A-Z][a-z]+(?: [A-Z][a-z]+)*(?: \\([A-Z][a-z]+(?: [A-Z][a-z]+)*\\))? \\([,0-9]+\\))?$'
	)
	summitpost = re.compile(
		'^<td><a href="https://www\\.summitpost\\.org/([-0-9a-z]+)/([0-9]+)">SP</a></td>$'
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
		'^<td><a href="https://forecast\\.weather\\.gov/MapClick\\.php\\?'
		'lon=(-[0-9]{1,3}\\.[0-9]{1,6})&lat=([0-9]{1,2}\\.[0-9]{1,6})">WX</a></td>$'
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

def str2int(s):
	if len(s) < 4:
		if RE.numLT1k.match(s) is None:
			badLine()
		return int(s)

	if RE.numGE1k.match(s) is None:
		badLine()
	return int(s[:-4]) * 1000 + int(s[-3:])

def elevStr2Int(e):
	if e[-1] == 'm':
		e = e[:-1]
		if RE.numMeters.match(e) is None:
			badLine()
		if len(e) > 2 and e[-2] == '.':
			return float(e), True
		return int(e), True

	return str2int(e), False

class SimpleElevation(object):
	def __init__(self, baseElevation, contourInterval=0, inMeters=False, saddle=False):
		assert contourInterval in (0, 10, 20, 40)
		assert contourInterval == 0 and inMeters or isinstance(baseElevation, int)

		if saddle:
			self.minElev = baseElevation - contourInterval
			self.maxElev = baseElevation
		else:
			self.minElev = baseElevation
			self.maxElev = baseElevation + contourInterval

		self.inMeters = inMeters
		self.saddle = saddle

	def getFeetPb(self):
		if self.inMeters:
			if self.minElev == self.maxElev:
				feet = toFeet(round(self.minElev))
				return (feet, feet)
			return (toFeet(self.minElev), toFeet(self.maxElev))
		return (self.minElev, self.maxElev)

	def avgFeet(self, toFeet=toSurveyFeet):
		avgElev = (self.minElev + self.maxElev) / 2
		return toFeet(avgElev) if self.inMeters else avgElev

	def __str__(self):
		if self.minElev == self.maxElev:
			if self.inMeters:
				return str(self.minElev) + "m"
			return int2str(self.minElev)

		contour = self.maxElev - self.minElev
		if self.saddle:
			elev = self.maxElev
			sign = "-"
		else:
			elev = self.minElev
			sign = "+"

		if self.inMeters:
			return "({}m {} {}m/2)".format(elev, sign, contour)

		return "({} {} {}/2)".format(int2str(elev), sign, contour)

class Prominence(object):
	def __init__(self, peakElev, saddleElev, source, extraInfo=None):
		self.peakElev = peakElev
		self.saddleElev = saddleElev
		self.source = source
		self.extraInfo = "" if extraInfo is None else extraInfo

	def minMaxPb(self):
		if self.peakElev.inMeters and self.saddleElev.inMeters:
			minProm = toFeet(round(self.peakElev.minElev) - round(self.saddleElev.maxElev))
			maxProm = toFeet(round(self.peakElev.maxElev) - round(self.saddleElev.minElev))
			return (minProm, maxProm)

		peakMin, peakMax = self.peakElev.getFeetPb()
		saddleMin, saddleMax = self.saddleElev.getFeetPb()

		return (peakMin - saddleMax, peakMax - saddleMin)

	def avgFeet(self, **kwargs):
		return self.peakElev.avgFeet(**kwargs) - self.saddleElev.avgFeet(**kwargs)

	def avgStr(self):
		return int2str(self.avgFeet())

	def html(self):
		return '<span>{}<div class="tooltip">{} - {} ({}){}</div></span>'.format(
			self.avgStr(),
			self.peakElev,
			self.saddleElev,
			self.source,
			self.extraInfo)

def promElevation(baseElevation, contourInterval, elevation, saddle=False):
	if baseElevation is None:
		elevation, inMeters = elevStr2Int(elevation)
		return SimpleElevation(elevation, 0, inMeters, saddle)

	baseElevation, inMeters = elevStr2Int(baseElevation)
	contourInterval, contourIntervalInMeters = elevStr2Int(contourInterval)

	if inMeters != contourIntervalInMeters:
		badLine()

	return SimpleElevation(baseElevation, contourInterval, inMeters, saddle)

def getProminence(e1a, c1a, e1, e2a, c2a, e2, source, extraInfo):
	e1 = promElevation(e1a, c1a, e1)
	e2 = promElevation(e2a, c2a, e2, True)

	if source not in ("LoJ", "Pb", "LoJ/Pb"):
		raise FormatError("Prominence source must be LoJ, Pb, or LoJ/Pb")

	return Prominence(e1, e2, source, extraInfo)

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
		prom = str2int(m.group())
		line = line[m.end():]

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
			line = line[m.end():]

			promObj = getProminence(*m.groups())
			if prom != promObj.avgFeet():
				raise FormatError("Tooltip doesn't match prominence")

			if not line.startswith('</div></span>'):
				raise FormatError('Expected </div></span>')
			line = line[13:]

			prominences.append(promObj)
		else:
			prominences.append(prom)

		if not line.startswith('<br>'):
			break

	if not line == '</td>\n':
		badLine()

	return prominences

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

			if peak.baseLayer != ('t1' if peak.nonUS else 't4'):
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
				if line != emptyCell or pl.id not in ('OSP',):
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

			if pl.column12 is not None:
				line = htmlFile.next()
				columnClass, allowEmpty = pl.column12(sectionNumber, peakNumber)
				if line == emptyCell:
					if not allowEmpty:
						badLine()
				else:
					peak.column12 = columnClass.match(line)

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
	column2Format = '<td><a href="https://mappingsupport.com/p/gmap4.php?ll={},{}&z={}&t={}">{}</a>{}{}</td>'
	summitpostFormat = '<td><a href="https://www.summitpost.org/{0}/{1}">SP</a></td>'
	wikipediaFormat = '<td><a href="https://en.wikipedia.org/wiki/{0}">W</a></td>'
	bobBurdFormat = '<td><a href="http://www.snwburd.com/dayhikes/peak/{0}">BB</a></td>'
	listsOfJohnFormat = '<td><a href="https://listsofjohn.com/peak/{0}">LoJ</a></td>'
	peakbaggerFormat = '<td><a href="http://peakbagger.com/peak.aspx?pid={0}">Pb</a></td>'
	weatherFormat = '<td><a href="https://forecast.weather.gov/MapClick.php?lon={0}&lat={1}">WX</a></td>'

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
			if peak.delisted:
				classNames.append('delisted')
			elif peak.suspended:
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

			if peak.landManagement:
				print '<td>{}</td>'.format(peak.landManagementHTML())
			else:
				print emptyCell

			print '<td>{}</td>'.format(peak.elevationHTML())
			print '<td>Class {}</td>'.format(peak.grade)
			print '<td>{}</td>'.format(peak.prominenceHTML())

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

			if pl.column12 is not None:
				if peak.column12 is None:
					print emptyCell
				else:
					print str(peak.column12),

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
	f('\t\t"geometry": {"type": "Point", "coordinates": [')
	f(peak.longitude)
	f(',')
	f(peak.latitude)
	f(']},\n')
	f('\t\t"properties": {\n')

	p = [('id', peak.id), ('name', peak.name)]
	if peak.otherName is not None:
		p.append(('name2', peak.otherName))

	p.append(('prom', peak.prominenceHTML().replace('"', '\\"')))
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
			if not (peak.delisted or peak.suspended):
				if firstPeak:
					firstPeak = False
				else:
					f(',')
				writePeakJSON(f, peak)
	f(']\n')
	f('}\n')

def checkData(pl):
	import sps_create
	sps_create.checkData(pl)

def setProm(pl):
	import sps_create
	sps_create.checkData(pl, setProm=True)
	writeHTML(pl)

def setVR(pl):
	import sps_create
	sps_create.checkData(pl, setVR=True)
	writeHTML(pl)

def create(pl):
	import sps_create
	sps_create.loadData(pl)

def readAllHTML():
	for id in peakListParams:
		if id not in peakLists:
			PeakList(id).readHTML()

def main():
	outputFunction = {
		'check': checkData,
		'create': create,
		'elev': printElevationStats,
		'html': writeHTML,
		'json': writeJSON,
		'land': printLandManagementAreas,
		'setprom': setProm,
		'setvr': setVR,
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
