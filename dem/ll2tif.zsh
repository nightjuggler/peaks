#
# The USGS_OPR_CA_SantaClaraCounty_2020_A20_{x}{y}.tif tiles at
# https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Elevation/OPR/Projects/CA_SantaClaraCounty_2020_A20/CA_SantaClaraCounty_2020/
# use EPSG 6420 (https://epsg.io/6420) (NAD83(2011) / California zone 3 (ftUS))
# OPR = Original Product Resolution
# These tiles are also available Deflate-compressed at
# https://noaa-nos-coastal-lidar-pds.s3.us-east-1.amazonaws.com/dem/CA_Santa_Clara_DEM_2020_9330/index.html
#
# x ranges from 0525 to 3675 in increments of 25
# y ranges from 7700 to 0150 in increments of 25
#
# The x and y correspond to the bottom-left corner of the tile.
# int(round(src.bounds.left,7)) == (x + 60_000) * 100
# int(round(src.bounds.bottom,7)) == (y + (20_000 if y < 1_000 else 10_000)) * 100
#
# The data in these tiles is a 2500 x 2500 float32 array of elevations in feet.
# int(round(src.bounds.left,7)) + 2500 == int(round(src.bounds.right,7))
# int(round(src.bounds.bottom,7)) + 2500 == int(round(src.bounds.top,7))
#
# To determine the filename of the tile that contains a given lat/lng, convert the lat/lng
# to EPSG 6420 easting (x) and northing (y) and take digits 2 through 5 of each coordinate.
#
proj=/usr/local/bin/proj
project='CA_SantaClaraCounty_2020_A20'

ll2tif_opr() {
	if (( $# != 2 )) { return }
	xy=(`echo $2 $1 | $proj EPSG:6420 -f '%.0f'`)
	(( x = xy[1] / 2500 * 25 % 10000 ))
	(( y = xy[2] / 2500 * 25 % 10000 ))
	print -n $xy ''
	print -f 'USGS_OPR_%s_%04d%04d.tif\n' $project $x $y
}
#
# The USGS_1M_10_x{x}y{y}_CA_SantaClaraCounty_2020_A20.tif tiles at
# https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Elevation/1m/Projects/CA_SantaClaraCounty_2020_A20/
# use EPSG 26910 (https://epsg.io/26910) (NAD83 / UTM zone 10N)
#
# x ranges from 56 to 66 in increments of 1
# y ranges from 408 to 416 in increments of 1
#
# The x and y correspond to the top-left corner of the tile.
# int(round(src.bounds.left,4)) == x*10_000 - 6
# int(round(src.bounds.top,4)) == y*10_000 + 6
#
# The data in these tiles is a 10012 x 10012 float32 array of elevations in meters.
# int(round(src.bounds.left,4)) + 10_012 == int(round(src.bounds.right,4))
# int(round(src.bounds.top,4)) - 10_012 == int(round(src.bounds.bottom,4))
#
ll2tif_1m() {
	if (( $# != 2 )) { return }
	xy=(`echo $2 $1 | $proj EPSG:26910 -f '%.0f'`)
	(( x = xy[1] / 10000 ))
	(( y = xy[2] / 10000 + 1 ))
	print -n $xy ''
	print -f 'USGS_1M_10_x%dy%d_%s.tif\n' $x $y $project
}
ll2tif_test() {
	ll2tif_opr 37.21723 -121.44024 # x=6287881 y=1902943 (ft)
	ll2tif_1m 37.21723 -121.44024 # x=638390 y=4120110 (m)
}
