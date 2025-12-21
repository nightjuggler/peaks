#!/usr/local/Cellar/rasterio/1.4.4/libexec/bin/python
import os.path
import re
import sys
import numpy as np
import rasterio
from rasterio import warp
from rasterio.crs import CRS

WGS84 = CRS.from_epsg(4326)

def to_meters(feet): return feet * 12/39.37
def to_feet(meters): return meters * 39.37/12

def get_units(src):
	units = src.units[0]
	if units:
		assert units == 'US survey foot'
		radius, units, precision, u2, p2, to_u2 = 60, 'feet', 1, 'meters', 2, to_meters
	else:
		radius, units, precision, u2, p2, to_u2 = 20, 'meters', 2, 'feet', 1, to_feet
	def elev_str(elev):
		return f'{elev:.{precision}f} {units} = {to_u2(elev):.{p2}f} {u2}'

	return radius, units, elev_str

def process(src, lat, lng):
	in_lat, lat_digits = lat
	in_lng, lng_digits = lng
	lat = in_lat
	lng = in_lng

	wr, units, elev_str = get_units(src)
	ww = 2*wr + 1 # wr = window radius, ww = window width

	(x,), (y,) = warp.transform(WGS84, src.crs, [lng], [lat])
	row, col = src.index(x, y)
	x2, y2 = src.transform * (col, row)
#	assert row, col == src.index(x2, y2)
	w = rasterio.windows.Window(col-wr, row-wr, ww, ww)
	elevs = src.read(indexes=1, window=w)
	elev = elevs[wr, wr]

	print('\nElevation at the converted input latitude/longitude:')
	print(f'{lng:.6f} {lat:.6f} => {x:.3f} {y:.3f} => {col} {row} => {x2:.3f} {y2:.3f}')
	print(elev_str(elev))

	cols = np.tile(range(col-wr, col+wr+1), ww) # 0,1,2,0,1,2,0,1,2
	rows = np.repeat(range(row-wr, row+wr+1), ww) # 0,0,0,1,1,1,2,2,2
	xs, ys = src.transform * (cols, rows)
	lngs, lats = warp.transform(src.crs, WGS84, xs, ys)
	elevs = sorted(zip(elevs.flat, lats, lngs, ys, xs, rows, cols, strict=True))
	elev, lat, lng, y, x, row, col = elevs[-1]

	print(f'\nMaximum elevation within {wr} {units}:')
	print(f'{col} {row} => {x:.3f} {y:.3f} => {lng:.6f} {lat:.6f}')
	print(elev_str(elev))

	print('\nLocations that round to the input latitude/longitude:')
	p_lat = lat_digits + 2
	p_lng = lng_digits + 2
	for elev, lat, lng, y,  x, row, col in elevs:
		if round(lat, lat_digits) == in_lat and round(lng, lng_digits) == in_lng:
			print(f'{col} {row} | {x:.1f} {y:.1f} | '
				f'{lng:.{p_lng}f} {lat:.{p_lat}f} |', elev_str(elev))

def get_filenames(lat, lng):
	lat = lat[0]
	lng = lng[0]
	project = 'CA_SantaClaraCounty_2020_A20'
	filenames = []

	(x,), (y,) = warp.transform(WGS84, CRS.from_epsg(6420), [lng], [lat])
	x = int(round(x)) // 2500 * 25 % 10_000
	y = int(round(y)) // 2500 * 25 % 10_000
	filenames.append(f'USGS_OPR_{project}_{x:04}{y:04}.tif')

	(x,), (y,) = warp.transform(WGS84, CRS.from_epsg(26910), [lng], [lat])
	x = int(round(x)) // 10_000
	y = int(round(y)) // 10_000 + 1
	filenames.append(f'USGS_1M_10_x{x}y{y}_{project}.tif')

	return filenames

ll_pattern = re.compile('-?[0-9]{1,3}(\\.[0-9]{1,14})?')

def get_ll(arg):
	m = ll_pattern.fullmatch(arg)
	return (float(arg), len(m.group(1))-1) if m else None

def main(args):
	if len(args) != 4:
		return f'Usage: {args[0]} <latitude> <longitude> <directory>'

	lat, lng, path = args[1:]
	if not (lat := get_ll(lat)):
		return 'Please specify a valid latitude!'
	if not (lng := get_ll(lng)):
		return 'Please specify a valid longitude!'

	for filename in get_filenames(lat, lng):
		filename = os.path.join(path, filename)
		if os.path.exists(filename):
			print('Opening', filename)
			with rasterio.open(filename) as src:
				process(src, lat, lng)
	print()

if __name__ == '__main__':
	sys.exit(main(sys.argv))
