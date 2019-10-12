/* globals document, Option, window */
'use strict';

var radiansPerDegree = Math.PI / 180.0; // 0.017453292519943295
var degreesPerRadian = 180.0 / Math.PI;
var earthRadius = 6378137.0; // WGS 84 equatorial radius in meters

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
function extentForLatLong(latitude, longitude)
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

	return [xmin, ymin, xmax, ymax, '102113'].join(',');
}
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
	var distance = 3000; // meters
	var deltaLat = deltaLatForDistanceNorth(distance);
	var deltaLong = deltaLongForDistanceEast(latitude, distance);

	var camera = {
		west: round(longitude - deltaLong, 6),
		east: round(longitude + deltaLong, 6),
		south: round(latitude - deltaLat, 6),
		north: round(latitude + deltaLat, 6)
	};
	return {
		initSources: [
			{
				initialCamera: camera
			}
		]
	};
}

// See https://en.wikipedia.org/wiki/Geometric_Shapes
var rowCollapsedIcon = ' \u25B6\uFE0E';
var rowExpandedIcon = ' \u25BC';
var mapLinkIconUp = '\u25B2';
var mapLinkIconDown = '\u25BC';
var mapLinkHash = {};
var extraRow = {};
var landColumnArray = [];
var climbedColumnArray = [];
var activePopup = null;
var mobileMode = false;
var globalPeakInfo = {
	pathPrefix: '',
	peakListId: '',

	numPeaks: 0,
	numClimbed: 0,
	numDelisted: 0,
	numDelistedClimbed: 0,
	numSuspended: 0,
	numSuspendedClimbed: 0,

	delistedPeaks: [],
	suspendedPeaks: [],

	showDelisted: false,
	showSuspended: false,

	flags: {
		country_US: true,
		state_CA: true,
		BigSur: false,
		CC: false,
	},
};
function isValidParam(s)
{
	return s.length <= 16 && s.match(/^[a-z][_0-9A-Za-z]*$/) !== null;
}
function parseQueryString()
{
	var q = window.location.search;

	if (typeof q !== 'string' || q.charAt(0) !== '?') return;

	var flags = {
		showDelisted: 'showDelisted',
		showSuspended: 'showSuspended',
	};
	var handlers = {
	};

	for (var s of q.substring(1).split('&'))
	{
		var i = s.indexOf('=');
		if (i < 0 && isValidParam(s) && flags[s]) {
			globalPeakInfo[flags[s]] = true;
			continue;
		}
		if (i < 1 || i === s.length - 1) continue;
		var k = s.substring(0, i);
		var v = s.substring(i + 1);

		if (isValidParam(k) && handlers[k])
			handlers[k](v);
	}
}
function newPeakFlags(parentFlags)
{
	return {
		country_US: parentFlags.country_US,
		state_CA: parentFlags.state_CA,
		CC: parentFlags.CC,
	};
}
function getPeakFlag(attrValue, trueValue)
{
	for (var value of attrValue.split('/'))
		if (value === trueValue)
			return true;
	return false;
}
function setPeakFlag(row, parentFlags, attrName, trueValue)
{
	var attrValue = row.dataset[attrName];
	if (!attrValue) return;

	var flagName = attrName + '_' + trueValue;
	var flagValue = getPeakFlag(attrValue, trueValue);
	if (flagValue === parentFlags[flagName]) return;

	if (row.peakFlags === parentFlags)
		row.peakFlags = newPeakFlags(parentFlags);
	row.peakFlags[flagName] = flagValue;
}
function setPeakFlags(row, parentFlags, attrName, setValue)
{
	var attrValue = row.dataset[attrName];
	if (!attrValue) return;

	for (var flagName of attrValue.split(','))
	{
		var flagValue = parentFlags[flagName];
		if (typeof flagValue !== 'boolean' || flagValue === setValue) continue;
		if (row.peakFlags === parentFlags)
			row.peakFlags = newPeakFlags(parentFlags);
		row.peakFlags[flagName] = setValue;
	}
}
function setRowFlags(row, parentFlags)
{
	row.peakFlags = parentFlags;
	setPeakFlag(row, parentFlags, 'country', 'US');
	setPeakFlag(row, parentFlags, 'state', 'CA');
	setPeakFlags(row, parentFlags, 'enable', true);
	setPeakFlags(row, parentFlags, 'disable', false);
}
function getPeakListId()
{
	var path = window.location.href;
	var n = path.length;
	var i = -1;
	var j = 0;

	while (j < n) {
		var ch = path.charAt(j);
		if (ch === '/')
			i = j;
		else if (ch === '?' || ch === '#')
			break;
		j += 1;
	}

	globalPeakInfo.pathPrefix = path.substring(0, i + 1);

	if (path.endsWith('.html', j))
		return path.substring(i + 1, j - 5);

	return null;
}
function initPeakListMenu()
{
	var id = getPeakListId();

	var peakLists = [
		{id: 'dps', name: 'Desert Peaks Section'},
		{id: 'gbp', name: 'Great Basin Peaks List'},
		{id: 'hps', name: 'Hundred Peaks Section'},
		{id: 'lpc', name: 'Lower Peaks Committee'},
		{id: 'npc', name: 'Nevada Peaks Club'},
		{id: 'sps', name: 'Sierra Peaks Section'},
		{id: 'ogul',name: 'Tahoe Ogul Peaks List'},
		{id: 'odp', name: 'Other Desert Peaks'},
		{id: 'osp', name: 'Other Sierra Peaks'},
		{id: 'ocap',name: 'Other California Peaks'},
		{id: 'owp', name: 'Other Western Peaks'},
	];

	var menu = document.getElementById('peakListMenu');

	for (var pl of peakLists)
	{
		var selected = pl.id === id;
		if (menu)
			menu.add(new Option(pl.name, pl.id, selected, selected));
		if (selected)
			globalPeakInfo.peakListId = id;
	}

	if (menu)
	{
		var selectedIndex = menu.selectedIndex;

		menu.addEventListener('change', function() {
			var id = peakLists[menu.selectedIndex].id;

			menu.selectedIndex = selectedIndex;

			window.location = globalPeakInfo.pathPrefix + id + '.html';
		}, false);
	}
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
function createMapLinkBox(latCommaLong, peakFlags)
{
	var latLong = latCommaLong.split(',');
	var latitude = Number(latLong[0]);
	var longitude = Number(latLong[1]);
	var extent = extentForLatLong(latitude, longitude);
	var pathPrefix = globalPeakInfo.pathPrefix;
	var peakListId = globalPeakInfo.peakListId;

	var listNode = document.createElement('UL');

	addMapLink(listNode, 'Andrew Kirmse P300 Peaks',
		'https://fusiontables.googleusercontent.com/embedviz?' +
		'q=select+col0+from+1oAUIuqAirzAY_wkouZLdM4nRYyZ1p4TAg3p6aD2T' +
		'&viz=MAP&h=false&lat=' + latLong[0] + '&lng=' + latLong[1] +
		'&t=4&z=13&l=col0&y=8&tmplt=9&hml=TWO_COL_LAT_LNG');

	if (peakFlags.BigSur)
		addMapLink(listNode, 'Big Sur Trailmap',
			'https://bigsurtrailmap.net/interactivemap.html?mode=trailmap&latlon=' +
			latCommaLong + '&zoom=15&bkgmap=USGS+Quad');

	addMapLink(listNode, 'BLM National Data',
		'https://blm-egis.maps.arcgis.com/apps/webappviewer/index.html?' +
		'id=6f0da4c7931440a8a80bfe20eddd7550&extent=' + extent);

	if (peakFlags.state_CA)
		addMapLink(listNode, 'California Protected Areas (CPAD)',
			'http://www.mapcollaborator.org/cpad/?base=topo&y=' + latLong[0] + '&x=' +
			latLong[1] + '&z=12&layers=mapcollab_cpadng_cpad_ownership&opacs=50');

	addMapLink(listNode, 'CalTopo with Land Management',
		'https://caltopo.com/map.html#ll=' + latCommaLong + '&z=14&b=t&o=r&n=0.25&a=sma');

	addMapLink(listNode, 'CalTopo with Map Builder Topo',
		'https://caltopo.com/map.html#ll=' + latCommaLong + '&z=15&b=mbt');

	addMapLink(listNode, 'CalTopo with USGS 7.5\' Topo',
		'https://caltopo.com/map.html#ll=' + latCommaLong + '&z=15&b=t&o=r&n=0.25');

	if (peakFlags.CC)
		addMapLink(listNode, 'Closed Contour',
			'http://www.closedcontour.com/sps/?zoom=7&lat=' + latLong[0] + '&lon=' + latLong[1]);

	addMapLink(listNode, 'GeoMAC Wildfire Viewer',
		'https://nifc.maps.arcgis.com/apps/webappviewer/index.html?' +
		'id=fa067b6b21534df283a87acc3ae3227c&extent=' + extent);

	addMapLink(listNode, 'GIS Surfer',
		'https://mappingsupport.com/p2/gissurfer.php?center=' + latCommaLong + '&zoom=14&basemap=USA_basemap');

	addMapLink(listNode, 'Google Maps', 'https://www.google.com/maps/@' + latCommaLong + ',10z');

	addMapLink(listNode, 'Interagency Elevation Inventory',
		'https://coast.noaa.gov/inventory/index.html?layers=1&zoom=14&center=' +
		latLong[1] + ',' + latLong[0] + '&basemap=esristreet');

	addMapLink(listNode, 'NGS Datasheets (Radial Search)',
		'https://www.ngs.noaa.gov/cgi-bin/ds_radius.prl'
		+ '?FormatBox=Decimal%20Degrees'
		+ '&selectedFormat=Decimal%20Degrees'
		+ '&DLatBox=' + latLong[0]
		+ '&DLonBox=' + latLong[1].substring(1)
		+ '&RadBox=1'
		+ '&TypeSelected=X-0'
		+ '&StabilSelected=0'
		+ '&SubmitBtn=Submit'
		+ '&dump_app_trace=false'
		+ '&db_debug=false');

	addMapLink(listNode, 'OpenStreetMap',
		'https://www.openstreetmap.org/#map=16/' + latLong[0] + '/' + latLong[1] + '&layers=C');

	addMapLink(listNode, 'OpenTopoMap',
		'https://opentopomap.org/#map=14/' + latLong[0] + '/' + latLong[1]);

	addMapLink(listNode, 'PMap (Leaflet)',
		pathPrefix + 'pmap.html?o=' + peakListId + '&z=15&ll=' + latCommaLong);

	addMapLink(listNode, 'PMap (Mapbox.js)',
		pathPrefix + 'pmapmb.html?o=' + peakListId + '&z=15&ll=' + latCommaLong);

	addMapLink(listNode, 'PMap with Wilderness Areas',
		pathPrefix + 'pmap.html?o=' + peakListId + '&ot=w&q=w&z=15&ll=' + latCommaLong);

	addMapLink(listNode, 'PMap GL (Mapbox GL JS)',
		pathPrefix + 'pmapgl.html?o=' + peakListId + '&z=15&ll=' + latCommaLong);

	addMapLink(listNode, 'SkyVector',
		'https://skyvector.com/?ll=' + latCommaLong + '&chart=301&zoom=1');

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

	addMapLink(listNode, 'USGS Protected Areas Database',
		'https://maps.usgs.gov/padus/#start='
		+ encodeURIComponent(JSON.stringify(terriaObject(latitude, longitude))));

	addMapLink(listNode, 'USGS TopoView',
		'https://ngmdb.usgs.gov/maps/topoview/viewer/#15/' + latLong[0] + '/' + latLong[1]);

	addMapLink(listNode, 'Water & Climate Center', wccLink(latLong[0], latLong[1]));

	addMapLink(listNode, 'Wilderness.net',
		'https://umontana.maps.arcgis.com/apps/webappviewer/index.html?' +
		'id=a415bca07f0a4bee9f0e894b0db5c3b6&extent=' + extent);

	var llSpan = document.createElement('SPAN');
	llSpan.style.color = 'black';
	llSpan.style.cursor = 'pointer';
	var deg = '\u00B0';
	var llText = (latitude < 0 ? -latitude + deg + 'S ' : latitude + deg + 'N ') +
		(longitude < 0 ? -longitude + deg + 'W' : longitude + deg + 'E');
	llSpan.appendChild(document.createTextNode(llText));
	llSpan.addEventListener('click', function() {
		llSpan.firstChild.nodeValue = latCommaLong;
		window.getSelection().selectAllChildren(llSpan);
		document.execCommand('copy');
		llSpan.firstChild.nodeValue = llText;
	});

	var llDiv = document.createElement('DIV');
	llDiv.style.textAlign = 'center';
	llDiv.style.paddingBottom = '2px';
	llDiv.appendChild(llSpan);

	var mapLinkBox = document.createElement('DIV');
	mapLinkBox.className = 'mapLinkBox';
	mapLinkBox.appendChild(llDiv);
	mapLinkBox.appendChild(listNode);
	return mapLinkBox;
}
function addMapLinkBox(mapLinkSpan)
{
	var secondColumn = mapLinkSpan.parentNode;
	var peakFlags = secondColumn.parentNode.peakFlags;

	var mapLink = secondColumn.firstElementChild;
	var latCommaLong = mapLink.href.split('#')[1].split('&')[0].split('=')[1];

	mapLinkSpan.appendChild(createMapLinkBox(latCommaLong, peakFlags));
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
	setActivePopup(mapLinkBox);
}
function showMapLinkBoxOnEnter(event)
{
	if (event.key !== 'Enter')
		return true;

	let mapLinkSpan = event.currentTarget;
	if (mapLinkSpan.lastChild === activePopup)
		closeActivePopup();
	else
		showMapLinkBox(event);

	return false;
}
function showMapLinkIcon(event)
{
	var mapLinkSpan = mapLinkHash[event.currentTarget.id];

	if (mapLinkSpan.lastChild !== activePopup)
		mapLinkSpan.className = 'mapLink';
}
function hideMapLinkIcon(event)
{
	var mapLinkSpan = mapLinkHash[event.currentTarget.id];

	if (mapLinkSpan.lastChild === activePopup)
		closeActivePopup();
	else
		mapLinkSpan.className = 'mapLinkHidden';
}
function clickFirstColumn(event)
{
	var firstColumn = event.currentTarget;
	var row = firstColumn.parentNode;
	var peakTable = row.parentNode;
	var nextRow = row.nextElementSibling;
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
function hiddenRows(rows)
{
	return rows.length > 0 && rows[0][0].parentNode === null;
}
function delistedHidden()
{
	return hiddenRows(globalPeakInfo.delistedPeaks);
}
function suspendedHidden()
{
	return hiddenRows(globalPeakInfo.suspendedPeaks);
}
function addListLink(row)
{
	var refArray = row.dataset.also ? row.dataset.also.split(' ') : [];

	if (row.dataset.from)
		refArray.unshift(row.dataset.from);

	const pll = document.createElement('DIV');
	pll.className = 'pll';

	for (var ref of refArray)
	{
		var m = ref.match(/^((?:[A-Z]|x[0-9])[0-9A-Z]*(?:[A-Z]|[0-9]x))([0-9]+)\.[0-9]+[ab]?([ds]?)$/);
		if (m === null) continue;

		var htmlId = m[1];
		var listId = htmlId;
		var sectionNumber = m[2];

		if (listId.charAt(0) === 'x')
			listId = listId.substring(1);
		if (listId.charAt(listId.length - 1) === 'x')
			listId = listId.substring(0, listId.length - 1);

		var linkHref = listId.toLowerCase() + '.html';
		var linkText = listId;

		if (m[3] === 'd') {
			linkHref += '?showDelisted';
			linkText = 'ex-' + listId;
		}
		else if (m[3] === 's') {
			linkHref += '?showSuspended';
			linkText = '(' + listId + ')';
		}

		var listLink = document.createElement('A');
		listLink.href = globalPeakInfo.pathPrefix + linkHref + '#' + htmlId + sectionNumber;
		listLink.appendChild(document.createTextNode(linkText));

		if (pll.children.length !== 0)
			pll.appendChild(document.createTextNode(' '));
		pll.appendChild(listLink);
	}

	row.children[1].appendChild(pll);
}
function peakTableFirstRow()
{
	return document.getElementById('firstRow');
}
function decorateTable()
{
	var g = globalPeakInfo;
	var sectionFlags = g.flags;

	parseQueryString();
	initPeakListMenu();

	for (var a of document.getElementsByTagName('a'))
		if (a.hostname === 'caltopo.com' && a.href.substring(a.href.length - 4) === '&b=t')
			a.href += '&o=r&n=0.2';

	const firstRow = peakTableFirstRow();

	for (var row = firstRow; row !== null; row = row.nextElementSibling)
	{
		var firstColumn = row.children[0];
		if (firstColumn.colSpan !== 1) {
			if (row.className === 'section') {
				setRowFlags(row, g.flags);
				sectionFlags = row.peakFlags;
				if (row === firstRow)
					g.flags = sectionFlags;
			}
			continue;
		}

		setRowFlags(row, sectionFlags);
		var climbed = row.className.slice(0, 7) === 'climbed';
		var delisted = row.className.slice(-8) === 'delisted';
		var suspended = row.className.slice(-9) === 'suspended';

		g.numPeaks += 1;
		if (climbed) {
			g.numClimbed += 1;
			if (delisted)
				g.numDelistedClimbed += 1;
			else if (suspended)
				g.numSuspendedClimbed += 1;
		}
		if (row.dataset.from || row.dataset.also)
			addListLink(row);
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

			var nextRow = row.nextElementSibling;
			extraRow[firstColumn.id] = nextRow.parentNode.removeChild(nextRow);
		}
		if (row.peakFlags.country_US)
		{
			var secondColumn = firstColumn.nextElementSibling;
			var lineBreak = secondColumn.firstElementChild.nextElementSibling;
			var mapLinkSpan = document.createElement('SPAN');
			mapLinkSpan.className = 'mapLinkHidden';
			mapLinkSpan.appendChild(document.createTextNode(mapLinkIconUp));
			mapLinkSpan.tabIndex = 0;
			secondColumn.id = 'm' + g.numPeaks;
			secondColumn.insertBefore(mapLinkSpan, lineBreak);
			secondColumn.addEventListener('mouseenter', showMapLinkIcon, false);
			secondColumn.addEventListener('mouseleave', hideMapLinkIcon, false);
			mapLinkHash[secondColumn.id] = mapLinkSpan;
			mapLinkSpan.addEventListener('click', showMapLinkBox, false);
			mapLinkSpan.addEventListener('keydown', showMapLinkBoxOnEnter, false);
		}
		if (delisted) {
			g.numDelisted += 1;
			g.delistedPeaks.unshift([row, row.nextSibling]);
		}
		else if (suspended) {
			g.numSuspended += 1;
			g.suspendedPeaks.unshift([row, row.nextSibling]);
		}
	}

	if (!g.showDelisted)
		removeRows(g.delistedPeaks);
	if (!g.showSuspended)
		removeRows(g.suspendedPeaks);
	updateClimbedCount();
	setCount('delistedCountSpan', g.numDelisted);
	setCount('suspendedCountSpan', g.numSuspended);
	addClickHandlers(firstRow);
	if (window.matchMedia('(hover: none)').matches)
		clickMobile();

	if (window.location.hash)
		window.location.replace(window.location.href);

	window.removeEventListener('DOMContentLoaded', decorateTable, false);
}
function closeActivePopup(event)
{
	if (!activePopup) return;

	const mapLinkSpan = activePopup.parentNode;

	if (event)
		for (let node = event.target; node; node = node.parentNode)
			if (node === mapLinkSpan) return;

	activePopup.style.display = 'none';
	mapLinkSpan.className = mobileMode ? 'mapLink' : 'mapLinkHidden';
	mapLinkSpan.addEventListener('click', showMapLinkBox, false);
	activePopup = null;

	if (mobileMode) {
		const body = document.body;
		body.removeEventListener('touchstart', closeActivePopup);
		body.removeEventListener('mousedown', closeActivePopup);
	}
}
function setActivePopup(element)
{
	closeActivePopup();

	activePopup = element;
	activePopup.parentNode.removeEventListener('click', showMapLinkBox, false);

	if (mobileMode) {
		const body = document.body;
		body.addEventListener('touchstart', closeActivePopup);
		body.addEventListener('mousedown', closeActivePopup);
	}
}
function clickMobile()
{
	let elem = document.getElementById('headerRight');
	if (!elem) return;

	elem = elem.firstChild; // the div containing the text node
	if (!elem) return;

	elem = elem.firstChild; // the text node
	if (!elem) return;

	closeActivePopup();

	if (elem.nodeValue === 'MOBILE')
	{
		Object.values(mapLinkHash).forEach(mapLinkSpan => {
			const parent = mapLinkSpan.parentNode;
			parent.removeEventListener('mouseenter', showMapLinkIcon, false);
			parent.removeEventListener('mouseleave', hideMapLinkIcon, false);
			mapLinkSpan.className = 'mapLink';
		});
		elem.nodeValue = 'DESKTOP';
		mobileMode = true;
	}
	else if (elem.nodeValue === 'DESKTOP')
	{
		Object.values(mapLinkHash).forEach(mapLinkSpan => {
			const parent = mapLinkSpan.parentNode;
			parent.addEventListener('mouseenter', showMapLinkIcon, false);
			parent.addEventListener('mouseleave', hideMapLinkIcon, false);
			mapLinkSpan.className = 'mapLinkHidden';
		});
		elem.nodeValue = 'MOBILE';
		mobileMode = false;
	}
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
	var delistedPeaks = globalPeakInfo.delistedPeaks;
	var addRemoveDelisted = hiddenRows(delistedPeaks);
	if (addRemoveDelisted) addRows(delistedPeaks);

	var suspendedPeaks = globalPeakInfo.suspendedPeaks;
	var addRemoveSuspended = hiddenRows(suspendedPeaks);
	if (addRemoveSuspended) addRows(suspendedPeaks);

	for (var row = peakTableFirstRow(); row !== null; row = row.nextElementSibling)
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

	if (addRemoveDelisted) removeRows(delistedPeaks);
	if (addRemoveSuspended) removeRows(suspendedPeaks);
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

	if (delistedHidden()) {
		numClimbed -= globalPeakInfo.numDelistedClimbed;
		numPeaks -= globalPeakInfo.numDelisted;
	}
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
function setCount(spanId, count)
{
	var span = document.getElementById(spanId);
	if (!span) return;

	var text = '(' + count + ')';
	if (span.firstChild)
		span.firstChild.nodeValue = text;
	else
		span.appendChild(document.createTextNode(text));
}
function addRows(rows)
{
	for (var item of rows)
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
function removeRows(rows)
{
	for (var item of rows)
	{
		var row = item[0];
		var firstColumn = row.children[0];
		if (firstColumn.rowSpan === 2)
			row.parentNode.removeChild(extraRow[firstColumn.id]);

		row.parentNode.removeChild(row);
	}
}
function toggleRows(rows)
{
	if (hiddenRows(rows))
		addRows(rows);
	else
		removeRows(rows);

	updateClimbedCount();
}
function toggleDelisted()
{
	toggleRows(globalPeakInfo.delistedPeaks);
}
function toggleSuspended()
{
	toggleRows(globalPeakInfo.suspendedPeaks);
}
function changeColors()
{
	var colorMenu = document.getElementById('colorMenu');
	setPeakTableClass(0, colorMenu.options[colorMenu.selectedIndex].value);
}
function addClickHandlers(firstRow)
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

	checkbox = document.getElementById('toggleDelisted');
	if (checkbox) {
		checkbox.checked = !delistedHidden();
		checkbox.addEventListener('click', toggleDelisted, false);
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

	function createHeaderLink(label, callback)
	{
		const button = document.createElement('button');
		button.type = 'button';
		button.className = 'headerLink';
		button.appendChild(document.createTextNode(label));
		button.addEventListener('click', callback, false);
		return button;
	}

	const tableHeader = firstRow.firstElementChild;
	const headerGrid = document.createElement('div');
	const headerLeft = document.createElement('div');
	const headerCenter = document.createElement('div');
	const headerRight = document.createElement('div');

	headerGrid.id = 'headerGrid';
	headerLeft.id = 'headerLeft';
	headerCenter.id = 'headerCenter';
	headerRight.id = 'headerRight';

	headerRight.appendChild(createHeaderLink('MOBILE', clickMobile));
	headerRight.appendChild(createHeaderLink('LEGEND', showLegend));

	while (tableHeader.firstChild)
		headerCenter.appendChild(tableHeader.firstChild);

	headerGrid.appendChild(headerLeft);
	headerGrid.appendChild(headerCenter);
	headerGrid.appendChild(headerRight);

	tableHeader.appendChild(headerGrid);

	var closeLegend = document.getElementById('closeLegend');
	if (closeLegend)
		closeLegend.addEventListener('click', hideLegend, false);
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
