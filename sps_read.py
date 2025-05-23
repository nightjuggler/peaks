import re
import sys
import vertcon

def log(message, *args, **kwargs):
	print(message.format(*args, **kwargs), file=sys.stderr)

def err(*args, **kwargs):
	log(*args, **kwargs)
	sys.exit()

class FormatError(Exception):
	def __init__(self, message, *formatArgs):
		self.message = message.format(*formatArgs)

class InputFile(object):
	def __init__(self, fileName):
		self.lineNumber = 0
		self.fileObject = open(fileName)

	def close(self):
		self.fileObject.close()

	def __iter__(self):
		return self

	def __next__(self):
		line = self.fileObject.__next__()
		self.lineNumber += 1
		return line

	next = __next__

def int2str(n):
	return str(n) if n < 1000 else '{},{:03}'.format(*divmod(n, 1000))

peakLists = {}
peakListsOrdered = [
	('dps', 'Desert Peaks Section', 99, 9),
	('sps', 'Sierra Peaks Section', 248, 24),
	('hps', 'Hundred Peaks Section', 67, 32),
	('ogul','Tahoe Ogul Peaks', 63, 15),
	('lpc', 'Lower Peaks Committee', 48, 16),
	('gbp', 'Great Basin Peaks', 120, 14),
	('npc', 'Nevada Peaks Club', 76, 6),
	('odp', 'Other Desert Peaks', 10, 6),
	('osp', 'Other Sierra Peaks', 97, 27),
	('ocap','Other California Peaks', 112, 17),
	('owp', 'Other Western Peaks', 21, 10),
]

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
	def __init__(self, lowerCaseId, name, numPeaks, numSections):
		self.id = lowerCaseId.upper()
		self.name = name
		self.numPeaks = numPeaks
		self.numSections = numSections
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

def initPeakLists():
	for i, params in enumerate(peakListsOrdered):
		pl = PeakList(*params)
		pl.sortkey = i
		peakListsOrdered[i] = pl

def allPeaksGenerator():
	for pl in peakListsOrdered:
		for section in pl.sections:
			for peak in section.peaks:
				if peak.dataFrom is None:
					yield peak

def readAllHTML():
	for pl in peakListsOrdered:
		pl.readHTML()

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
			tally, attrValue = max([(v, k) for k, v in count.items()])
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
		self.quad = None
		self.latitude = ''
		self.longitude = ''
		self.zoom = '16'
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
		self.landClass = None
		self.landManagement = []
		self.delisted = False
		self.suspended = False

	def idSuffix(self):
		if self.delisted:
			return 'd'
		if self.suspended:
			return 's'
		return ''

	def fromId(self):
		return self.peakList.htmlId + self.id + self.idSuffix()

	def jsonId(self):
		if not self.dataAlsoPeaks:
			return '"{}{}"'.format(self.id, self.idSuffix())

		peaks = self.dataAlsoPeaks[:]
		if self.dataFrom is None:
			peaks.insert(0, self)
		else:
			peaks.insert(0, self.dataFromPeak)

		peaks.sort(key=lambda p: p.peakList.sortkey)

		return '[{}]'.format(','.join(['"{}.{}{}"'.format(p.peakList.id, p.id, p.idSuffix())
			for p in peaks]))

	def elevationHTML(self):
		return '<br>'.join([e.html() for e in self.elevations])

	def elevationJSON(self):
		return '[{}]'.format(','.join([e.json() for e in self.elevations]))

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

	def getElevForStats(self):
		e_best = self.elevations[0]
		k_best = e_best.sortkeyForStats()
		for e in self.elevations[1:]:
			k = e.sortkeyForStats()
			if k > k_best:
				e_best = e
				k_best = k

		return e_best.elevationFeet

	def getPromForStats(self):
		return max([prom if isinstance(prom, int)
			else prom.avgFeet() for prom in self.prominences])

	def getDataSheets(self):
		dataSheets = []
		for e in self.elevations:
			if isinstance(e.source, NGSDataSheet):
				dataSheets.append(e.source.id)
			else:
				break
		if not dataSheets and self.elevations[-1].source is None:
			return None
		return dataSheets

	def copyFrom(self, other):
		doNotCopy = {'id', 'peakList', 'column12', 'dataFrom', 'dataAlso',
			'hasHtmlId', 'isEmblem', 'isMtneer', 'delisted', 'suspended'}

		if other.dataFrom is not None:
			err("{} should not have the data-from attribute!", self.dataFrom)

		for p in other.dataAlsoPeaks:
			if p.peakList is self.peakList:
				err('{} {} ({}) and {} ({}) should not both have data-from="{}"!',
					p.peakList.id, p.id, p.name, self.id, self.name, self.dataFrom)

		for k, v in vars(other).items():
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
		self.name = name
		self.peaks = set()
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
		landClass = landNameLookup.get(name)
		if landClass is not None:
			return landClass

		for suffix, landClass in landNameSuffixes:
			if name.endswith(suffix):
				return landClass

		if name.startswith("BLM "):
			return "landBLM"
		if name.startswith("City of "):
			return "landCity"

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

		if peak in area.peaks:
			raise FormatError("Duplicate land management area: {}", name)
		area.peaks.add(peak)

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
	"Agua Tibia Research Natural Area":             'Agua Tibia Wilderness',
	"Antelope Valley California Poppy Reserve":     'landSP',
	"Avi Kwa Ame National Monument":                'landBLM',
	"Basin and Range National Monument":            'landBLM',
	"Berryessa Snow Mountain National Monument":    'landBLM',
	"Bishop Peak Natural Reserve":                  'City of San Luis Obispo',
	"California Tahoe Conservancy":                 'landCNRA',
	"Cameron Nature Preserve":                      'landMRCA',
	"Carrizo Plain National Monument":              'landBLM',
	"Catalina Island Conservancy":                  'landPrivate',
	"Conejo Canyons Open Space":                    'landCity',
	"Dos Vientos Open Space":                       'landCity', # 'City of Thousand Oaks'
	"Giant Sequoia National Monument":              'Sequoia National Forest',
	"Griffith Park":                                'City of Los Angeles',
	"Gold Butte National Monument":                 'landBLM',
	"Golden Gate National Recreation Area":         'landNPS',
	"Harry Barbier Memorial Park":                  'City of San Rafael',
	"Hart Mountain NAR":                            'landFWS',
	"Harvey Monroe Hall RNA":                       'Hoover Wilderness',
	"Hawthorne Army Depot":                         'landDOD',
	"Hood Mountain Regional Park":                  'landCounty',
	"Indian Peaks WMA":                             'landUDWR',
	"Kings River SMA":                              'Sierra National Forest',
	"Lake Mead NRA":                                'landNPS',
	"Lake Perris SRA":                              'landSP',
	"Lake Tahoe Basin Management Unit":             'landFS',
	"Lake Tahoe Nevada State Park":                 'landNVSP',
	"Lava Beds National Monument":                  'landNPS',
	"Los Coyotes Indian Reservation":               'landRez',
	"Lyon Peak-Needle Lake RNA":                    'Tahoe National Forest',
	"Marin Municipal Water District":               'landCounty',
	"Mono Basin National Forest Scenic Area":       'Inyo National Forest',
	"Moran State Park":                             'landWASP',
	"Mount Davidson Park":                          'landCity',
	"Mount Eddy Research Natural Area":             'Shasta-Trinity National Forest',
	"Mount St. Helens National Volcanic Monument":  'Gifford Pinchot National Forest',
	"Navajo Nation":                                'landRez',
	"NAWS China Lake":                              'landDOD',
	"North Ranch Open Space":                       'landCity',
	"Olompali State Historic Park":                 'landSP',
	"Organ Pipe Cactus NM":                         'landNPS',
	"Pearl Peak RNA":                               'Humboldt-Toiyabe National Forest',
	"Point Reyes National Seashore":                'landNPS',
	"Pole Mountain Preserve":                       'landSLT',
	"Providence Mountains SRA":                     'landSP',
	"Pyramid Lake Indian Reservation":              'landRez',
	"Reservoir Canyon Natural Reserve":             'City of San Luis Obispo',
	"Rocky Peak Park":                              'landMRCA',
	"San Gabriel Mountains NM":                     'landFS',
	"Sand to Snow National Monument":               'landFS',
	"Santa Rosa and San Jacinto Mountains NM":      'landBLM',
	"Santa Monica Mountains NRA":                   'landNPS',
	"Spring Mountains NRA":                         'Humboldt-Toiyabe National Forest',
	"Steens Mountain CMPA":                         'landBLM',
	"Tohono O'odham Nation":                        'landRez',
	"Twin Peaks Natural Area":                      'landCity',
	"Ventu Park Open Space":                        'landCity',
	"Wildwood Park":                                'landCity',
	"Wind Wolves Preserve":                         'landTWC',

	# East Bay Regional Park District
	"Mission Peak Regional Preserve":       'landEBRPD',
	"Ohlone Regional Wilderness":           'landEBRPD',
	"Pleasanton Ridge Regional Park":       'landEBRPD',
	"Sibley Volcanic Regional Preserve":    'landEBRPD',
	"Sunol Regional Wilderness":            'landEBRPD',

	# Marin County Parks
	"Loma Alta Preserve":                   'landCounty',
	"Little Mountain Preserve":             'landCounty',
	"Lucas Valley Preserve":                'landCounty',
	"Mount Burdell Preserve":               'landCounty',
	"Ring Mountain Preserve":               'landCounty',
	"White Hill Preserve":                  'landCounty',

	# Midpeninsula Regional Open Space District
	"Monte Bello Open Space Preserve":              'landMROSD',
	'Purisima Creek Redwoods Open Space Preserve':  'landMROSD',
	"Russian Ridge Open Space Preserve":            'landMROSD',
	"Sierra Azul Open Space Preserve":              'landMROSD',
}
landNameSuffixes = [
	(' Wilderness',                 'landWild'),
	(' National Forest',            'landFS'),
	(' National Park',              'landNPS'),
	(' National Preserve',          'landNPS'),
	(' National Wildlife Refuge',   'landFWS'),
	(' State Park',                 'landSP'),
	(' NCA',                        'landBLM'),
	(' WSA',                        'landBLM'),
	(' County Park',                'landCounty'),
]
landMgmtPattern = re.compile('^(?:<a href="([^"]+)">([- &\'.;A-Za-z]+)</a>( HP)?)|([- \'.A-Za-z]+)')
landLinkPattern = {
	'landWild':     re.compile('^https://wilderness\\.net/visit-wilderness/\\?ID=[0-9]+$'),
	'landEBRPD':    re.compile('^https://www\\.ebparks\\.org/parks/[-a-z]+$'),
	'landFS':       re.compile('^https://www\\.fs\\.usda\\.gov/(?:visit/)?[-a-z]+$'),
	'landFWS':      re.compile('^https://www\\.fws\\.gov/refuge/[_a-z]+/$'),
	'landMROSD':    re.compile('^https://www\\.openspace\\.org/preserves/[-a-z]+$'),
	'landNPS':      re.compile('^https://www\\.nps\\.gov/[a-z]{4}/index\\.htm$'),
	'landSP':       re.compile('^https://www\\.parks\\.ca\\.gov/\\?page_id=[0-9]+$'),
}
landOrder = {landClass: i for i, landClass in enumerate((
	'landPrivate',
	'landMRCA',     # Mountains Recreation and Conservation Authority - https://mrca.ca.gov/
	'landSLT',      # Sonoma Land Trust - https://sonomalandtrust.org/
	'landTWC',      # The Wildlands Conservancy - https://www.wildlandsconservancy.org/
	'landCity',
	'landCounty',
	'landEBRPD',    # East Bay Regional Park District - https://www.ebparks.org/
	'landMROSD',    # Midpeninsula Regional Open Space District - https://www.openspace.org/
	'landDOD',
	'landRez',
	'landNVSP',     # Nevada Division of State Parks
	'landUDWR',     # Utah Division of Wildlife Resources - https://wildlife.utah.gov/
	'landWASP',     # Washington State Parks - https://parks.state.wa.us/
	'landBLM',
	'landCNRA',     # California Natural Resources Agency (other than Department of Parks and Recreation)
	'landSP',       # California Department of Parks and Recreation - https://www.parks.ca.gov/
	'landFS',
	'landFWS',
	'landBLMW',
	'landFSW',
	'landNPS',
))}

def getLandClass(landList):
	landClass = None
	parent = None

	for i, area in enumerate(landList):
		currentClass = area.landClass

		if currentClass == "landWild":
			if landClass == "landFS":
				landClass = "landFSW"
			elif landClass is None or landClass == "landBLM":
				landClass = "landBLMW"
			elif landClass not in ("landBLMW", "landFSW", "landFWS", "landNPS"):
				raise FormatError("Wilderness must be BLM, NPS, USFS, or USFWS")

		elif currentClass.startswith("land"):
			if landClass is None:
				landClass = currentClass
			elif landOrder[landClass] < landOrder[currentClass]:
				raise FormatError("Unexpected order of land management areas")
			parent = area

		elif i == 0 or currentClass != landList[i-1].name and currentClass != parent.name:
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

	if line == '&nbsp;':
		if peak.landClass == 'landPrivate':
			return
		raise FormatError("Empty land management column")

	landList = peak.landManagement

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

class LandMgmtSummary(object):
	def __init__(self, title):
		self.title = title
		self.areas = []
		self.peaks = set()
		self.maxNumPeaks = 0
		self.maxLenAreaName = 0
		self.maxLenPeakName = 0

	def add(self, area):
		self.areas.append(area)
		self.peaks.update(area.peaks)

		nameLen = len(area.name)
		if nameLen > self.maxLenAreaName:
			self.maxLenAreaName = nameLen

		nameLen = len(area.highPoint.name if area.highPoint else '-')
		if nameLen > self.maxLenPeakName:
			self.maxLenPeakName = nameLen

		numPeaks = len(area.peaks)
		if numPeaks > self.maxNumPeaks:
			self.maxNumPeaks = numPeaks

	def printSummary(self):
		len1 = len(str(self.maxNumPeaks))
		len2 = self.maxLenAreaName
		len3 = self.maxLenPeakName

		maxLineLen = 119
		lineFormat = '| {{:{}}} | {{:{}}} | {{:{}}} | {{}}'.format(len1, len2, len3)

		maxLenURL = maxLineLen - len1 - len2 - len3 - 11
		if maxLenURL < 3:
			maxLenURL = 3

		titleBar = '+-{}-+-{}-+-{}-+-{}'.format('-'*len1, '-'*len2, '-'*len3, '-'*maxLenURL)

		print('+{}'.format('-'*(maxLineLen - 1)))
		print('| {} ({} peaks)'.format(self.title, len(self.peaks)))
		print(titleBar)

		for area in self.areas:
			hp = area.highPoint.name if area.highPoint else '-'

			url = area.link if area.link else '-'
			if len(url) > maxLenURL:
				url = url[:url.rfind('/', 0, maxLenURL - 3) + 1] + '...'

			print(lineFormat.format(len(area.peaks), area.name, hp, url))

		print(titleBar)

def printLandManagementAreas():
	summaryLookup = {
		'landBLM':      LandMgmtSummary('BLM'),
		'landEBRPD':    LandMgmtSummary('East Bay Regional Park District'),
		'landFS':       LandMgmtSummary('U.S. Forest Service'),
		'landFWS':      LandMgmtSummary('U.S. Fish & Wildlife Service'),
		'landNPS':      LandMgmtSummary('National Park Service'),
		'landSP':       LandMgmtSummary('California State Parks'),
		'landWild':     LandMgmtSummary('National Wilderness'),
	}
	miscSummary = LandMgmtSummary('Miscellaneous')

	for name, area in sorted(LandMgmtArea.name2area.items()):
		(summaryLookup.get(area.landClass) or miscSummary).add(area)

	for summary in sorted(summaryLookup.values(), key=lambda s: s.title):
		summary.printSummary()
		print()

	miscSummary.printSummary()

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
		'^([1-9][0-9]{2,3}(?:\\.[0-9]{1,2})?m) \\(NAVD 88\\) NGS Data Sheet '
		'&quot;((?:(?:Mc)?[A-Z][a-z]+(?: [A-Z][a-z]*)*'
		'(?: [123])?(?:(?: 1[89][0-9]{2})|(?: VABM [1-9][0-9]{3}))?'
		'(?:(?: Reset)|(?: RM(?: [12345])?))?)'
		'|(?:[1-9][0-9]{2,4}(?: VA)?))&quot; \\(([A-Z]{2}[0-9]{4})\\)$')

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

	def elevJSON(self, elev):
		return '[2,{},"{}","{}"]'.format(elev.elevationMeters, self.id, self.name)

class USGSTopo(object):
	sources = {}
	sourcesJSON = set()
	linkPrefix = 'https://ngmdb.usgs.gov/ht-bin/tv_browse.pl?id='
	linkPattern = re.compile('^[0-9a-f]{32}$')
	namePattern = re.compile('^(?:Mc)?[A-Z][a-z]+\\.?(?: [A-Z][a-z]+\\.?)*(?: (?:[SN][WE]|[A-D]))?$')
	tooltipPattern = re.compile(
		'^((?:[0-9]{3,4}(?:(?:\\.[0-9])|(?:-[0-9]{3,4}))?m)|(?:[0-9]{3,5}(?:-[0-9]{3,5})?\'))'
		'(?: \\((MSL|NGVD 29)\\))? USGS ([\\.013567x]+)\' Quad \\(1:([012456]{2,3},[05]00)\\) '
		'&quot;([\\. A-Za-z]+), ([A-Z]{2})&quot; \\(([0-9]{4}(?:/[0-9]{4})?)\\)$')

	class QuadInfo(object):
		def __init__(self, seriesID, scale, vdatum):
			self.id = seriesID
			self.scale = scale
			self.vdatum = vdatum

	quadInfo = {
		'7.5':          QuadInfo(0,  '24,000', ('MSL', 'NGVD 29')),
		'7.5x15':       QuadInfo(1,  '25,000', ('NGVD 29',)),
		'15':           QuadInfo(2,  '62,500', ('MSL', 'NGVD 29')),
		'30':           QuadInfo(3, '125,000', ('MSL',)),
		'60':           QuadInfo(4, '250,000', ('MSL', 'NGVD 29', None)),
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
		if not self.namePattern.match(name):
			raise FormatError("Topo name doesn't match expected pattern")

		self.vdatum = vdatum
		self.series = series
		self.seriesID = info.id
		self.scale = scale
		self.name = name
		self.state = state
		self.year = year

		self.linkSuffix = None
		self.contourInterval = None

	def setLinkSuffix(self, linkSuffix):
		if not self.linkPattern.match(linkSuffix):
			raise FormatError("Elevation link suffix doesn't match expected pattern")
		self.id = linkSuffix
		self.linkSuffix = linkSuffix

	def __str__(self):
		return "USGS {}' Quad (1:{}) &quot;{}, {}&quot; ({})".format(
			self.series, self.scale, self.name, self.state, self.year)

	def setUnits(self, inMeters):
		if inMeters and self.seriesID > 1:
			raise FormatError("Unexpected elevation in meters on {}' quad", self.series)
		self.inMeters = inMeters

	def setContourInterval(self, interval):
		if self.series not in ('7.5', '15'):
			raise FormatError("Unexpected elevation range on {}' quad", self.series)
		self.contourInterval = interval

	def setPeakQuad(self, peak):
		name = (self.name
				.replace(" Mtn. ", " Mountain ")
				.replace(" Mts. ", " Mountains ")
				.replace(" St. ", " Saint "))
		if name[:4] == "Mt. ":
			name = "Mount " + name[4:]
		elif name[:3] == "Mt ":
			name = "Mount " + name[3:]
		elif name[-5:] == " Mtn.":
			name = name[:-5] + " Mountain"
		elif name[-4:] == " Mtn":
			name = name[:-4] + " Mountain"
		elif name[-5:] == " Res.":
			name = name[:-5] + " Reservoir"

		if peak.quad is None:
			peak.quad = name
		elif peak.quad != name:
			if peak.quad == "San Guillermo Mountain" and name == "San Guillermo":
				return
			raise FormatError("Expected '{}' quad instead of '{}'", peak.quad, self.name)

	def addPeak(self, peak):
		if self.seriesID <= 1:
			self.setPeakQuad(peak)

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

	def elevJSON(self, elev):
		self.sourcesJSON.add(self)

		args = [1, elev.elevationMeters] if self.inMeters else [0, elev.elevationFeet]
		args.append(self.contourInterval if elev.isRange else 0)
		args.append(self.id)

		return '[{}]'.format(','.join(map(str, args)))

	def json(self):
		vdatumID = 2 if self.vdatum is None else 1 if self.vdatum == 'MSL' else 0

		return '"{}":[{},{},"{}, {}","{}","{}"]'.format(self.id, self.seriesID, vdatumID,
			self.name, self.state, self.year, self.linkSuffix)

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
	pattern1 = re.compile('^([1-9](?:[0-9]?,[0-9])?[0-9]{2}\\+?)')
	pattern2 = re.compile(
		'^<span><a href="([^"]+)">' + pattern1.pattern[1:] + '</a>'
		'<div class="tooltip">([- &\'(),\\.:;/0-9A-Za-z]+)(?:(</div></span>)|$)')

	def __init__(self, elevation, latlng):
		self.isRange = elevation[-1] == '+'
		if self.isRange:
			elevation = elevation[:-1]
		self.elevationFeet = int(elevation[:-4] + elevation[-3:])
		self.source = None
		self.latlng = latlng

	def getElevation(self):
		return int2str(self.elevationFeet) + ('+' if self.isRange else '')

	def sortkey(self):
		src = self.source
		if src is None:
			return (2, not self.isRange, self.elevationFeet)
		if isinstance(src, NGSDataSheet):
			return (3, self.elevationFeet, src.id)
		if isinstance(src, USGSTopo):
			return (1, -src.seriesID, not self.isRange, src.year)
		raise FormatError("Elevation source must be None, NGSDataSheet, or USGSTopo")

	def sortkeyForStats(self):
		src = self.source
		if src is None:
			return (3, not self.isRange, self.elevationFeet)
		if isinstance(src, NGSDataSheet):
			return (1, self.elevationFeet, src.id)
		if isinstance(src, USGSTopo):
			return (2, -src.seriesID, not self.isRange, src.year, self.elevationFeet)
		raise FormatError("Elevation source must be None, NGSDataSheet, or USGSTopo")

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

	def json(self):
		if self.source is None:
			return '"{}"'.format(self.getElevation())

		jstr = self.source.elevJSON(self)

		if self.extraLines:
			return '[{},"{}"]'.format(jstr[1:-1],
				self.extraLines.replace('"', '\\"').replace('\n', '\\n'))

		return jstr

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
			if self.source.seriesID == 0:
				contourIntervals = (10, 20) if inMeters else (20, 25, 40, 50)
			else:
				contourIntervals = (80, 50, 40, 25)
			if interval not in contourIntervals or elevationMin % interval != 0:
				raise FormatError("Elevation range in tooltip not valid")
			self.source.setContourInterval(interval)
		if inMeters:
			self.elevationMeters = float(elevation) if '.' in elevation else int(elevation)
			if isinstance(self.source, NGSDataSheet):
				elevation = toSurveyFeet(self.elevationMeters)
			else:
				elevation = toFeet(self.elevationMeters)
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
				return feet == toFeet(self.elevationMeters + self.source.contourInterval // 2, 0)

			return feet == self.elevationFeet + self.source.contourInterval // 2

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

def checkElevationOrder(peak):
	same = None
	e1 = peak.elevations[0]
	k1 = e1.sortkey()
	for e2 in peak.elevations[1:]:
		k2 = e2.sortkey()
		if k2 > k1:
			raise FormatError("Elevations are not in the expected order")
		if k2 == k1:
			if not isinstance(e2.source, USGSTopo):
				raise FormatError("Duplicate elevation")
			if e2.elevationFeet > e1.elevationFeet:
				raise FormatError("Elevations are not in the expected order")
			if same is None:
				same = []
			same.append(e1)
			for e1 in same:
				if e1.extraLines == e2.extraLines:
					raise FormatError("Duplicate topo elevation")
		elif same is not None:
			same = None
		e1 = e2
		k1 = k2

def checkElevationTypes(peak):
	src = peak.elevations[-1].source

	if isinstance(src, NGSDataSheet):
		raise FormatError("Expected at least one elevation not from an NGS Data Sheet")

	if isinstance(src, USGSTopo) and src.seriesID > 1:
		for e in peak.elevations[:-1]:
			src = e.source
			if isinstance(src, USGSTopo) and src.seriesID <= 1:
				break
		else:
			raise FormatError("Expected 7.5' topo")

def parseElevation(htmlFile, peak):
	line = htmlFile.next()

	if line[:4] != '<td>':
		badLine()

	latlng = float(peak.latitude), float(peak.longitude)

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

	checkElevationOrder(peak)
	if peak.countryUS:
		checkElevationTypes(peak)

def printElevationStats():
	print('====== Number of peaks with some/all elevations sourced\n')

	for pl in peakListsOrdered:
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
		print('{:4}: {:3}/{:3}/{:3}'.format(pl.id, numSomeSourced, numAllSourced, pl.numPeaks))

	print('\n====== {} NGS Data Sheets\n'.format(len(NGSDataSheet.sources)))

	for stationID, src in sorted(NGSDataSheet.sources.items()):
		peak = src.peak
		print(stationID, '({})'.format(src.name), peak.name, end='')
		if peak.otherName is not None:
			print(' ({})'.format(peak.otherName), end='')
		print()

	print('\n====== {} USGS Topo Maps\n'.format(len(USGSTopo.sources)))

	sameMap = []
	lastLine = ""

	for src in sorted(USGSTopo.sources.values(), key=lambda topo:
		(topo.seriesID, topo.state, topo.name, topo.year, topo.id)):

		numRefs = len(src.peaks)
		numPeaks = len(set(src.peaks))

		line = "{}  {:>6}  {:>7}  {} {:28} {:9}  {}/{}{}".format(src.id,
			src.series, src.scale, src.state, src.name, src.year,
			numPeaks, numRefs, '' if numRefs == numPeaks else ' *')

		print(line)

		if line[34:92] == lastLine[34:92]:
			if not (sameMap and lastLine is sameMap[-1]):
				sameMap.append(lastLine)
			sameMap.append(line)

		lastLine = line

	print('\n====== Different Scans of the Same Map\n')

	for line in sameMap:
		print(line)

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
	prefix = '<td><a href="https://hundredpeaks.org/guides/'
	suffix = '.htm">HPS</a></td>\n'
	pattern = re.compile('^[0-9]{2}[a-z]$')

class ColumnPY(SimpleColumn):
	prefix = '<td><a href="https://www.petesthousandpeaks.com/Captions/nspg/'
	suffix = '.html">PY</a></td>\n'
	pattern = re.compile('^[a-z]+$')

class ColumnVR(object):
	spec = '<td><a href="https://vulgarianramblers.org/peak_detail.php?peak_name={}">{}</a></td>\n'
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
	dataFlags = re.compile('^[A-Za-z]+(?:,[A-Za-z]+)*$')
	dataFrom = re.compile('(' + listId + ')(' + number + ')\\.(' + number + '[ab]?)[ds]?')
	dataAlso = re.compile(fromId + '(?: ' + fromId + ')*')

	firstRow = re.compile(
		'^<tr id="firstRow" class="section"' + dataAttributes + '><td colspan="1[0-9]">'
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
		'^<td><a href="https://caltopo\\.com/map\\.html#'
		'll=([34][0-9]\\.[0-9]{1,5}),(-1[012][0-9]\\.[0-9]{1,5})&z=(1[0-9])&b=t">'
		'([- #&\'()+.0-9;A-Za-z]+)</a>( \\*{1,2})?'
		'(?:<br>\\(([A-Z][a-z]+(?: [A-Z][a-z]+)*(?: (?:HP|[1-9][0-9]+|VOR))?)\\))?</td>$'
	)
	peakName = (
		re.compile('^(?:Mc)?[A-Z][a-z]+(?:\'s)?(?: (?:Mc|Le)?[A-Z][&;a-z]+)*(?: #[1-9])?$'),
		re.compile('^(?:[A-Z][a-z]+ )+(?:Mountains|Range|Wilderness) HP$'),
		re.compile('^(?:[A-Z][a-z]+ )+\\([A-Z][a-z]+(?: [A-Z][a-z]+)*\\)$'),
		re.compile('^(?:[A-Z][a-z]+ )+(?:[A-Z]\\.|St\\.|del|in the|of the|and)(?: [A-Z][a-z]+)+$'),
		re.compile('^[A-Z][a-z]+(?:-[a-z]{2,})?(?: [A-Z][a-z]+(?:-[a-z]{2,})?)+$'),
		re.compile('^Mount [A-Z][a-z]+-[A-Z][a-z]+$'),
		re.compile('^&quot;[A-Z][a-z]+(?: [A-Z][a-z]+)*&quot;$'),
		re.compile('^Peak [1-9][0-9]{2,4}m?\\+?$'),
	)
	grade = re.compile(
		'^<td>Class ([123456](?:s[23456])?\\+?)</td>$'
	)
	numLT1k = re.compile('^[1-9][0-9]{0,2}|0$')
	numGE1k = re.compile('^[1-9][0-9]?,[0-9]{3}$')
	numMeters = re.compile('^[1-9][0-9]{0,3}(?:\\.[0-9])?$')
	prominence = re.compile('^[,0-9]+')
	prominenceTooltip = re.compile(
		'^(?:\\(([,0-9]+m?) \\+ (10m?|20m?|25|40|50)/2\\)|([,0-9]+(?:(?:\\.[0-9])?m)?))'
		' - (?:\\(([,0-9]+m?) - (10m?|20m?|25|40|50|80)/2\\)|([,0-9]+(?:(?:\\.[0-9])?m)?))'
		'(?: \\(([A-Z][A-Za-z]+(?:/[A-Z][A-Za-z]+)*)\\))?(<br>Line Parent: '
		'[A-Z][a-z]+(?: [A-Z][a-z]+)*(?: \\([A-Z][a-z]+(?: [A-Z][a-z]+)*\\))? \\([,0-9]+\\))?$'
	)
	summitpost = re.compile(
		'^<td><a href="https://www\\.summitpost\\.org/([-0-9a-z]+)/([0-9]+)">SP</a></td>$'
	)
	wikipedia = re.compile(
		'^<td><a href="https://en\\.wikipedia\\.org/wiki/([-%(),.0-9A-Z_a-z]+)">W</a></td>$'
	)
	bobBurd = re.compile(
		'^<td><a href="https://www\\.snwburd\\.com/dayhikes/peak/([0-9]+)">BB</a></td>$'
	)
	listsOfJohn = re.compile(
		'^<td><a href="https://listsofjohn\\.com/peak/([0-9]+)">LoJ</a></td>$'
	)
	peakbagger = re.compile(
		'^<td><a href="https://peakbagger\\.com/peak.aspx\\?pid=(-?[1-9][0-9]*)">Pb</a></td>$'
	)
	weather = re.compile(
		'^<td><a href="https://forecast\\.weather\\.gov/MapClick\\.php\\?'
		'lon=(-[0-9]{1,3}\\.[0-9]{1,6})&lat=([0-9]{1,2}\\.[0-9]{1,6})">WX</a></td>$'
	)
	climbedDate = re.compile('^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}')
	climbedLink = re.compile('^/photos/((?:[0-9A-Za-z]+/){1,2}(?:index[0-9]{2}\\.html)?)">')
	climbedWithLink = re.compile('^(https?://[-\\./0-9A-Za-z]+)">')
	climbedWithName = re.compile('^[A-Z](?:[a-z]+|[A-Z]{1,2})(?: [A-Z][a-z]+)*')

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

def parseClimbedTooltip(line):
	if not line.startswith('<div class="tooltip"><b>with</b><br>'):
		raise FormatError("Climbed tooltip doesn't match expected pattern")
	line = line[36:]

	climbedWith = []
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

		if not line.startswith('<br>'):
			break
		line = line[4:]

	if not line.startswith('</div></span>'):
		raise FormatError("Climbed tooltip doesn't match expected pattern")

	return line[13:], climbedWith

def parseClimbed(line, htmlFile):
	climbed = []

	if not line.startswith('<td>'):
		badLine()

	while True:
		line = line[4:]

		tooltip = False
		if line.startswith('<span>'):
			tooltip = True
			line = line[6:]

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

		if tooltip:
			line, climbedWith = parseClimbedTooltip(line)
			climbed.append((climbedDate, climbedWith, True))
		elif line.startswith(' solo'):
			line = line[5:]
			climbed.append((climbedDate, [], False))
		elif line.startswith(' with '):
			line, climbedWith = parseClimbedWith(line[6:])
			climbed.append((climbedDate, climbedWith, False))
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

	for date, climbedWith, tooltip in climbed:
		line = []

		if isinstance(date, str):
			line.append(date)
		else:
			line.append('<a href="/photos/{1}">{0}</a>'.format(*date))

		if climbedWith:
			names = []
			for name in climbedWith:
				if isinstance(name, str):
					names.append(name)
				else:
					names.append('<a href="{1}">{0}</a>'.format(*name))

			if tooltip:
				line.insert(0, '<span>')
				line.append('<div class="tooltip"><b>with</b><br>')
				line.append('<br>'.join(names))
				line.append('</div></span>')
			elif len(names) > 2:
				line.append(' with ')
				line.append(', '.join(names[:-1]))
				line.append(', and ')
				line.append(names[-1])
			else:
				line.append(' with ')
				line.append(' and '.join(names))
		else:
			line.append(' solo')

		lines.append(''.join(line))

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
		assert contourInterval in (0, 10, 20, 25, 40, 50, 80)
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
		return toFeet(avgElev) if self.inMeters else int(avgElev)

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

	for flag in ("BigSur", "CC"):
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
			(peak.latitude, peak.longitude, peak.zoom,
				peak.name, suffix, peak.otherName) = m.groups()

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
				badSuffix()

			for pattern in RE.peakName:
				if pattern.match(peak.name):
					break
			else:
				raise FormatError("Peak name doesn't match expected pattern")

			parseLandManagement(htmlFile, peak)
			parseElevation(htmlFile, peak)

			line = htmlFile.next()
			m = RE.grade.match(line)
			if m is None:
				if line != emptyCell or (pl.id, peak.id) not in ():
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
			if m:
				peak.bobBurdId = m.group(1)
			elif line != emptyCell or (pl.id, peak.id) not in (
				('OCAP', '6.4'), # Mount Saint Helena Southeast
				('OCAP','16.1'), # Peak 2440+
				('OCAP','17.2'), # Elliott Mountain
				('OCAP','17.6'), # Angel Vista
				('OCAP','17.8'), # Pop Top
				('OSP', '17.4'), # Ruby Mesa
				('OSP', '27.2'), # Snow Valley Peak East
				('OSP', '27.3'), # Herlan Peak South
				('OSP', '27.5'), # Peak 7136
				('OWP',  '1.1'), # Sourdough Mountain Lookout
			):
				badLine()

			line = htmlFile.next()
			m = RE.listsOfJohn.match(line)
			if m:
				peak.listsOfJohnId = m.group(1)
			elif line != emptyCell or peak.countryUS and (pl.id, peak.id) not in (
				('OCAP', '6.4'), # Mount Saint Helena Southeast
				('OCAP','16.1'), # Peak 2440+
				('OCAP','17.2'), # Elliott Mountain
				('OCAP','17.3'), # Lizard Rock
				('OCAP','17.6'), # Angel Vista
				('OCAP','17.8'), # Pop Top
				('OSP', '17.4'), # Ruby Mesa
				('OSP', '27.2'), # Snow Valley Peak East
				('OSP', '27.3'), # Herlan Peak South
				('OSP', '27.5'), # Peak 7136
				('OWP',  '1.1'), # Sourdough Mountain Lookout
			):
				badLine()

			line = htmlFile.next()
			m = RE.peakbagger.match(line)
			if m:
				peak.peakbaggerId = m.group(1)
			elif line != emptyCell or (pl.id, peak.id) not in (
				('OCAP', '3.5'), # Peak 7905
				('OCAP','16.1'), # Peak 2440+
				('OSP', '17.4'), # Ruby Mesa
				('OSP', '19.2'), # Peak 3113m
				('OSP', '19.5'), # Volcanic Ridge East
				('OSP', '27.5'), # Peak 7136
			):
				badLine()

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
			raise FormatError("Peak list '{}' doesn't exist", pl2Id)
		section = pl2.sections[sectionNumber - 1]
		if section.id2Peak is None:
			section.id2Peak = {p.id[p.id.find(".")+1:]: p for p in section.peaks}
		peak.copyFrom(section.id2Peak[peakNumber])

def writeHTML(pl):
	sectionFormat = '<tr class="section"{4}><td id="{0}{1}" colspan="{2}">{1}. {3}</td></tr>'
	column2Format = '<td><a href="https://caltopo.com/map.html#ll={},{}&z={}&b=t">{}</a>{}{}</td>'
	summitpostFormat = '<td><a href="https://www.summitpost.org/{0}/{1}">SP</a></td>'
	wikipediaFormat = '<td><a href="https://en.wikipedia.org/wiki/{0}">W</a></td>'
	bobBurdFormat = '<td><a href="https://www.snwburd.com/dayhikes/peak/{0}">BB</a></td>'
	listsOfJohnFormat = '<td><a href="https://listsofjohn.com/peak/{0}">LoJ</a></td>'
	peakbaggerFormat = '<td><a href="https://peakbagger.com/peak.aspx?pid={0}">Pb</a></td>'
	weatherFormat = '<td><a href="https://forecast.weather.gov/MapClick.php?lon={0}&lat={1}">WX</a></td>'

	emptyCell = '<td>&nbsp;</td>'
	extraRowFirstLine = '<tr><td colspan="{}"><ul>'.format(pl.numColumns - 1)
	extraRowLastLine = '</ul></td></tr>'

	htmlFile = open(pl.htmlFilename)
	for line in htmlFile:
		print(line, end='')
		if line == tableLine:
			break
	for line in htmlFile:
		m = RE.sectionRow.match(line)
		if m is not None:
			break
		print(line, end='')

	for sectionNumber, section in enumerate(pl.sections, start=1):
		print(sectionFormat.format(pl.htmlId, sectionNumber, pl.numColumns, section.name,
			getCommonDataAttributes(section, pl)))

		for peak in section.peaks:
			suffix = ''
			classNames = []

			if peak.isClimbed:
				classNames.append('climbed')
			if peak.isMtneer:
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
			print('<tr{}{}>'.format(attr, getCommonDataAttributes(peak, section)))

			attr = ''
			if peak.hasHtmlId:
				attr += ' id="{}{}"'.format(pl.htmlId, peak.id)
			if peak.extraRow is not None:
				attr += ' rowspan="2"'
			print('<td{}>{}</td>'.format(attr, peak.id))

			otherName = '' if peak.otherName is None else '<br>({})'.format(peak.otherName)

			print(column2Format.format(peak.latitude, peak.longitude, peak.zoom,
				peak.name, suffix, otherName))

			if peak.landManagement:
				print('<td>{}</td>'.format(peak.landManagementHTML()))
			else:
				print(emptyCell)

			print('<td>{}</td>'.format(peak.elevationHTML()))

			if peak.grade is None:
				print(emptyCell)
			else:
				print('<td>Class {}</td>'.format(peak.grade))

			print('<td>{}</td>'.format(peak.prominenceHTML()))

			if peak.summitpostId is None:
				print(emptyCell)
			else:
				print(summitpostFormat.format(peak.summitpostName, peak.summitpostId))

			if peak.wikipediaLink is None:
				print(emptyCell)
			else:
				print(wikipediaFormat.format(peak.wikipediaLink))

			if peak.bobBurdId is None:
				print(emptyCell)
			else:
				print(bobBurdFormat.format(peak.bobBurdId))

			if peak.listsOfJohnId is None:
				print(emptyCell)
			else:
				print(listsOfJohnFormat.format(peak.listsOfJohnId))

			if peak.peakbaggerId is None:
				print(emptyCell)
			else:
				print(peakbaggerFormat.format(peak.peakbaggerId))

			if pl.column12 is not None:
				if peak.column12 is None:
					print(emptyCell)
				else:
					print(str(peak.column12), end='')

			if peak.countryUS:
				print(weatherFormat.format(peak.longitude, peak.latitude))
			else:
				print(emptyCell)

			if peak.isClimbed:
				print('<td>{}</td>'.format(climbed2Html(peak.climbed)))
			else:
				print(emptyCell)

			print('</tr>')
			if peak.extraRow is not None:
				print(extraRowFirstLine)
				print(peak.extraRow, end='')
				print(extraRowLastLine)

	for line in htmlFile:
		if line == '</table>\n':
			print(line, end='')
			break
	for line in htmlFile:
		print(line, end='')
	htmlFile.close()

def writePeakJSON(f, peak):
	f('{\n"type":"Feature",\n"geometry":{"type":"Point","coordinates":')
	f('[{},{}]'.format(peak.longitude, peak.latitude))
	f('},\n"properties":{\n')
	f('"id":{},\n'.format(peak.jsonId()))

	p = [('name', peak.name)]
	if peak.otherName is not None:
		p.append(('name2', peak.otherName))

	p.append(('prom', peak.prominenceHTML().replace('"', '\\"')))
	if peak.grade is not None:
		p.append(('YDS', peak.grade))
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
			for date, climbedWith, tooltip in peak.climbed])))

	for k, v in p:
		f('"{}":"{}",\n'.format(k, v))

	if peak.zoom != '15':
		f('"z":{},\n'.format(peak.zoom))
	if peak.isEmblem:
		f('"emblem":true,\n')
	elif peak.isMtneer:
		f('"mtneer":true,\n')
	if not peak.countryUS:
		f('"noWX":true,\n')

	f('"elev":')
	if len(peak.elevations) == 1 and peak.elevations[0].source is None:
		f(peak.elevations[0].json())
	else:
		f(peak.elevationJSON())
	f('\n}}')

def writeJSON(pl):
	import topoview
	topos = topoview.read_csv()

	for topo in USGSTopo.sources.values():
		topo.id = topos[topo.id].scan_id

	f = sys.stdout.write
	firstPeak = True

	f('{\n')
	f('"id":"{}",\n'.format(pl.id))
	f('"name":"{}",\n'.format(pl.name))
	f('"type":"FeatureCollection",\n')
	f('"features":[')
	for section in pl.sections:
		for peak in section.peaks:
			if not (peak.delisted or peak.suspended):
				if firstPeak:
					firstPeak = False
				else:
					f(',')
				writePeakJSON(f, peak)

	f('],\n"topomaps":{\n')
	f(',\n'.join([topo.json() for topo in sorted(USGSTopo.sourcesJSON, key=lambda topo: topo.id)]))
	f('\n}}\n')

def checkData(pl):
	import sps_create
	sps_create.checkData(pl)

def compareTopoMetadata():
	import topoview
	topoview.compare(USGSTopo.sources)

def setProm(pl):
	import sps_create
	sps_create.checkData(pl, setProm=True)
	writeHTML(pl)

def setVR(pl):
	import sps_create
	sps_create.checkData(pl, setVR=True)
	writeHTML(pl)

def loadPeakFiles(pl):
	import sps_create
	sps_create.loadPeakFiles(pl)

def loadPeakListFiles(pl):
	import sps_create
	sps_create.loadPeakListFiles(pl)

def loadTopoMetadata():
	import topoview
	topoview.load(USGSTopo.sources)

def newTopoLink(pl):
	import topoview
	old_topos = topoview.read_csv()
	new_topos = topoview.read_new()

	for topo in USGSTopo.sources.values():
		topo.linkSuffix = new_topos[old_topos[topo.id].scan_id].md5

	writeHTML(pl)

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

def printStats():
	climbedElevs = []
	climbedProms = []
	for peak in allPeaksGenerator():
		if peak.isClimbed:
			name = peak.name.replace('&quot;', '"')

			prom = toMeters(peak.getPromForStats())
			climbedProms.append((prom, name))

			if prom >= 100:
				elev = toMeters(peak.getElevForStats())
				climbedElevs.append((elev, name))

	n = len(climbedElevs)
	eIndex = 0
	for elev, name in sorted(climbedElevs):
		print("{:3}.  {:4}m  {}".format(n, elev, name))
		if eIndex == 0 and elev >= n:
			eIndex = n
		n -= 1

	print("E-Index:", eIndex)
	print()

	n = len(climbedProms)
	pIndex = 0
	for prom, name in sorted(climbedProms):
		print("{:3}.  {:4}m  {}".format(n, prom, name))
		if pIndex == 0 and prom >= n:
			pIndex = n
		n -= 1

	print("P-Index:", pIndex)

class RegionInfo(object):
	def __init__(self, peak, elev, prom):
		self.elevs = [elev]
		self.minElev = elev
		self.maxElev = elev
		self.proms = [prom]
		self.minProm = prom
		self.maxProm = prom
		self.minElevPeaks = [peak]
		self.maxElevPeaks = [peak]
		self.minPromPeaks = [peak]
		self.maxPromPeaks = [peak]

	def update(self, peak, elev, prom):
		self.elevs.append(elev)
		self.proms.append(prom)

		if elev < self.minElev:
			self.minElev = elev
			self.minElevPeaks[:] = [peak]
		elif elev == self.minElev:
			self.minElevPeaks.append(peak)
		if elev > self.maxElev:
			self.maxElev = elev
			self.maxElevPeaks[:] = [peak]
		elif elev == self.maxElev:
			self.maxElevPeaks.append(peak)

		if prom < self.minProm:
			self.minProm = prom
			self.minPromPeaks[:] = [peak]
		elif prom == self.minProm:
			self.minPromPeaks.append(peak)
		if prom > self.maxProm:
			self.maxProm = prom
			self.maxPromPeaks[:] = [peak]
		elif prom == self.maxProm:
			self.maxPromPeaks.append(peak)

def printSummary(elevThreshold=3000, elevInMeters=True, promThreshold=100, promInMeters=True, allPeaks=False):
	regionInfoMap = {}
	total = None

	for peak in allPeaksGenerator():
		if allPeaks or peak.isClimbed:
			prom = peak.getPromForStats()
			if promInMeters:
				prom = toMeters(prom)
			if prom < promThreshold:
				continue

			elev = peak.getElevForStats()
			if elevInMeters:
				elev = toMeters(elev)
			if elev < elevThreshold:
				continue

			region = (peak.country[0], peak.state[0])
			info = regionInfoMap.get(region)
			if info is None:
				regionInfoMap[region] = RegionInfo(peak, elev, prom)
			else:
				info.update(peak, elev, prom)

			if total is None:
				total = RegionInfo(peak, elev, prom)
			else:
				total.update(peak, elev, prom)

	def peakNames(peaks):
		return "({})".format(", ".join([peak.name.replace('&quot;', '"') for peak in peaks]))

	int2StrMeters = lambda n: "{:6,}m".format(n)
	int2StrFeet = lambda n: "{:6,}'".format(n)
	elev2Str = int2StrMeters if elevInMeters else int2StrFeet
	prom2Str = int2StrMeters if promInMeters else int2StrFeet

	def average(values):
		return int(round(float(sum(values)) / len(values)))

	def median(values):
		values.sort()
		i, j = divmod(len(values), 2)
		if j == 0:
			return int(round((values[i] + values[i-1]) / 2.0))
		return values[i]

	def align(label):
		return "{:>16}:".format(label)

	def printInfo(info, label):
		print("{}: {}".format(label, len(info.elevs)))

		print(align("Min Elev"), elev2Str(info.minElev), peakNames(info.minElevPeaks))
		print(align("Max Elev"), elev2Str(info.maxElev), peakNames(info.maxElevPeaks))
		print(align("Mean Elev"), elev2Str(average(info.elevs)))
		print(align("Median Elev"), elev2Str(median(info.elevs)))

		print(align("Min Prom"), prom2Str(info.minProm), peakNames(info.minPromPeaks))
		print(align("Max Prom"), prom2Str(info.maxProm), peakNames(info.maxPromPeaks))
		print(align("Mean Prom"), prom2Str(average(info.proms)))
		print(align("Median Prom"), prom2Str(median(info.proms)))

	for region, info in sorted(regionInfoMap.items()):
		printInfo(info, "/".join(region))

	printInfo(total, "Total")

def printHistory():
	history = []
	for peak in allPeaksGenerator():
		if peak.isClimbed:
			for date, climbedWith, tooltip in peak.climbed:
				if isinstance(date, tuple):
					date = date[0]
				month, day, year = map(int, date.split("/"))
				name = peak.name.replace('&quot;', '"')
				history.append(((year, month, day), name))

	for date, name in sorted(history):
		print("{}-{:02}-{:02}".format(*date), name)

def checkPeakListArg(args):
	if len(args) < 1:
		err("Please specify the peak list abbreviation after the command.")
	if len(args) > 1:
		err("Please specify only the peak list abbreviation after the command.")
	pl = peakLists.get(args[0])
	if pl is None:
		err("Please specify a valid peak list abbreviation.")
	return pl

def checkNoArgs(args):
	if len(args) != 0:
		err("Too many command-line arguments!")
	return None

def checkSumArgs(args):
	elev, elevInMeters = 3000, True
	prom, promInMeters =  100, True

	allPeaks = len(args) > 0 and args[0] == "all"
	if allPeaks:
		args.pop(0)

	if len(args) > 2:
		err("Too many command-line arguments!")
	if len(args) > 0:
		elev = args[0]
		if elev[-1] == 'm':
			elev = elev[:-1]
		else:
			elevInMeters = False
		try:
			elev = int(elev)
		except ValueError:
			err("Please specify an integer elevation threshold.")

		if len(args) > 1:
			prom = args[1]
			if prom[-1] == 'm':
				prom = prom[:-1]
			else:
				promInMeters = False
			try:
				prom = int(prom)
			except ValueError:
				err("Please specify a non-negative prominence threshold.")
			if prom < 0:
				err("Please specify a non-negative prominence threshold.")

	return (elev, elevInMeters, prom, promInMeters, allPeaks)

def main():
	initPeakLists()

	commandMap = {
		'check': (checkData, checkPeakListArg),
		'cmptopo': (compareTopoMetadata, checkNoArgs),
		'create': (createList, checkPeakListArg),
		'elev': (printElevationStats, checkNoArgs),
		'history': (printHistory, checkNoArgs),
		'html': (writeHTML, checkPeakListArg),
		'json': (writeJSON, checkPeakListArg),
		'land': (printLandManagementAreas, checkNoArgs),
		'load': (loadPeakFiles, checkPeakListArg),
		'loadlist': (loadPeakListFiles, checkPeakListArg),
		'loadtopo': (loadTopoMetadata, checkNoArgs),
		'newtopo': (newTopoLink, checkPeakListArg),
		'stats': (printStats, checkNoArgs),
		'sum': (printSummary, checkSumArgs),
	}

	if len(sys.argv) < 2:
		err("Please specify a command, e.g. 'html' or 'json'.")

	command, args = sys.argv[1], sys.argv[2:]

	info = commandMap.get(command)
	if info is None:
		err("Please specify a valid command, e.g. 'html' or 'json'.")

	commandFunction, checkArgs = info
	args = checkArgs(args)

	readAllHTML()

	if args is None:
		commandFunction()
	elif isinstance(args, tuple):
		commandFunction(*args)
	else:
		commandFunction(args)

if __name__ == '__main__':
	main()
