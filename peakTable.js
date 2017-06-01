var radiansPerDegree = Math.PI / 180.0; // 0.017453292519943295
var degreesPerRadian = 180.0 / Math.PI;
var earthRadius = 6378137.0; // WGS 84 equatorial radius in meters

function haversineDistance(lat1, long1, lat2, long2)
{
	lat1 *= radiansPerDegree;
	lat2 *= radiansPerDegree;
	long1 *= radiansPerDegree;
	long2 *= radiansPerDegree;

	// See https://en.wikipedia.org/wiki/Haversine_formula

	var sinLat = Math.sin((lat2 - lat1) / 2.0);
	var sinLong = Math.sin((long2 - long1) / 2.0);
	var cosLat = Math.cos(lat1) * Math.cos(lat2);

	return 2.0 * earthRadius * Math.asin(Math.sqrt(sinLat * sinLat + cosLat * sinLong * sinLong));
}
function deltaLatForDistanceNorth(distance)
{
	// Derived from solving the Haversine formula for lat2 when long1 == long2

	return (distance / earthRadius) * degreesPerRadian;
}
function deltaLongForDistanceEast(lat1, distance)
{
	// Derived from solving the Haversine formula for long2 when lat1 == lat2

	return 2.0 * Math.asin(Math.sin(distance / (2.0 * earthRadius)) /
		Math.cos(lat1 * radiansPerDegree)) * degreesPerRadian;
}
function latitudeToWebMercatorY(latitude)
{
	// See https://en.wikipedia.org/wiki/Mercator_projection#Alternative_expressions

	var y = Math.sin(latitude * radiansPerDegree);

	return earthRadius / 2.0 * Math.log((1.0 + y) / (1.0 - y));
}
function longitudeToWebMercatorX(longitude)
{
	// See https://en.wikipedia.org/wiki/Mercator_projection#Derivation_of_the_Mercator_projection

	return earthRadius * longitude * radiansPerDegree;
}
function wildernessURL(latitude, longitude)
{
/*
	When querying the ArcGIS VEGeocoder for "lat,long", the bestView extent of the
	result is (1) centered on "lat,long", (2) ymax-ymin (delta latitude) is approx.
	8 miles, and (3) xmax-xmin (delta longitude) is approx. 10.667 miles (8 * 4/3).
*/
	var distance = 8 * 1609.344; // Convert 8 miles to meters
	var deltaLat = deltaLatForDistanceNorth(distance / 2);
	var deltaLong = deltaLongForDistanceEast(latitude, distance * 2/3);

	var xmin = longitude - deltaLong;
	var xmax = longitude + deltaLong;
	var ymin = latitude - deltaLat;
	var ymax = latitude + deltaLat;

	xmin = longitudeToWebMercatorX(xmin);
	xmax = longitudeToWebMercatorX(xmax);
	ymin = latitudeToWebMercatorY(ymin);
	ymax = latitudeToWebMercatorY(ymax);

	return "http://www.wilderness.net/map.cfm" +
		"?xmin=" + xmin +
		"&ymin=" + ymin +
		"&xmax=" + xmax +
		"&ymax=" + ymax;
}
function legendLink(mapServer)
{
	return encodeURIComponent('<b><a href="' + mapServer + '/legend" target="_blank">Legend</a></b>');
}
// See http://www.wilderness.net/NWPS/geography
var wildernessMapServer = 'http://services.cfc.umt.edu/ArcGIS/rest/services/ProctectedAreas/Wilderness/MapServer';

function wccLink(latitude, longitude)
{
	// WCC = National Water and Climate Center
	var url = 'https://www.wcc.nrcs.usda.gov/webmap_beta/#';

	var params = [
		['activeForecastPointsOnly', 'true'],
		['openSections', ''],
		['base', 'esriNgwm'],
		['dataElement', 'SNWD'], // Snow Depth
		['parameter', 'OBS'],
		['frequency', 'DAILY'],
		['dayPart', 'B'],
		['relativeDate', '-1'],
		['lat', latitude],
		['lon', longitude],
		['zoom', '12'],
	];

	var q = []; for (var p of params) q.push(p.join('='));

	return url + q.join('&');
}

// See https://en.wikipedia.org/wiki/Geometric_Shapes
var rowCollapsedIcon = ' \u25B6';
var rowExpandedIcon = ' \u25BC';
var mapLinkIconUp = '\u25B2';
var mapLinkIconDown = '\u25BC';
var mapLinkHash = {};
var extraRow = {};
var isCAPeak = function(peakId) { return true; }
var isUSPeak = function(peakId) { return true; }

function nextNode(node, nodeName)
{
	while (node !== null && node.nodeName !== nodeName)
		node = node.nextSibling;
	return node;
}
function totalOffsetTop(element)
{
	var top = 0;
	for (; element; element = element.offsetParent)
		top += element.offsetTop;
	return top;
}
function addMapLink(listNode, linkText, url)
{
	var listItem = document.createElement('LI');
	var linkNode = document.createElement('A');
	linkNode.href = url;
	linkNode.appendChild(document.createTextNode(linkText));
	listItem.appendChild(linkNode);
	listNode.appendChild(listItem);
}
function createMapLinkBox(latCommaLong, inCalifornia)
{
	var latLong = latCommaLong.split(',');
	var latitude = Number(latLong[0]);
	var longitude = Number(latLong[1]);

	var listNode = document.createElement('UL');

	if (inCalifornia)
		addMapLink(listNode, 'California Protected Areas (CPAD)',
			'http://www.calands.org/map?simple=true&base=topo&y=' + latLong[0] + '&x=' +
			latLong[1] + '&z=12&layers=mapcollab_cpadng_cpad_ownership&opacs=50');

	addMapLink(listNode, 'CalTopo with Land Management',
		'https://caltopo.com/map.html#ll=' + latCommaLong + '&z=14&b=t&o=r&n=0.25&a=sma');

	addMapLink(listNode, 'CalTopo with MB Topo Base Layer',
		'https://caltopo.com/map.html#ll=' + latCommaLong + '&z=16&b=mbt');

	var gmap4Link = 'https://mappingsupport.com/p/gmap4.php?ll=' + latCommaLong + '&z=15&t=t4';

	addMapLink(listNode, 'Gmap4 (CalTopo Hi-res Basemap)', gmap4Link);

	addMapLink(listNode, 'Gmap4 with Wilderness Boundaries',
		gmap4Link + ',Wilderness_Boundaries&markers=title=' + legendLink(wildernessMapServer)
		+ '&rest=' + wildernessMapServer + '?name=Wilderness_Boundaries&layers=1&transparent=true'
		+ '&rest=' + wildernessMapServer + '?name=Wilderness_Names&layers=0&transparent=true'
		+ '&rest=' + wildernessMapServer + '?name=Wilderness_Areas&layers=2&transparent=true');

	addMapLink(listNode, 'Google Maps', 'https://www.google.com/maps/@' + latCommaLong + ',10z');

	addMapLink(listNode, 'NGS Datasheets (Radial Search)',
		'https://www.ngs.noaa.gov/cgi-bin/ds_radius.prl'
		+ '?FormatBox=Decimal%20Degrees'
		+ '&selectedFormat=Decimal%20Degrees'
		+ '&DLatBox=' + latLong[0]
		+ '&DLonBox=' + latLong[1].substr(1)
		+ '&RadBox=1'
		+ '&TypeSelected=X-0'
		+ '&StabilSelected=0'
		+ '&SubmitBtn=Submit'
		+ '&dump_app_trace=false'
		+ '&db_debug=false');

	addMapLink(listNode, 'PMap (Mapbox.js)',
		'https://nightjuggler.com/nature/pmap.html?o=dps&o=sps&ll=' + latCommaLong)

	addMapLink(listNode, 'PMap GL (Mapbox GL JS)',
		'https://nightjuggler.com/nature/pmapgl.html?o=dps&o=sps&ll=' + latCommaLong)

	addMapLink(listNode, 'USGS National Map',
		'https://viewer.nationalmap.gov/basic/?basemap=b1&zoom=14&bbox='
		+ latLong[1] + ',' + latLong[0] + ','
		+ latLong[1] + ',' + latLong[0]);

	addMapLink(listNode, 'USGS National Map (Legacy)',
		'https://viewer.nationalmap.gov/viewer/?p=default&b=base1&l=14'
		+ '&x=' + longitudeToWebMercatorX(longitude)
		+ '&y=' + latitudeToWebMercatorY(latitude));

	addMapLink(listNode, 'USGS TopoView',
		'https://ngmdb.usgs.gov/maps/topoview/viewer/#15/' + latLong[0] + '/' + latLong[1]);

	addMapLink(listNode, 'Water & Climate Center', wccLink(latLong[0], latLong[1]));

	addMapLink(listNode, 'Wilderness.net', wildernessURL(latitude, longitude));

	var mapLinkBox = document.createElement('DIV');
	mapLinkBox.className = 'mapLinkBox';
	mapLinkBox.appendChild(listNode);
	return mapLinkBox;
}
function addMapLinkBox(mapLinkSpan)
{
	var secondColumn = mapLinkSpan.parentNode;
	var firstColumn = nextNode(secondColumn.parentNode.firstChild, 'TD');

	var peakId = firstColumn.firstChild.nodeValue;
	var mapLink = nextNode(secondColumn.firstChild, 'A');
	var latCommaLong = mapLink.search.split('&')[0].split('=')[1];

	mapLinkSpan.appendChild(createMapLinkBox(latCommaLong, isCAPeak(peakId)));
}
function showMapLinkBox(event)
{
	var mapLinkSpan = event.currentTarget;
	mapLinkSpan.className = 'mapLinkWithBox';
	if (mapLinkSpan.lastChild !== mapLinkSpan.firstChild)
		mapLinkSpan.lastChild.style.display = 'block';
	else
		addMapLinkBox(mapLinkSpan);

	var offsetTop = totalOffsetTop(mapLinkSpan);
	var mapLinkBox = mapLinkSpan.lastChild;
	if (offsetTop - window.scrollY > mapLinkBox.offsetHeight) {
		mapLinkBox.style.top = 'auto';
		mapLinkBox.style.bottom = '14px';
		mapLinkSpan.firstChild.nodeValue = mapLinkIconUp;
	} else {
		mapLinkBox.style.top = '14px';
		mapLinkBox.style.bottom = 'auto';
		mapLinkSpan.firstChild.nodeValue = mapLinkIconDown;
	}
}
function showMapLinkIcon(event)
{
	var mapLinkSpan = mapLinkHash[event.currentTarget.id];
	mapLinkSpan.className = 'mapLink';
}
function hideMapLinkIcon(event)
{
	var mapLinkSpan = mapLinkHash[event.currentTarget.id];
	if (mapLinkSpan.lastChild !== mapLinkSpan.firstChild)
		mapLinkSpan.lastChild.style.display = 'none';
	mapLinkSpan.className = 'mapLinkHidden';
}
function clickFirstColumn(event)
{
	var firstColumn = event.currentTarget;
	var row = firstColumn.parentNode;
	var peakTable = row.parentNode;
	var nextRow = nextNode(row.nextSibling, 'TR');
	var peakId = firstColumn.id;
	row = extraRow[peakId];
	if (row.parentNode === null) {
		peakTable.insertBefore(row, nextRow);
		firstColumn.rowSpan = 2;
		firstColumn.lastChild.firstChild.nodeValue = rowExpandedIcon;
	} else {
		firstColumn.rowSpan = 1;
		peakTable.removeChild(row);
		firstColumn.lastChild.firstChild.nodeValue = rowCollapsedIcon;
	}
	return false;
}
function decorateTable()
{
	var peakNumber = 0;
	var peakTable = document.getElementById('peakTable');
	peakTable = nextNode(peakTable.firstChild, 'TBODY');
	var row = nextNode(peakTable.firstChild, 'TR');
	while (row !== null)
	{
		var firstColumn = nextNode(row.firstChild, 'TD');
		row = nextNode(row.nextSibling, 'TR');
		if (firstColumn.colSpan !== 1) continue;
		var peakId = firstColumn.firstChild.nodeValue;
		peakNumber = peakNumber + 1;
		if (firstColumn.rowSpan === 2)
		{
			var spanElement = document.createElement('SPAN');
			spanElement.className = 'expandCollapse';
			spanElement.appendChild(document.createTextNode(rowCollapsedIcon));
			firstColumn.appendChild(spanElement);
			if (!firstColumn.id)
				firstColumn.id = 'p' + peakNumber;
			firstColumn.addEventListener('click', clickFirstColumn, false);
			firstColumn.style.cursor = 'pointer';
			firstColumn.rowSpan = 1;

			var nextRow = nextNode(row.nextSibling, 'TR');
			extraRow[firstColumn.id] = peakTable.removeChild(row);
			row = nextRow;
		}
		if (isUSPeak(peakId))
		{
			var secondColumn = nextNode(firstColumn.nextSibling, 'TD');
			var lineBreak = nextNode(secondColumn.firstChild, 'BR');
			var mapLinkSpan = document.createElement('SPAN');
			mapLinkSpan.className = 'mapLinkHidden';
			mapLinkSpan.appendChild(document.createTextNode(mapLinkIconUp));
			secondColumn.id = 'm' + peakNumber;
			secondColumn.insertBefore(mapLinkSpan, lineBreak);
			secondColumn.addEventListener('mouseenter', showMapLinkIcon, false);
			secondColumn.addEventListener('mouseleave', hideMapLinkIcon, false);
			mapLinkHash[secondColumn.id] = mapLinkSpan;
			mapLinkSpan.addEventListener('click', showMapLinkBox, false);
		}
	}
	if (window.location.hash)
		window.location.replace(window.location.href);
}
window.addEventListener('DOMContentLoaded', decorateTable, false);

var landColumnArray = [];
var climbedColumnArray = [];

function removeLandColumn(row)
{
	landColumnArray.push(row.removeChild(row.children[2]));
}
function insertLandColumn(row)
{
	row.insertBefore(landColumnArray.shift(), row.children[2]);
}
function removeClimbedColumn(row)
{
	climbedColumnArray.push(row.removeChild(row.children[row.children.length - 1]));
}
function insertClimbedColumn(row)
{
	row.appendChild(climbedColumnArray.shift());
}
function addRemoveColumn(addRemoveFunction, colDiff)
{
	var row = document.getElementById('header').parentNode;
	while (row != null)
	{
		var firstColumn = row.children[0];
		if (firstColumn.colSpan === 1) {
			addRemoveFunction(row);
			var row2 = extraRow[firstColumn.id];
			if (row2 && !row2.parentNode)
				row2.children[0].colSpan += colDiff;
		} else {
			firstColumn.colSpan += colDiff;
		}
		row = nextNode(row.nextSibling, 'TR');
	}
}
function getPeakTableClass(i)
{
	var peakTable = document.getElementById('peakTable');
	return peakTable.className.split(' ')[i];
}
function setPeakTableClass(i, className)
{
	var peakTable = document.getElementById('peakTable');
	var classList = peakTable.className.split(' ');
	classList[i] = className;
	peakTable.className = classList.join(' ');
}
function toggleLandColumn(event)
{
	if (landColumnArray.length === 0) {
		addRemoveColumn(removeLandColumn, -1);
		setPeakTableClass(1, 'noLand');
	} else {
		addRemoveColumn(insertLandColumn, 1);
		setPeakTableClass(1, 'landColumn');
	}
}
function toggleClimbedColumn(event)
{
	if (climbedColumnArray.length === 0)
		addRemoveColumn(removeClimbedColumn, -1);
	else
		addRemoveColumn(insertClimbedColumn, 1);
}
function changeColors(event)
{
	var colorMenu = document.getElementById('colorMenu');
	setPeakTableClass(0, colorMenu.options[colorMenu.selectedIndex].value);
}
function addClickHandlers()
{
	var checkbox;

	checkbox = document.getElementById('toggleLandColumn');
	checkbox.checked = landColumnArray.length === 0;
	checkbox.addEventListener('click', toggleLandColumn, false);

	checkbox = document.getElementById('toggleClimbedColumn');
	checkbox.checked = climbedColumnArray.length === 0;
	checkbox.addEventListener('click', toggleClimbedColumn, false);

	var colorMenu = document.getElementById('colorMenu');
	var numColors = colorMenu.options.length;
	var color = getPeakTableClass(0);
	for (var i = 0; i < numColors; ++i)
		if (colorMenu.options[i].value === color) {
			colorMenu.selectedIndex = i;
			break;
		}
	colorMenu.addEventListener('change', changeColors, false);
}
window.addEventListener('DOMContentLoaded', addClickHandlers, false);

function showLegend()
{
	var legend = document.getElementById('legend');
	legend.style.display = 'block';
}
function hideLegend()
{
	var legend = document.getElementById('legend');
	legend.style.display = 'none';
}
