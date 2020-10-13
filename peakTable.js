/* globals document, Option, window, enableTooltips */
(function() {
'use strict';

const radiansPerDegree = Math.PI / 180;
const degreesPerRadian = 180 / Math.PI;
const earthRadius = 6378137.0; // WGS 84 equatorial radius in meters

function deltaLatForDistanceNorth(distance)
{
	// Derived from solving the Haversine formula for lat2 when long1 == long2

	return distance / earthRadius * degreesPerRadian;
}
function deltaLongForDistanceEast(lat1, distance)
{
	// Derived from solving the Haversine formula for long2 when lat1 == lat2

	return 2 * Math.asin(Math.sin(distance / (2 * earthRadius)) /
		Math.cos(lat1 * radiansPerDegree)) * degreesPerRadian;
}
function latitudeToWebMercatorY(latitude)
{
	// See https://en.wikipedia.org/wiki/Mercator_projection#Alternative_expressions

	const y = Math.sin(latitude * radiansPerDegree);

	return (earthRadius / 2 * Math.log((1 + y) / (1 - y))).toFixed(4);
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
	const distance = 8 * 1609.344; // Convert 8 miles to meters
	const deltaLat = deltaLatForDistanceNorth(distance / 2);
	const deltaLong = deltaLongForDistanceEast(latitude, distance * 2/3);

	const xmin = longitudeToWebMercatorX(longitude - deltaLong);
	const xmax = longitudeToWebMercatorX(longitude + deltaLong);

	const ymin = latitudeToWebMercatorY(latitude - deltaLat);
	const ymax = latitudeToWebMercatorY(latitude + deltaLat);

	return [xmin, ymin, xmax, ymax, '102113'].join(',');
}
function wccLink(latitude, longitude)
{
	// WCC = National Water and Climate Center
	return 'https://www.nrcs.usda.gov/wps/portal/wcc/home/quicklinks/imap#' +
	[
		['version', '125'],
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
		['zoom', '12.0'],

	].map(p => p.join('=')).join('&');
}
function round(number, precision)
{
	const p = Math.pow(10, precision);
	return Math.round(number * p) / p;
}
function terriaObject(latitude, longitude)
{
	const distance = 3000; // meters
	const deltaLat = deltaLatForDistanceNorth(distance);
	const deltaLong = deltaLongForDistanceEast(latitude, distance);

	const camera = {
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
// The "right-pointing pointer" looks better in Firefox on the desktop.
// Use the "right-pointing triangle" in all other cases.
const rightPointer = '\u25BA'; // black right-pointing pointer
const rightTriangle = '\u25B6\uFE0E'; // black right-pointing triangle
const collapsedIcon = window.navigator.vendor === '' && !window.matchMedia('(hover: none)').matches ?
	rightPointer : rightTriangle;
const expandedAboveIcon = '\u25B2'; // black up-pointing triangle
const expandedBelowIcon = '\u25BC'; // black down-pointing triangle
const mapLinkHash = new Map();
const extraRow = {};
const landColumnArray = [];
const climbedColumnArray = [];
let activePopup = null;
let mobileMode = false;
const globalPeakInfo = {
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
function parseQueryString()
{
	const q = window.location.search;

	if (typeof q !== 'string' || q.charAt(0) !== '?') return;

	const flags = {
		showDelisted: 'showDelisted',
		showSuspended: 'showSuspended',
	};
	const handlers = {
	};

	const validKey = (key) => key.length <= 16 && /^[a-z][A-Za-z]*$/.test(key);

	for (const s of q.substring(1).split('&'))
	{
		const i = s.indexOf('=');
		if (i < 0) {
			if (validKey(s) && flags.hasOwnProperty(s))
				globalPeakInfo[flags[s]] = true;
		} else {
			const [k, v] = [s.substring(0, i), s.substring(i + 1)];

			if (validKey(k) && handlers.hasOwnProperty(k))
				handlers[k](v);
		}
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
	for (const value of attrValue.split('/'))
		if (value === trueValue)
			return true;
	return false;
}
function setPeakFlag(row, parentFlags, attrName, trueValue)
{
	const attrValue = row.dataset[attrName];
	if (!attrValue) return;

	const flagName = attrName + '_' + trueValue;
	const flagValue = getPeakFlag(attrValue, trueValue);
	if (flagValue === parentFlags[flagName]) return;

	if (row.peakFlags === parentFlags)
		row.peakFlags = newPeakFlags(parentFlags);
	row.peakFlags[flagName] = flagValue;
}
function setPeakFlags(row, parentFlags, attrName, setValue)
{
	const attrValue = row.dataset[attrName];
	if (!attrValue) return;

	for (const flagName of attrValue.split(','))
	{
		const flagValue = parentFlags[flagName];
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
	const path = window.location.href;
	const n = path.length;
	let i = -1;
	let j = 0;

	while (j < n) {
		const ch = path.charAt(j);
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
	const id = getPeakListId();

	const peakLists = [
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
		{id: 'SierraPasses', name: 'Sierra Passes'},
	];

	const menu = document.getElementById('peakListMenu');

	for (const pl of peakLists)
	{
		const selected = pl.id === id;
		if (menu)
			menu.add(new Option(pl.name, pl.id, selected, selected));
		if (selected)
			globalPeakInfo.peakListId = id;
	}

	if (menu)
	{
		const selectedIndex = menu.selectedIndex;

		menu.addEventListener('change', function() {
			const id = peakLists[menu.selectedIndex].id;

			menu.selectedIndex = selectedIndex;

			window.location = globalPeakInfo.pathPrefix + id + '.html';
		});
	}
}
function addMapLink(listNode, linkText, url)
{
	const listItem = document.createElement('li');
	const linkNode = document.createElement('a');
	linkNode.href = url;
	linkNode.appendChild(document.createTextNode(linkText));
	listItem.appendChild(linkNode);
	listNode.appendChild(listItem);
}
function createMapLinkBox(latCommaLong, peakFlags)
{
	const latLong = latCommaLong.split(',');
	const latitude = Number(latLong[0]);
	const longitude = Number(latLong[1]);
	const extent = extentForLatLong(latitude, longitude);
	const pathPrefix = globalPeakInfo.pathPrefix;
	const peakListId = globalPeakInfo.peakListId;

	const listNode = document.createElement('ul');

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

	addMapLink(listNode, 'GIS Surfer',
		'https://mappingsupport.com/p2/gissurfer.php?center=' + latCommaLong + '&zoom=14&basemap=USA_basemap');

	addMapLink(listNode, 'Google Maps', 'https://www.google.com/maps/@' + latCommaLong + ',10z');

	addMapLink(listNode, 'Interagency Elevation Inventory',
		'https://coast.noaa.gov/inventory/index.html?layers=1&zoom=14&center=' +
		latLong[1] + ',' + latLong[0] + '&basemap=esristreet');

	addMapLink(listNode, 'Lists of John',
		'https://listsofjohn.com/mapf?lat=' + latLong[0] + '&lon=' + latLong[1] + '&z=15&d=y');

	addMapLink(listNode, 'National Fire Situational Awareness',
		'https://maps.nwcg.gov/sa/#/%3F/' + latLong[0] + '/' + latLong[1] + '/12');

	addMapLink(listNode, 'National Weather Service',
		'https://forecast.weather.gov/MapClick.php?lon=' + latLong[1] + '&lat=' + latLong[0]);

	addMapLink(listNode, 'NGS Datasheets (Radial Search)',
		'https://www.ngs.noaa.gov/cgi-bin/ds_radius.prl' +
		'?FormatBox=Decimal%20Degrees' +
		'&selectedFormat=Decimal%20Degrees' +
		'&DLatBox=' + latLong[0] +
		'&DLonBox=' + latLong[1].substring(1) +
		'&RadBox=1' +
		'&TypeSelected=X-0' +
		'&StabilSelected=0' +
		'&SubmitBtn=Submit' +
		'&dump_app_trace=false' +
		'&db_debug=false');

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
		'https://nationalmap.gov/epqs/pqs.php' +
		'?x=' + latLong[1] + '&y=' + latLong[0] + '&units=Feet&output=json');

	addMapLink(listNode, 'USGS National Map (Basic)',
		'https://viewer.nationalmap.gov/basic/?basemap=b1&zoom=15&bbox=' +
		latLong[1] + ',' + latLong[0] + ',' +
		latLong[1] + ',' + latLong[0]);

	addMapLink(listNode, 'USGS National Map (Advanced)',
		'https://viewer.nationalmap.gov/advanced-viewer/viewer/index.html?center=' +
		longitudeToWebMercatorX(longitude) + ',' +
		latitudeToWebMercatorY(latitude) + ',102100&level=15');

	addMapLink(listNode, 'USGS Protected Areas Database',
		'https://maps.usgs.gov/padus/#start=' +
		encodeURIComponent(JSON.stringify(terriaObject(latitude, longitude))));

	addMapLink(listNode, 'USGS TopoView',
		'https://ngmdb.usgs.gov/maps/topoview/viewer/#15/' + latLong[0] + '/' + latLong[1]);

	addMapLink(listNode, 'Water & Climate Center', wccLink(latLong[0], latLong[1]));

	addMapLink(listNode, 'Wilderness.net',
		'https://umontana.maps.arcgis.com/apps/webappviewer/index.html?' +
		'id=a415bca07f0a4bee9f0e894b0db5c3b6&extent=' + extent);

	const llSpan = document.createElement('span');
	llSpan.style.color = 'black';
	llSpan.style.cursor = 'pointer';
	const deg = '\u00B0';
	const llText = (latitude < 0 ? -latitude + deg + 'S ' : latitude + deg + 'N ') +
		(longitude < 0 ? -longitude + deg + 'W' : longitude + deg + 'E');
	llSpan.appendChild(document.createTextNode(llText));
	llSpan.addEventListener('click', function() {
		llSpan.firstChild.nodeValue = latCommaLong;
		window.getSelection().selectAllChildren(llSpan);
		document.execCommand('copy');
		llSpan.firstChild.nodeValue = llText;
	});

	const llDiv = document.createElement('div');
	llDiv.style.textAlign = 'center';
	llDiv.style.paddingBottom = '2px';
	llDiv.appendChild(llSpan);

	const mapLinkBox = document.createElement('div');
	mapLinkBox.className = 'mapLinkBox';
	mapLinkBox.appendChild(llDiv);
	mapLinkBox.appendChild(listNode);
	return mapLinkBox;
}
function addMapLinkBox(mapLinkSpan)
{
	const secondColumn = mapLinkSpan.parentNode;
	const peakFlags = secondColumn.parentNode.peakFlags;

	const mapLink = secondColumn.firstElementChild;
	const latCommaLong = mapLink.href.split('#')[1].split('&')[0].split('=')[1];

	return mapLinkSpan.appendChild(createMapLinkBox(latCommaLong, peakFlags));
}
function toggleMapLinkBox(event)
{
	const toggle = event.currentTarget;
	toggle.focus();

	let mapLinkBox = toggle.nextSibling;
	const active = mapLinkBox && mapLinkBox === activePopup;

	closeActivePopup();
	if (active) return;

	const mapLinkSpan = toggle.parentNode;
	mapLinkSpan.className = 'mapLinkOpen';

	if (!mapLinkBox)
		mapLinkBox = addMapLinkBox(mapLinkSpan);

	const {top, height} = toggle.getBoundingClientRect();

	if (top > mapLinkBox.offsetHeight) {
		mapLinkBox.style.top = 'auto';
		mapLinkBox.style.bottom = height + 'px';
		toggle.firstChild.nodeValue = expandedAboveIcon;
	} else {
		mapLinkBox.style.top = height + 'px';
		mapLinkBox.style.bottom = 'auto';
		toggle.firstChild.nodeValue = expandedBelowIcon;
	}

	setActivePopup(mapLinkBox);
}
function showMapLinkIcon(event)
{
	const mapLinkSpan = mapLinkHash.get(event.currentTarget);

	if (mapLinkSpan.lastChild !== activePopup)
		mapLinkSpan.className = 'mapLinkClosed';
}
function hideMapLinkIcon(event)
{
	const mapLinkSpan = mapLinkHash.get(event.currentTarget);

	mapLinkSpan.firstChild.blur();

	if (mapLinkSpan.lastChild === activePopup)
		closeActivePopup();

	mapLinkSpan.className = 'mapLinkHidden';
}
function toggleExtraRow(event)
{
	const toggle = event.currentTarget;
	const firstColumn = toggle.parentNode;
	const row = firstColumn.parentNode;
	const nextRow = row.nextElementSibling;

	if (firstColumn.rowSpan === 1) {
		row.parentNode.insertBefore(extraRow[firstColumn.id], nextRow);
		firstColumn.rowSpan = 2;
		toggle.firstChild.nodeValue = expandedBelowIcon;
	} else {
		firstColumn.rowSpan = 1;
		row.parentNode.removeChild(nextRow);
		toggle.firstChild.nodeValue = collapsedIcon;
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
	const refArray = row.dataset.also ? row.dataset.also.split(' ') : [];

	if (row.dataset.from)
		refArray.unshift(row.dataset.from);

	const pll = document.createElement('div');
	pll.className = 'pll';

	for (const ref of refArray)
	{
		const m = ref.match(/^((?:[A-Z]|x[0-9])[0-9A-Z]*(?:[A-Z]|[0-9]x))([0-9]+)\.[0-9]+[ab]?([ds]?)$/);
		if (m === null) continue;

		const htmlId = m[1];
		let listId = htmlId;
		const sectionNumber = m[2];

		if (listId.charAt(0) === 'x')
			listId = listId.substring(1);
		if (listId.charAt(listId.length - 1) === 'x')
			listId = listId.substring(0, listId.length - 1);

		let linkHref = listId.toLowerCase() + '.html';
		let linkText = listId;

		if (m[3] === 'd') {
			linkHref += '?showDelisted';
			linkText = 'ex-' + listId;
		}
		else if (m[3] === 's') {
			linkHref += '?showSuspended';
			linkText = '(' + listId + ')';
		}

		const listLink = document.createElement('a');
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
	const g = globalPeakInfo;
	let sectionFlags = g.flags;
	let sectionNumber = 0;
	let sectionPeakNumber = 0;

	parseQueryString();
	initPeakListMenu();

	for (const a of document.getElementsByTagName('a'))
		if (a.hostname === 'caltopo.com' && a.href.substring(a.href.length - 4) === '&b=t')
			a.href += '&o=r&n=0.2';

	const firstRow = peakTableFirstRow();

	for (let row = firstRow; row !== null; row = row.nextElementSibling)
	{
		const firstColumn = row.children[0];
		if (firstColumn.colSpan !== 1) {
			if (row.className === 'section') {
				setRowFlags(row, g.flags);
				sectionFlags = row.peakFlags;
				if (row === firstRow)
					g.flags = sectionFlags;
				else {
					sectionNumber += 1;
					sectionPeakNumber = 0;
				}
			}
			continue;
		}

		sectionPeakNumber += 1;
		setRowFlags(row, sectionFlags);
		const climbed = row.className.slice(0, 7) === 'climbed';
		const delisted = row.className.slice(-8) === 'delisted';
		const suspended = row.className.slice(-9) === 'suspended';

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
		if (!firstColumn.firstChild)
			firstColumn.appendChild(document.createTextNode(sectionNumber + '.' + sectionPeakNumber));
		if (firstColumn.rowSpan === 2)
		{
			if (!firstColumn.id)
				firstColumn.id = 'p' + g.numPeaks;

			const toggle = document.createElement('button');
			toggle.className = 'toggle';
			toggle.appendChild(document.createTextNode(collapsedIcon));
			toggle.addEventListener('click', toggleExtraRow);
			firstColumn.appendChild(toggle);
			firstColumn.rowSpan = 1;

			extraRow[firstColumn.id] = row.parentNode.removeChild(row.nextElementSibling);
		}
		if (row.peakFlags.country_US)
		{
			const toggle = document.createElement('button');
			toggle.className = 'toggle';
			toggle.appendChild(document.createTextNode(collapsedIcon));
			toggle.addEventListener('click', toggleMapLinkBox);

			const mapLinkSpan = document.createElement('span');
			mapLinkSpan.className = 'mapLinkHidden';
			mapLinkSpan.appendChild(toggle);

			const secondColumn = firstColumn.nextElementSibling;
			const lineBreak = secondColumn.firstElementChild.nextElementSibling;

			secondColumn.insertBefore(mapLinkSpan, lineBreak);
			secondColumn.addEventListener('mouseenter', showMapLinkIcon);
			secondColumn.addEventListener('mouseleave', hideMapLinkIcon);
			mapLinkHash.set(secondColumn, mapLinkSpan);
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

	window.removeEventListener('DOMContentLoaded', decorateTable);
}
function closeActivePopup(event)
{
	if (!activePopup) return;

	const mapLinkSpan = activePopup.parentNode;

	if (event)
		for (let node = event.target; node; node = node.parentNode)
			if (node === mapLinkSpan) return;

	mapLinkSpan.className = 'mapLinkClosed';
	mapLinkSpan.firstChild.firstChild.nodeValue = collapsedIcon;
	activePopup = null;

	if (mobileMode) {
		const body = document.body;
		body.removeEventListener('touchstart', closeActivePopup);
		body.removeEventListener('mousedown', closeActivePopup);
	}
}
function setActivePopup(element)
{
	activePopup = element;

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
	if (!(elem = elem.firstChild)) return; // the button containing the text node
	if (!(elem = elem.firstChild)) return; // the text node

	closeActivePopup();

	mobileMode = !mobileMode;
	if (mobileMode) {
		mapLinkHash.forEach(mapLinkSpan => {
			const parent = mapLinkSpan.parentNode;
			parent.removeEventListener('mouseenter', showMapLinkIcon);
			parent.removeEventListener('mouseleave', hideMapLinkIcon);
			mapLinkSpan.className = 'mapLinkClosed';
		});
		elem.nodeValue = 'DESKTOP';
	} else {
		mapLinkHash.forEach(mapLinkSpan => {
			const parent = mapLinkSpan.parentNode;
			parent.addEventListener('mouseenter', showMapLinkIcon);
			parent.addEventListener('mouseleave', hideMapLinkIcon);
			mapLinkSpan.className = 'mapLinkHidden';
		});
		elem.nodeValue = 'MOBILE';
	}
	enableTooltips(document.body, mobileMode);
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
	const delistedPeaks = globalPeakInfo.delistedPeaks;
	const addRemoveDelisted = hiddenRows(delistedPeaks);
	if (addRemoveDelisted) addRows(delistedPeaks);

	const suspendedPeaks = globalPeakInfo.suspendedPeaks;
	const addRemoveSuspended = hiddenRows(suspendedPeaks);
	if (addRemoveSuspended) addRows(suspendedPeaks);

	for (let row = peakTableFirstRow(); row !== null; row = row.nextElementSibling)
	{
		const firstColumn = row.children[0];
		if (firstColumn.colSpan === 1) {
			addRemoveFunction(row);
			const row2 = extraRow[firstColumn.id];
			if (row2 && !row2.parentNode)
				row2.children[0].colSpan += colDiff;
		} else
			firstColumn.colSpan += colDiff;
	}

	if (addRemoveDelisted) removeRows(delistedPeaks);
	if (addRemoveSuspended) removeRows(suspendedPeaks);
}
function getPeakTable()
{
	let peakTable = peakTableFirstRow().parentNode;
	if (peakTable.tagName !== 'TABLE')
		peakTable = peakTable.parentNode;
	return peakTable;
}
function getPeakTableClass(i)
{
	return getPeakTable().className.split(' ')[i];
}
function setPeakTableClass(i, className)
{
	const peakTable = getPeakTable();
	const classList = peakTable.className.split(' ');
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
	const span = document.getElementById('climbedCountSpan');
	if (!span) return;

	let numClimbed = globalPeakInfo.numClimbed;
	let numPeaks = globalPeakInfo.numPeaks;

	if (delistedHidden()) {
		numClimbed -= globalPeakInfo.numDelistedClimbed;
		numPeaks -= globalPeakInfo.numDelisted;
	}
	if (suspendedHidden()) {
		numClimbed -= globalPeakInfo.numSuspendedClimbed;
		numPeaks -= globalPeakInfo.numSuspended;
	}

	const text = '(' + numClimbed + '/' + numPeaks + ')';
	if (span.firstChild)
		span.firstChild.nodeValue = text;
	else
		span.appendChild(document.createTextNode(text));
}
function setCount(spanId, count)
{
	const span = document.getElementById(spanId);
	if (!span) return;

	const text = '(' + count + ')';
	if (span.firstChild)
		span.firstChild.nodeValue = text;
	else
		span.appendChild(document.createTextNode(text));
}
function addRows(rows)
{
	for (const item of rows)
	{
		const row = item[0];
		let nextSibling = item[1];
		const firstColumn = row.children[0];
		if (firstColumn.rowSpan === 2)
		{
			const row2 = extraRow[firstColumn.id];
			nextSibling.parentNode.insertBefore(row2, nextSibling);
			nextSibling = row2;
		}
		nextSibling.parentNode.insertBefore(row, nextSibling);
	}
}
function removeRows(rows)
{
	for (const item of rows)
	{
		const row = item[0];
		const firstColumn = row.children[0];
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
	const colorMenu = document.getElementById('colorMenu');
	setPeakTableClass(0, colorMenu.options[colorMenu.selectedIndex].value);
}
function addClickHandlers(firstRow)
{
	let checkbox = document.getElementById('toggleLandColumn');
	if (checkbox) {
		checkbox.checked = landColumnArray.length === 0;
		checkbox.addEventListener('click', toggleLandColumn);
	}

	checkbox = document.getElementById('toggleClimbedColumn');
	if (checkbox) {
		checkbox.checked = climbedColumnArray.length === 0;
		checkbox.addEventListener('click', toggleClimbedColumn);
	}

	checkbox = document.getElementById('toggleDelisted');
	if (checkbox) {
		checkbox.checked = !delistedHidden();
		checkbox.addEventListener('click', toggleDelisted);
	}

	checkbox = document.getElementById('toggleSuspended');
	if (checkbox) {
		checkbox.checked = !suspendedHidden();
		checkbox.addEventListener('click', toggleSuspended);
	}

	const colorMenu = document.getElementById('colorMenu');
	if (colorMenu) {
		const color = getPeakTableClass(0);
		for (const option of colorMenu.options)
			if (option.value === color) {
				colorMenu.selectedIndex = option.index;
				break;
			}
		colorMenu.addEventListener('change', changeColors);
	}

	function createHeaderLink(label, callback)
	{
		const button = document.createElement('button');
		button.type = 'button';
		button.className = 'headerLink';
		button.appendChild(document.createTextNode(label));
		button.addEventListener('click', callback);
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

	const closeLegend = document.getElementById('closeLegend');
	if (closeLegend)
		closeLegend.addEventListener('click', hideLegend);
}
function showLegend()
{
	const legend = document.getElementById('legend');
	legend.style.display = 'block';
}
function hideLegend()
{
	const legend = document.getElementById('legend');
	legend.style.display = 'none';
}
window.addEventListener('DOMContentLoaded', decorateTable);
})();
