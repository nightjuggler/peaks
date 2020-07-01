import os
import os.path
import random
import re
import stat
import subprocess
import sys
import time
import HTMLParser

def log(message, *args, **kwargs):
	print >>sys.stderr, message.format(*args, **kwargs)

def err(*args, **kwargs):
	log(*args, **kwargs)
	sys.exit()

def int2str(n):
	return str(n) if n < 1000 else '{},{:03}'.format(*divmod(n, 1000))

class TableParserError(Exception):
	def __init__(self, message, *args, **kwargs):
		self.message = message.format(*args, **kwargs)

	def __str__(self):
		return self.message

class TableParser(HTMLParser.HTMLParser):
	def handle_starttag(self, tag, attributes):
		if self.tableDepth == 0:
			if tag == self.startTag and (
				self.startTagAttributes is None or
				self.startTagAttributes == dict(attributes)):
				self.startTag = None

			if tag == "table" and self.startTag is None:
				self.tableDepth = 1
				self.tableRows = []
				self.currentRow = None
				self.currentCol = None
		else:
			if tag == "td":
				if self.tableDepth == 1:
					if self.currentCol is not None:
						self.currentRow.append(self.currentCol)
					self.currentCol = ""
					return
			elif tag == "tr":
				if self.tableDepth == 1:
					if self.currentCol is not None:
						self.currentRow.append(self.currentCol)
						self.currentCol = None
					if self.currentRow:
						self.tableRows.append(self.currentRow)
					self.currentRow = []
					return
			elif tag == "table":
				self.tableDepth += 1

			if self.currentCol is not None:
				if tag == "a":
					attributes = [(k, v) for k, v in attributes
						if k == "href" and "/glossary" not in v]
				else:
					attributes = []
				self.currentCol += "<{}{}>".format(tag,
					"".join([" {}=\"{}\"".format(k, v) for k, v in attributes]))

	def handle_endtag(self, tag):
		if self.tableDepth == 0:
			return
		if tag == "td":
			if self.tableDepth == 1:
				if self.currentCol is not None:
					self.currentRow.append(self.currentCol)
					self.currentCol = None
				return
		elif tag == "tr":
			if self.tableDepth == 1:
				if self.currentCol is not None:
					self.currentRow.append(self.currentCol)
					self.currentCol = None
				if self.currentRow:
					self.tableRows.append(self.currentRow)
				self.currentRow = None
				return
		elif tag == "table":
			self.tableDepth -= 1
			if self.tableDepth == 0:
				if self.currentCol is not None:
					self.currentRow.append(self.currentCol)
					self.currentCol = None
				if self.currentRow:
					self.tableRows.append(self.currentRow)
				self.currentRow = None
				self.tables.append(self.tableRows)
				self.numTables -= 1
				return

		if self.currentCol is not None:
			self.currentCol += "</{}>\n".format(tag)

	def handle_startendtag(self, tag, attributes):
		if self.tableDepth > 0:
			if self.currentCol is not None:
				attributes = []
				self.currentCol += "<{}{}/>".format(tag,
					"".join([" {}=\"{}\"".format(k, v) for k, v in attributes]))

	def handle_data(self, data):
		if self.tableDepth > 0:
			if self.currentCol is not None:
				self.currentCol += data

	def __init__(self, fileName, numTables=1, startTag="table", startTagAttributes=None):
		self.reset()

		self.numTables = numTables
		self.startTag = startTag
		self.startTagAttributes = startTagAttributes
		self.tableDepth = 0
		self.tables = []

		fileObj = open(fileName)

		while self.numTables > 0:
			bytes = fileObj.read(1000)
			if bytes == "":
				break
			self.feed(bytes)

		fileObj.close()

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

	def __init__(self, fileName, upper=False, tableAttributes=None):
		self.bytes = ""
		self.rowNum = 0
		self.colNum = 0
		self.fileObj = open(fileName)

		if upper:
			self.TABLE, self.TR, self.TD, self.TH = ("TABLE", "TR", "TD", "TH")
		else:
			self.TABLE, self.TR, self.TD, self.TH = ("table", "tr", "td", "th")

		self.tag_TR = "<" + self.TR + ">"
		self.endTag_TR = "</" + self.TR + ">"
		self.endTag_TD = "</" + self.TD + ">"
		self.endTag_TH = "</" + self.TH + ">"

		while True:
			self.readUntil("<" + self.TABLE, discard=True)
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

	def readUntil(self, untilStr, errMsg="Can't find '{untilStr}'", bufSize=1000, discard=False):
		bytes = self.bytes
		bytesLen = len(bytes)
		untilLen = len(untilStr)
		start = 0

		while True:
			i = bytes.find(untilStr, start)
			if i >= 0:
				self.bytes = bytes[i + untilLen:]
				return None if discard else bytes[:i]
			newbytes = self.fileObj.read(bufSize)
			if newbytes == "":
				self.err(errMsg, untilStr=untilStr)
			start = bytesLen - untilLen + 1
			if start < 0:
				start = 0
			if discard:
				bytes = bytes[start:] + newbytes
				bytesLen += bufSize - start
				start = 0
			else:
				bytes += newbytes
				bytesLen += bufSize

	def next(self):
		if self.fileObj is None:
			raise StopIteration()

		b = self.readUntil("<", errMsg="Can't find '<' for next tag after {prevTag}")

		if b.strip() != "":
			self.err("Expected only whitespace between {prevTag} and next tag")

		b = self.readUntil(">", errMsg="Can't find '>' for next tag after {prevTag}")

		if len(b) >= 2 and b[:2] == self.TR and (len(b) == 2 or b[2] == " "):
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
			columns.append(col.replace("&#039;", ""))

		self.colNum = 0
		return columns

class RE(object):
	numLT1k = re.compile('^[1-9][0-9]{0,2}$')
	numGE1k = re.compile('^[1-9][0-9]?,[0-9]{3}$')
	numLT10k = re.compile('^[1-9][0-9]{0,3}$')
	numGE10k = re.compile('^[1-9][0-9],[0-9]{3}$')
	htmlTag = re.compile('<[^>]*>')
	whitespace = re.compile('\\s{2,}')
	nonAlphaNum = re.compile('[^-0-9A-Za-z]')

def toFeet(meters):
	return int(meters / 0.3048 + 0.5)

def toFeetRoundDown(meters):
	return int(meters / 0.3048)

def toMeters(feet):
	return int(feet * 0.3048 + 0.5)

def str2IntLoJ(s, description, peakName):
	if RE.numLT1k.match(s):
		return int(s)
	if RE.numGE1k.match(s):
		return int(s[:-4]) * 1000 + int(s[-3:])
	if s == "0":
		return 0

	err("{} '{}' ({}) doesn't match expected pattern", description, s, peakName)

def str2IntPb(s, description, peak):
	if RE.numLT10k.match(s):
		return int(s)
	if RE.numGE10k.match(s):
		return int(s[:-4]) * 1000 + int(s[-3:])
	if s == "0":
		return 0

	err("{} {} doesn't match expected pattern: {}", peak.fmtIdName, description, s)

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
		self.maxFeet = maxFeet
		self.isRange = minFeet < maxFeet

	def __str__(self):
		return int2str(self.feet) + ("+" if self.isRange else "")

	def __eq__(self, other):
		return self.feet == other.feet and self.maxFeet == other.maxFeet

	def __ne__(self, other):
		return self.feet != other.feet or self.maxFeet != other.maxFeet

	def diff(self, e):
		return "({}){}".format(self.feet - e.elevationFeet,
			"" if self.isRange == e.isRange else " and range mismatch")

	html = __str__

class SimpleElevation(object):
	def __init__(self, feet):
		self.feet = feet

	def __str__(self):
		return int2str(self.feet)

	def __eq__(self, other):
		return self.feet == other.feet

	def __ne__(self, other):
		return self.feet != other.feet

	def diff(self, e):
		return "({})".format(self.feet - e.elevationFeet)

	html = __str__

class ElevationLoJ(SimpleElevation):
	classId = "LoJ"

class ElevationVR(SimpleElevation):
	classId = "VR"

countryNameMap = {
	"Mexico":         "MX",
	"United States":  "US",
}
stateNameMap = {
	"Baja California":      "MX-BCN",
	"Sonora":               "MX-SON",

	"Arizona":        "AZ",
	"California":     "CA",
	"Colorado":       "CO",
	"Idaho":          "ID",
	"Montana":        "MT",
	"Nevada":         "NV",
	"New Mexico":     "NM",
	"Oregon":         "OR",
	"Utah":           "UT",
	"Washington":     "WA",
	"Wyoming":        "WY",
}
class LandMgmtArea(object):
	npsWilderness = {
		"Death Valley":         "National Park",
		"Joshua Tree":          "National Park",
		"Lassen Volcanic":      "National Park",
		"Mojave":               "National Preserve",
		"Organ Pipe Cactus":    "NM",
		"Pinnacles":            "National Park",
		"Sequoia-Kings Canyon": ("Kings Canyon National Park", "Sequoia National Park"),
		"Yosemite":             "National Park",
		"Zion":                 "National Park",
	}

	def __init__(self, name):
		self.count = 0
		self.name = name
		self.highPoint = None
		self.nps = None

		if name.endswith(" Wilderness"):
			park = self.npsWilderness.get(name[:-11])
			if park is not None:
				self.nps = name[:-11] + " " + park if isinstance(park, str) else park

	@classmethod
	def add(self, name, peak, isHighPoint=False):
		area = self.areaLookup.get(name)
		if area is None:
			self.areaLookup[name] = area = self(name)

		area.count += 1
		if isHighPoint:
			hp = area.highPoint
			if hp is None:
				area.highPoint = peak
			elif peak.elevation.feet > hp.elevation.feet:
				print "{} Overriding HP for {} (> {})".format(peak.fmtIdName, name, hp.name)
				area.highPoint = peak
			elif peak.elevation.feet < hp.elevation.feet:
				print "{} Ignoring HP for {} (< {})".format(peak.fmtIdName, name, hp.name)
			else:
				print "{} Ignoring HP for {} (= {})".format(peak.fmtIdName, name, hp.name)

		return area

	@classmethod
	def addAll(self, peak):
		landAreas = []
		highPointSuffix = self.highPointSuffix
		highPointSuffixLen = len(highPointSuffix)

		for name in peak.landManagement:
			isHighPoint = name.endswith(highPointSuffix)
			if isHighPoint:
				name = name[:-highPointSuffixLen]
			name = self.normalizeName(name, peak)
			area = self.add(name, peak, isHighPoint)
			if area in landAreas:
				print "{} Duplicate land \"{}\"".format(peak.fmtIdName, name)
			elif area.nps:
				landAreas.insert(0, area)
			else:
				landAreas.append(area)

		peak.landManagement = landAreas

class LandMgmtAreaPb(LandMgmtArea):
	highPointSuffix = " (Highest Point)"

	areaLookup = {}
	nameLookup = {
	"Antelope Valley California Poppy Reserve "
	"State Natural Reserve":                        "Antelope Valley California Poppy Reserve",
	"Desert National Wildlife Range":               "Desert National Wildlife Refuge",
	"Giant Sequoia NM":                             "Giant Sequoia National Monument",
	"Hart Mountain National Antelope Refuge":       "Hart Mountain NAR",
	"Hawthorne Army Ammunition Depot":              "Hawthorne Army Depot",
	"Indian Peak State Game Management Area":       "Indian Peaks WMA",
	"Lake Mead National Recreation Area":           "Lake Mead NRA",
	"Lake Tahoe State Park":                        "Lake Tahoe Nevada State Park",
	"Mount Saint Helens National Volcanic Monument":"Mount St. Helens National Volcanic Monument",
	"Mount Saint Helens NVM":                       "Mount St. Helens National Volcanic Monument",
	"Organ Pipe Cactus National Monument":          "Organ Pipe Cactus NM",
	"Providence Mountains State Recreation Area":   "Providence Mountains SRA",
	"Red Rock Canyon National Conservation Area":   "Red Rock Canyon NCA",
	"Steens Mountain National Recreation Lands":    "Steens Mountain CMPA",
	}

	@classmethod
	def normalizeName(self, name, peak):
		if name.endswith(" Wilderness Area"):
			name = name[:-5]
		return self.nameLookup.get(name, name)

class LandMgmtAreaLoJ(LandMgmtArea):
	highPointSuffix = " Highpoint"

	areaLookup = {}
	nameLookup = {
	"Arapaho National Forest":                      "Arapaho and Roosevelt National Forest",
	"Challis National Forest":                      "Salmon-Challis National Forest",
	"Humboldt National Forest":                     "Humboldt-Toiyabe National Forest",
	"Palen/McCoy Wilderness":                       "Palen-McCoy Wilderness",
	"Pike National Forest":                         "Pike and San Isabel National Forest",
	"Shasta National Forest":                       "Shasta-Trinity National Forest",
	"Toiyabe National Forest":                      "Humboldt-Toiyabe National Forest",
	"Trinity National Forest":                      "Shasta-Trinity National Forest",
	"Wasatch National Forest":                      "Uinta-Wasatch-Cache National Forest",
	"Winema National Forest":                       "Fremont-Winema National Forest",
	}

	@classmethod
	def normalizeName(self, name, peak):
		if not name.endswith((" Wilderness", " National Forest", " National Park")):
			err("{} Unexpected land \"{}\"", peak.fmtIdName, name)
		return self.nameLookup.get(name, name)

# Doesn't work with https URLs on my system:
# import urllib
# filename, headers = urllib.urlretrieve(url, filename)

def formatTime(timestamp):
	ymdhms = time.localtime(timestamp)[0:6]
	return "{}-{:02}-{:02} {:02}:{:02}:{:02}".format(*ymdhms)

def loadURLs(loadLists):
	random.seed()
	for loadList in loadLists:
		random.shuffle(loadList)

	listLengths = "/".join([str(len(loadList)) for loadList in loadLists])

	mode444 = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
	mode644 = stat.S_IWUSR | mode444

	for i, loadList in enumerate(map(lambda *a: filter(None, a), *loadLists)):
		if i != 0:
			sleepTime = int(random.random() * 7 + 7.5)
			log("{}/{} Sleeping for {} seconds", i, listLengths, sleepTime)
			time.sleep(sleepTime)

		for url, filename in loadList:
			if os.path.exists(filename):
				os.chmod(filename, mode644)

			command = ["/usr/local/opt/curl/bin/curl", "-o", filename, url]
			print " ".join(command)

			rc = subprocess.call(command)
			if rc != 0:
				print "Exit code", rc
				return

			os.chmod(filename, mode444)

def getLoadLists(pl):
	loadLists = []

	for peakClass in (PeakLoJ, PeakPb):
		loadList = []
		loadLists.append(loadList)

		for peak in peakClass.getPeaks(pl.id):
			filename = peak.getPeakFileName(peak.id)
			if not os.path.exists(filename):
				loadList.append((peak.getPeakURL(peak.id), filename))
	return loadLists

def getLoadListsFromTable(pl):
	loadLists = []
	cutoffTime = time.time() - 180 * 24 * 60 * 60
	cutoffTimeStr = formatTime(cutoffTime)

	for peakClass in (PeakLoJ, PeakPb):
		loadList = []
		loadLists.append(loadList)

		for section in pl.sections:
			for peak in section.peaks:
				peakId = getattr(peak, peakClass.classAttrId, None)
				if peakId is None or peakId[0] == "-":
					continue
				filename = peakClass.getPeakFileName(peakId)
				if os.path.exists(filename):
					modTime = os.stat(filename).st_mtime
					if modTime > cutoffTime:
						continue
					print "{:5} {:24} {} Last mod ({}) > 180 days ago ({})".format(
						peak.id,
						peak.name.replace('&quot;', '"'),
						peakClass.classId,
						formatTime(modTime),
						cutoffTimeStr)

				loadList.append((peakClass.getPeakURL(peakId), filename))
	return loadLists

class TablePeak(object):
	@classmethod
	def getPeaks(self, peakListId, fileNameSuffix=""):
		fileName = "extract/data/{}/{}{}.html".format(
			peakListId.lower(), self.classId.lower(), fileNameSuffix)

		if not os.path.exists(fileName):
			return []

		table = TableReader(fileName, **getattr(self, "tableReaderArgs", {}))
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
			peak.postProcess(peakListId)
			peaks.append(peak)

		assert len(peaks) == self.numPeaks[peakListId]
		return peaks

	@classmethod
	def getAttr(self, attr, peak):
		peak2 = getattr(peak, self.classAttrPeak, None)
		if peak2 is None:
			return None
		return getattr(peak2, attr, None)

	def checkLand(self, peak):
		land1 = peak.landManagement
		land1 = {} if land1 is None else {area.name: area for area in land1}

		def getArea(name):
			return land1.get(name) if self.expectLandNPS(name) else land1.pop(name, None)

		def getAreaNPS(nps):
			if isinstance(nps, str):
				return getArea(nps)
			for name in nps:
				area = getArea(name)
				if area:
					return area
			return None

		for area2 in self.landManagement:
			area1 = getAreaNPS(area2.nps) if area2.nps else land1.pop(area2.name, None)
			if area1 is None:
				print "{} '{}' not in table".format(peak.fmtIdName, area2.name)
			elif area1.isHighPoint(peak) != (area2.highPoint is self):
				print "{} High Point mismatch ({})".format(peak.fmtIdName, area2.name)

		for name, area in sorted(land1.iteritems()):
			if self.expectLand(area):
				print "{} '{}' not on {}".format(peak.fmtIdName, name, self.classTitle)

	def checkDataSheet(self, peak):
		dataSheets = peak.getDataSheets()
		if dataSheets is None:
			return

		ds = self.dataSheet
		if ds is None:
			if dataSheets:
				print self.fmtIdName, "Datasheet not on", self.classTitle
		else:
			if ds not in dataSheets:
				print self.fmtIdName, "Datasheet", ds, "not in table"

class PeakPb(TablePeak):
	classId = 'Pb'
	classTitle = 'Peakbagger'
	classAttrId = 'peakbaggerId'
	classAttrPeak = 'peakbaggerPeak'

	@classmethod
	def getPeakFileName(self, peakId):
		return "extract/data/pb/{}/p{}.html".format(peakId[0], peakId)
	@classmethod
	def getPeakURL(self, peakId):
		return "https://peakbagger.com/peak.aspx?pid={}".format(peakId)
	@classmethod
	def expectLand(self, area):
		return not (area.name.startswith("BLM ") or area.landClass in ("landCity", "landEBRPD", "landMROSD"))
	@classmethod
	def expectLandNPS(self, name):
		return True

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
			re.compile('^([1-9]|[0-9]{2})(?:\\.| -) ([- A-Za-z]+(?:\\.? [1-9][0-9]*)?)$'),
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
			re.compile('^((?:[1-9][0-9],[0-9]{3})|(?:[1-9][0-9]{0,3})|0|)$'),
			('prominence',)
		),
		'Ascents': (
			re.compile('^[1-9][0-9]*$'),
			None
		),
	}
	columnMap['Elev-Ft(Opt)'] = columnMap['Elev-Ft']
	columnMap['Prom-Ft(Opt)'] = columnMap['Prom-Ft']
	numPeaks = {
		'DPS':   96,
		'GBP':  115,
		'HPS':  281,
		'NPC':   73,
		'OGUL':  63,
		'SPS':  247,
	}
	nameMap = {
	# Desert Peaks Section:
		('Chuckwalla Peak', 3446):              'Bunch Benchmark',
		('Eagle Mountain', 5350):               'Eagle Mountains HP',
		('Granite Mountain', 6762):             'Granite Peak',
		('Granite Mountain', 4331):             'Granite Benchmark',
		('Old Woman Mountain', 5325):           'Old Woman Mountains HP',
		('Spectre Peak', 4482):                 'Spectre Point',
		('Stepladder Mountains', 2940):         'Stepladder Mountains HP',
		('Superstition Benchmark', 5057):       'Superstition Mountain',
	# Hundred Peaks Section:
		('Black Mountain', 7438):               'Black Mountain #5',
		('Cannell Point', 8314):                'Cannel Point',
		('Granite Mountain', 5633):             'Granite Mountain #2',
	# Great Basin Peaks / Nevada Peaks Club:
		('Baker Peak', 12305):                  'Baker Peak East',
		('Baker Peak-West Summit', 12298):      'Baker Peak',
		('Duffer Peak-North Peak', 9400):       'Duffer Peak',
		('Duffer Peak', 9428):                  'Duffer Peak South',
		('Granite Peak', 8980):                 'Granite Peak (Washoe)',
		('Granite Peak', 9732):                 'Granite Peak (Humboldt)',
		('Granite Peak', 11218):                'Granite Peak (Snake Range)',
		('Morey Peak-North Peak', 10240):       'Morey Peak North',
		('Mount Grant', 11280):                 'Mount Grant (West)',
		('Mount Jefferson-North Summit', 11814):'Mount Jefferson North',
		('Petersen Mountains HP', 7841):        'Petersen Mountain',
	# Sierra Peaks Section:
		('Adams Peak-West Peak', 8197):         'Adams Peak',
		('Devils Crags', 12400):                'Devil\'s Crag #1',
		('Mount Morgan', 13748):                'Mount Morgan (South)',
		('Mount Morgan', 12992):                'Mount Morgan (North)',
		('Mount Stanford', 13973):              'Mount Stanford (South)',
		('Mount Stanford', 12838):              'Mount Stanford (North)',
		('Pilot Knob', 6200):                   'Pilot Knob (South)',
		('Pilot Knob', 12245):                  'Pilot Knob (North)',
		('Pyramid Peak', 12779):                'Pyramid Peak (South)',
		('Pyramid Peak', 9983):                 'Pyramid Peak (North)',
		('Sawtooth Peak', 8000):                'Sawtooth Peak (South)',
		('Sawtooth Peak', 12343):               'Sawtooth Peak (North)',
		('Sierra Buttes Lookout', 8590):        'Sierra Buttes',
	# Tahoe Ogul Peaks:
		('Silver Peak', 8930):                     'Silver Peak (Desolation)',
		('Silver Peak - Northeast Summit', 10800): 'Silver Peak Northeast',
		('Silver Peak-Southwest Summit', 10772):   'Silver Peak Southwest',
	# Other Sierra Peaks:
		("Gambler's Special", 12927):           'Gamblers Special Peak',
		('Maggies Peaks-South Summit', 8699):   'Maggies Peaks South',
		('Mount Lamarck-North Peak', 13464):    'Northwest Lamarck',
		('Mount Lola-North Ridge Peak', 8844):  'Mount Lola North',
		('Peak 3560', 11680):                   'Peak 3560m+',
		('Peak 9980', 9980):                    'Sirretta Peak North',
		('Peak 10570', 10570):                  'Peak 3222m',
		('Pk 10597', 10597):                    'Peak 3230m',
		('Shepherd Crest', 12040):              'Shepherd Crest East',
		('Snow Valley Peak-East Peak', 9170):   'Snow Valley Peak East',
		('The Sisters', 10153):                 'The Sisters East',
		('Volcanic Ridge', 11501):              'Volcanic Ridge West',
		('White Mountain', 12057):              'White Mountain (Tioga Pass)',
		('White Mountain', 11398):              'White Mountain (Sonora Pass)',
	# Other Desert Peaks:
		('Antelope Buttes HP', 3040):           'Antelope Buttes',
		('Ruby Dome-East Peak', 11360):         'Ruby Pyramid',
	# Other California Peaks:
		('Maguire Peak', 1688):                 'Maguire Peaks West',
		('Maguire Peaks-East Summit', 1640):    'Maguire Peaks East',
		('Monument Peak North', 2600):          'Monument Peak',
		('Mount Saint Helena-East Peak', 4200): 'Mount Saint Helena East',
		('Mount Saint Helena-South Peak', 4003):'Mount Saint Helena South',
		('Mount Saint Helena-Southeast Peak', 4023): 'Mount Saint Helena Southeast',
		('Mount Tamalpais-East Peak', 2572):    'Mount Tamalpais East Peak',
		('Mount Tamalpais-Middle Peak', 2518):  'Mount Tamalpais Middle Peak',
		('Mount Tamalpais-West Peak', 2576):    'Mount Tamalpais West Peak',
		('Peak 1380', 1380):                    'Peak 1390',
		('Snow Mountain', 7056):                'Snow Mountain East',
	# Other Western Peaks:
		('Mount Evans-West Peak', 14256):       'West Evans',
		('Mount Saint Helens', 8333):           'Mount St. Helens',
		('Trail Canyon Saddle Peak', 11325):    'Trail Canyon Peak',
	}
	@classmethod
	def normalizeName(self, name, elevation=None):
		if name.endswith(' High Point'):
			name = name[:-10] + 'HP'
		return self.nameMap.get((name, elevation), name)

	elevationMap = {
	# Pb DPS Elevation Adjustments:
	#
	# - Needle Peak
	#   See LoJ DPS Elevation Adjustments, except that a possible reason for Pb's 5,801'
	#   is that the 1768.8m spot elevation from the 7.5' topo was rounded down to 1768m.
	#   1768m = 5800.525' which is 5,801' when rounded to the nearest foot.
	#
	# - Stepladder Mountains HP
	#   See LoJ DPS Elevation Adjustments. Pb seems to have done the same as LoJ, except
	#   that instead of rounding down (2939.6' => 2939'), Pb rounded to the nearest foot
	#   (2939.6' => 2940')

		('Needle Peak', 5801, 'min'): 5804, # 1769m
		('Needle Peak', 5801, 'max'): 5804, # 1769m
		('Stepladder Mountains HP', 2940, 'min'): 2920, # 890m
		('Stepladder Mountains HP', 2940, 'max'): 2953, # 900m

	# Pb SPS Elevation Adjustments:
	#
	# - Basin Mountain
	#   See LoJ SPS Elevation Adjustments. Pb did the same.
	#
	# - Highland Peak
	#   All of the Ebbetts Pass 7.5' topos show a spot elevation of 10,935'
	#   All of the Markleeville 15' topos show a spot elevation of 10,934'
	#   The 1985 Smith Valley 1:100,000 topo doesn't show a spot elevation.
	#   The 1889, 1891, and 1893 Markleeville 1:125,000 maps show a spot elevation of 10,955'
	#   All of the Walker Lake 1:250,000 maps show spot elevations of either 10,935' or 10,955'
	#   How does Pb get 10,936'?
	#
	# - Kearsarge Peak
	#   The 1994 Kearsarge Peak 7.5' topo doesn't show a spot elevation.
	#   The highest contour is at 3840m, and the contour interval is 20m.
	#   The 1985 and 1992 Kearsarge Peak 7.5' topos show a spot elevation of 3846m = 12,618'
	#   The Mt. Pinchot 15' topos show a spot elevation of 12,598'
	#   The 1978 Mount Whitney 1:100,000 topo shows a spot elevation of 3840m = 12,598'
	#   The 1937 Mt. Whitney 1:125,000 topos show a spot elevation of 12,650'
	#   The 1:250,000 topos show a spot elevation of 12,650'
	#   How does Pb get 12,615'?
	#
	# - Kern Peak
	#   None of the maps on topoView (1:24,000, 1:62,500, 1:100k, 1:125k, and 1:250k) show a
	#   spot elevation of 11,480'. It's likely that Pb just didn't set the optimistic elevation.
	#   The highest contour on the 7.5' topos is at 11,480', and the contour interval is 40'.
	#
	# - Mount Carillon
	#   Pb's elevation of 13,553' implies that there's a map showing a spot elevation of either
	#   13,553' or 4131m, but none of the maps currently on topoView show this.
	#   The 1985, 1993, and 1994 editions of the Mount Whitney 7.5' topo don't show a spot elevation
	#   for Mount Carillon. The highest contour is at 4120m, and the interval is 20m.
	#   All of the Mount Whitney 15' topos (3x 1956, 2x 1967) show a spot elevation of 13,552'
	#   The 1978/1990 Mount Whitney 1:100,000 topo doesn't show a spot elevation.
	#   The highest contour is at 4100m, and the contour interval is 50m.
	#   The 1907, 1919, and 1937 Mt. Whitney 1:125,000 topos show a spot elevation of 13,571'
	#   None of the Fresno 1:250,000 maps show a spot elevation, nor do they label Mount Carillon.
	#
	# - Mount Jordan
	#   Very similar to Mount Carillon:
	#   Pb's elevation of 13,343' implies that there's a map showing a spot elevation of either
	#   13,343' or 4067m, but none of the maps currently on topoView show this.
	#   The Mt. Brewer 7.5' quads don't show a spot elevation.
	#   The highest contour is at 4060m, and the interval is 20m.
	#   The Mount Whitney 15' quads show a spot elevation of 13,344'
	#   The 1978/1990 Mount Whitney 1:100,000 topo doesn't show a spot elevation.
	#   The 1907, 1919, and 1937 Mt. Whitney 1:125,000 maps show a spot elevation of 13,316'
	#   None of the Fresno 1:250,000 maps show a spot elevation, nor do they label Mount Jordan.
	#
	# - Mount Williamson
	#   Pb's elevation of 14,373' implies that there's a map showing a spot elevation of either
	#   14,373' or 4381m, but none of the maps currently on topoView show this.
	#   The 1984, 1993, and 1994 Mt. Williamson 7.5' topos don't show a spot elevation.
	#   The highest contour is at 4380m, and the interval is 20m.
	#   All of the Mount Whitney 15' topos (3x 1956, 2x 1967) show a spot elevation of 14,375'
	#   The 1978/1990 Mount Whitney 1:100,000 topo shows a spot elevation of 4382m = 14376.6'
	#   The 1907, 1919, and 1937 Mt. Whitney 1:125,000 topos show a spot elevation of 14,384'
	#   The 1948-1960 Fresno 1:250,000 maps show a spot elevation of 14,384'
	#   The 1962 Fresno 1:250,000 maps show a spot elevation of 14,375'
	#
	# - Sierra Buttes
	#   The Sierra City 7.5' topos show a spot elevation of 8,591'
	#   The Sierra City 15' topos show a spot elevation of 8,587'
	#   The 1979/1990 Portola 1:100,000 topo doesn't show a spot elevation.
	#   The highest contour is at 2550m, and the interval is 50m.
	#   The 1891-1897 Downieville 1:125,000 maps show a spot elevation of 8,615'
	#   The 1958 Chico 1:250,000 maps show a spot elevation of 8,587'
	#   So perhaps Pb got 8,590' from NGS Data Sheet "Sierra" (KS1520). However, that's the
	#   NAVD 88 elevation which "was computed by applying the VERTCON shift value to the
	#   NGVD 29 height" which is given as 8,587'. Since the vertical datum for primary
	#   elevations on Pb is NGVD 29, it seems that either 8,591' or 8,587' should be used.

		('Basin Mountain', 13200, 'max'): 13181,
		('Highland Peak', 10936, 'min'): 10935,
		('Highland Peak', 10936, 'max'): 10935,
		('Kearsarge Peak', 12615, 'min'): 12618,
		('Kearsarge Peak', 12615, 'max'): 12618,
		('Kern Peak', 11480, 'max'): 11520,
		('Mount Carillon', 13553, 'min'): 13552,
		('Mount Carillon', 13553, 'max'): 13552,
		('Mount Jordan', 13343, 'min'): 13344,
		('Mount Jordan', 13343, 'max'): 13344,
		('Mount Williamson', 14373, 'min'): 14375,
		('Mount Williamson', 14373, 'max'): 14375,
		('Sierra Buttes', 8590, 'min'): 8591,
		('Sierra Buttes', 8590, 'max'): 8591,

	# Pb HPS Elevation Adjustments:

		('San Jacinto Peak', 10839, 'min'): 10804,
		('San Jacinto Peak', 10839, 'max'): 10804,

	# Pb Elevation Adjustments for Great Basin Peaks / Nevada Peaks Club
	#
	# - Bull Mountain
	#   "Field observations by visitors to this mountain indicate that the main point shown here is
	#    about 8 or 9 feet higher than the nearby Dunn Benchmark. So the elevation of the large contour
	#    to the east of the benchmark is shown as 9934 feet. The terrain is very gentle and most
	#    peakbaggers will visit both spots anyway."
	#   [https://peakbagger.com/peak.aspx?pid=3440]
	#
	# - Hays Canyon Peak
	#   "Field observations show that the highest point on this flat-topped mountain is near the
	#    7916-foot benchmark. The two tiny 7920-foot contours north of the benchmark are about 10 feet
	#    lower than the benchmark knoll. These contour are likely a map error, but the benchmark
	#    elevation might be too low, too. Here, the elevation is given as 7920 feet, assuming the
	#    benchmark is 4 feet below the high point."
	#   [https://peakbagger.com/peak.aspx?pid=3304]
	#
	# - Green Mountain (NPC)
	#   The last 0 in 10680 was likely misread as an 8 (a contour line bisects it on the 7.5' topo).

		('Bull Mountain', 9934, 'min'): 9920,
		('Bull Mountain', 9934, 'max'): 9960,
		('Duffer Peak', 9400, 'min'): 9397,
		('Duffer Peak', 9440, 'max'): 9397,
		('Granite Peak (Washoe)', 8980, 'min'): 8960,
		('Granite Peak (Washoe)', 8980, 'max'): 9000,
		('Green Mountain', 10688, 'min'): 10680,
		('Green Mountain', 10688, 'max'): 10680,
		('Hays Canyon Peak', 7920, 'min'): 7916,
		('Hays Canyon Peak', 7920, 'max'): 7916,
		('Morey Peak North', 10248, 'min'): 10240,
		('Morey Peak North', 10248, 'max'): 10280,

	# Pb Elevation Adjustments for Other Desert Peaks:

		('Kelso Peak', 4777, 'min'): 4757, # 1450m
		('Kelso Peak', 4777, 'max'): 4790, # 1460m

	# Pb Elevation Adjustments for Other Sierra Peaks:
	#
	# - Mount Starr
	#   "Field observations by climbers have shown that the highest point on Mount Starr is south
	#    of the point marked 12,835' on the topographic map. A point on the ridge to the south is
	#    approximately five feet higher and thus the summit of this peak."
	#   [https://peakbagger.com/peak.aspx?pid=2660]

		('Duck Lake Peak', 12051, 'min'): 12077, # 3681m
		('Duck Lake Peak', 12051, 'max'): 12077, # 3681m
		('Grouse Mountain', 8123, 'max'): 8083,
		('Lost World Peak', 11353, 'min'): 11447, # 3489m
		('Lost World Peak', 11353, 'max'): 11447, # 3489m
		('Shepherd Crest East', 12040, 'min'): 12000,
		('Shepherd Crest East', 12080, 'max'): 12040,
		('Mount Starr', 12840, 'min'): 12835,
		('Mount Starr', 12840, 'max'): 12835,
		('Peak 3222m', 10570, 'min'): 10571, # 3222m
		('Peak 3222m', 10570, 'max'): 10571, # 3222m
		('Peak 3560m+', 11680, 'max'): 11745, # 3580m

	# Pb Elevation Adjustments for Other California Peaks:

		('Hawk Hill', 920, 'min'): 900,
		('Hawk Hill', 920, 'max'): 925,
		('Islay Hill', 780, 'min'): 760,
		('Islay Hill', 820, 'max'): 800,
		('Mine Hill', 1728, 'min'): 1720,
		('Mine Hill', 1728, 'max'): 1760,
		('Mount Tamalpais East Peak', 2572, 'min'): 2571,
		('Mount Tamalpais East Peak', 2574, 'max'): 2571,
		('Mount Tamalpais Middle Peak', 2518, 'min'): 2480,
		('Mount Tamalpais Middle Peak', 2520, 'max'): 2520,
		('Mount Tamalpais West Peak', 2576, 'min'): 2560,
		('Mount Tamalpais West Peak', 2578, 'max'): 2600,
		('Peak 1390', 1380, 'min'): 1390,
		('Peak 1390', 1400, 'max'): 1390,
		('Point Reyes Hill', 1342, 'min'): 1336,
		('Point Reyes Hill', 1344, 'max'): 1336,
		('Post Summit', 3456, 'min'): 3455,
		('Post Summit', 3456, 'max'): 3455,
		('Slacker Hill', 937, 'min'): 925,
		('Slacker Hill', 937, 'max'): 950,
		('White Hill', 1434, 'min'): 1430,
		('White Hill', 1434, 'max'): 1430,
	}
	prominenceMap = {
	# --------------------------
	# Pb Prominence Adjustments
	# --------------------------
	#
	# - East Ord Mountain (DPS)
	#   The contour interval at the saddle is 40', not 20'. So the saddle range is 4680'-4640', not
	#   4680'-4660'. Thus the maximum prominence is raised by 20'. LoJ also uses 4660' for the saddle.
	#
	# - Signal Peak (DPS)
	#   The minimum saddle elevation can be raised from 1380' to 1390', thus reducing the maximum
	#   prominence by 10' to 3487'. The main contour interval on the 7.5' quad (Lone Mountain, AZ)
	#   is 20 feet, giving a saddle range of 1380'-1400', but there's a supplementary contour on
	#   both downward-sloping sides (east and west) of the saddle at 1390'. LoJ also uses 1395' for
	#   the average saddle elevation.

		('Billy Goat Peak',               896, 'min'):   879, # 1748m - 1480m           OWP
		('Billy Goat Peak',               896, 'max'):   912, # 1748m - 1470m           OWP
		('Duffer Peak',                    40, 'min'):     0, #                         GBP
		('Duffer Peak',                   120, 'max'):    80, #                         GBP
		('East Ord Mountain',            1508, 'max'):  1528, #                         DPS
		('Gamblers Special Peak',         263, 'min'):   262, # 80m                     OSP
		('Gamblers Special Peak',         393, 'max'):   394, # 120m                    OSP
		('Peak 3222m',                    431, 'min'):   399, # 10570' - 3100m          OSP
		('Peak 3222m',                    431, 'max'):   465, # 10570' - 3080m          OSP
		('Peak 3230m',                    394, 'min'):   361, # 3230m - 3120m           OSP
		('Peak 3230m',                    394, 'max'):   427, # 3230m - 3100m           OSP
		('Pilot Knob (South)',            720, 'min'):   680, #                         SPS
		('Pilot Knob (South)',            800, 'max'):   760, #                         SPS
		('Ring Mountain',                 402, 'min'):   442, # 602'-160'               OCAP
		('Ring Mountain',                 442, 'max'):   482, # 602'-120'               OCAP
		('Signal Peak',                  3497, 'max'):  3487, #                         DPS
		('Slacker Hill',                  274, 'min'):   262, # 937' - 675'             OCAP
		('Slacker Hill',                  274, 'max'):   287, # 937' - 650'             OCAP
		('Two Teats',                     132, 'min'):   131, # 40m                     OSP
		('White Hill',                    308, 'min'):   314, # 1434' - 1120'           OCAP
		('White Hill',                    310, 'max'):   354, # 1434' - 1080'           OCAP
	}
	def postProcess(self, peakListId=None):
		def str2int(s):
			return int(s) if len(s) <= 4 else int(s[:-4]) * 1000 + int(s[-3:])

		self.elevation = str2int(self.elevation)
		self.prominence = str2int(self.prominence) if len(self.prominence) > 0 else None

	def postProcess2(self, maxPeak):
		self.name = self.normalizeName(self.name, self.elevation)

		elevMin = self.elevation
		elevMin = self.elevationMap.get((self.name, elevMin, 'min'), elevMin)
		elevMax = maxPeak.elevation
		elevMax = self.elevationMap.get((self.name, elevMax, 'max'), elevMax)

		promMin = self.prominence
		promMin = self.prominenceMap.get((self.name, promMin, 'min'), promMin)
		promMax = maxPeak.prominence
		promMax = self.prominenceMap.get((self.name, promMax, 'max'), promMax)

		if elevMin > elevMax:
			err("Pb: Max elevation ({}) must be >= min elevation ({}) for {}",
				elevMax, elevMin, self.name)
		if promMin > promMax:
			err("Pb: Max prominence ({}) must be >= min prominence ({}) for {}",
				promMax, promMin, self.name)

		promMin += elevMin - self.elevation
		promMax += elevMax - maxPeak.elevation

		self.elevation = ElevationPb(elevMin, elevMax)
		self.prominence = (promMin, promMax)

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

			peak.postProcess2(maxPeak)

		return minPeaks

	landPattern = re.compile(
		"^(?:Land: ([- '()./A-Za-z]+))?(?:<br/>)?"
		"(?:Wilderness/Special Area: ([- ()/A-Za-z]+))?$"
	)
	def readLandManagement(self, land):
		land = land.replace("\xE2\x80\x99", "'") # Tohono O'odham Nation
		land = land.replace("Palen/McCoy", "Palen-McCoy")
		m = self.landPattern.match(land)
		if m is None:
			err("{} Land doesn't match pattern:\n{}", self.fmtIdName, land)
		land, wilderness = m.groups()
		if land is not None:
			self.landManagement.extend(land.split("/"))
		if wilderness is not None:
			self.landManagement.extend(wilderness.split("/"))

	elevationPattern1 = re.compile(
		"^<h2>Elevation: ([1-9][0-9]{2,3}|[1-9][0-9],[0-9]{3})(\\+?) feet, ([1-9][0-9]{2,3})\\2 meters</h2>$"
	)
	elevationPattern2 = re.compile(
		"^<h2>Elevation: ([1-9][0-9]{2,3})(\\+?) meters, ([1-9][0-9]{2,3}|[1-9][0-9],[0-9]{3})\\2 feet</h2>$"
	)
	def readElevation(self, maxPeak, html):
		m = self.elevationPattern1.match(html)
		if m is None:
			m = self.elevationPattern2.match(html)
			if m is None:
				err("{} Elevation doesn't match pattern:\n{}", self.fmtIdName, html)
			meters, isRange, feet = m.groups()
		else:
			feet, isRange, meters = m.groups()

		isRange = (isRange == "+")
		feet = str2IntPb(feet, "Elevation in feet", self)
		meters = str2IntPb(meters, "Elevation in meters", self)
		if toMeters(feet) != meters:
			err("{} Elevation in feet ({}) != {} meters", self.fmtIdName, feet, meters)

		self.elevation = feet
		maxPeak.elevation = None if isRange else feet

	elevationRangePattern = re.compile(
		"^Elevation range:([,0-9]+) - ([,0-9]+) (ft|m)<br/>"
	)
	def readElevationInfo(self, maxPeak, html):
		m = self.elevationRangePattern.match(html)
		if m is None:
			print self.fmtIdName, "Elevation Info doesn't match pattern"
			maxPeak.elevation = self.elevation
			return

		minElev, maxElev, elevUnit = m.groups()
		minElev = str2IntPb(minElev, "Minimum elevation", self)
		maxElev = str2IntPb(maxElev, "Maximum elevation", self)
		if elevUnit == "m":
			minElev = toFeet(minElev)
			maxElev = toFeet(maxElev)

		assert minElev == self.elevation
		maxPeak.elevation = maxElev

	prominencePattern = re.compile(
		"^(?:<a href=\"KeyCol\\.aspx\\?pid=([1-9][0-9]*)\">Key Col Page</a>\n"
		"\\(Detailed prominence information\\)<br/>)?<a>Clean Prominence</a>\n"
		": ([,0-9]+) (ft|m)/([,0-9]+) (ft|m)<br/><a>Optimistic Prominence</a>\n"
		": ([,0-9]+) \\3/([,0-9]+) \\5<br/><a>(?:Line Parent</a>\n"
		": <a href=\"peak\\.aspx\\?pid=([1-9][0-9]*)\">([- 0-9A-Za-z]+)</a>\n<br/><a>)?Key Col</a>\n"
		": ([A-Z][a-z]+(?:[- /][A-Za-z]+)*(?:, [A-Z]{2})?)?([,0-9]+) \\3/([,0-9]+) \\5$"
	)
	def readProminence(self, maxPeak, html):
		m = self.prominencePattern.match(html)
		if m is None:
			err("{} Prominence doesn't match pattern:\n{}", self.fmtIdName, html)
		(
		peakId,
		minProm1, unit1,
		minProm2, unit2,
		maxProm1,
		maxProm2,
		lineParentId,
		lineParentName,
		keyColName,
		maxSaddleElev1,
		maxSaddleElev2,
		) = m.groups()

		minProm1 = str2IntPb(minProm1, "Clean prominence ({})".format(unit1), self)
		minProm2 = str2IntPb(minProm2, "Clean prominence ({})".format(unit2), self)
		maxProm1 = str2IntPb(maxProm1, "Optimistic prominence ({})".format(unit1), self)
		maxProm2 = str2IntPb(maxProm2, "Optimistic prominence ({})".format(unit2), self)
		maxSaddleElev1 = str2IntPb(maxSaddleElev1, "Max saddle elevation ({})".format(unit1), self)
		maxSaddleElev2 = str2IntPb(maxSaddleElev2, "Max saddle elevation ({})".format(unit2), self)

		if unit1 == "ft":
			assert unit2 == "m"
		else:
			assert unit2 == "ft"
			minProm1, minProm2 = minProm2, minProm1
			maxProm1, maxProm2 = maxProm2, maxProm1
			maxSaddleElev1, maxSaddleElev2 = maxSaddleElev2, maxSaddleElev1

		if peakId != self.id and peakId is not None:
			err("{} Pb ID from Key Col Page link ({}) != {}", self.fmtIdName, peakId, self.id)
		self.prominence = minProm1
		maxPeak.prominence = maxProm1

	def readLatLng(self, html):
		latlng = html.split("<br/>")[1]
		assert latlng.endswith(" (Dec Deg)")
		latlng = latlng[:-10].split(", ")
		latlng = map(lambda d: str(round(float(d), 5)), latlng)
		self.latitude, self.longitude = latlng

	rangePattern = re.compile(
		'^(Range[23456]|Continent): <a href="range\\.aspx\\?rid=([1-9][0-9]*)">'
		'((?:Mc|Le)?[A-Z][a-z]+(?: U\\.S\\.)?(?:[- ][A-Z]?[a-z]+)*)(?: \\(Highest Point\\))?</a>$'
	)
	def readRanges(self, rangeLines):
		rangeList = []
		for line in rangeLines:
			if line == "":
				continue
			m = self.rangePattern.match(line)
			if m is None:
				err("{} Range doesn't match pattern:\n{}", self.fmtIdName, line)
			label, rangeId, rangeName = m.groups()
			rangeList.append((rangeId, rangeName))
			expectedLabel = "Continent" if len(rangeList) == 1 else "Range" + str(len(rangeList))
			if label != expectedLabel:
				err("{} Unexpected range label:\n{}", self.fmtIdName, line)

		self.rangeId, self.rangeName = rangeList[4]
		self.rangeList = rangeList

	quadPattern = re.compile(
		'^([A-Za-z]+(?: [A-Za-z]+)*)  O[34][0-9]1[0-9][0-9][a-h][1-8]  1:24,000$'
	)
	def readQuad(self, html):
		m = self.quadPattern.match(html)
		if m is None:
			err("{} Topo Map doesn't match pattern:\n{}", self.fmtIdName, html)
		self.quadName = m.group(1)

	def readName(self, html):
		if html[:34] != "\n<br/><iframe></iframe>\n<br/><img>":
			err("{} Maps HTML doesn't match pattern:\n{}", self.fmtIdName, html)
		i = html.find("<img>", 34)
		if i < 0:
			err("{} Maps HTML doesn't match pattern:\n{}", self.fmtIdName, html)
		self.name = html[34:i]
		if self.name[-5:] == "<br/>":
			self.name = self.name[:-5]

	def readCountry(self, countries):
		self.country = []
		for country in countries:
			if country.endswith(" (Highest Point)"):
				country = country[:-16]
			code = countryNameMap.get(country)
			if code is None:
				err("{} Cannot get country code for {}", self.fmtIdName, country)
			self.country.append(code)

	def readState(self, states):
		self.state = []
		for state in states:
			if state.endswith(" (Highest Point)"):
				state = state[:-16]
			code = stateNameMap.get(state)
			if code is None:
				err("{} Cannot get state code for {}", self.fmtIdName, state)
			self.state.append(code)

	def readPeakFile(self, fileName):
		tables = TableParser(fileName, numTables=3, startTag="h1").tables

		maxPeak = PeakPb()

		self.readElevation(maxPeak, tables[0][0][1]) # First table, first row, second column

		for row in tables[1]:
			if row[0] == "Elevation Info:":
				if maxPeak.elevation is None:
					self.readElevationInfo(maxPeak, row[1])

			elif row[0] == "Latitude/Longitude (WGS84)":
				self.readLatLng(row[1])

			elif row[0] == "Country":
				self.readCountry(row[1].split("<br/>"))

			elif row[0] == "State/Province":
				self.readState(row[1].split("<br/>"))

		self.landManagement = []
		for row in tables[2]:
			if row[0] == "<a>Prominence</a>\n":
				self.readProminence(maxPeak, row[1])

			elif row[0] == "Ranges":
				self.readRanges(row[1].split("<br/>"))

			elif row[0] == "Ownership":
				self.readLandManagement(row[1])

			elif row[0] == "Topo Map":
				self.readQuad(row[1])

			elif row[0].startswith("<b>Dynamic Map</b>"):
				self.readName(row[0][18:])

		self.postProcess2(maxPeak)
		LandMgmtAreaPb.addAll(self)

	def compare(self, other):
		for attr in ("id", "name", "elevation", "rangeId", "rangeName"):
			v1 = getattr(self, attr)
			v2 = getattr(other, attr)
			if v1 != v2:
				print "{} {} doesn't match: {} != {}".format(self.fmtIdName, attr, v1, v2)

		min1, max1 = self.prominence
		min2, max2 = other.prominence

		if not (abs(min2-min1) in (0,1,2) and abs(max2-max1) in (0,1,2)):
			print "{} Prominence doesn't match: {} != {}".format(self.fmtIdName,
				self.prominence, other.prominence)

	def copyListFields(self, other):
		for attr in ("prominence", "sectionNumber", "sectionName"):
			setattr(self, attr, getattr(other, attr, None))

class PeakLoJ(TablePeak):
	classId = 'LoJ'
	classTitle = 'Lists of John'
	classAttrId = 'listsOfJohnId'
	classAttrPeak = 'listsOfJohnPeak'

	@classmethod
	def getPeakFileName(self, peakId):
		return "extract/data/loj/{}/p{}.html".format(peakId[0], peakId)
	@classmethod
	def getPeakURL(self, peakId):
		return "https://listsofjohn.com/peak/{}".format(peakId)
	@classmethod
	def expectLand(self, area):
		name = area.name
		return (name.endswith((" National Forest", " National Park")) or
			name.endswith(" Wilderness") and not name.endswith(" Regional", 0, -11))
	@classmethod
	def expectLandNPS(self, name):
		return name.endswith(" National Park")

	peakNamePattern = (' *('
		'(?:[A-Z][- \\.0-9A-Za-z]+(?:, [A-Z][a-z]+)?(?:-[A-Z][ A-Za-z]+)?(?: \\(HP\\))?)|'
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
			re.compile('^([A-Z]{2}(?:, [A-Z]{2})*)$'),
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
			re.compile('^([1-9][0-9]?)\\. ([A-Z][a-z]+(?:[- ][A-Z]?[a-z]+)+(?: [1-9][0-9]*)?)$'),
			('sectionNumber', 'sectionName')
		),
	}
	numPeaks = {
		'DPS':   95, # The four Mexican peaks are missing from the LoJ DPS list.
		'GBP':  115,
		'HPS':  281,
		'NPC':   73,
		'OGUL':  63,
		'SPS':  246, # Pilot Knob (North) is missing from the LoJ SPS list.
	}
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
		('Mount Jefferson-South Summit', 11941):        'Mount Jefferson',
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
	# Hundred Peaks Section:
		('Black Mountain', 7438):                       'Black Mountain #5',
		('Cannel Benchmark', 8314):                     'Cannel Point',
		('Granite Mountain', 5633):                     'Granite Mountain #2',
		('Inspiration Benchmark', 5580):                'Mount Inspiration',
		('Little Berdoo Benchmark', 5460):              'Little Berdoo Peak',
		('Warren Benchmark', 5103):                     'Warren Point',
	# Great Basin Peaks / Nevada Peaks Club:
		('Granite Peak', 8980):                         'Granite Peak (Washoe)',
		('Granite Peak', 9732):                         'Granite Peak (Humboldt)',
		('Granite Peak', 11218):                        'Granite Peak (Snake Range)',
		('Mount Grant', 11300):                         'Mount Grant (West)',
		('Mount Jefferson-North Summit', 11814):        'Mount Jefferson North',
		('Muddy Mountains HP', 5431):                   'Muddy Benchmark',
		('Peak 11340', 11340):                          'Thomas Peak',
		('Peak 12305', 12305):                          'Baker Peak East',
	# Sierra Peaks Section:
		('Coyote Peaks, East', 10892):  'Coyote Peaks',
		('Devils Crags', 12420):        'Devil\'s Crag #1',
		('Mount Morgan', 13748):        'Mount Morgan (South)',
		('Mount Morgan', 13001):        'Mount Morgan (North)',
		('Mount Stanford', 13973):      'Mount Stanford (South)',
		('Mount Stanford', 12838):      'Mount Stanford (North)',
		('Pilot Knob', 6220):           'Pilot Knob (South)',
		('Pilot Knob', 12245):          'Pilot Knob (North)',
		('Pyramid Peak', 12778):        'Pyramid Peak (South)',
		('Pyramid Peak', 9983):         'Pyramid Peak (North)',
		('Sawtooth Peak', 8020):        'Sawtooth Peak (South)',
		('Sawtooth Peak', 12343):       'Sawtooth Peak (North)',
		('Sierra Buttes, North', 8591): 'Sierra Buttes',
		('Three Sisters, East', 10612): 'Three Sisters',
	# Tahoe Ogul Peaks:
		('Silver Peak', 8930):                          'Silver Peak (Desolation)',
		('Silver Peak', 10772):                         'Silver Peak Southwest',
		('Twin Peaks, East', 8878):                     'Twin Peaks',
	# Other Sierra Peaks:
		('Maggies Peaks, South', 8699):                 'Maggies Peaks South',
		('Peak 9970', 9970):                            'Mariuolumne Dome',
		('Peak 9980', 9980):                            'Sirretta Peak North',
		('Peak 10213', 10213):                          'Peak 3113m',
		('Peak 10570', 10570):                          'Peak 3222m',
		('Peak 10597', 10597):                          'Peak 3230m',
		('Peak 11446', 11446):                          'Lost World Peak',
		('Peak 11712', 11712):                          'Peak 3560m+',
		('Peak 12076', 12076):                          'Duck Lake Peak',
		('Peak 13074', 13074):                          'Rosco Peak',
		('Peak 13464', 13464):                          'Northwest Lamarck',
		('Shepherd Crest, East', 12020):                'Shepherd Crest East',
		('Silver Peak', 10820):                         'Silver Peak Northeast',
		('Volcanic Ridge, East', 11207):                'Volcanic Ridge East',
		('Volcanic Ridge, West', 11486):                'Volcanic Ridge West',
		('White Mountain', 12057):                      'White Mountain (Tioga Pass)',
		('White Mountain', 11398):                      'White Mountain (Sonora Pass)',
	# Other California Peaks:
		('East Peak', 2571):                            'Mount Tamalpais East Peak',
		('Maguire Peaks, East', 1660):                  'Maguire Peaks East',
		('Maguire Peaks, West', 1688):                  'Maguire Peaks West',
		('Middle Peak', 2500):                          'Mount Tamalpais Middle Peak',
		('Mount Tamalpais', 2580):                      'Mount Tamalpais West Peak',
		('North Peak', 1898):                           'Montara Mountain',
		('Peak 2620', 2620):                            'Monument Peak',
		('South Peak', 4003):                           'Mount Saint Helena South',
		('South Yolla Bolly', 8093):                    'South Yolla Bolly Mountain',
		('Twin Peaks, South', 922):                     'Twin Peaks',
	# Other Western Peaks:
		('Mount Saint Helens', 8333):                   'Mount St. Helens',
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
			elif name[i + 7] == '-':
				name = 'Mount ' + name[:i] + name[i + 7:]
		elif name.endswith(', The'):
			name = 'The ' + name[:-5]
		if name.endswith(' (HP)'):
			name = name[:-4] + 'HP'
		return self.nameMap.get((name, elevation), name)

	elevationMap = {
	# LoJ SPS Elevation Adjustments:
	#
	# - Adams Peak (8,199) vs 8,197 (topo):
	#   "East Summit determined higher than west by 2 feet using photo pixel analysis."
	#   [https://listsofjohn.com/peak/17460]
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
	# - Mount Mills (13,460) vs 13,451 (topo):
	#   "This summit observed higher than location to the north with spot elevation 13,451' -
	#    contour missing from map."
	#   [https://listsofjohn.com/peak/32310]
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
	# - Seven Gables (13,074) vs 13,075 (15' topo)
	#   "13,080+40' contour on map is erroneous. NW summit is highest and shown as 3,985m on 1:100k map."
	#   [https://listsofjohn.com/peak/32383]
	#   The 1978/1988 Bishop 1:100,000 topo does indeed show a spot elevation of 3985m for Seven Gables,
	#   and 3985m = 13,074'. However, this topo says that it was "Compiled from USGS 1:62 500-scale
	#   topographic maps dated 1949-1962" and "Elevations shown to the nearest meter". So it seems likely
	#   that the elevation for Seven Gables was taken from the 15' topo which shows a spot elevation of
	#   13,075', converted to meters (3985.26m), and rounded to the nearest meter. Converting this
	#   rounded value back to feet and rounding down to the nearest foot gives the elevation used by LoJ
	#   which is one foot less than that on the 15' topo. Thus, the elevation shown on the 15' topo
	#   seems a sliver more accurate to me.
	#
	# - South Guard
	#   The Mt. Brewer 7.5' topos all show a spot elevation of 4033m = 13231.6' which, by LoJ's standard
	#   of rounding down, should be listed as 13,231', but LoJ uses 13,232'.
	#   The Mount Whitney 15' topos all show a spot elevation of 13,224'.
	#   The 1978/1990 Mount Whitney 1:100,000 topo doesn't show a spot elevation.
	#   The Fresno 1:250,000 maps also don't show a spot elevation.
	#   However, the 1907-1937 Mount Whitney 30' (1:125,000) quads show a spot elevation of 13,232' for
	#   the peak directly east of South Guard Lake! Did LoJ get the elevation from one of these maps?
	#   I added support for 30' quads so I don't have to make an adjustment for this peak.

		('Adams Peak', 8199): 8197,
		('Basin Mountain', 13190): 13181,
		('Mount Baxter', 13140): 4004.0,
		('Deerhorn Mountain', 13281): 4048.0, # didn't round down: 4048m = 13280.8' (Mt. Brewer 7.5')
		('Mount Hitchcock', 13186): 4019.0, # didn't round down: 4019m = 13185.7' (1993 Mount Whitney 7.5')
		('Joe Devel Peak', 13327): 4062.0, # didn't round down: 4062m = 13326.8' (1993 Mount Whitney 7.5')
		('Mount Mills', 13460): 13451,
		('Mount Morrison', 12296): 3742.0,
		('Mount Newcomb', 13422): 4091.0, # didn't round down: 4091m = 13421.9' (1993 Mount Whitney 7.5')
		('Mount Russell', 14088): 4294.0, # didn't round down: 4294m = 14087.9' (1993 Mount Whitney 7.5')
		('Seven Gables', 13074): 13075,
		('Temple Crag', 12976): 3955.0, # didn't round down: 3955m = 12975.7' (1990 Split Mtn. 7.5')
		('Trojan Peak', 13947): 4251.0, # didn't round down: 4251m = 13946.85' (1993 Mt. Williamson 7.5')
		('Tunnabora Peak', 13563): 4134.0, # didn't round down: 4134m = 13562.99' (1993 Mount Whitney 7.5')

	# LoJ DPS Elevation Adjustments:
	#
	# - Boundary Peak
	#   The 7.5' and 15' topos show a spot elevation of 13,140'.
	#   The 1:250,000 topos show either a spot elevation of 13,145' or no spot elevation.
	#   The 1:100,000 topos show a spot elevation of 4005m (13,140').
	#   So how does LoJ get 13,143'?
	#
	# - Needle Peak
	#   The 7.5' topo shows a spot elevation of 1768.8m = 5803.15'
	#   The 15' topos show a spot elevation of 5,805'
	#   The 1:100,000 topos show a spot elevation of 1769m = 5803.8'
	#   The 1:250,000 topos show spot elevations of either 5,782' or 5,805'
	#   How does LoJ get 5,802'?
	#   On the 7.5' topo, the top of the second 8 of the spot elevation is partially cut off by the
	#   old Death Valley National Monument boundary line. Perhaps it was misread as a 6?
	#   1768.6m does round down to 5,802'
	#
	# - Stepladder Mountains HP
	#   "This location is higher than contour with spot elevation 892m. Elevation is interpolation of
	#    spot elevation and next higher contour." (892m + 900m) / 2 / 0.3048 m/ft = 2939.6 ft
	#   [https://listsofjohn.com/peak/65349]

		('Boundary Peak', 13143): 13140,
		('East Ord Mountain', 6169): 6168,
		('Needle Peak', 5802): 1768.8,
		('Old Woman Mountains HP', 5325): 1623.0,
		('Spectre Point', 4483): 4482,
		('Stepladder Mountains HP', 2939): 895.0,

	# Other LoJ Elevation Adjustments:
	#
	# - Eagle Peak (GBP)
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
	# - Kumiva Peak (GBP / NPC)
	#   The LoJ page for Kumiva Peak has the following note: "1:250k map has spot elevation 8237,
	#   consistent with 2511 meters on 1:100k map." [https://listsofjohn.com/peak/16838]
	#   8237' is approximately 2510.6m and thus rounds to 2511m, and 2511m is approximately 8238.2'
	#   and thus rounds to 8238'. However, the 1:100k map was "Compiled from USGS 1:24 000 and
	#   1:62 500-scale topographic maps dated 1964-1981", and the 1:62,500-scale topo shows a spot
	#   elevation of 8237'. So 8237' seems more correct than 8238'.
	#
	# - Verdi Peak (NPC)
	#   "This contour [the north summit] determined higher than contour with spot elevation 11,074'.
	#    Elevation [11,077'] is interpolation of spot elevation and next higher contour [11,080']."
	#   [https://listsofjohn.com/peak/40725]

		('Billy Goat Peak',      5735):  1748.0,        # OWP -- LoJ didn't round down
		('Eagle Peak',           9900):  9892,          # GBP
		('Kumiva Peak',          8238):  8237,          # GBP
		('Mount Ian Campbell',  10615): 10616,          # OSP
		('Verdi Peak',          11077): 11074,          # NPC
	}
	saddleElevationMap = {
		('Mount Hitchcock', 12697): 3870.0, # LoJ didn't round down
		('Humphreys Peak', 6580): 6590, # LoJ seems to have used 6600'-40'/2, but the interval is only 20'
		('Joe Devel Peak', 12894): 3930.0, # LoJ didn't round down
		('Kingston Peak', 3582): 1092.1, # LoJ seems to have used 1092m
		('Peak 3222m', 10138): 3090.0, # LoJ didn't round down
		('Ring Mountain', 189): 140, # The saddle is between the 120' and 160' contours
		('Slacker Hill', 663): 662, # The saddle is between the 650' and 675' contours
	}
	def postProcess(self, peakListId=None):
		self.elevation = str2IntLoJ(self.elevation, 'Elevation', self.name)
		self.saddleElev = str2IntLoJ(self.saddleElev, 'Saddle elevation', self.name)
		self.prominence = str2IntLoJ(self.prominence, 'Prominence', self.name)

		assert self.prominence == self.elevation - self.saddleElev

		if isinstance(self.state, basestring):
			self.state = self.state.split(', ')
		if isinstance(self.counties, basestring):
			self.counties = self.counties.split(' &amp; ')
		self.isolation = float(self.isolation)
		self.saddleLat = float(self.saddleLat)
		self.saddleLng = float(self.saddleLng)

		self.name = self.normalizeName(self.name, self.elevation)
		self.lineParent = self.normalizeName(self.lineParent)
		self.proximateParent = self.normalizeName(self.proximateParent)

		adjElev = self.elevationMap.get((self.name, self.elevation))
		if adjElev is not None:
			if isinstance(adjElev, float):
				adjElev = toFeetRoundDown(adjElev)

			elevDiff = adjElev - self.elevation
			assert elevDiff != 0
			self.elevation = adjElev
			self.prominence += elevDiff

		self.elevation = ElevationLoJ(self.elevation)

		adjElev = self.saddleElevationMap.get((self.name, self.saddleElev))
		if adjElev is not None:
			if isinstance(adjElev, float):
				adjElev = toFeetRoundDown(adjElev)

			elevDiff = adjElev - self.saddleElev
			assert elevDiff != 0
			self.saddleElev = adjElev
			self.prominence -= elevDiff

		if peakListId == 'NPC':
			assert 'NV' in self.state

	parentPeakPattern = re.compile(
		'^<a href="/peak/([1-9][0-9]*)">' + peakNamePattern + '</a>$'
	)
	peakFilePatterns = {
		"Coords": (
			re.compile("^([0-9]{1,2}\\.[0-9]{1,4})N, ([0-9]{1,3}\\.[0-9]{1,4})W"),
			("latitude", "longitude")
		),
		"County": (
			re.compile('^<a href="/county/[1-9][0-9]*">([A-Z][a-z]+(?: [A-Z][a-z]+)*)</a>$'),
			("counties",)
		),
		"Elevation": (
			re.compile("^ ([1-9][0-9]?(?:,[0-9]{3}|[0-9]?))'$"),
			("elevation",)
		),
		"Isolation": (
			re.compile("^([0-9]+\\.[0-9]{2}) miles$"),
			("isolation",)
		),
		"LineParent": (
			parentPeakPattern,
			("lineParentId", "lineParent")
		),
		"ProximateParent": (
			parentPeakPattern,
			("proximateParentId", "proximateParent")
		),
		"Quad": (
			re.compile(
				'^<a href="/quad\\?q=([1-9][0-9]*)">((?:Mc)?[A-Z][a-z]+(?: [A-Z]?[a-z]+)*'
				'(?: [A-Z]{2})?)</a>$'
			),
			("quadId", "quadName")
		),
		"Rise": (
			re.compile("^([1-9][0-9]?(?:,[0-9]{3}|[0-9]?))'$"),
			("prominence",)
		),
		"Saddle": (
			re.compile(
				"^<a href=\"/(?:qmap|mapf)\\?"
				"lat=(-?[0-9]{1,2}\\.[0-9]{1,4})&"
				"lon=(-?[0-9]{1,3}\\.[0-9]{1,4})&z=15\">([,0-9]+)'</a>$"
			),
			("saddleLat", "saddleLng", "saddleElev")
		),
		"YDSClass": (
			re.compile(
				'^ ((?:[1-4]\\+?)|(?:5\\.[0-9](?: A1)?))'
				' <a href="/class\\?Id=([1-9][0-9]*)">Discussion</a>'
			),
			("ydsClass", "id")
		),
	}
	peakFilePatterns["City"] = peakFilePatterns["County"]
	peakFileLine1Pattern = re.compile("^<b>" + peakNamePattern + "</b> <b>([A-Z]{2}(?:, [A-Z]{2})*)</b>")
	peakFileLabelPattern = re.compile("^[A-Z][A-Za-z]+$")
	dataSheetPattern = re.compile("<a href=\"http://www\\.ngs\\.noaa\\.gov/cgi-bin/ds_mark\\.prl\\?"
		"PidBox=([A-Z]{2}[0-9]{4})\">Datasheet</a>")

	def readPeakFile_DataSheet(self, line):
		if "Datasheet" not in line:
			return
		if "(No Datasheet)" in line:
			return
		if self.dataSheet is not None:
			err("{} More than one datasheet!", self.fmtIdName)

		m = self.dataSheetPattern.search(line)
		if m is None:
			err("{} Datasheet pattern doesn't match: {}", self.fmtIdName, line)

		self.dataSheet = m.group(1)

	def readPeakFile_Counties(self, line):
		self.counties = []
		regExp = self.peakFilePatterns["County"][0]
		for html in line.split("  "):
			m = regExp.match(html)
			if m is None:
				err("{} County doesn't match pattern: {}", self.fmtIdName, html)
			self.counties.append(m.group(1))

	def readPeakFile(self, fileName):
		lines = (TableParser(fileName).tables[0][0][0] # First table, first row, first column
				.translate(None, "\r\n")
				.replace(" <a><img></a>", "")
				.replace("<small>", "").replace("</small>", "")
				.replace("<font>", "").replace("</font>", "")
				.replace("<div>", "").replace("</div>", "")
				.split("<br>"))

		line = lines.pop(0)
		m = self.peakFileLine1Pattern.match(line)
		if m is None:
			err("{} Line 1 doesn't match pattern: {}", self.fmtIdName, line)
		self.name, self.state = m.groups()
		self.state = self.state.split(", ")
		self.country = ["US"]
		self.ydsClass = None
		self.dataSheet = None
		self.landManagement = []
		getLand = False

		self.readPeakFile_DataSheet(line)

		for line in lines:
			if getLand:
				if line.startswith("YDS Class:"):
					getLand = False
				else:
					line = RE.htmlTag.sub("", line)
					if line == "Submit YDS Class Rating":
						getLand = False
						break
					if line.startswith("US Steepness Rank:"):
						getLand = False
					else:
						if line.endswith((" County Highpoint", " City Highpoint")):
							continue
						self.landManagement.append(line)
						continue
			if ":" not in line:
				line = RE.htmlTag.sub("", line)
				if line == "Submit YDS Class Rating":
					break
				continue
			label, value = line.split(":", 1)
			label = label.replace(" ", "")
			m = self.peakFileLabelPattern.match(label)
			if m is None:
				log("{} Skipping label \"{}\"", self.fmtIdName, label)
				continue
			if label == "Isolation":
				getLand = True
			pattern = self.peakFilePatterns.get(label)
			if pattern is None:
				if label == "Counties":
					self.readPeakFile_Counties(value)
				elif label == "AlternateNames":
					self.readPeakFile_DataSheet(value)
				continue
			pattern, attributes = pattern
			m = pattern.match(value)
			if m is None:
				if label in ("LineParent", "ProximateParent"):
					pattern, attributes = self.columnMap[label[:-6] + " Parent"]
					m = pattern.match(value)
				if m is None:
					log("{} {} doesn't match pattern: {}", self.fmtIdName, label, value)
					continue
			values = m.groups()
			assert len(attributes) == len(values)
			for attr, value in zip(attributes, values):
				setattr(self, attr, value)
			if label == "YDSClass":
				break

		self.postProcess()
		LandMgmtAreaLoJ.addAll(self)

	def compare(self, other):
		for attr in ("id", "name", "elevation", "prominence", "saddleLat", "saddleLng", "saddleElev",
			"lineParent", "proximateParent", "isolation", "state", "counties", "quadId", "quadName"):
			v1 = getattr(self, attr)
			v2 = getattr(other, attr)
			if v1 != v2:
				print "{} {} doesn't match: {} != {}".format(self.fmtIdName, attr, v1, v2)

	def copyListFields(self, other):
		for attr in ("sectionNumber", "sectionName"):
			setattr(self, attr, getattr(other, attr, None))

class PeakBB(object):
	classId = "BB"
	classTitle = "Bob Burd"
	classAttrId = "bobBurdId"
	classAttrPeak = "bobBurdPeak"

	patterns = (
		(
			re.compile("^<a href=/dayhikes/peak/([1-9][0-9]*)>([ #\\(\\),0-9A-Za-z]+)</a>$"),
			("id", "name")
		),
		(
			re.compile("^([1-9][0-9]?(?:,[0-9]{3}|[0-9]?))ft$"),
			("elevation",)
		),
		(
			re.compile("^([0-9]{1,2}\\.[0-9]{1,4})N (-[0-9]{1,3}\\.[0-9]{1,4})W$"),
			("latitude", "longitude"),
		),
		(
			re.compile("^prom\\. - ([1-9][0-9]?(?:,[0-9]{3}|[0-9]?))ft$"),
			("prominence",)
		),
	)
	linkPattern = re.compile("^<a href=//([^0-9]+)([1-9][0-9]*)>([A-Z][A-Za-z]*)</a>$")
	linkMap = {
		"LoJ": ("listsOfJohnId", "www.listsofjohn.com/peak/"),
		"PB": ("peakbaggerId", "peakbagger.com/peak.aspx?pid="),
		"SP": ("summitpostId", "www.summitpost.org/mountain/"),
	}
	numPeaks = {
		"GBP": 120,
	}
	ListAdditions = {
		"GBP": ((
			("id", "24904"),
			("name", "Duffer Peak South"),
			("latitude", "41.6574"),
			("longitude", "-118.7323"),
			("elevation", 9428),
			("prominence", 4139),
			("listsOfJohnId", "16781"), # Pine Forest Range HP
			("peakbaggerId", "3322"),
			("summitpostId", "518638"),
			),(
			("id", "33951"),
			("name", "Baker Peak East"),
			("latitude", "38.9687"),
			("longitude", "-114.3092"),
			("elevation", 12305),
			("prominence", 496),
			("listsOfJohnId", "40688"), # Peak 12305
			("peakbaggerId", "3573"),
			("summitpostId", "153395"),
			),(
			("id", "34060"),
			("name", "Morey Peak North"),
			("latitude", "38.6305"),
			("longitude", "-116.2859"),
			("elevation", 10260),
			("prominence", 2600),
			("listsOfJohnId", "17187"), # Hot Creek Range HP
			("peakbaggerId", "34519"),
			("summitpostId", "577683"),
			),(
			("id", "34255"),
			("name", "Chocolate Peak"),
			("latitude", "39.3532"),
			("longitude", "-119.8970"),
			("elevation", 9402),
			("prominence", 262),
			("listsOfJohnId", "41109"),
			("peakbaggerId", "30104"),
			("summitpostId", "351277"),
			),(
			("id", "59012"),
			("name", "Bull Mountain"),
			("latitude", "41.9105"),
			("longitude", "-113.3658"),
			("elevation", 9940),
			("prominence", 3744),
			("listsOfJohnId", "16828"),
			("peakbaggerId", "3440"),
			("summitpostId", "183282"),
			),
		),
	}
	ListDeletions = {
	}
	PeakMods = {
		"6259": (("name", "Mount Jefferson"),), # Mount Jefferson-South (11,941')
		"9008": (("name", "Mount Grant (West)"),), # Mount Grant (11,300')
		"10043": (("name", "Granite Peak (Washoe)"),), # Granite Peak (8,980')
		"10219": (("name", "Granite Peak (Humboldt)"),), # Granite Peak (9,732')
		"10287": (("name", "Mount Jefferson North"),), # Mount Jefferson-North (11,814')
	}
	@classmethod
	def normalizeName(self, name):
		if name.endswith(", Mount"):
			name = "Mount " + name[:-7]
		elif name.endswith(" BM"):
			name = name[:-2] + "Benchmark"
		elif name.endswith(" Ridge"):
			name = name[:-6]
		return name

	def __init__(self):
		self.listsOfJohnId = None
		self.peakbaggerId = None
		self.summitpostId = None

	@classmethod
	def getPeaks(self, peakListId):
		def str2int(s):
			return int(s) if len(s) < 4 else int(s[:-4]) * 1000 + int(s[-3:])

		fileName = "extract/data/{}/bb.html".format(peakListId.lower())

		if not os.path.exists(fileName):
			return []

		additions = self.ListAdditions.get(peakListId, ())
		deletions = self.ListDeletions.get(peakListId, ())

		peaks = []
		htmlFile = open(fileName)

		for line in htmlFile:
			if line[:11] != "    PMarker":
				continue
			lines = (line.split("\"")[1]
				.replace(" style='font-size:9px;color:gray'", "")
				.replace("<span>", "").replace("</span>", "")
				.split("<br>")[:5])
			links = lines.pop().split(" - ")[1:]

			peak = PeakBB()
			peaks.append(peak)

			for line, (regExp, attributes) in zip(lines, self.patterns):
				m = regExp.match(line)
				if m is None:
					err("Line doesn't match pattern: {}", line)
				values = m.groups()
				assert len(attributes) == len(values)
				for attr, value in zip(attributes, values):
					setattr(peak, attr, value)

			peak.elevation = str2int(peak.elevation)
			peak.prominence = str2int(peak.prominence)
			peak.name = self.normalizeName(peak.name)

			for line in links:
				m = self.linkPattern.match(line)
				if m is None:
					err("Link doesn't match pattern: {}", line)
				linkPrefix, peakId, siteAbbr = m.groups()
				attr, expectedPrefix = self.linkMap[siteAbbr]
				if linkPrefix != expectedPrefix:
					err("Unexpected link prefix: {}", linkPrefix)
				setattr(peak, attr, peakId)

			if peak.id in deletions:
				del peaks[-1]
				continue

			mods = self.PeakMods.get(peak.id)
			if mods is not None:
				for attr, value in mods:
					setattr(peak, attr, value)

		htmlFile.close()

		for addition in additions:
			peak = PeakBB()
			peaks.append(peak)
			for attr, value in addition:
				setattr(peak, attr, value)

		name2peak = {}
		for peak in peaks:
			peak.elevation = ElevationLoJ(peak.elevation)
			peakInMap = name2peak.setdefault(peak.name, peak)
			if peakInMap is not peak:
				err("BB name {} used for both ID {} ({}') and ID {} ({}')!",
					peak.name,
					peakInMap.id,
					peakInMap.elevation,
					peak.id,
					peak.elevation)

		assert len(peaks) == self.numPeaks[peakListId]
		return name2peak

class PeakVR(object):
	classId = "VR"
	classTitle = "Vulgarian Ramblers"
	classAttrId = "vulgarianRamblersId"
	classAttrPeak = "vulgarianRamblersPeak"

	columnMap = {
		"Rank": (
			re.compile("^([1-9][0-9]*)?$"),
			("rank",)
		),
		"Peak Name": (
			re.compile(
				"<a id='peak_UID_[1-9][0-9]*' href='\\./peak_detail\\.php\\?peak_name="
				"([A-Z][-%0-9A-Za-z]+)'>([- &\\(\\)\\.0-9;A-Za-z]+)</a> "
			),
			("linkName", "name")
		),
		"Elevation": (
			re.compile(
				"^<a +href='[^']+'>(1[234],[0-9]{3})' or ([34][0-9]{3})m"
				"(?:<span [^>]+>([ ',0-9a-z]+)</span>)?</a>$"
			),
			("elevationFeet", "elevationMeters", "elevationTooltip")
		),
		"Prominence": (
			re.compile(
				"^([1-9][0-9]{1,2}')|(?:<a [^>]+>((?:300m\\+)|(?:[1-9][0-9]{1,2}'))"
				"<span [^>]+>([ '0-9A-Za-z]+)</span></a>)$"
			),
			("prominence", "promWithTooltip", "promTooltip")
		),
	}
	nameMap = {
		"Black Mountain (South)": "Black Mountain",
		"CalTech Peak": "Caltech Peak",
		"Twin Peaks": "Peak 3981m",
		"UTM888455": "Rosco Peak",
	}
	def postProcess(self):
		self.id = None

		name = self.name
		if name.startswith("&ldquo;"):
			assert name.endswith("&rdquo;")
			name = name[7:-7]

		self.name = name = name.replace("&rsquo;", "'")

		if name.startswith("Mt. "):
			name = name[4:]
			self.name = "Mount " + name

		name = RE.nonAlphaNum.sub(lambda m: "%{:02x}".format(ord(m.group())), name)

		if name != self.linkName:
			err("Unexpected link name '{}' for '{}'", self.linkName, self.name)

		feet = self.elevationFeet
		feet = int(feet[:-4]) * 1000 + int(feet[-3:])

		if toMeters(feet) != int(self.elevationMeters):
			err("Elevation in feet ({}) != elevation in meters ({}) for '{}'",
				self.elevationFeet, self.elevationMeters, self.name)

		self.elevation = ElevationVR(feet)

		if self.prominence is None:
			self.prominence = self.promWithTooltip

		self.name = self.nameMap.get(self.name, self.name)

		if self.rank is not None:
			self.rank = int(self.rank)

	def __str__(self):
		return '<td><a href="http://vulgarianramblers.org/peak_detail.php?peak_name={}">{}</a></td>\n'.format(
			self.linkName, "VR" if self.rank is None else "#" + str(self.rank))

	@classmethod
	def readTable(self, fileName, numPeaks, searchStr=None):
		table = TableReader(fileName,
			tableAttributes="id='peak_list_ID' class=\"peak_list\" align=\"center\"")

		if searchStr is not None:
			table.readUntil(searchStr, discard=True)
			table.readUntil("</tr>", discard=True)
		row = table.next()

		columns = []
		for colNum, colStr in enumerate(row):
			colStr = RE.htmlTag.sub("", colStr)
			colStr = RE.whitespace.sub("\n", colStr)
			colStr = colStr[:colStr.find("\n")]
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
			if len(peaks) == numPeaks:
				break

		return peaks

	@classmethod
	def getPeaks(self, peakListId=None):
		peaks1 = self.readTable("extract/data/vr/ca_13ers.html", 147)
		peaks2 = self.readTable("extract/data/vr/non_13ers.html", 19, "Marginal Failing Peaks")
		peaks3 = self.readTable("extract/data/vr/non_13ers.html", 58, "Clearly Failing Peaks")
		return peaks1 + peaks2 + peaks3

	@classmethod
	def getAttr(self, attr, peak):
		peak2 = getattr(peak, self.classAttrPeak, None)
		if peak2 is None:
			return None
		return getattr(peak2, attr, None)

def matchElevation(peak, elevation):
	line = "{} {:7} {{:7}}".format(peak.fmtIdName, elevation)

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

		for section in pl.sections:
			for peak in section.peaks:
				name = peak.name
				if name.startswith("&quot;"):
					assert name.endswith("&quot;")
					name = name[6:-6]
				peak.matchName = name
				peak.fmtIdName = "{:5} {:24}".format(peak.id, name)
				put(name, peak)
				if peak.otherName is not None:
					put(peak.otherName, peak)

		self.name2peak = name2peak
		self.id = pl.id

	def get(self, peak2):
		peak = self.name2peak.get(peak2.name)
		if peak is not None:
			if not isinstance(peak, list):
				peakId = getattr(peak, peak2.classAttrId, None)
				if peakId != peak2.id:
					err("ID ({}) doesn't match {} ({}) for {}",
						peak2.id, peak2.classAttrId, peakId, peak2.name)
				setattr(peak, peak2.classAttrPeak, peak2)
				return peak
			log("Peak name '{}' is not unique!", peak2.name)
		return None

def printTitle(title):
	width = 60
	border = "+" + ("-" * (width - 2)) + "+"
	title = "| " + title + (" " * (width - 4 - len(title))) + " |"

	print border
	print title
	print border

def checkElevation(pl, peakClass):
	printTitle("Elevations - " + peakClass.classTitle)

	for section in pl.sections:
		for peak in section.peaks:
			elevation = peakClass.getAttr("elevation", peak)
			if elevation is not None:
				matchElevation(peak, elevation)

def checkProminence(pl, setProm=False):
	printTitle("Prominences")

	numMatchPb = 0
	numMatchLoJ = 0
	numMatchBoth = 0
	numMatchNone = 0

	def getMatchLoJ(prom, promLoJ):
		if promLoJ is None:
			return "not listed"
		if not isinstance(prom, int):
			prom = prom.avgFeet(toFeet=toFeetRoundDown)
		if prom == promLoJ:
			return True
		return "{} != {}".format(prom, promLoJ)

	def getMatchPb(prom, promPb):
		if promPb is None:
			return "not listed"
		if isinstance(prom, int):
			minPb, maxPb = promPb
			if prom == (minPb + maxPb) / 2:
				return True
			return "{} != ({} + {})/2".format(prom, minPb, maxPb)

		prom = prom.minMaxPb()
		if prom == promPb:
			return True
		return "{} != {}".format(prom, promPb)

	for section in pl.sections:
		for peak in section.peaks:
			newProm = None
			promLoJ = PeakLoJ.getAttr("prominence", peak)
			promPb = PeakPb.getAttr("prominence", peak)

			for prom in peak.prominences:
				matchLoJ = getMatchLoJ(prom, promLoJ)
				matchPb = getMatchPb(prom, promPb)

				source = None
				promObj = None
				if not isinstance(prom, int):
					promObj = prom
					prom = promObj.avgFeet()

				if matchLoJ is True:
					if matchPb is True:
						numMatchBoth += 1
						source = "LoJ/Pb"
					else:
						numMatchLoJ += 1
						source = "LoJ"
				elif matchPb is True:
					numMatchPb += 1
					source = "Pb"

					if promObj is None:
						print peak.fmtIdName, "{:6} ".format(prom),
						print "Matches Pb but not LoJ [{}]".format(matchLoJ)
				else:
					numMatchNone += 1
					print peak.fmtIdName, "{:6} ".format(prom),

					if promObj is None and promLoJ is not None and promPb is not None:
						minPb, maxPb = promPb
						avgPb = (minPb + maxPb) / 2
						if avgPb == promLoJ and len(peak.prominences) == 1:
							if prom == minPb:
								newProm = (avgPb, "min")
								break
							if prom == maxPb:
								newProm = (avgPb, "max")
								break

					print "Matches neither LoJ [{}] nor Pb [{}]".format(matchLoJ, matchPb)

				if promObj is not None and source != promObj.source:
					print peak.fmtIdName, "{:6} ".format(prom),
					print "Source should be {} instead of {}".format(source, promObj.source)

			if newProm is not None:
				newProm, promType = newProm
				if setProm:
					print "Setting to {} [LoJ={}, Pb={}]".format(newProm, promLoJ, promPb)
					peak.prominences = [newProm]
				else:
					print "Matches {}Pb and avgPb == LoJ".format(promType)

	printTitle("Prominences: LoJ/Pb={}, LoJ={}, Pb={}, None={}".format(
		numMatchBoth, numMatchLoJ, numMatchPb, numMatchNone))

def checkThirteeners(pl, setVR=False):
	printTitle("Thirteeners")

	for section in pl.sections:
		for peak in section.peaks:
			thirteener = False
			for e in peak.elevations:
				if e.elevationFeet >= 13000:
					thirteener = True
					break
			vr = getattr(peak, PeakVR.classAttrPeak, None)
			if vr is None:
				if thirteener:
					print peak.fmtIdName, "Missing VR link"
			else:
				if not thirteener:
					print peak.fmtIdName, "Unexpected VR link"
				colVR = peak.column12
				if colVR is None:
					if setVR:
						peak.column12 = vr
				else:
					if vr.rank != colVR.rank or vr.linkName != colVR.name:
						print "{} VR rank/link {}/{} doesn't match {}/{}".format(
							peak.fmtIdName, colVR.rank, colVR.name, vr.rank, vr.linkName)

def checkData(pl, setProm=False, setVR=False):
	verbose = pl.id not in ('HPS',)

	peakClasses = [PeakLoJ, PeakPb]
	if pl.id in ('SPS', 'OSP'):
		peakClasses.append(PeakVR)

	peakMap = MatchByName(pl)

	for peakClass in peakClasses:
		printTitle("Getting Peaks - " + peakClass.classTitle)
		verbose = verbose and peakClass is not PeakVR
		numMapped = 0
		peaks = peakClass.getPeaks(pl.id)
		for peak in peaks:
			if peakMap.get(peak) is None:
				if verbose:
					print "Cannot map '{}' ({})".format(peak.name, peak.elevation)
			else:
				numMapped += 1
		print "Mapped {}/{} peaks".format(numMapped, len(peaks))

	for peakClass in (PeakLoJ, PeakPb):
		printTitle("Reading Peak Files - " + peakClass.classTitle)
		for section in pl.sections:
			for peak in section.peaks:
				peakId = getattr(peak, peakClass.classAttrId, None)
				if peakId is None or peakId[0] == "-":
					continue

				fileName = peakClass.getPeakFileName(peakId)
				if not os.path.exists(fileName):
					continue

				peak2 = peakClass()
				peak2.id = peakId
				peak2.fmtIdName = peak.fmtIdName
				peak2.readPeakFile(fileName)

				peak3 = getattr(peak, peakClass.classAttrPeak, None)
				if peak3 is None:
					peak3 = peakMap.get(peak2)
					if peak3 is None:
						print "{} Name doesn't match ({})".format(
							peak.fmtIdName, peak2.name)
						setattr(peak, peakClass.classAttrPeak, peak2)
					elif peak3 is not peak:
						print "{} Name matches a different peak ({})!".format(
							peak.fmtIdName, peak2.name)
						continue
				else:
					peak2.compare(peak3)

				peak2.checkLand(peak)

				if peakClass is PeakPb:
					haveFlag = "CC" in peak.flags
					wantFlag = (peak2.rangeList[2] == ("126", "Sierra Nevada") and
						float(peak.latitude) > 35.36)

					if haveFlag != wantFlag:
						print "{} Should {}able CC flag".format(peak.fmtIdName,
							"en" if wantFlag else "dis")
				else:
					peak2.checkDataSheet(peak)

				if peak.quad is not None:
					if peak.quad != peak2.quadName:
						print "{} Quad '{}' != '{}'".format(peak.fmtIdName,
							peak2.quadName, peak.quad)

				if peak.country != peak2.country:
					print '{} data-country should be "{}" instead of "{}"'.format(
						peak.fmtIdName, "/".join(peak2.country), "/".join(peak.country))

				if peak.state != peak2.state:
					print '{} data-state should be "{}" instead of "{}"'.format(
						peak.fmtIdName, "/".join(peak2.state), "/".join(peak.state))

	for peakClass in peakClasses:
		checkElevation(pl, peakClass)

	checkProminence(pl, setProm)

	if PeakVR in peakClasses:
		checkThirteeners(pl, setVR)

def loadFiles(pl):
	loadURLs(getLoadListsFromTable(pl))
#	loadURLs(getLoadLists(pl))

PeakAttributes = {
	"GBP": {
	"Arc Dome": (("isEmblem", True),),
	"Boundary Peak": (("isEmblem", True),),
	"Cache Peak": (("isEmblem", True),),
	"Charleston Peak": (("isEmblem", True),),
	"Duffer Peak South": (("otherName", "Pine Forest Range HP"),),
	"Hayden Peak": (("otherName", "Cinnabar Mountain"),),
	"Ibapah Peak": (("isEmblem", True),),
	"McCullough Mountain": (("isEmblem", True),),
	"Morey Peak North": (("otherName", "Hot Creek Range HP"),),
	"Mount Rose": (("isEmblem", True),),
	"Navajo Mountain": (("delisted", True),),
	"Tule Peak": (("isEmblem", True),),
	"Warner Peak": (("isEmblem", True),),
	"Wheeler Peak": (("isEmblem", True),),
	"White Mountain Peak": (("isEmblem", True),),
	"Yellow Peak": (("otherName", "Bald Mountain"),),
	},
}

def readListFile(peakListId):
	sectionPattern = re.compile("^([1-9][0-9]?)\\. ([- &,;0-9A-Za-z]+)$")
	peakPattern = re.compile("^([1-9][0-9]?)\\.([1-9][0-9]?[ab]?) +([#&'0-9;A-Za-z]+(?: [#&'()0-9;A-Za-z]+)*)")

	fileName = "extract/data/{0}/{0}.txt".format(peakListId.lower())
	listFile = open(fileName)

	sections = []
	expectedSectionNumber = 0

	for line in listFile:
		expectedSectionNumber += 1
		m = sectionPattern.match(line)
		if m is None:
			err("Section header doesn't match pattern:\n{}", line)
		sectionNumber, sectionName = m.groups()

		if int(sectionNumber) != expectedSectionNumber:
			err("Expected section number {}:\n{}", expectedSectionNumber, line)
		if listFile.next() != "\n":
			err("Expected empty line after section header:\n{}", line)

		peaks = []
		expectedPeakNumber = ("1", "1a")
		sections.append((sectionName, peaks))

		for line in listFile:
			if line == "\n":
				break

			m = peakPattern.match(line)
			if m is None:
				err("Peak line doesn't match pattern:\n{}", line)
			sectionNumber, peakNumber, peakName = m.groups()

			if int(sectionNumber) != expectedSectionNumber:
				err("Expected section number {}:\n{}", expectedSectionNumber, line)
			if peakNumber not in expectedPeakNumber:
				err("Expected peak number {}:\n{}", " or ".join(expectedPeakNumber), line)

			peakId = "{}.{}".format(sectionNumber, peakNumber)
			peaks.append((peakId, peakName))

			if peakNumber[-1] == "a":
				expectedPeakNumber = (peakNumber[:-1] + "b",)
			else:
				peakNumber = int(peakNumber[:-1] if peakNumber[-1] == "b" else peakNumber)
				peakNumber = str(peakNumber + 1)
				expectedPeakNumber = (peakNumber, peakNumber + "a")

	listFile.close()
	return sections

def createBBMap(peakLists):
	bbMap = {}
	for pl in peakLists.itervalues():
		for section in pl.sections:
			for peak in section.peaks:
				if peak.bobBurdId is None:
					continue
				if peak.dataFrom is None:
					peakInMap = bbMap.setdefault(peak.bobBurdId, peak)
					if peakInMap is not peak:
						err("BB ID {} used for both {} {} ({}) and {} {} ({})!",
							peak.bobBurdId,
							peakInMap.peakList.id,
							peakInMap.id,
							peakInMap.name,
							peak.peakList.id,
							peak.id,
							peak.name)
	return bbMap

def setPeak(peak, peakClass, idMap):
	peak2Id = getattr(peak, peakClass.classAttrId, None)
	if peak2Id is None:
		log("{:5} {:24} Missing {} ID", peak.id, peak.name, peakClass.classId)
		peak2 = None
	elif peak2Id[0] == "-":
		log("{:5} {:24} Skipping provisional {} ID {}", peak.id, peak.name, peakClass.classId, peak2Id)
		peak2 = None
	else:
		fileName = peakClass.getPeakFileName(peak2Id)
		if not os.path.exists(fileName):
			loadURLs([[(peakClass.getPeakURL(peak2Id), fileName)]])

		peak2 = peakClass()
		peak2.id = peak2Id
		peak2.fmtIdName = "{:5} {:24} {}".format(peak.id, peak.name, peakClass.classId)
		peak2.readPeakFile(fileName)

		mapPeak = idMap.pop(peak2Id, None)
		if mapPeak is None:
			log("{} list doesn't include ID {}", peak2.fmtIdName, peak2Id)
		else:
			peak2.compare(mapPeak)
			peak2.copyListFields(mapPeak)

	setattr(peak, peakClass.classAttrPeak, peak2)

def printPeaks(pl):
	for sectionNumber, section in enumerate(pl.sections, start=1):
		if sectionNumber != 1:
			print
		print "{}. {}".format(sectionNumber, section.name)
		print
		for peak in section.peaks:
			print "{:5} {:28} {} {:12} {}".format(peak.id, peak.name,
				peak.listsOfJohnPeak.state[0],
				peak.listsOfJohnPeak.counties[0],
				peak.peakbaggerPeak.rangeList[-1][1])

def createList(pl, peakLists, peakClass, sectionClass, setLandManagement, verbose=False):
	sections = readListFile(pl.id)
	peakAttributes = PeakAttributes.get(pl.id, {})

	mapPb = {p.id: p for p in PeakPb.getPeaks(pl.id)}
	mapLoJ = {p.id: p for p in PeakLoJ.getPeaks(pl.id)}

	bbIdMap = createBBMap(peakLists)
	bbNameMap = PeakBB.getPeaks(pl.id)

	pl.sections = []

	for sectionName, sectionPeaks in sections:
		section = sectionClass(pl, sectionName)
		pl.sections.append(section)

		for peakId, peakName in sectionPeaks:
			peakBB = bbNameMap.get(peakName)
			if peakBB is None:
				err("{} {} not found in bbNameMap!", peakId, peakName)

			fmtIdName = "{:5} {:24}".format(peakId, peakName)

			existingPeak = bbIdMap.get(peakBB.id)
			if existingPeak is None:
				peak = peakClass(section)
				peak.name = peakName
				peak.bobBurdId = peakBB.id
				peak.listsOfJohnId = peakBB.listsOfJohnId
				peak.peakbaggerId = peakBB.peakbaggerId
				peak.summitpostId = peakBB.summitpostId
				peak.summitpostName = "mountain"

			elif existingPeak.peakList is pl:
				if verbose:
					log("{} Using existing data", fmtIdName)

				peak = existingPeak
			else:
				if verbose:
					log("{} Using existing data from {} {}", fmtIdName,
						existingPeak.peakList.id, existingPeak.id)

				peak = peakClass(section)
				peak.dataFrom = existingPeak.fromId()

				for i, p in enumerate(existingPeak.dataAlsoPeaks):
					if p.peakList is pl:
						del existingPeak.dataAlsoPeaks[i]
						break

				peak.copyFrom(existingPeak)

			peak.id = peakId
			setPeak(peak, PeakPb, mapPb)
			setPeak(peak, PeakLoJ, mapLoJ)
			section.peaks.append(peak)

			for attr, value in peakAttributes.get(peakName, ()):
				setattr(peak, attr, value)

			if existingPeak is None:
				peakPb = peak.peakbaggerPeak
				peakLoJ = peak.listsOfJohnPeak

				peak.latitude = peakPb.latitude
				peak.longitude = peakPb.longitude
				peak.elevations = [peakPb.elevation]
				peak.prominences = [peakLoJ.prominence]

				if peakBB.elevation != peakLoJ.elevation:
					log("{} BB elevation ({}) != LoJ elevation ({})",
						fmtIdName, peakBB.elevation, peakLoJ.elevation)
				if peakBB.prominence != peakLoJ.prominence:
					log("{} BB prominence ({}) != LoJ prominence ({})",
						fmtIdName, peakBB.prominence, peakLoJ.prominence)
				if peakPb.state != peakLoJ.state:
					log("{} Pb state ({}) != LoJ state ({})", fmtIdName,
						"/".join(peakPb.state), "/".join(peakLoJ.state))

				if peak.country != peakPb.country:
					peak.country = peakPb.country
				if peak.state != peakPb.state:
					peak.state = peakPb.state
				if peakLoJ.ydsClass is not None:
					peak.grade = peakLoJ.ydsClass

				setLandManagement(peak)
			else:
				if peak.name != peakName:
					log("Existing peak name ({}) doesn't match {}!", peak.name, peakName)

				fromId = peak.fromId()

				if peak.dataFrom is not None and pl.sortkey < existingPeak.peakList.sortkey:
					peak.dataFrom = None
					peak.dataAlsoPeaks.remove(peak)
					peak.dataAlsoPeaks.append(existingPeak)

				if peak.dataFrom is None:
					for p in peak.dataAlsoPeaks:
						if p.dataFrom != fromId:
							log('{} Set {} {} data-from="{}"',
								fmtIdName, p.peakList.id, p.id, fromId)
				else:
					alsoList = [p for p in peak.dataAlsoPeaks if p is not peak]
					alsoList.append(existingPeak)
					for p in alsoList:
						if fromId not in p.dataAlso:
							log('{} Add "{}" to data-also for {} {}',
								fmtIdName, fromId, p.peakList.id, p.id)
		section.setDataAttributes()

	for peak in mapPb.itervalues():
		log("Pb peak {} ({}) not used!", peak.id, peak.name)
	for peak in mapLoJ.itervalues():
		log("LoJ peak {} ({}) not used!", peak.id, peak.name)
