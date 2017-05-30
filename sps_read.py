#!/usr/bin/python
import re
import sys

class G(object):
	sps = True
	dps = False
	peakIdPrefix = 'SPS'
	htmlFilename = 'sps.html'
	colspan = '14'
	colspanMinus1 = '13'
	geojsonTitle = 'Sierra Peaks'
	numPeaks = 247
	numSections = 24

	@classmethod
	def setDPS(self):
		self.dps = True
		self.sps = False
		self.peakIdPrefix = 'DPS'
		self.htmlFilename = 'dps.html'
		self.colspan = '13'
		self.colspanMinus1 = '12'
		self.geojsonTitle = 'Desert Peaks'
		self.numPeaks = 99
		self.numSections = 9

peakArray = []
sectionArray = []

class Peak(object):
	def __init__(self):
		self.id = ''
		self.name = ''
		self.otherName = None
		self.latitude = ''
		self.longitude = ''
		self.zoom = ''
		self.baseLayer = ''
		self.elevation = ''
		self.prominence = ''
		self.prominenceLink = None
		self.grade = ''
		self.ccLatitude = ''
		self.ccLongitude = ''
		self.summitpostId = None
		self.summitpostName = None
		self.wikipediaLink = None
		self.bobBurdId = None
		self.listsOfJohnId = None
		self.peakbaggerId = None
		self.climbDate = None
		self.climbPhotos = None
		self.climbWith = None
		self.extraRow = None
		self.hasHtmlId = False
		self.isClimbed = False
		self.isEmblem = False
		self.isMtneer = False
		self.isHighPoint = False
		self.landClass = None
		self.landManagement = None

def compareLatLong(peak):
	mmFormat = 'Mismatched {0:14s} for {1:22s}:'
	llFormat = '{0:10.6f} != {1:10.6f} ({2:.6f})'

	latitude = float(peak.latitude)
	longitude = float(peak.longitude)
	ccLatitude = float(peak.ccLatitude)
	ccLongitude = float(peak.ccLongitude)
	deltaLat = abs(latitude - ccLatitude)
	deltaLong = abs(longitude - ccLongitude)

	if deltaLat > 0.0002:
		print >>sys.stderr, mmFormat.format('LATITUDE', peak.name),
		print >>sys.stderr, llFormat.format(latitude, ccLatitude, deltaLat)
	if deltaLong > 0.0002:
		print >>sys.stderr, mmFormat.format('LONGITUDE', peak.name),
		print >>sys.stderr, llFormat.format(longitude, ccLongitude, deltaLong)

def badLine(lineNumber):
	sys.exit("Line {0} doesn't match expected pattern!".format(lineNumber))

def badSuffix(lineNumber):
	sys.exit("Suffix and class don't match on line {0}".format(lineNumber))

def badClimbed(lineNumber):
	sys.exit("Climbed column doesn't match class on line {0}".format(lineNumber))

def badSection(lineNumber):
	sys.exit("Unexpected section number on line {0}".format(lineNumber))

def badWxLatLong(lineNumber):
	sys.exit("Peak lat/long doesn't match WX lat/long on line {0}".format(lineNumber))

def badLandMgmt(lineNumber):
	sys.exit("Land management column doesn't match class on line {0}".format(lineNumber))

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
	(' National Wildlife Range',    'landFWS'),
	(' National Wildlife Refuge',   'landFWS'),
	(' State Park',                 'landSP'),
]
landNamePrefixes = [
	('BLM ',                        'landBLM'),
]
landMgmtAreas = {}
landMgmtPattern = re.compile('^(?:<a href="([^"]+)">([- A-Za-z]+)</a>( HP)?)|([- \'A-Za-z]+)')
fsLinkPattern = re.compile('^https://www\\.fs\\.usda\\.gov/[a-z]+$')
fwsLinkPattern = re.compile('^https://www\\.fws\\.gov/refuge/[a-z]+/$')
npsLinkPattern = re.compile('^https://www\\.nps\\.gov/[a-z]{4}/index\\.htm$')
stateParkPattern = re.compile('^http://www\\.parks\\.ca\\.gov/\\?page_id=[0-9]+$')
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

def parseLandManagement(peak, lineNumber, htmlFile):
	line = htmlFile.next()
	lineNumber += 1

	if line[:4] != '<td>' or line[-6:] != '</td>\n':
		badLine(lineNumber)
	line = line[4:-6]

	if G.dps and peak.section == 9:
		if line == '&nbsp;':
			return lineNumber
		badLine(lineNumber)

	landList = []
	landClass = None

	while True:
		m = landMgmtPattern.match(line)
		if m is None:
			badLine(lineNumber)

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
				e = "Wilderness URL doesn't match expected pattern on line {}"
				sys.exit(e.format(lineNumber))
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
						e = "Unrecognized land management name on line {}"
						sys.exit(e.format(lineNumber))

			if currentClass.startswith('land'):
				linkPattern = landLinkPattern.get(currentClass)
				if linkPattern is not None:
					if landLink is None or linkPattern.match(landLink) is None:
						e = "Land management URL doesn't match expected pattern on line {}"
						sys.exit(e.format(lineNumber))

				if landClass is None:
					landClass = currentClass
				elif landOrder[landClass] < landOrder[currentClass]:
					e = "Unexpected order of land management areas on line {}"
					sys.exit(e.format(lineNumber))

			elif not (landList and currentClass == landList[-1][1]):
				e = '"{}" must follow "{}" on line {}'
				sys.exit(e.format(landName, currentClass, lineNumber))

		if landName in landMgmtAreas:
			errorMsg = landMgmtAreas[landName].add(peak, landLink, landHP is not None)
			if errorMsg:
				sys.exit("{} for {} on line {}".format(errorMsg, landName, lineNumber))
		else:
			landMgmtAreas[landName] = LandMgmtArea(peak, landLink, landHP is not None)

		if landHP is None:
			landHP = ''
		landList.append((landLink, landName, landHP))
		if line == '':
			break
		if line[:4] != '<br>':
			badLine(lineNumber)
		line = line[4:]

	if peak.landClass != landClass:
		badLandMgmt(lineNumber)
	peak.landManagement = '<br>'.join([
		'<a href="{}">{}</a>{}'.format(landLink, landName, landHP) if landLink
		else landName + landHP
		for (landLink, landName, landHP) in landList])
	return lineNumber

def printLandManagementAreas():
	for name, area in sorted(landMgmtAreas.iteritems()):
		print '{:35}{: 3}  {:22} {}'.format(name,
			area.count,
			area.highPoint.name if area.highPoint else '-',
			area.url if area.url else '-')

ngsLinkPrefix = 'https://www.ngs.noaa.gov/cgi-bin/ds_mark.prl?PidBox='
topoLinkPrefix = 'https://ngmdb.usgs.gov/img4/ht_icons/Browse/CA/CA_'
topoLinkPattern = re.compile('^([A-Z][a-z]+(?:%20[A-Z][a-z]+)*)_[0-9]{6}_([0-9]{4})_([0-9]{5})\\.jpg$')
elevFromNGS = re.compile('^([0-9]{4}(?:\\.[0-9])?)m \\(NAVD 88\\) NGS Data Sheet &quot;[A-Z][a-z]+(?: [A-Z][a-z]+)*(?: [0-9]+)?&quot; \\(([A-Z]{2}[0-9]{4})\\)$')
elevFromTopo = re.compile('^((?:[0-9]{4}(?:(?:\\.[0-9])|(?:-[0-9]{4}))?m)|(?:[0-9]{4,5}(?:-[0-9]{4,5})?\')) \\(NGVD 29\\) USGS (7\\.5|15)\' Quad \\(1:([0-9]{2}),([0-9]{3})\\) &quot;([\\. A-Za-z]+), CA&quot; \\(([0-9]{4})(?:/[0-9]{4})?\\)$')
contourIntervals = (10, 20, 40, 80)

def checkElevationTooltip(e, lineNumber):
	if e.link.startswith(ngsLinkPrefix):
		m = elevFromNGS.match(e.tooltip)
		if m is None or e.link[len(ngsLinkPrefix):] != m.group(2):
			badLine(lineNumber)
		elevation = int(float(m.group(1)) / 0.3048 + 0.49)
		elevation = '{},{:03}'.format(*divmod(elevation, 1000))
		if elevation != e.elevation:
			sys.exit("Elevation in tooltip doesn't match on line {}".format(lineNumber))
		return
	if e.link.startswith(topoLinkPrefix):
		m = elevFromTopo.match(e.tooltip)
		if m is None:
			badLine(lineNumber)
		elevation, quad, scale1, scale2, quadName, year = m.groups()
		scale = scale1 + scale2
		if quad == '7.5' and scale != '24000' or quad == '15' and scale != '62500':
			badLine(lineNumber)
		quadName = quadName.replace('.', '')
		quadName = quadName.replace(' ', '%20')
		m = topoLinkPattern.match(e.link[len(topoLinkPrefix):])
		if m is None:
			sys.exit("Topo URL doesn't match expected pattern on line {}".format(lineNumber))
		if quadName != m.group(1) or year != m.group(2) or scale != m.group(3):
			sys.exit("Quad name, year, or scale doesn't match topo URL on line {}".format(lineNumber))
		unit = elevation[-1]
		elevation = elevation[:-1]
		if '-' in elevation:
			elevation, elevationMax = elevation.split('-')
			elevationMin = int(elevation)
			elevationMax = int(elevationMax)
			interval = elevationMax - elevationMin + 1
			if interval not in contourIntervals or elevationMin % interval != 0:
				sys.exit("Elevation range in tooltip not valid on line {}".format(lineNumber))
			suffix = '+'
		else:
			suffix = ''
		if unit == 'm':
			elevation = int(float(elevation) / 0.3048 + 0.5)
		else:
			elevation = int(elevation)
		elevation = '{},{:03}'.format(*divmod(elevation, 1000)) + suffix
		if elevation != e.elevation:
			sys.exit("Elevation in tooltip doesn't match on line {}".format(lineNumber))
		return
	badLine(lineNumber)

class Elevation(object):
	pattern1 = re.compile('^([0-9]{1,2},[0-9]{3}\\+?)')
	pattern2 = re.compile('^<span><a href="([^"]+)">([0-9]{1,2},[0-9]{3}\\+?)</a><div class="tooltip">([- &\'(),\\.:;/0-9A-Za-z]+)(?:(</div></span>)|$)')

	def __init__(self, elevation, link=None, tooltip=None):
		self.elevation = elevation
		self.link = link
		self.tooltip = tooltip
		self.extraLines = ''

	def html(self):
		if self.link is None:
			return self.elevation

		return '<span><a href="{}">{}</a><div class="tooltip">{}{}</div></span>'.format(
			self.link, self.elevation, self.tooltip, self.extraLines)

def parseElevation(peak, lineNumber, htmlFile):
	line = htmlFile.next()
	lineNumber += 1

	if line[:4] != '<td>':
		badLine(lineNumber)
	line = line[4:]

	elevations = []

	while True:
		m = Elevation.pattern1.match(line)
		if m is not None:
			e = Elevation(m.group(1))
			line = line[m.end():]
		else:
			m = Elevation.pattern2.match(line)
			if m is None:
				badLine(lineNumber)

			e = Elevation(m.group(2), m.group(1), m.group(3))
			checkElevationTooltip(e, lineNumber)
			if m.group(4) is None:
				e.extraLines = '\n'
				for line in htmlFile:
					lineNumber += 1
					if line.startswith('</div></span>'):
						line = line[13:]
						break
					e.extraLines += line
			else:
				line = line[m.end():]

		elevations.append(e)

		if line == '</td>\n':
			break
		if line[:4] != '<br>':
			badLine(lineNumber)
		line = line[4:]

	peak.elevation = '<br>'.join([e.html() for e in elevations])
	return lineNumber

tableLine = '<p><table id="peakTable" class="land landColumn">\n'

def readHTML():
	sectionRowPattern = re.compile('^<tr class="section"><td id="' + G.peakIdPrefix + '([0-9]+)" colspan="' + G.colspan + '">\\1\\. ([- &,;A-Za-z]+)</td></tr>$')
	peakRowPattern = re.compile('^<tr(?: class="([A-Za-z]+(?: [A-Za-z]+)*)")?>$')
	column1Pattern = re.compile('^<td(?: id="' + G.peakIdPrefix + '([0-9]+\\.[0-9]+)")?( rowspan="2")?>([0-9]+\\.[0-9]+)</td>$')
	column2Pattern = re.compile('^<td><a href="https://mappingsupport\\.com/p/gmap4\\.php\\?ll=([0-9]+\\.[0-9]+),-([0-9]+\\.[0-9]+)&z=([0-9]+)&t=(t[14])">([ \'#()0-9A-Za-z]+)</a>( \\*{1,2}| HP)?(?:<br>\\(([ A-Za-z]+)\\))?</td>$')
	gradePattern = re.compile('^<td>Class ([123456](?:s[23456])?)</td>$')
	prominencePattern1 = re.compile('^<td>((?:[0-9]{1,2},)?[0-9]{3})</td>$')
	prominencePattern2 = re.compile('^<td><a href="([^"]+)">((?:[0-9]{1,2},)?[0-9]{3})</a></td>$')
	summitpostPattern = re.compile('^<td><a href="http://www\\.summitpost\\.org/([-a-z]+)/([0-9]+)">SP</a></td>$')
	wikipediaPattern = re.compile('^<td><a href="https://en\\.wikipedia\\.org/wiki/([_,()%0-9A-Za-z]+)">W</a></td>$')
	bobBurdPattern = re.compile('^<td><a href="http://www\\.snwburd\\.com/dayhikes/peak/([0-9]+)">BB</a></td>$')
	listsOfJohnPattern = re.compile('^<td><a href="http://listsofjohn\\.com/peak/([0-9]+)">LoJ</a></td>$')
	peakbaggerPattern = re.compile('^<td><a href="http://peakbagger\\.com/peak.aspx\\?pid=([0-9]+)">Pb</a></td>$')
	closedContourPattern = re.compile('^<td><a href="http://www\\.closedcontour\\.com/sps/\\?zoom=7&lat=([0-9]+\\.[0-9]+)&lon=-([0-9]+\\.[0-9]+)">CC</a></td>$')
	weatherPattern = re.compile('^<td><a href="http://forecast\\.weather\\.gov/MapClick\\.php\\?lon=-([0-9]+\\.[0-9]+)&lat=([0-9]+\\.[0-9]+)">WX</a></td>$')
	climbedPattern = re.compile('^<td>(?:([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})|(?:<a href="/photos/([0-9A-Za-z]+(?:/best)?)/">([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})</a>))(?: (solo|(?:with .+)))</td>$')
	emptyCell = '<td>&nbsp;</td>\n'
	lineNumber = 0

	htmlFile = open(G.htmlFilename)
	for line in htmlFile:
		lineNumber += 1
		if line == tableLine:
			break
	for line in htmlFile:
		lineNumber += 1
		m = sectionRowPattern.match(line)
		if m is not None:
			sectionArray.append(m.group(2))
			if int(m.group(1)) != len(sectionArray):
				badSection(lineNumber)
			break
	for line in htmlFile:
		lineNumber += 1
		m = peakRowPattern.match(line)
		if m is not None:
			peak = Peak()
			if not parseClasses(peak, m.group(1)):
				sys.exit("Bad class names on line {0}".format(lineNumber))

			line = htmlFile.next()
			lineNumber += 1
			m = column1Pattern.match(line)
			if m is None:
				badLine(lineNumber)
			if m.group(2) is not None:
				peak.extraRow = ''
			peak.id = m.group(3)
			if m.group(1) is not None:
				if peak.id != m.group(1):
					sys.exit("HTML ID doesn't match peak ID on line {0}".format(lineNumber))
				peak.hasHtmlId = True

			sectionNumber, peakNumber = peak.id.split('.')
			peak.section = int(sectionNumber)
			if peak.section != len(sectionArray):
				sys.exit("Peak ID doesn't match section number on line {0}".format(lineNumber))

			line = htmlFile.next()
			lineNumber += 1
			m = column2Pattern.match(line)
			if m is None:
				badLine(lineNumber)
			peak.latitude = m.group(1)
			peak.longitude = m.group(2)
			peak.zoom = m.group(3)
			peak.baseLayer = m.group(4)
			peak.name = m.group(5)
			suffix = m.group(6)
			peak.otherName = m.group(7)

			if G.dps and peak.section == 9:
				if peak.baseLayer != 't1':
					badLine(lineNumber)
			else:
				if peak.baseLayer != 't4':
					badLine(lineNumber)

			if suffix is None:
				if peak.isEmblem or peak.isMtneer:
					badSuffix(lineNumber)
			elif suffix == ' *':
				if not peak.isMtneer:
					badSuffix(lineNumber)
			elif suffix == ' **':
				if not peak.isEmblem:
					badSuffix(lineNumber)
			else:
				peak.isHighPoint = True

			lineNumber = parseLandManagement(peak, lineNumber, htmlFile)
			lineNumber = parseElevation(peak, lineNumber, htmlFile)

			line = htmlFile.next()
			lineNumber += 1
			m = gradePattern.match(line)
			if m is None:
				badLine(lineNumber)
			peak.grade = m.group(1)

			line = htmlFile.next()
			lineNumber += 1
			m = prominencePattern1.match(line)
			if m is not None:
				peak.prominence = m.group(1)
			else:
				m = prominencePattern2.match(line)
				if m is None:
					badLine(lineNumber)
				peak.prominenceLink = m.group(1)
				peak.prominence = m.group(2)

			line = htmlFile.next()
			lineNumber += 1
			if line != emptyCell:
				m = summitpostPattern.match(line)
				if m is None:
					badLine(lineNumber)
				peak.summitpostName = m.group(1)
				peak.summitpostId = int(m.group(2))

			line = htmlFile.next()
			lineNumber += 1
			if line != emptyCell:
				m = wikipediaPattern.match(line)
				if m is None:
					badLine(lineNumber)
				peak.wikipediaLink = m.group(1)

			line = htmlFile.next()
			lineNumber += 1
			m = bobBurdPattern.match(line)
			if m is None:
				badLine(lineNumber)
			peak.bobBurdId = m.group(1)

			line = htmlFile.next()
			lineNumber += 1
			m = listsOfJohnPattern.match(line)
			if m is None:
				if not (G.dps and peak.section == 9 and line == emptyCell):
					badLine(lineNumber)
			else:
				peak.listsOfJohnId = m.group(1)

			line = htmlFile.next()
			lineNumber += 1
			m = peakbaggerPattern.match(line)
			if m is None:
				badLine(lineNumber)
			peak.peakbaggerId = m.group(1)

			if G.sps:
				line = htmlFile.next()
				lineNumber += 1
				m = closedContourPattern.match(line)
				if m is None:
					badLine(lineNumber)
				peak.ccLatitude = m.group(1)
				peak.ccLongitude = m.group(2)
#				compareLatLong(peak)

			line = htmlFile.next()
			lineNumber += 1
			m = weatherPattern.match(line)
			if m is None:
				if not (G.dps and peak.section == 9 and line == emptyCell):
					badLine(lineNumber)
			else:
				wxLatitude = m.group(2)
				wxLongitude = m.group(1)
				if wxLatitude != peak.latitude or wxLongitude != peak.longitude:
					badWxLatLong(lineNumber)

			line = htmlFile.next()
			lineNumber += 1
			if line == emptyCell:
				if peak.isClimbed:
					badClimbed(lineNumber)
			else:
				m = climbedPattern.match(line)
				if m is None:
					badLine(lineNumber)
				if not peak.isClimbed:
					badClimbed(lineNumber)
				climbDate, peak.climbPhotos, peak.climbDate, peak.climbWith = m.groups()
				if peak.climbDate is None:
					peak.climbDate = climbDate

			line = htmlFile.next()
			lineNumber += 1
			if line != '</tr>\n':
				badLine(lineNumber)
			if peak.extraRow is not None:
				line = htmlFile.next()
				lineNumber += 1
				if line != '<tr><td colspan="' + G.colspanMinus1 + '"><ul>\n':
					badLine(lineNumber)
				for line in htmlFile:
					lineNumber += 1
					if line == '</ul></td></tr>\n':
						break
					peak.extraRow += line

			peakArray.append(peak)
		else:
			m = sectionRowPattern.match(line)
			if m is not None:
				sectionArray.append(m.group(2))
				if int(m.group(1)) != len(sectionArray):
					badSection(lineNumber)
			elif line == '</table>\n':
				break
			else:
				badLine(lineNumber)
	htmlFile.close()
	if len(peakArray) != G.numPeaks:
		sys.exit("Number of peaks in HTML file is not {}.".format(G.numPeaks))
	if len(sectionArray) != G.numSections:
		sys.exit("Number of sections in HTML file is not {}.".format(G.numSections))

def writeHTML():
	oldColspan = ' colspan="' + G.colspan + '"'
	newColspan = ' colspan="' + G.colspan + '"'
	sectionFormat = '<tr class="section"><td id="{0}{1}"' + newColspan + '>{1}. {2}</td></tr>'
	column2Format = '<td><a href="https://mappingsupport.com/p/gmap4.php?ll={},-{}&z={}&t={}">{}</a>{}{}</td>'
	summitpostFormat = '<td><a href="http://www.summitpost.org/{0}/{1}">SP</a></td>'
	wikipediaFormat = '<td><a href="https://en.wikipedia.org/wiki/{0}">W</a></td>'
	bobBurdFormat = '<td><a href="http://www.snwburd.com/dayhikes/peak/{0}">BB</a></td>'
	listsOfJohnFormat = '<td><a href="http://listsofjohn.com/peak/{0}">LoJ</a></td>'
	closedContourFormat = '<td><a href="http://www.closedcontour.com/sps/?zoom=7&lat={0}&lon=-{1}">CC</a></td>'
	peakbaggerFormat = '<td><a href="http://peakbagger.com/peak.aspx?pid={0}">Pb</a></td>'
	weatherFormat = '<td><a href="http://forecast.weather.gov/MapClick.php?lon=-{0}&lat={1}">WX</a></td>'
	emptyCell = '<td>&nbsp;</td>'
	section1Line = sectionFormat.format(G.peakIdPrefix, 1, sectionArray[0]) + '\n';

	htmlFile = open(G.htmlFilename)
	for line in htmlFile:
		print line,
		if line == tableLine:
			break
	for line in htmlFile:
		if line == section1Line:
			break
		line = line.replace(oldColspan, newColspan)
		print line,

	sectionNumber = 0
	for peak in peakArray:
		if peak.section != sectionNumber:
			sectionNumber = peak.section
			print sectionFormat.format(G.peakIdPrefix, sectionNumber, sectionArray[sectionNumber - 1])

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

		if classNames:
			print '<tr class="{0}">'.format(' '.join(classNames))
		else:
			print '<tr>'

		attr = ''
		if peak.hasHtmlId:
			attr += ' id="{}{}"'.format(G.peakIdPrefix, peak.id)
		if peak.extraRow is not None:
			attr += ' rowspan="2"'

		print '<td{0}>{1}</td>'.format(attr, peak.id)

		otherName = '' if peak.otherName is None else '<br>({})'.format(peak.otherName)

		print column2Format.format(peak.latitude, peak.longitude, peak.zoom, peak.baseLayer,
			peak.name, suffix, otherName)

		if peak.landManagement is None:
			print emptyCell
		else:
			print '<td>{0}</td>'.format(peak.landManagement)

		print '<td>{0}</td>'.format(peak.elevation)
		print '<td>Class {0}</td>'.format(peak.grade)

		if peak.prominenceLink is None:
			print '<td>{0}</td>'.format(peak.prominence)
		else:
			print '<td><a href="{0}">{1}</a></td>'.format(peak.prominenceLink, peak.prominence)

		if peak.summitpostId is None:
			print emptyCell
		else:
			print summitpostFormat.format(peak.summitpostName, peak.summitpostId)

		if peak.wikipediaLink is None:
			print emptyCell
		else:
			print wikipediaFormat.format(peak.wikipediaLink)

		print bobBurdFormat.format(peak.bobBurdId)
		if peak.listsOfJohnId is None:
			print emptyCell
		else:
			print listsOfJohnFormat.format(peak.listsOfJohnId)
		print peakbaggerFormat.format(peak.peakbaggerId)
		if G.sps:
			print closedContourFormat.format(peak.ccLatitude, peak.ccLongitude)
		if G.dps and peak.section == 9:
			print emptyCell
		else:
			print weatherFormat.format(peak.longitude, peak.latitude)

		if peak.isClimbed:
			if peak.climbPhotos is None:
				print '<td>{} {}</td>'.format(peak.climbDate, peak.climbWith)
			else:
				print '<td><a href="/photos/{}/">{}</a> {}</td>'.format(
					peak.climbPhotos, peak.climbDate, peak.climbWith)
		else:
			print emptyCell

		print '</tr>'
		if peak.extraRow is not None:
			print '<tr><td colspan="' + G.colspanMinus1 + '"><ul>'
			print peak.extraRow,
			print '</ul></td></tr>'

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
			p.append(('climbed', '<a href=\\"https://nightjuggler.com/photos/{}/\\">{}</a>'.format(
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
	if G.dps and peak.section == 9:
		f('\t\t\t"noWX": true,\n')

	f('\t\t\t"elev": "')
	f(peak.elevation.replace('"', '\\"').replace('\n', '\\n'))
	f('"\n\t\t}}')

def writeJSON():
	f = sys.stdout.write
	firstPeak = True

	f('{\n')
	f('\t"id": "')
	f(G.peakIdPrefix)
	f('",\n\t"name": "')
	f(G.geojsonTitle)
	f('",\n')
	f('\t"type": "FeatureCollection",\n')
	f('\t"features": [')
	for peak in peakArray:
		if firstPeak:
			firstPeak = False
		else:
			f(',')
		writePeakJSON(f, peak)
	f(']\n')
	f('}\n')

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('inputMode', nargs='?', default='sps', choices=['dps', 'sps'])
	parser.add_argument('outputMode', nargs='?', default='html', choices=['html', 'json', 'land'])
	args = parser.parse_args()

	if args.inputMode == 'dps':
		G.setDPS()

	readHTML()
	if args.outputMode == 'html':
		writeHTML()
	elif args.outputMode == 'json':
		writeJSON()
	elif args.outputMode == 'land':
		printLandManagementAreas()
