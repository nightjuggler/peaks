#!/usr/bin/python
import re
import sys
import vertcon

def log(message, *args, **kwargs):
	print >>sys.stderr, message.format(*args, **kwargs)

def err(*args, **kwargs):
	log(*args, **kwargs)
	sys.exit()

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
		'numPeaks': 120,
		'numSections': 14,
	},
	'hps': {
		'geojsonTitle': 'Hundred Peaks Section',
		'numPeaks': 23,
		'numSections': 32,
	},
	'npc': {
		'geojsonTitle': 'Nevada Peaks Club',
		'numPeaks': 53,
		'numSections': 6,
	},
	'ogul': {
		'geojsonTitle': 'Tahoe Ogul Peaks',
		'numPeaks': 63,
		'numSections': 15,
	},
	'ocap': {
		'geojsonTitle': 'Other California Peaks',
		'numPeaks': 7,
		'numSections': 4,
	},
	'odp': {
		'geojsonTitle': 'Other Desert Peaks',
		'numPeaks': 8,
		'numSections': 8,
	},
	'osp': {
		'geojsonTitle': 'Other Sierra Peaks',
		'numPeaks': 40,
		'numSections': 26,
	},
}
def addPeakListSortKey():
	for i, peakListId in enumerate(('dps', 'sps', 'hps', 'ogul', 'gbp', 'npc', 'odp', 'osp', 'ocap')):
		peakListParams[peakListId]['sortkey'] = i
addPeakListSortKey()

def html2ListId(htmlId):
	if htmlId[0] == 'x':
		htmlId = htmlId[1:]
	if htmlId[-1] == 'x':
		htmlId = htmlId[:-1]
	return htmlId.lower()

def listId2Html(listId):
	if listId[0] in '0123456789':
		listId = 'x' + listId
	if listId[-1] in '0123456789':
		listId += 'x'
	return listId

class PeakList(object):
	def __init__(self, lowerCaseId):
		self.__dict__.update(peakListParams[lowerCaseId])

		self.id = lowerCaseId.upper()
		self.htmlId = listId2Html(self.id)
		self.htmlFilename = lowerCaseId + '.html'
		self.column12 = globals().get('column12_' + self.id)
		self.numColumns = 13 if self.column12 is None else 14
		self.sections = []
		self.country = ['US']
		self.state = ['CA']
		self.flags = set()

		peakLists[lowerCaseId] = self

	def readHTML(self):
		try:
			readHTML(self)
		except FormatError as e:
			err("[{}:{}] {}!", self.htmlFilename, self.htmlFile.lineNumber, e.message)

class Section(object):
	def __init__(self, peakList, name):
		self.name = name
		self.peaks = []
		self.id2Peak = None
		self.peakList = peakList
		self.country = peakList.country
		self.state = peakList.state
		self.flags = peakList.flags

	def setDataAttributes(self):
		countryCount = {}
		stateCount = {}

		def incr(attr, count):
			attr = "/".join(attr)
			count[attr] = count.get(attr, 0) + 1

		def setmax(attr, count):
			tally, attrValue = max([(v, k) for k, v in count.iteritems()])
			if tally > 1 or len(count) == 1:
				attrValue = attrValue.split("/")
				if getattr(self, attr) != attrValue:
					setattr(self, attr, attrValue)

		for peak in self.peaks:
			incr(peak.country, countryCount)
			incr(peak.state, stateCount)

		setmax("country", countryCount)
		setmax("state", stateCount)

class Peak(object):
	def __init__(self, section):
		self.id = ''
		self.name = ''
		self.otherName = None
		self.peakList = section.peakList
		self.latitude = ''
		self.longitude = ''
		self.zoom = '16'
		self.baseLayer = 't4'
		self.elevations = []
		self.prominences = []
		self.grade = None
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
		self.dataAlso = []
		self.dataAlsoPeaks = []
		self.country = section.country
		self.countryUS = 'US' in self.country
		self.state = section.state
		self.flags = section.flags
		self.hasHtmlId = False
		self.isClimbed = False
		self.isEmblem = False
		self.isMtneer = False
		self.isHighPoint = False
		self.landClass = None
		self.landManagement = None
		self.delisted = False
		self.suspended = False

	def fromId(self):
		from_id = self.peakList.htmlId + self.id
		if self.delisted:
			from_id += 'd'
		elif self.suspended:
			from_id += 's'
		return from_id

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
		doNotCopy = {'id', 'peakList', 'column12', 'dataFrom', 'dataAlso',
			'hasHtmlId', 'isEmblem', 'isMtneer', 'delisted', 'suspended'}

		if other.dataFrom is not None:
			err("{} should not have the data-from attribute!", self.dataFrom)

		for p in other.dataAlsoPeaks:
			if p.peakList is self.peakList:
				err('{} {} ({}) and {} ({}) should not both have data-from="{}"!',
					p.peakList.id, p.id, p.name, self.id, self.name, self.dataFrom)

		for k, v in vars(other).iteritems():
			if not (k[0] == '_' or k in doNotCopy):
				setattr(self, k, v)

		if other.column12 is not None:
			self.column12 = other.column12

		fromId = other.fromId()

		if self.dataFrom != fromId:
			log('{} {} ({}) should have data-from="{}" instead of "{}"',
				self.peakList.id, self.id, self.name, fromId, self.dataFrom)

		self.dataFromPeak = other
		other.dataAlsoPeaks.append(self)

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
	name2link = {
	}
	def __init__(self, name, link):
		self.count = 0
		self.name = name
		self.landClass = self.getLandClass(name)
		self.setLink(link)
		self.highPoint = None
		self.highestPoint = None

	def err(self, message):
		raise FormatError("{} for {}", message, self.name)

	def isHighPoint(self, peak):
		if peak.dataFrom is not None:
			peak = peak.dataFromPeak

		return self.highPoint is peak

	def html(self, peak):
		highPoint = " HP" if self.isHighPoint(peak) else ""

		if self.link is None:
			return self.name + highPoint

		return '<a href="{}">{}</a>{}'.format(self.link, self.name, highPoint)

	def getLandClass(self, name):
		if name.endswith(" Wilderness"):
			return "landWild"

		landClass = landNameLookup.get(name)
		if landClass is not None:
			return landClass

		for suffix, landClass in landNameSuffixes:
			if name.endswith(suffix):
				return landClass

		if name.startswith("BLM "):
			return "landBLM"

		raise FormatError("Unrecognized land management name: {}", name)

	def setLink(self, link):
		self.link = link

		linkPattern = landLinkPattern.get(self.landClass)
		if linkPattern is None:
			return

		if link is None:
			link = self.name2link.get(self.name)
			if link is None:
				log("Add URL for {}", self.name)
			else:
				self.link = link
			return

		if linkPattern.match(link) is None:
			self.err("URL doesn't match expected pattern")

	@classmethod
	def add(self, peak, name, link, isHighPoint):
		area = self.name2area.get(name)
		if area is None:
			self.name2area[name] = area = self(name, link)

		if peak.dataFrom is not None:
			return area

		area.count += 1
		if link is not None and link != area.link:
			if area.link is not None:
				area.err("URL doesn't match previous URL")
			area.setLink(link)
		if isHighPoint:
			if area.highPoint is not None:
				area.err("Duplicate high point")
			area.highPoint = peak

		return area

landNameLookup = {
	"Carrizo Plain National Monument":      'landBLM',
	"Giant Sequoia National Monument":      'Sequoia National Forest',
	"Gold Butte National Monument":         'landBLM',
	"Hart Mountain NAR":                    'landFWS',
	"Harvey Monroe Hall RNA":               'Hoover Wilderness',
	"Hawthorne Army Depot":                 'landDOD',
	"Indian Peak WMA":                      'landUDWR',
	"Lake Mead NRA":                        'landNPS',
	"Lake Tahoe Basin Management Unit":     'landFS',
	"Mono Basin Scenic Area":               'Inyo National Forest',
	"Navajo Nation":                        'landRez',
	"NAWS China Lake":                      'landDOD',
	"Organ Pipe Cactus NM":                 'landNPS',
	"Providence Mountains SRA":             'landSP',
	"Pyramid Lake Indian Reservation":      'landRez',
	"Spring Mountains NRA":                 'Humboldt-Toiyabe National Forest',
	"Steens Mountain CMPA":                 'landBLM',
	"Tohono O'odham Indian Reservation":    'landRez',
}
landNameSuffixes = [
	(' National Forest',            'landFS'),
	(' National Park',              'landNPS'),
	(' National Preserve',          'landNPS'),
	(' National Wildlife Refuge',   'landFWS'),
	(' State Park',                 'landSP'),
	(' NCA',                        'landBLM'),
	(' WSA',                        'landBLM'),
]
landMgmtPattern = re.compile('^(?:<a href="([^"]+)">([- A-Za-z]+)</a>( HP)?)|([- \'A-Za-z]+)')
landLinkPattern = {
	'landWild':     re.compile('^https://www\\.wilderness\\.net/NWPS/wildView\\?WID=[0-9]+$'),
	'landFS':       re.compile('^https://www\\.fs\\.usda\\.gov/[-a-z]+$'),
	'landFWS':      re.compile('^https://www\\.fws\\.gov/refuge/[_a-z]+/$'),
	'landNPS':      re.compile('^https://www\\.nps\\.gov/[a-z]{4}/index\\.htm$'),
	'landSP':       re.compile('^https://www\\.parks\\.ca\\.gov/\\?page_id=[0-9]+$'),
}
landOrder = {
	'landDOD':      0,
	'landRez':      1,
	'landFWS':      2,
	'landBLM':      3,
	'landFS':       4,
	'landBLMW':     5,
	'landFSW':      6,
	'landSP':       7, # California Department of Parks and Recreation - https://www.parks.ca.gov/
	'landUDWR':     7, # Utah Division of Wildlife Resources - https://wildlife.utah.gov/
	'landNPS':      8,
}

def getLandClass(landList):
	landClass = None

	for i, area in enumerate(landList):
		currentClass = area.landClass

		if currentClass == "landWild":
			if landClass == "landFS":
				landClass = "landFSW"
			elif landClass is None or landClass == "landBLM":
				landClass = "landBLMW"

		elif currentClass.startswith("land"):
			if landClass is None:
				landClass = currentClass
			elif landOrder[landClass] < landOrder[currentClass]:
				raise FormatError("Unexpected order of land management areas")

		elif i == 0 or currentClass != landList[i-1].name:
			raise FormatError('"{}" must follow "{}"', area.name, currentClass)

	return landClass

def parseLandManagement(htmlFile, peak):
	line = htmlFile.next()

	if line[:4] != '<td>' or line[-6:] != '</td>\n':
		badLine()
	line = line[4:-6]

	if not peak.countryUS:
		if line == '&nbsp;':
			return
		badLine()

	peak.landManagement = landList = []

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

		landList.append(LandMgmtArea.add(peak, landName, landLink, landHP is not None))

		if line == '':
			break
		if line[:4] != '<br>':
			badLine()
		line = line[4:]

	if peak.landClass != getLandClass(landList):
		raise FormatError("Land management column doesn't match class")

def printLandManagementAreas(pl):
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
		'&quot;((?:(?:Mc)?[A-Z][a-z]+(?: [A-Z][a-z]+)*(?: 2)?(?: VABM)?(?: [1-9][0-9]{3})?)'
		'|[1-9][0-9]{3,4})&quot; \\(([A-Z]{2}[0-9]{4})\\)$')

	def __init__(self, name, stationID):
		self.id = stationID
		self.name = name
		self.vdatum = 'NAVD 88'
		self.linkSuffix = stationID
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
		'([0-9]{6})_[0-9]{4}_(?:[012456]{5,6})\\.jpg$')
	tooltipPattern = re.compile(
		'^((?:[0-9]{3,4}(?:(?:\\.[0-9])|(?:-[0-9]{3,4}))?m)|(?:[0-9]{4,5}(?:-[0-9]{4,5})?\'))'
		'(?: \\((MSL|NGVD 29)\\))? USGS ([\\.013567x]+)\' Quad \\(1:([012456]{2,3},[05]00)\\) '
		'&quot;([\\. A-Za-z]+), ([A-Z]{2})&quot; \\(([0-9]{4}(?:/[0-9]{4})?)\\)$')

	# Special cases for maps whose JPG filename prefix doesn't match the directory name
	jpgState = {
		'283359': 'OR', # 1954/1984 60' (1:250,000) Vya, NV -- directory is NV, but prefix is OR
		'320710': 'NV', # 1962/1969 15' (1:62,500) Benton, CA -- directory is CA, but prefix is NV
	}

	class QuadInfo(object):
		def __init__(self, scale, vdatum):
			self.scale = scale
			self.vdatum = vdatum

	quadInfo = {
		'7.5':          QuadInfo( '24,000', ('MSL', 'NGVD 29')),
		'7.5x15':       QuadInfo( '25,000', ('NGVD 29',)),
		'15':           QuadInfo( '62,500', ('MSL', 'NGVD 29')),
		'30':           QuadInfo('125,000', ('MSL',)),
		'60':           QuadInfo('250,000', ('MSL', 'NGVD 29', None)),
	}

	def __init__(self, vdatum, series, scale, name, state, year):
		info = self.quadInfo.get(series)

		if info is None:
			raise FormatError("Unexpected quad series")
		if scale != info.scale:
			raise FormatError("Scale doesn't match {}' quad", series)
		if vdatum not in info.vdatum:
			if vdatum is None:
				raise FormatError("Missing vertical datum for {}' quad", series)
			raise FormatError("Unexpected vertical datum ({}) for {}' quad", vdatum, series)

		self.vdatum = vdatum
		self.series = series
		self.scale = scale
		self.name = name
		self.state = state
		self.year = year

		self.linkSuffix = None
		self.contourInterval = None

	def setLinkSuffix(self, linkSuffix):
		m = self.linkPattern.match(linkSuffix)
		if m is None:
			raise FormatError("Elevation link suffix doesn't match expected pattern")
		self.id = m.group(1)

		self.linkSuffix = "{0}/{1}_{2}_{3}_{4}_{5}{6}.jpg".format(
			self.state,
			self.jpgState.get(self.id, self.state),
			self.name.replace('.', '').replace(' ', '%20'),
			self.id,
			self.year[:4],
			self.scale[:-4],
			self.scale[-3:])

	def __str__(self):
		return "USGS {}' Quad (1:{}) &quot;{}, {}&quot; ({})".format(
			self.series, self.scale, self.name, self.state, self.year)

	def setUnits(self, inMeters):
		if inMeters and self.series not in ('7.5', '7.5x15'):
			raise FormatError("Unexpected elevation in meters on {}' quad", self.series)
		self.inMeters = inMeters

	def setContourInterval(self, interval):
		if self.series not in ('7.5', '15'):
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
			if self.source.series in ('7.5', '7.5x15'):
				contourIntervals = (10, 20) if inMeters else (20, 40)
			else:
				contourIntervals = (80,)
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

def parseElevation(htmlFile, peak):
	line = htmlFile.next()

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
				for line in htmlFile:
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
	numAllSourced = 0
	numSomeSourced = 0
	for section in pl.sections:
		for peak in section.peaks:
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

	for stationID, src in sorted(NGSDataSheet.sources.iteritems()):
		peak = src.peak
		print stationID, "({})".format(src.name), peak.name,
		if peak.isHighPoint:
			print "HP",
		if peak.otherName is not None:
			print "({})".format(peak.otherName),
		print

	print '\n====== {} USGS Topo Maps\n'.format(len(USGSTopo.sources))

	for topoID, src in sorted(USGSTopo.sources.iteritems()):
		numRefs = len(src.peaks)
		numPeaks = len(set(src.peaks))

		print '{}  {:>3}  {:>7}  {} {:20} {:9}  {}/{}{}'.format(topoID,
			src.series, src.scale, src.state, src.name, src.year,
			numPeaks, numRefs, '' if numRefs == numPeaks else ' *')

RE_Escape = re.compile('[\\' + '\\'.join('$()*+.?[]^') + ']')

def toRegExp(spec, *args):
	return re.compile('^' + RE_Escape.sub('\\\\\\g<0>', spec[:-1]).format(*args) + '$')

class SimpleColumn(object):
	def __init__(self, urlPart):
		self.id = urlPart

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

def column12_HPS(peak):
	return ColumnHPS, False

def column12_OGUL(peak):
	return ColumnPY, peak.id == "4.2"

def column12_OSP(peak):
	sectionNumber = peak.idTuple[0]
	if sectionNumber == 1:
		return ColumnHPS, True
	if sectionNumber >= 23:
		return ColumnPY, True
	return ColumnVR, True

def column12_SPS(peak):
	sectionNumber = peak.idTuple[0]
	if sectionNumber == 1:
		return ColumnHPS, True
	if sectionNumber >= 23:
		return ColumnPY, False
	return ColumnVR, True

def checkPeakNumber(peak):
	maxSubPeak = 2

	sectionNumber, peakNumber = peak.id.split(".")
	sectionNumber = int(sectionNumber)

	if sectionNumber != len(peak.peakList.sections):
		raise FormatError("Peak ID doesn't match section number")

	subPeakNumber = ord(peakNumber[-1]) - ord("a") + 1
	if subPeakNumber <= 0:
		subPeakNumber = 0
		peakNumber = int(peakNumber)
	else:
		peakNumber = int(peakNumber[:-1])

	section = peak.peakList.sections[-1]

	if section.peaks:
		prevPeakNum, prevSubPeak = section.peaks[-1].idTuple[1:]
		if prevSubPeak in (0, maxSubPeak):
			expected = ((prevPeakNum + 1, 0), (prevPeakNum + 1, 1))
		elif prevSubPeak == 1:
			expected = ((prevPeakNum, 2),)
		else:
			expected = ((prevPeakNum + 1, 0), (prevPeakNum + 1, 1), (prevPeakNum, prevSubPeak + 1))
	else:
		expected = ((1, 0), (1, 1))

	if (peakNumber, subPeakNumber) not in expected:
		raise FormatError("Invalid peak number (expected {})", " or ".join(
			[str(n1) + chr(ord("a") + n2 - 1) if n2 else str(n1) for n1, n2 in expected]))

	peak.idTuple = (sectionNumber, peakNumber, subPeakNumber)

def addSection(pl, m):
	expectedNumber = len(pl.sections) + 1
	dataAttributes, htmlListId, sectionNumber, colspan, sectionName = m.groups()

	if int(sectionNumber) != expectedNumber:
		raise FormatError("Expected section number {}", expectedNumber)
	if htmlListId != pl.htmlId:
		raise FormatError('Expected id="{}{}" for section row', pl.htmlId, expectedNumber)
	if int(colspan) != pl.numColumns:
		raise FormatError('Expected colspan="{}" for section row', pl.numColumns)

	section = Section(pl, sectionName)
	pl.sections.append(section)
	parseDataAttributes(section, dataAttributes)
	return section

class RE(object):
	number = '[1-9][0-9]*'
	peakId = number + '\\.' + number + '[ab]?'
	listId = '(?:[A-Z]|x[0-9])[0-9A-Z]*(?:[A-Z]|[0-9]x)'
	fromId = listId + peakId + '[ds]?'

	dataValue = '[- ,\\./0-9A-Za-z]+'
	dataAttribute = re.compile('^ data-([a-z]+)="(' + dataValue + ')"')
	dataAttributes = '((?: data-[a-z]+="' + dataValue + '")*)'

	dataCountry = re.compile('^[A-Z]{2}(?:/[A-Z]{2})*$')
	dataState = re.compile('^[A-Z]{2}(?:-[A-Z]{2,3})?(?:/[A-Z]{2}(?:-[A-Z]{2,3})?)*$')
	dataFlags = re.compile('^[A-Z]+(?:,[A-Z]+)*$')
	dataFrom = re.compile('(' + listId + ')(' + number + ')\\.(' + number + '[ab]?)[ds]?')
	dataAlso = re.compile(fromId + '(?: ' + fromId + ')*')

	firstRow = re.compile(
		'^<tr class="section"' + dataAttributes + '><td id="header" colspan="1[0-9]">'
	)
	sectionRow = re.compile(
		'^<tr class="section"' + dataAttributes + '>'
		'<td id="(' + listId + ')(' + number + ')" colspan="(1[0-9])">'
		'\\3\\. ([- &,;0-9A-Za-z]+)</td></tr>$'
	)
	peakRow = re.compile(
		'^<tr(?: class="([A-Za-z]+(?: [A-Za-z]+)*)")?' + dataAttributes + '>$'
	)
	column1 = re.compile(
		'^<td(?: id="(' + listId + ')(' + peakId + ')")?( rowspan="2")?>(' + peakId + ')</td>$'
	)
	column2 = re.compile(
		'^<td><a href="https://mappingsupport\\.com/p/gmap4\\.php\\?'
		'll=([0-9]{1,2}\\.[0-9]{1,6}),(-[0-9]{1,3}\\.[0-9]{1,6})&z=(1[0-9])&t=(t[14])">'
		'([ #&\'()\\.0-9;A-Za-z]+)</a>( \\*{1,2}| HP)?(?:<br>\\(([ A-Za-z]+)\\))?</td>$'
	)
	grade = re.compile(
		'^<td>Class ([123456](?:s[23456])?\\+?)</td>$'
	)
	numLT1k = re.compile('^[1-9][0-9]{0,2}$')
	numGE1k = re.compile('^[1-9][0-9]?,[0-9]{3}$')
	numMeters = re.compile('^[1-9][0-9]{0,3}(?:\\.[0-9])?$')
	prominence = re.compile('^[,0-9]+')
	prominenceTooltip = re.compile(
		'^(?:\\(([,0-9]+m?) \\+ ([124]0m?)/2\\)|([,0-9]+(?:(?:\\.[0-9])?m)?))'
		' - (?:\\(([,0-9]+m?) - ([124]0m?)/2\\)|([,0-9]+(?:(?:\\.[0-9])?m)?))'
		'(?: \\(([A-Z][A-Za-z]+(?:/[A-Z][A-Za-z]+)*)\\))?(<br>Line Parent: '
		'[A-Z][a-z]+(?: [A-Z][a-z]+)*(?: \\([A-Z][a-z]+(?: [A-Z][a-z]+)*\\))? \\([,0-9]+\\))?$'
	)
	summitpost = re.compile(
		'^<td><a href="https://www\\.summitpost\\.org/([-0-9a-z]+)/([0-9]+)">SP</a></td>$'
	)
	wikipedia = re.compile(
		'^<td><a href="https://en\\.wikipedia\\.org/wiki/([_,()%0-9A-Za-z]+)">W</a></td>$'
	)
	bobBurd = re.compile(
		'^<td><a href="https://www\\.snwburd\\.com/dayhikes/peak/([0-9]+)">BB</a></td>$'
	)
	listsOfJohn = re.compile(
		'^<td><a href="https://listsofjohn\\.com/peak/([0-9]+)">LoJ</a></td>$'
	)
	peakbagger = re.compile(
		'^<td><a href="http://peakbagger\\.com/peak.aspx\\?pid=(-?[1-9][0-9]*)">Pb</a></td>$'
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
		return '<span>{}<div class="tooltip">{} - {}{}{}</div></span>'.format(
			self.avgStr(),
			self.peakElev,
			self.saddleElev,
			"" if self.source is None else " ({})".format(self.source),
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

	if source not in ("LoJ", "Pb", "LoJ/Pb", None):
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

def parseDataCountry(row, value):
	m = RE.dataCountry.match(value)
	if m is None:
		raise FormatError("Invalid data-country attribute")
	row.country = value.split("/")
	if isinstance(row, Peak):
		row.countryUS = "US" in row.country

def parseDataState(row, value):
	m = RE.dataState.match(value)
	if m is None:
		raise FormatError("Invalid data-state attribute")
	row.state = value.split("/")

def parseDataEnable(row, value):
	m = RE.dataFlags.match(value)
	if m is None:
		raise FormatError("Invalid data-enable attribute")
	newFlags = row.flags.union(value.split(","))
	if newFlags != row.flags:
		row.flags = newFlags

def parseDataDisable(row, value):
	m = RE.dataFlags.match(value)
	if m is None:
		raise FormatError("Invalid data-disable attribute")
	newFlags = row.flags.difference(value.split(","))
	if newFlags != row.flags:
		row.flags = newFlags

def parseDataFrom(peak, fromValue):
	if not isinstance(peak, Peak):
		raise FormatError("Unexpected data-from attribute")
	m = RE.dataFrom.match(fromValue)
	if m is None:
		raise FormatError("Invalid data-from attribute")
	peak.dataFrom = fromValue
	peak.dataFromInfo = (html2ListId(m.group(1)), int(m.group(2)), m.group(3))

def parseDataAlso(peak, alsoValue):
	if not isinstance(peak, Peak):
		raise FormatError("Unexpected data-also attribute")
	m = RE.dataAlso.match(alsoValue)
	if m is None:
		raise FormatError("Invalid data-also attribute")
	peak.dataAlso = alsoValue.split(" ")

parseDataMap = {
	'country':      parseDataCountry,
	'state':        parseDataState,
	'enable':       parseDataEnable,
	'disable':      parseDataDisable,
	'from':         parseDataFrom,
	'also':         parseDataAlso,
}
def parseDataAttributes(row, data):
	if data is None:
		return

	seen = set()
	while data != "":
		m = RE.dataAttribute.match(data)
		if m is None:
			badLine()
		name, value = m.groups()
		data = data[m.end():]
		parseFunction = parseDataMap.get(name)
		if parseFunction is None:
			raise FormatError("Unrecognized data-{} attribute", name)
		if name in seen:
			raise FormatError("Duplicate data-{} attribute", name)
		seen.add(name)
		parseFunction(row, value)

def getCommonDataAttributes(row, parent):
	attr = ""

	if row.country != parent.country:
		attr += ' data-country="{}"'.format("/".join(row.country))
	if row.state != parent.state:
		attr += ' data-state="{}"'.format("/".join(row.state))

	dataEnable = []
	dataDisable = []

	for flag in ("CC",):
		if flag in row.flags:
			if flag not in parent.flags:
				dataEnable.append(flag)
		elif flag in parent.flags:
			dataDisable.append(flag)

	if dataEnable:
		attr += ' data-enable="{}"'.format(",".join(dataEnable))
	if dataDisable:
		attr += ' data-disable="{}"'.format(",".join(dataDisable))

	return attr

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
	else:
		raise FormatError("Cannot find start of peak table")

	line = htmlFile.next()
	m = RE.firstRow.match(line)
	if m is None:
		raise FormatError("First row of peak table doesn't match expected pattern")
	parseDataAttributes(pl, m.group(1))

	for line in htmlFile:
		m = RE.sectionRow.match(line)
		if m is not None:
			section = addSection(pl, m)
			break
	else:
		raise FormatError("Cannot find first section row")

	for line in htmlFile:
		m = RE.peakRow.match(line)
		if m is not None:
			peak = Peak(section)
			if not parseClasses(peak, m.group(1)):
				raise FormatError("Bad class names")
			parseDataAttributes(peak, m.group(2))
			if peak.dataFrom is not None:
				dataFromList.append(peak)

			line = htmlFile.next()
			m = RE.column1.match(line)
			if m is None:
				badLine()
			htmlListId, htmlPeakId, extraRow, peak.id = m.groups()
			if extraRow is not None:
				peak.extraRow = ''
			if htmlPeakId is not None:
				if pl.htmlId != htmlListId or peak.id != htmlPeakId:
					raise FormatError("HTML ID doesn't match peak ID and/or peak list ID")
				peak.hasHtmlId = True

			checkPeakNumber(peak)

			line = htmlFile.next()
			m = RE.column2.match(line)
			if m is None:
				badLine()
			(peak.latitude, peak.longitude,
				peak.zoom, peak.baseLayer,
				peak.name, suffix, peak.otherName) = m.groups()

			if peak.baseLayer != ('t4' if peak.countryUS else 't1'):
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

			parseLandManagement(htmlFile, peak)
			parseElevation(htmlFile, peak)

			line = htmlFile.next()
			m = RE.grade.match(line)
			if m is None:
				if line != emptyCell or (pl.id, peak.id) not in (('GBP', '9.10'),):
					badLine()
			else:
				peak.grade = m.group(1)
				if len(peak.grade) > 2:
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
				if line != emptyCell or pl.id not in ('OSP',) and peak.countryUS:
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
				columnClass, allowEmpty = pl.column12(peak)
				if line == emptyCell:
					if not allowEmpty:
						badLine()
				else:
					peak.column12 = columnClass.match(line)

			line = htmlFile.next()
			m = RE.weather.match(line)
			if m is None:
				if line != emptyCell or peak.countryUS:
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

			section.peaks.append(peak)
		else:
			m = RE.sectionRow.match(line)
			if m is not None:
				section = addSection(pl, m)
			elif line == '</table>\n':
				break
			else:
				badLine()
	htmlFile.close()
	if sum([len(section.peaks) for section in pl.sections]) != pl.numPeaks:
		raise FormatError("Number of peaks is not {}", pl.numPeaks)
	if len(pl.sections) != pl.numSections:
		raise FormatError("Number of sections is not {}", pl.numSections)

	for peak in dataFromList:
		pl2Id, sectionNumber, peakNumber = peak.dataFromInfo
		pl2 = peakLists.get(pl2Id)
		if pl2 is None:
			pl2 = PeakList(pl2Id)
			pl2.readHTML()
		section = pl2.sections[sectionNumber - 1]
		if section.id2Peak is None:
			section.id2Peak = {p.id[p.id.find(".")+1:]: p for p in section.peaks}
		peak.copyFrom(section.id2Peak[peakNumber])

def writeHTML(pl):
	sectionFormat = '<tr class="section"{4}><td id="{0}{1}" colspan="{2}">{1}. {3}</td></tr>'
	column2Format = '<td><a href="https://mappingsupport.com/p/gmap4.php?ll={},{}&z={}&t={}">{}</a>{}{}</td>'
	summitpostFormat = '<td><a href="https://www.summitpost.org/{0}/{1}">SP</a></td>'
	wikipediaFormat = '<td><a href="https://en.wikipedia.org/wiki/{0}">W</a></td>'
	bobBurdFormat = '<td><a href="https://www.snwburd.com/dayhikes/peak/{0}">BB</a></td>'
	listsOfJohnFormat = '<td><a href="https://listsofjohn.com/peak/{0}">LoJ</a></td>'
	peakbaggerFormat = '<td><a href="http://peakbagger.com/peak.aspx?pid={0}">Pb</a></td>'
	weatherFormat = '<td><a href="https://forecast.weather.gov/MapClick.php?lon={0}&lat={1}">WX</a></td>'

	emptyCell = '<td>&nbsp;</td>'
	extraRowFirstLine = '<tr><td colspan="{}"><ul>'.format(pl.numColumns - 1)
	extraRowLastLine = '</ul></td></tr>'

	htmlFile = open(pl.htmlFilename)
	for line in htmlFile:
		print line,
		if line == tableLine:
			break
	for line in htmlFile:
		m = RE.sectionRow.match(line)
		if m is not None:
			break
		print line,

	for sectionNumber, section in enumerate(pl.sections, start=1):
		print sectionFormat.format(pl.htmlId, sectionNumber, pl.numColumns, section.name,
			getCommonDataAttributes(section, pl))

		for peak in section.peaks:
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
				peak.dataAlsoPeaks.remove(peak)
			if peak.dataAlsoPeaks:
				peak.dataAlsoPeaks.sort(key=lambda p: p.peakList.sortkey)
				attr += ' data-also="{}"'.format(" ".join([p.fromId() for p in peak.dataAlsoPeaks]))
			print '<tr{}{}>'.format(attr, getCommonDataAttributes(peak, section))

			attr = ''
			if peak.hasHtmlId:
				attr += ' id="{}{}"'.format(pl.htmlId, peak.id)
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

			if peak.grade is None:
				print emptyCell
			else:
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

			if peak.countryUS:
				print weatherFormat.format(peak.longitude, peak.latitude)
			else:
				print emptyCell

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
	if peak.grade is not None:
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
	if not peak.countryUS:
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
	for section in pl.sections:
		for peak in section.peaks:
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

def loadFiles(pl):
	import sps_create
	sps_create.loadFiles(pl)

def setLandManagement(peak):
	peakPb = peak.peakbaggerPeak

	if peakPb.landManagement:
		peak.landManagement = [LandMgmtArea.add(peak, area.name, None, peakPb is area.highPoint)
			for area in peakPb.landManagement]
	else:
		peak.landManagement = [LandMgmtArea.add(peak, "BLM " + peakPb.state, None, False)]

	peak.landClass = getLandClass(peak.landManagement)

def createList(pl):
	import sps_create

	try:
		sps_create.createList(pl, peakLists, Peak, Section, setLandManagement)
	except FormatError as e:
		sys.exit(e.message)

	writeHTML(pl)

def readAllHTML():
	for plId in peakListParams:
		if plId not in peakLists:
			PeakList(plId).readHTML()

def main():
	outputFunction = {
		'check': checkData,
		'create': createList,
		'elev': printElevationStats,
		'html': writeHTML,
		'json': writeJSON,
		'land': printLandManagementAreas,
		'load': loadFiles,
		'setprom': setProm,
		'setvr': setVR,
	}
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('inputMode', nargs='?', default='sps', choices=sorted(peakListParams.keys()))
	parser.add_argument('outputMode', nargs='?', default='html', choices=sorted(outputFunction.keys()))
	args = parser.parse_args()

	readAllHTML()
	outputFunction[args.outputMode](peakLists[args.inputMode])

if __name__ == '__main__':
	main()
