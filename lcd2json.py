#!/usr/bin/python
#
# lcd2json - Convert Layer Control Data to JSON
#            Usage: ./lcd2json.py pmap.lcd > pmap_lcd.json
#
import os
import re
import sys

lineNumber = 0
linePattern = re.compile('^(\t*)([- /A-Za-z0-9\\|\\(\\)]+) ([:=])([a-z0-9]+)(\\^*)(?: add([_A-Za-z]+))?$')
commentPattern = re.compile('^\t*#')

addPatterns = [
	re.compile('^(?:_(?:[A-Z]+|(?:[A-Z][a-z]+)+))+$'),      # add_BLM_CA_Districts
	re.compile('^(?:[A-Z][a-z]+)+$'),                       # addPeakOverlay
	re.compile('^(?:_[a-z]+)+$'),                           # add_peak_overlay
]

def log(message, *formatArgs):
	print >>sys.stderr, message.format(*formatArgs)

def err(*args):
	log(*args)
	sys.exit()

def ppSize(bytes, fileName):
	#
	# Pretty print size (e.g. convert 2113961 bytes to '2.02 MB')
	#
	K = 1 << 10
	M = 1 << 20
	maxSize = 20 * M

	if bytes < K:
		size = '{} B'.format(bytes)
	elif bytes < maxSize:
		if bytes < M:
			divisor = K
			suffix = 'K'
		else:
			divisor = M
			suffix = 'M'

		size = round(float(bytes) / divisor, 2)
		if size > 100:
			size = int(round(size, 0))
		elif size > 10:
			size = round(size, 1)
		size = '{} {}B'.format(size, suffix)
	else:
		err('Line {}: Size of file "{}" > 10 MB', lineNumber, fileName)

	log('Size of {} is {} bytes ({})', fileName, bytes, size)
	return size

def parseLCD(lcdFile):
	global lineNumber

	hasFile = False
	parent = {}
	parentItems = {'root': parent}
	parentOrder = ['root']
	parents = []
	path = []

	for line in lcdFile:
		lineNumber += 1
		m = linePattern.match(line)
		if m is None:
			if commentPattern.match(line):
				continue
			err("Line {} doesn't match pattern", lineNumber)

		indent, name, idType, id, upLevel, addFunction = m.groups()

		if name[0] in ' ()-/|':
			err("Name on line {} must begin with a letter or number", lineNumber)

		item = {'name': name}

		if addFunction is not None:
			for pattern in addPatterns:
				if pattern.match(addFunction):
					break
			else:
				err("addFunction on line {} doesn't match pattern", lineNumber)
			item['add'] = addFunction

		level = len(indent)
		prevLevel = len(parents) - 1

		if level > prevLevel:
			if level != prevLevel + 1:
				err("Indentation too deep on line {}", lineNumber)
			parent = parentItems[parentOrder[-1]]
			parent['items'] = parentItems = {}
			parent['order'] = parentOrder = []
			parents.append(parent)
			path.append(None)

			if not hasFile and 'size' in parent:
				hasFile = True
		elif level < prevLevel:
			parent = parents[level]
			parentItems = parent['items']
			parentOrder = parent['order']
			del parents[level + 1:]
			del path[level + 1:]

			for p in parents:
				if 'size' in p:
					hasFile = True
					break
			else:
				hasFile = False

		if id in parentItems:
			err('Cannot use ID "{}" again on line {}', id, lineNumber)

		parentItems[id] = item
		parentOrder.append(id)
		path[level] = id

		if idType == ':':
			if hasFile:
				err('Cannot specify a file within a file on line {}', lineNumber)

			fileName = 'json/' + '/'.join(path) + '.json'
			try:
				statinfo = os.stat(fileName + '.gz')
			except OSError, e:
				if e.errno != 2:
					err('Line {}: stat("{}") failed: {} (errno {})',
						lineNumber, fileName + '.gz', e.strerror, e.errno)
				try:
					statinfo = os.stat(fileName)
				except OSError, e:
					err('Line {}: stat("{}") failed: {} (errno {})',
						lineNumber, fileName, e.strerror, e.errno)

			item['size'] = ppSize(statinfo.st_size, fileName)

		upLevel = len(upLevel)
		if upLevel > 0:
			upLevel = level - upLevel
			if upLevel < 0:
				err("Up-level too deep on line {}", lineNumber)

			upLevelItems = parents[upLevel]['items']
			if id in upLevelItems:
				err('Cannot use ID "{}" again for level {} on line {}', id, upLevel, lineNumber)

			upLevelItems[id] = '/'.join(path[upLevel:-1])

	return parents[0]

def main():
	import argparse
	import json
	import ppjson

	parser = argparse.ArgumentParser()
	parser.add_argument('fileName')
	parser.add_argument('--pp', action='store_true')
	args = parser.parse_args()

	lcdFile = open(args.fileName)
	lcdJSON = parseLCD(lcdFile)
	lcdFile.close()

	if args.pp:
		ppjson.prettyPrint(lcdJSON)
	else:
		json.dump(lcdJSON, sys.stdout, separators=(',', ':'))

if __name__ == '__main__':
	main()
