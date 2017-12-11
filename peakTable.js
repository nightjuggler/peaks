/* globals document, Option, window */
"use strict";

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

	return (earthRadius / 2.0 * Math.log((1.0 + y) / (1.0 - y))).toFixed(4);
}
function longitudeToWebMercatorX(longitude)
{
	// See https://en.wikipedia.org/wiki/Mercator_projection#Derivation_of_the_Mercator_projection

	return (earthRadius * longitude * radiansPerDegree).toFixed(4);
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
function round(number, precision)
{
	var p = Math.pow(10, precision);
	return Math.round(number * p) / p;
}
function terriaObject(latitude, longitude)
{
	var distance = 600;
	var deltaLat = deltaLatForDistanceNorth(distance);
	var deltaLong = deltaLongForDistanceEast(latitude, distance * 4/3);

	var camera = {
		west: round(longitude - deltaLong, 6),
		east: round(longitude + deltaLong, 6),
		south: round(latitude - deltaLat, 6),
		north: round(latitude + deltaLat, 6)
	};
	return {
		version: "0.0.05",
		initSources: [
			"init/usgs.json",
			{
				initialCamera: camera,
				homeCamera: camera,
				baseMapName: "USGS Topo WMS",
				viewerMode: "2d"
			}
		]
	};
}

// See https://en.wikipedia.org/wiki/Geometric_Shapes
var rowCollapsedIcon = ' \u25B6';
var rowExpandedIcon = ' \u25BC';
var mapLinkIconUp = '\u25B2';
var mapLinkIconDown = '\u25BC';
var mapLinkHash = {};
var extraRow = {};
var landColumnArray = [];
var climbedColumnArray = [];
var suspendedPeaks = [];
var globalPeakInfo = {
	numPeaks: 0,
	numClimbed: 0,
	numSuspended: 0,
	numSuspendedClimbed: 0,
};
function getPeakListId()
{
	var i, path = window.location.pathname;

	if (path.substr(-5) === '.html' && (i = path.lastIndexOf('/')) >= 0)
		return path.substr(i + 1, path.length - i - 6);

	return null;
}
function initPeakListMenu()
{
	var id = getPeakListId();
	var returnTrue = function() { return true; };
	var returnFalse = function() { return false; };

	var peakLists = [
	{
		id: 'dps',
		name: 'Desert Peaks Section',
		isCAPeak: function(peakId) { return Number(peakId.split('.')[0]) < 6; },
		// Don't bother excepting 1.3 (Boundary Peak) and 2.12 (Grapevine Peak) (both in Nevada)
		isUSPeak: function(peakId) { return Number(peakId.split('.')[0]) < 9; },
	},
	{
		id: 'gbp',
		name: 'Great Basin Peaks List',
		isCAPeak: function(peakId) { return peakId.substr(0, 2) === '1.'; },
	},
	{
		id: 'npc',
		name: 'Nevada Peaks Club',
		// isSierraPeak: Don't bother excepting Mount Rose (3.1)
	},
	{
		id: 'sps',
		name: 'Sierra Peaks Section',
		isCAPeak: returnTrue, // Don't bother excepting Mount Rose (24.4)
		isSierraPeak: returnTrue,
	},
	{
		id: 'odp',
		name: 'Other Desert Peaks',
		isCAPeak: function(peakId) { return Number(peakId.split('.')[0]) < 6; },
	},
	{
		id: 'osp',
		name: 'Other Sierra Peaks',
		isCAPeak: returnTrue,
		isSierraPeak: returnTrue,
	},
	];

	var menu = document.getElementById('peakListMenu');

	for (var pl of peakLists)
	{
		var selected = pl.id === id;
		if (menu)
			menu.add(new Option(pl.name, pl.id, selected, selected));
		if (selected)
		{
			if (!pl.isCAPeak)
				pl.isCAPeak = returnFalse;
			if (!pl.isSierraPeak)
				pl.isSierraPeak = returnFalse;
			if (!pl.isUSPeak)
				pl.isUSPeak = returnTrue;

			globalPeakInfo.peakList = pl;
		}
	}

	if (menu)
	{
		var selectedIndex = menu.selectedIndex;

		menu.addEventListener('change', function() {
			var path = menu.options[menu.selectedIndex].value + '.html';
			var href = window.location.href;

			menu.selectedIndex = selectedIndex;
			window.location = href.substr(0, href.lastIndexOf('/') + 1) + path;
		}, false);
	}
}
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
function createMapLinkBox(latCommaLong, peakId)
{
	var latLong = latCommaLong.split(',');
	var latitude = Number(latLong[0]);
	var longitude = Number(latLong[1]);

	var listNode = document.createElement('UL');

	addMapLink(listNode, 'Andrew Kirmse P300 Peaks',
		'https://fusiontables.googleusercontent.com/embedviz?' +
		'q=select+col0+from+1oAUIuqAirzAY_wkouZLdM4nRYyZ1p4TAg3p6aD2T' +
		'&viz=MAP&h=false&lat=' + latLong[0] + '&lng=' + latLong[1] +
		'&t=4&z=13&l=col0&y=8&tmplt=9&hml=TWO_COL_LAT_LNG')

	if (globalPeakInfo.peakList.isCAPeak(peakId))
		addMapLink(listNode, 'California Protected Areas (CPAD)',
			'http://www.calands.org/map?simple=true&base=topo&y=' + latLong[0] + '&x=' +
			latLong[1] + '&z=12&layers=mapcollab_cpadng_cpad_ownership&opacs=50');

	addMapLink(listNode, 'CalTopo with Land Management',
		'https://caltopo.com/map.html#ll=' + latCommaLong + '&z=14&b=t&o=r&n=0.25&a=sma');

	addMapLink(listNode, 'CalTopo with MB Topo Base Layer',
		'https://caltopo.com/map.html#ll=' + latCommaLong + '&z=16&b=mbt');

	if (globalPeakInfo.peakList.isSierraPeak(peakId))
		addMapLink(listNode, 'Closed Contour',
			'http://www.closedcontour.com/sps/?zoom=7&lat=' + latLong[0] + '&lon=' + latLong[1]);

	var gmap4Link = 'https://mappingsupport.com/p/gmap4.php?ll=' + latCommaLong + '&z=15&t=t4';

	addMapLink(listNode, 'Gmap4 (CalTopo Hi-res Basemap)', gmap4Link);

	addMapLink(listNode, 'Gmap4 with Wilderness Boundaries',
		gmap4Link + ',Wilderness_Boundaries&markers=title=' + legendLink(wildernessMapServer)
		+ '&rest=' + wildernessMapServer + '?name=Wilderness_Boundaries&layers=1&transparent=true'
		+ '&rest=' + wildernessMapServer + '?name=Wilderness_Names&layers=0&transparent=true'
		+ '&rest=' + wildernessMapServer + '?name=Wilderness_Areas&layers=2&transparent=true');

	addMapLink(listNode, 'Google Maps', 'https://www.google.com/maps/@' + latCommaLong + ',10z');

	addMapLink(listNode, 'Interagency Elevation Inventory',
		'https://coast.noaa.gov/inventory/index.html?layers=1&zoom=14&center='
		+ latLong[1] + ',' + latLong[0] + '&basemap=esristreet');

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
		'https://nightjuggler.com/nature/pmap.html?o=dps&o=sps&ll=' + latCommaLong);

	addMapLink(listNode, 'PMap GL (Mapbox GL JS)',
		'https://nightjuggler.com/nature/pmapgl.html?o=dps&o=sps&ll=' + latCommaLong);

	addMapLink(listNode, 'USGS Elevation Point Query',
		'https://nationalmap.gov/epqs/pqs.php'
		+ '?x=' + latLong[1]
		+ '&y=' + latLong[0] + '&units=Feet&output=json');

	addMapLink(listNode, 'USGS National Map (Basic)',
		'https://viewer.nationalmap.gov/basic/?basemap=b1&zoom=15&bbox='
		+ latLong[1] + ',' + latLong[0] + ','
		+ latLong[1] + ',' + latLong[0]);

	addMapLink(listNode, 'USGS National Map (Advanced)',
		'https://viewer.nationalmap.gov/advanced-viewer/viewer/index.html?center='
		+ longitudeToWebMercatorX(longitude) + ','
		+ latitudeToWebMercatorY(latitude) + ',102100&level=15');

	addMapLink(listNode, 'USGS National Map (Terria)',
		'https://viewer.nationalmap.gov/advanced/terriajs-usgs/#start='
			+ encodeURIComponent(JSON.stringify(terriaObject(latitude, longitude)))
			+ '&hideExplorerPanel=1&activeTabId=DataCatalogue');

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

	mapLinkSpan.appendChild(createMapLinkBox(latCommaLong, peakId));
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
	row = extraRow[firstColumn.id];
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
function suspendedHidden()
{
	return suspendedPeaks.length > 0 && suspendedPeaks[0][0].parentNode === null;
}
function peakTableFirstRow()
{
	return document.getElementById('header').parentNode;
}
function decorateTable()
{
	var g = globalPeakInfo;

	initPeakListMenu();
	var isUSPeak = g.peakList.isUSPeak;

	for (var row = peakTableFirstRow(); row !== null; row = nextNode(row.nextSibling, 'TR'))
	{
		var firstColumn = row.children[0];
		if (firstColumn.colSpan !== 1) continue;

		var peakId = firstColumn.firstChild.nodeValue;
		var climbed = row.className.substr(0, 7) === 'climbed';
		var suspended = row.className.substr(-9) === 'suspended';

		g.numPeaks += 1;
		if (climbed) {
			g.numClimbed += 1;
			if (suspended)
				g.numSuspendedClimbed += 1;
		}
		if (firstColumn.rowSpan === 2)
		{
			var spanElement = document.createElement('SPAN');
			spanElement.className = 'expandCollapse';
			spanElement.appendChild(document.createTextNode(rowCollapsedIcon));
			firstColumn.appendChild(spanElement);
			if (!firstColumn.id)
				firstColumn.id = 'p' + g.numPeaks;
			firstColumn.addEventListener('click', clickFirstColumn, false);
			firstColumn.style.cursor = 'pointer';
			firstColumn.rowSpan = 1;

			var nextRow = nextNode(row.nextSibling, 'TR');
			extraRow[firstColumn.id] = nextRow.parentNode.removeChild(nextRow);
		}
		if (isUSPeak(peakId))
		{
			var secondColumn = nextNode(firstColumn.nextSibling, 'TD');
			var lineBreak = nextNode(secondColumn.firstChild, 'BR');
			var mapLinkSpan = document.createElement('SPAN');
			mapLinkSpan.className = 'mapLinkHidden';
			mapLinkSpan.appendChild(document.createTextNode(mapLinkIconUp));
			secondColumn.id = 'm' + g.numPeaks;
			secondColumn.insertBefore(mapLinkSpan, lineBreak);
			secondColumn.addEventListener('mouseenter', showMapLinkIcon, false);
			secondColumn.addEventListener('mouseleave', hideMapLinkIcon, false);
			mapLinkHash[secondColumn.id] = mapLinkSpan;
			mapLinkSpan.addEventListener('click', showMapLinkBox, false);
		}
		if (suspended) {
			g.numSuspended += 1;
			suspendedPeaks.unshift([row, row.nextSibling]);
		}
	}

	removeSuspended();
	updateClimbedCount();
	updateSuspendedCount();
	addClickHandlers();

	if (window.location.hash)
		window.location.replace(window.location.href);

	window.removeEventListener('DOMContentLoaded', decorateTable, false);
}
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
	var addRemoveSuspended = suspendedHidden();
	if (addRemoveSuspended) addSuspended();

	for (var row = peakTableFirstRow(); row !== null; row = nextNode(row.nextSibling, 'TR'))
	{
		var firstColumn = row.children[0];
		if (firstColumn.colSpan === 1) {
			addRemoveFunction(row);
			var row2 = extraRow[firstColumn.id];
			if (row2 && !row2.parentNode)
				row2.children[0].colSpan += colDiff;
		} else
			firstColumn.colSpan += colDiff;
	}

	if (addRemoveSuspended) removeSuspended();
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
function toggleLandColumn()
{
	if (landColumnArray.length === 0) {
		addRemoveColumn(removeLandColumn, -1);
		setPeakTableClass(1, 'noLand');
	} else {
		addRemoveColumn(insertLandColumn, 1);
		setPeakTableClass(1, 'landColumn');
	}
}
function toggleClimbedColumn()
{
	if (climbedColumnArray.length === 0)
		addRemoveColumn(removeClimbedColumn, -1);
	else
		addRemoveColumn(insertClimbedColumn, 1);
}
function updateClimbedCount()
{
	var span = document.getElementById('climbedCountSpan');
	if (!span) return;

	var numClimbed = globalPeakInfo.numClimbed;
	var numPeaks = globalPeakInfo.numPeaks;

	if (suspendedHidden()) {
		numClimbed -= globalPeakInfo.numSuspendedClimbed;
		numPeaks -= globalPeakInfo.numSuspended;
	}

	var text = '(' + numClimbed + '/' + numPeaks + ')';
	if (span.firstChild)
		span.firstChild.nodeValue = text;
	else
		span.appendChild(document.createTextNode(text));
}
function updateSuspendedCount()
{
	var span = document.getElementById('suspendedCountSpan');
	if (!span) return;

	var text = '(' + globalPeakInfo.numSuspended + ')';
	if (span.firstChild)
		span.firstChild.nodeValue = text;
	else
		span.appendChild(document.createTextNode(text));
}
function addSuspended()
{
	for (var item of suspendedPeaks)
	{
		var row = item[0];
		var nextSibling = item[1];
		var firstColumn = row.children[0];
		if (firstColumn.rowSpan === 2)
		{
			var row2 = extraRow[firstColumn.id];
			nextSibling.parentNode.insertBefore(row2, nextSibling);
			nextSibling = row2;
		}
		nextSibling.parentNode.insertBefore(row, nextSibling);
	}
}
function removeSuspended()
{
	for (var item of suspendedPeaks)
	{
		var row = item[0];
		var firstColumn = row.children[0];
		if (firstColumn.rowSpan === 2)
			row.parentNode.removeChild(extraRow[firstColumn.id]);

		row.parentNode.removeChild(row);
	}
}
function toggleSuspended()
{
	if (suspendedHidden())
		addSuspended();
	else
		removeSuspended();

	updateClimbedCount();
}
function changeColors()
{
	var colorMenu = document.getElementById('colorMenu');
	setPeakTableClass(0, colorMenu.options[colorMenu.selectedIndex].value);
}
function addClickHandlers()
{
	var checkbox = document.getElementById('toggleLandColumn');
	if (checkbox) {
		checkbox.checked = landColumnArray.length === 0;
		checkbox.addEventListener('click', toggleLandColumn, false);
	}

	checkbox = document.getElementById('toggleClimbedColumn');
	if (checkbox) {
		checkbox.checked = climbedColumnArray.length === 0;
		checkbox.addEventListener('click', toggleClimbedColumn, false);
	}

	checkbox = document.getElementById('toggleSuspended');
	if (checkbox) {
		checkbox.checked = !suspendedHidden();
		checkbox.addEventListener('click', toggleSuspended, false);
	}

	var colorMenu = document.getElementById('colorMenu');
	if (colorMenu) {
		var color = getPeakTableClass(0);
		for (var option of colorMenu.options)
			if (option.value === color) {
				colorMenu.selectedIndex = option.index;
				break;
			}
		colorMenu.addEventListener('change', changeColors, false);
	}
}
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
window.addEventListener('DOMContentLoaded', decorateTable, false);
