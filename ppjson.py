#!/usr/bin/python
#
# ppjson.py - Pretty Print JSON
#
import sys
import types

def log(message, *formatArgs):
	print >>sys.stderr, message.format(*formatArgs)

level = 0
write = sys.stdout.write

def writeTab():
	write('\t' * level)

def ppDict(o):
	global level, write

	n = len(o)
	if n == 0:
		write('{}')
		return
	if n == 1:
		write('{')
		key, value = o.popitem()
		write('"{}": '.format(key))
		prettyPrint(value)
		write('}')
		return

	write('{\n')
	level += 1
	first = True

	for key in sorted(o.keys()):
		if first:
			first = False
		else:
			write(',\n')

		writeTab()
		write('"{}": '.format(key))
		prettyPrint(o[key])

	level -= 1
	write('\n')
	writeTab()
	write('}')

def ppList(o):
	global level, write

	n = len(o)
	if n == 0:
		write('[]')
		return
	if n == 1:
		write('[')
		prettyPrint(o[0])
		write(']')
		return
	if n == 2 and isinstance(o[0], (float, int, long)) and isinstance(o[1], (float, int, long)):
		write('[{},{}]'.format(o[0], o[1]))
		return

	write('[\n')
	level += 1
	first = True

	for item in o:
		if first:
			first = False
		else:
			write(',\n')

		writeTab()
		prettyPrint(item)

	level -= 1
	write('\n')
	writeTab()
	write(']')

def prettyPrint(o):
	global level, write

	objType = type(o)

	if objType in (str, unicode):
		write('"{}"'.format(o))

	elif objType in (bool, float, int, long):
		write(str(o))

	elif objType is dict:
		ppDict(o)

	elif objType is list:
		ppList(o)

	elif objType is types.NoneType:
		write('null')

	else:
		log('Unrecognized object type: {}', objType)

	if level == 0:
		write('\n')

def main():
	import argparse
	import json

	parser = argparse.ArgumentParser()
	parser.add_argument('fileName')
	args = parser.parse_args()

	jsonFile = open(args.fileName)
	jsonData = json.load(jsonFile)
	jsonFile.close()

	prettyPrint(jsonData)

if __name__ == '__main__':
	main()
