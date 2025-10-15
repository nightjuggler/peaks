import re
import sys

def convert(dms, direction, name, max_deg, east, west):
	deg, minutes, seconds = dms.split()
	deg = int(deg) + int(minutes)/60 + float(seconds)/3600
	if deg > max_deg:
		print(f'{name}itude must be <= {max_deg}!')
		return None
	if direction == west:
		deg = -deg
	elif direction != east:
		print(f'{name}itude direction must be {east} or {west}!')
		return None
	return format(deg, '.5f')

def main(args):
	if len(args) != 2:
		print('Please specify exactly one command-line argument!')
		return
	arg = args[1]
	deg = '([0-9]{1,3} [0-9]{2} [0-9]{2}\\.[0-9]{5})\\(([NSEW])\\)'
	m = re.match(' '.join((deg, deg)), arg)
	if not m:
		print('Cannot parse command-line argument!')
		print('Example: \'37 11 31.00000(N) 121 25 39.00000(W)\'')
		return

	lat, northsouth, lng, eastwest = m.groups()
	lat = convert(lat, northsouth, 'Lat', 90, 'N', 'S')
	lng = convert(lng, eastwest, 'Long', 180, 'E', 'W')
	if lat and lng:
		print(f'https://caltopo.com/map.html#ll={lat},{lng}&z=16&b=t')

main(sys.argv)
