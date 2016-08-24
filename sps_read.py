#!/usr/bin/python
import re
import sys

peakArray = []
sectionArray = []

class Peak(object):
	def __init__(self):
		self.id = ''
		self.name = ''
		self.latitude = ''
		self.longitude = ''
		self.zoom = ''
		self.elevation = ''
		self.elevationLink = None
		self.elevationTooltip = None
		self.prominence = ''
		self.prominenceLink = None
		self.grade = ''
		self.ccLatitude = ''
		self.ccLongitude = ''
		self.summitpostId = None
		self.summitpostName = None
		self.wikipediaLink = None
		self.bobBurdId = ''
		self.listsOfJohnId = ''
		self.peakbaggerId = ''
		self.climbed = None
		self.extraRow = None
		self.hasHtmlId = False
		self.isClimbed = False
		self.isEmblem = False
		self.isMtneer = False
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

landMgmtPattern = re.compile('^(?:<a href="([^"]+)">([- A-Za-z]+)</a>( HP)?)|([- A-Za-z]+)')
npsLinkPattern = re.compile('^https://www\\.nps\\.gov/([a-z]{4})/index\\.htm$')
fsLinkPattern = re.compile('^http://www\\.fs\\.usda\\.gov/([a-z]+)$')
landMgmtAreas = {}

def parseLandManagement(peak, line, lineNumber):
	landList = []
	landClass = None

	if line[:4] != '<td>' or line[-6:] != '</td>\n':
		badLine(lineNumber)
	line = line[4:-6]

	while True:
		m = landMgmtPattern.match(line)
		if m is None:
			badLine(lineNumber)

		landLink, landName, landHP, landName2 = m.groups()
		line = line[m.end():]

		if landName2 is None:
			if landName.endswith(' National Park'):
				m = npsLinkPattern.match(landLink)
				if m is None:
					badLine(lineNumber)
				landClass = 'landNPS'
			elif (landName.endswith(' National Forest') or
				landName == 'Lake Tahoe Basin Management Unit'):
				m = fsLinkPattern.match(landLink)
				if m is None:
					badLine(lineNumber)
				if landClass is None:
					landClass = 'landFS'
			else:
				badLine(lineNumber)
		else:
			landName = landName2
			if landName[-3:] == ' HP':
				landHP = landName[-3:]
				landName = landName[:-3]
			if landName.endswith(' Wilderness'):
				if landClass == 'landFS':
					landClass = 'landFSW'
				elif landClass is None:
					landClass = 'landBLMW'
			elif landName == 'Harvey Monroe Hall RNA':
				if landClass != 'landNPS':
					badLine(lineNumber)
			elif landName == 'Giant Sequoia National Monument':
				if landClass != 'landFS':
					badLine(lineNumber)
			else:
				badLine(lineNumber)

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

def printLandManagementAreas():
	for name, area in sorted(landMgmtAreas.iteritems()):
		print '{:35}{: 3}  {:22} {}'.format(name,
			area.count,
			area.highPoint.name if area.highPoint else '-',
			area.url if area.url else '-')

ngsLinkPrefix = 'http://www.ngs.noaa.gov/cgi-bin/ds_mark.prl?PidBox='
elevFromNGS = re.compile('^([0-9]{4}\\.[0-9])m \\(NAVD 88\\) NGS Data Sheet &quot;[ A-Za-z]+&quot; \\(([A-Z]{2}[0-9]{4})\\)$')
elevFromTopo = re.compile('^((?:[0-9]{4}(?:(?:\\.[0-9])|(?:-[0-9]{4}))?m)|(?:[0-9]{4,5}(?:-[0-9]{4,5})?\')) \\(NGVD 29\\) USGS (7\\.5|15)\' Quad \\(1:([0-9]{2}),([0-9]{3})\\) &quot;[\\. A-Za-z]+, CA&quot; \\(([0-9]{4})(?:/[0-9]{4})?\\)$')
contourIntervals = (10, 20, 40, 80)

def checkElevationTooltip(peak, lineNumber):
	if peak.elevationLink.startswith(ngsLinkPrefix):
		m = elevFromNGS.match(peak.elevationTooltip)
		if m is None or peak.elevationLink[len(ngsLinkPrefix):] != m.group(2):
			badLine(lineNumber)
		elevation = int(float(m.group(1)) / 0.3048 + 0.5)
		elevation = '{},{:03}'.format(*divmod(elevation, 1000))
		if elevation != peak.elevation:
			sys.exit("Elevation in tooltip doesn't match on line {0}".format(lineNumber))
		return
	if peak.elevationLink.startswith('http://ngmdb.usgs.gov/img4/ht_icons/Browse/CA/CA_'):
		m = elevFromTopo.match(peak.elevationTooltip)
		if m is None:
			badLine(lineNumber)
		elevation, quad, scale1, scale2, year = m.groups()
		scale = scale1 + scale2
		if quad == '7.5' and scale != '24000' or quad == '15' and scale != '62500':
			badLine(lineNumber)
		suffix = '_{}_{}.jpg'.format(year, scale)
		if not peak.elevationLink.endswith(suffix):
			badLine(lineNumber)
		unit = elevation[-1]
		elevation = elevation[:-1]
		if '-' in elevation:
			elevation, elevationMax = elevation.split('-')
			elevationMin = int(elevation)
			elevationMax = int(elevationMax)
			interval = elevationMax - elevationMin + 1
			if interval not in contourIntervals or elevationMin % interval != 0:
				sys.exit("Elevation range in tooltip not valid on line {0}".format(lineNumber))
			suffix = '+'
		else:
			suffix = ''
		if unit == 'm':
			elevation = int(float(elevation) / 0.3048 + 0.5)
		else:
			elevation = int(elevation)
		elevation = '{},{:03}'.format(*divmod(elevation, 1000)) + suffix
		if elevation != peak.elevation:
			sys.exit("Elevation in tooltip doesn't match on line {0}".format(lineNumber))
		return
	badLine(lineNumber)

tableLine = '<p><table id="peakTable" class="land landColumn">\n'

def readHTML():
	sectionRowPattern = re.compile('^<tr class="section"><td colspan="14">([0-9]+)\\. ([- A-Za-z]+)</td></tr>$')
	peakRowPattern = re.compile('^<tr(?: class="([A-Za-z]+(?: [A-Za-z]+)*)")?>$')
	column1Pattern = re.compile('^<td(?: id="SPS([0-9]+\\.[0-9]+)")?( rowspan="2")?>([0-9]+\\.[0-9]+)</td>$')
	column2Pattern = re.compile('^<td><a href="https://mappingsupport\\.com/p/gmap4\\.php\\?ll=([0-9]+\\.[0-9]+),-([0-9]+\\.[0-9]+)&z=([0-9]+)&t=t4">([ \'#()0-9A-Za-z]+)</a>( \\*{1,2})?</td>$')
	elevationPattern1 = re.compile('^<td>([0-9]{1,2},[0-9]{3}\\+?)</td>$')
	elevationPattern2 = re.compile('^<td><span><a href="([^"]+)">([0-9]{1,2},[0-9]{3}\\+?)</a><div class="tooltip">(.+)</div></span></td>$')
	gradePattern = re.compile('^<td>Class ([12345](?:s[2345])?)</td>$')
	prominencePattern1 = re.compile('^<td>((?:[0-9]{1,2},)?[0-9]{3})</td>$')
	prominencePattern2 = re.compile('^<td><a href="([^"]+)">((?:[0-9]{1,2},)?[0-9]{3})</a></td>$')
	summitpostPattern = re.compile('^<td><a href="http://www\\.summitpost\\.org/([-a-z]+)/([0-9]+)">SP</a></td>$')
	wikipediaPattern = re.compile('^<td><a href="https://en\\.wikipedia\\.org/wiki/([_,()A-Za-z]+)">W</a></td>$')
	bobBurdPattern = re.compile('^<td><a href="http://www\\.snwburd\\.com/dayhikes/peak/([0-9]+)">BB</a></td>$')
	listsOfJohnPattern = re.compile('^<td><a href="http://listsofjohn\\.com/peak/([0-9]+)">LoJ</a></td>$')
	peakbaggerPattern = re.compile('^<td><a href="http://peakbagger\\.com/peak.aspx\\?pid=([0-9]+)">Pb</a></td>$')
	closedContourPattern = re.compile('^<td><a href="http://www\\.closedcontour\\.com/sps/\\?zoom=7&lat=([0-9]+\\.[0-9]+)&lon=-([0-9]+\\.[0-9]+)">CC</a></td>$')
	weatherPattern = re.compile('^<td><a href="http://forecast\\.weather\\.gov/MapClick\\.php\\?lon=-([0-9]+\\.[0-9]+)&lat=([0-9]+\\.[0-9]+)">WX</a></td>$')
	climbedPattern = re.compile('^<td>(?:([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})|(<a href="/photos/[0-9A-Za-z]+/">([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})</a>))(?: (solo|(?:with .+)))?</td>$')
	lineNumber = 0

	htmlFile = open('sps.html')
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
			peak.name = m.group(4)
			suffix = m.group(5)

			if suffix is None:
				if peak.isEmblem or peak.isMtneer:
					badSuffix(lineNumber)
			elif suffix == ' *':
				if not peak.isMtneer:
					badSuffix(lineNumber)
			else:
				if not peak.isEmblem:
					badSuffix(lineNumber)

			line = htmlFile.next()
			lineNumber += 1
			parseLandManagement(peak, line, lineNumber)

			line = htmlFile.next()
			lineNumber += 1
			m = elevationPattern1.match(line)
			if m is not None:
				peak.elevation = m.group(1)
			else:
				m = elevationPattern2.match(line)
				if m is None:
					badLine(lineNumber)
				peak.elevationLink = m.group(1)
				peak.elevation = m.group(2)
				peak.elevationTooltip = m.group(3)
				checkElevationTooltip(peak, lineNumber)

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
			if line != '<td>&nbsp;</td>\n':
				m = summitpostPattern.match(line)
				if m is None:
					badLine(lineNumber)
				peak.summitpostName = m.group(1)
				peak.summitpostId = int(m.group(2))

			line = htmlFile.next()
			lineNumber += 1
			if line != '<td>&nbsp;</td>\n':
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
				badLine(lineNumber)
			peak.listsOfJohnId = m.group(1)

			line = htmlFile.next()
			lineNumber += 1
			m = peakbaggerPattern.match(line)
			if m is None:
				badLine(lineNumber)
			peak.peakbaggerId = m.group(1)

			line = htmlFile.next()
			lineNumber += 1
			m = closedContourPattern.match(line)
			if m is None:
				badLine(lineNumber)
			peak.ccLatitude = m.group(1)
			peak.ccLongitude = m.group(2)

#			compareLatLong(peak)

			line = htmlFile.next()
			lineNumber += 1
			m = weatherPattern.match(line)
			if m is None:
				badLine(lineNumber)
			wxLatitude = m.group(2)
			wxLongitude = m.group(1)

			if wxLatitude != peak.latitude or wxLongitude != peak.longitude:
				badWxLatLong(lineNumber)

			line = htmlFile.next()
			lineNumber += 1
			if line == '<td>&nbsp;</td>\n':
				if peak.isClimbed:
					badClimbed(lineNumber)
			else:
				m = climbedPattern.match(line)
				if m is None:
					badLine(lineNumber)
				if not peak.isClimbed:
					badClimbed(lineNumber)
				peak.climbed = line[4:-6]

			line = htmlFile.next()
			lineNumber += 1
			if line != '</tr>\n':
				badLine(lineNumber)
			if peak.extraRow is not None:
				line = htmlFile.next()
				lineNumber += 1
				if line != '<tr><td colspan="13"><ul>\n':
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
	if len(peakArray) != 247:
		sys.exit("Number of peaks in HTML file is not 247.")
	if len(sectionArray) != 24:
		sys.exit("Number of sections in HTML file is not 24.")

def writeHTML():
	oldColspan = ' colspan="14"'
	newColspan = ' colspan="14"'
	sectionFormat = '<tr class="section"><td colspan="14">{0}. {1}</td></tr>'
	gmap4Format = '<a href="https://mappingsupport.com/p/gmap4.php?ll={0},-{1}&z={2}&t=t4">{3}</a>'
	summitpostFormat = '<td><a href="http://www.summitpost.org/{0}/{1}">SP</a></td>'
	wikipediaFormat = '<td><a href="https://en.wikipedia.org/wiki/{0}">W</a></td>'
	bobBurdFormat = '<td><a href="http://www.snwburd.com/dayhikes/peak/{0}">BB</a></td>'
	listsOfJohnFormat = '<td><a href="http://listsofjohn.com/peak/{0}">LoJ</a></td>'
	closedContourFormat = '<td><a href="http://www.closedcontour.com/sps/?zoom=7&lat={0}&lon=-{1}">CC</a></td>'
	peakbaggerFormat = '<td><a href="http://peakbagger.com/peak.aspx?pid={0}">Pb</a></td>'
	weatherFormat = '<td><a href="http://forecast.weather.gov/MapClick.php?lon=-{0}&lat={1}">WX</a></td>'
	emptyCell = '<td>&nbsp;</td>'

	htmlFile = open('sps.html')
	for line in htmlFile:
		print line,
		if line == tableLine:
			break
	for line in htmlFile:
		if line == '<tr class="section"><td colspan="14">1. Southern Sierra</td></tr>\n':
			break
		line = line.replace(oldColspan, newColspan)
		print line,

	sectionNumber = 0
	for peak in peakArray:
		if peak.section != sectionNumber:
			sectionNumber = peak.section
			print sectionFormat.format(sectionNumber, sectionArray[sectionNumber - 1])

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

		if classNames:
			print '<tr class="{0}">'.format(' '.join(classNames))
		else:
			print '<tr>'

		attr = ''
		if peak.hasHtmlId:
			attr += ' id="SPS{0}"'.format(peak.id)
		if peak.extraRow is not None:
			attr += ' rowspan="2"'

		print '<td{0}>{1}</td>'.format(attr, peak.id)

		print '<td>{0}{1}</td>'.format(
			gmap4Format.format(peak.latitude, peak.longitude, peak.zoom, peak.name),
			suffix)

		if peak.landManagement is None:
			print emptyCell
		else:
			print '<td>{0}</td>'.format(peak.landManagement)

		if peak.elevationLink is None:
			print '<td>{0}</td>'.format(peak.elevation)
		else:
			print '<td><span><a href="{0}">{1}</a><div class="tooltip">{2}</div></span></td>'.format(
				peak.elevationLink, peak.elevation, peak.elevationTooltip)

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
		print listsOfJohnFormat.format(peak.listsOfJohnId)
		print peakbaggerFormat.format(peak.peakbaggerId)
		print closedContourFormat.format(peak.ccLatitude, peak.ccLongitude)
		print weatherFormat.format(peak.longitude, peak.latitude)

		if peak.climbed is None:
			print emptyCell
		else:
			print '<td>{0}</td>'.format(peak.climbed)

		print '</tr>'
		if peak.extraRow is not None:
			print '<tr><td colspan="13"><ul>'
			print peak.extraRow,
			print '</ul></td></tr>'

	for line in htmlFile:
		if line == '</table>\n':
			print line,
			break
	for line in htmlFile:
		print line,
	htmlFile.close()

if __name__ == '__main__':
	readHTML()
#	printLandManagementAreas()
	writeHTML()
