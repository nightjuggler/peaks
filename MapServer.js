/* globals document, Image, L, loadJSON */
/* exported MapServer */

var MapServer = (function() {
'use strict';

function fitLink(map, spec)
{
	function fitBounds(event)
	{
		event.preventDefault();
		map.fitBounds(spec.outline.getBounds());
	}
	var img = new Image();
	img.alt = 'Zoom To Fit';
	img.src = 'ztf.svg';
	img.className = 'msZtf';
	img.addEventListener('click', fitBounds, false);
	return img;
}
function simpleLineSymbol(color, width)
{
	return {
		type: 'esriSLS',
		style: 'esriSLSSolid',
		color: color,
		width: width,
	};
}
function simpleFillSymbol(color, outline)
{
	var symbol = {
		type: 'esriSFS',
		style: 'esriSFSSolid',
		color: color,
	};
	if (outline)
		symbol.outline = outline;
	return symbol;
}
function classBreakInfo(maxValue, fillColor)
{
	return {
		classMaxValue: maxValue,
		symbol: simpleFillSymbol(fillColor),
	};
}
function uniqueValueInfo(value, fillColor)
{
	return {
		value: value,
		symbol: simpleFillSymbol(fillColor),
	};
}
function dynamicLayer(id, mapLayerId, renderer)
{
	return JSON.stringify([{
		id: id, source: {type: 'mapLayer', mapLayerId: mapLayerId},
		drawingInfo: {renderer: renderer}
	}]);
}

var MapServer = {
	// Spatial Reference: 102100 (EPSG:3857) (Web Mercator) unless otherwise specified.

	wildernessSpec: {
		// Spatial Reference: 102113 (EPSG:3785) (deprecated Web Mercator)
		alias: 'w',
		url: 'https://gisservices.cfc.umt.edu/arcgis/rest/services' +
			'/ProtectedAreas/National_Wilderness_Preservation_System/MapServer',
		transparent: true,
		options: {opacity: 0.5, zIndex: 210},
		queryLayer: '0',
		queryFields: ['OBJECTID_1', 'NAME', 'WID', 'Agency', 'YearDesignated', 'Acreage'],
	},
	topoSpec: {
		alias: 't',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer',
		exportLayers: '0',
	},
	imageryTopoSpec: {
		alias: 'ti',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer',
		exportLayers: '0',
	},
	esriTopoSpec: {
		alias: 'te',
		url: 'https://services.arcgisonline.com/arcgis/rest/services/USA_Topo_Maps/MapServer',
		exportLayers: '0',
	},
	stateCountySpec: {
		alias: 'sc',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16', // states and counties
		transparent: true,
		queryLayer: '12',
		queryFields: ['OBJECTID', 'NAME', 'STUSAB'],
	},
	countySpec: {
		alias: 'c',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '1,3,5,7,9,11,13', // counties only
		transparent: true,
		queryLayer: '13',
		queryFields: ['OBJECTID', 'NAME'],
	},
	countyLabelsSpec: {
		alias: 'cl',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Labels/MapServer',
		exportLayers: '65',
		transparent: true,
	},
	zipcodeSpec: {
		alias: 'zip',
		url: 'https://gis.usps.com/arcgis/rest/services/EDDM/EDDM_ZIP5/MapServer',
		exportLayers: '0',
		transparent: true,
	},
	npsSpec: {
		alias: 'nps',
		url: 'https://mapservices.nps.gov/arcgis/rest/services' +
			'/LandResourcesDivisionTractAndBoundaryService/MapServer',
		exportLayers: '2',
		transparent: true,
		queryLayer: '2',
		queryFields: ['OBJECTID', 'UNIT_NAME', 'UNIT_CODE'],
	},
	blmSpec: {
		alias: 'blm',
		url: 'https://gis.blm.gov/arcgis/rest/services/admin_boundaries/BLM_Natl_AdminUnit/MapServer',
		exportLayers: '3', // 1=State, 2=District, 3=Field Office, 4=Other
		transparent: true,
		queryLayer: '3',
		queryFields: ['OBJECTID', 'ADMU_NAME', 'ADMIN_ST', 'ADMU_ST_URL', 'PARENT_NAME'],
	},
};

if (false)
	MapServer.wildernessSpec.dynamicLayers = dynamicLayer(101, 0, {
		type: 'uniqueValue', field1: 'Agency',
		uniqueValueInfos: [
			uniqueValueInfo('BLM', [0, 255, 255, 255]), // Aqua
			uniqueValueInfo('FWS', [255, 160, 122, 255]), // LightSalmon
			uniqueValueInfo('FS', [50, 205, 50, 255]), // LimeGreen
			uniqueValueInfo('NPS', [255, 0, 255, 255]), // Fuchsia / Magenta
		]});
if (false)
	MapServer.wildernessSpec.dynamicLayers = dynamicLayer(101, 0, {

		// Visual variables (like colorInfo which could be used for a continuous
		// color ramp) are apparently not supported in the renderer for sublayers
		// (dynamic layers are sublayers) prior to ArcGIS Enterprise 10.6.

		type: 'classBreaks', field: 'YearDesignated', minValue: 1964,
		classBreakInfos: [
			classBreakInfo(1969, [255, 0, 0, 255]),
			classBreakInfo(1979, [255, 165, 0, 255]),
			classBreakInfo(1989, [255, 255, 0, 255]),
			classBreakInfo(1999, [0, 255, 0, 255]),
			classBreakInfo(2009, [0, 0, 255, 255]),
			classBreakInfo(2019, [255, 0, 255, 255]),
		]});
if (false)
	MapServer.blmSpec.dynamicLayers = dynamicLayer(101, 3, {
		type: 'simple',
		symbol: simpleFillSymbol([0, 0, 0, 0], simpleLineSymbol([138, 43, 226, 255], 2))
	});
if (true) {
	MapServer.npsSpec.dynamicLayers = dynamicLayer(101, 2, {
		type: 'simple',
		symbol: simpleFillSymbol([255, 255, 0, 255])
	});
	MapServer.npsSpec.options = {opacity: 0.5, zIndex: 210};
}
MapServer.npsSpec.popup = {
	init: function(div)
	{
		this.linkNode = document.createElement('a');
		this.nameNode = document.createTextNode('');

		this.linkNode.style.fontWeight = 'bold';
		this.linkNode.appendChild(this.nameNode);
		div.appendChild(this.linkNode);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		var code = attr.UNIT_CODE.toLowerCase();
		if (code === 'kica' || code === 'sequ') code = 'seki';

		this.linkNode.href = 'https://www.nps.gov/' + code + '/index.htm';
		this.nameNode.nodeValue = attr.UNIT_NAME;

		return {color: '#FFFF00', fillOpacity: 0};
	},
};
MapServer.wildernessSpec.popup = {
	outlineColor: {
		BLM: '#0000FF', // Blue   (fill color is #FFFF00)
		FWS: '#FFA500', // Orange (fill color is #FFAA00)
		NPS: '#800080', // Purple (fill color is #A900E6)
		USFS:'#008000', // Green  (fill color is #38A800)
	},
	init: function(div)
	{
		this.linkNode = document.createElement('a');
		this.nameNode = document.createTextNode('');
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');

		this.linkNode.style.fontWeight = 'bold';
		this.linkNode.appendChild(this.nameNode);
		div.appendChild(this.linkNode);
		div.appendChild(this.textNode1);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		var agency = attr.Agency;
		if (agency === 'FS') agency = 'USFS';

		this.linkNode.href = 'https://www.wilderness.net/NWPS/wildView?WID=' + attr.WID;
		this.nameNode.nodeValue = attr.NAME;
		this.textNode1.nodeValue = ' (' + agency + ')';
		this.textNode2.nodeValue = '(' + attr.YearDesignated + ') (' +
			attr.Acreage.toLocaleString() + ' acres)';

		return {color: this.outlineColor[agency] || '#000000', fillOpacity: 0};
	},
};
MapServer.countySpec.popup = {
	init: function(div)
	{
		this.nameNode = document.createTextNode('');

		div.appendChild(this.nameNode);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.nameNode.nodeValue = attr.NAME;

		return {color: '#000000', fillOpacity: 0};
	},
};
MapServer.blmSpec.popup = {
	init: function(div)
	{
		this.linkNode = document.createElement('a');
		this.nameNode = document.createTextNode('');
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');

		this.linkNode.appendChild(this.nameNode);
		div.appendChild(document.createTextNode('BLM '));
		div.appendChild(this.linkNode);
		div.appendChild(this.textNode1);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		var url = attr.ADMU_ST_URL;
		if (url.charAt(0) === '\'')
			url = url.substring(1);

		this.linkNode.href = url;
		if (this.linkNode.protocol !== 'https:')
			this.linkNode.protocol = 'https:';

		this.nameNode.nodeValue = attr.ADMU_NAME;
		this.textNode1.nodeValue = ' (' + attr.ADMIN_ST + ')';
		this.textNode2.nodeValue = '(' + attr.PARENT_NAME + ')';

		return {color: '#0000FF', fillOpacity: 0};
	},
};

var allQuerySpecs = [
	MapServer.npsSpec,
	MapServer.wildernessSpec,
	MapServer.countySpec,
	MapServer.blmSpec,
];
function getQuerySpecs()
{
	var querySpecs = [];
	for (var spec of allQuerySpecs)
		if (spec.popup)
			querySpecs.push(spec);
	return querySpecs;
}

var earthRadius = 6378137; // WGS 84 equatorial radius in meters
var earthCircumference = 2 * Math.PI * earthRadius;
var tileOrigin = -(Math.PI * earthRadius);

function tileLayer(spec)
{
	var baseURL = [spec.url + '/export?f=image', 'bboxSR=102113', 'imageSR=102113'];

	if (spec.transparent)
		baseURL.push('transparent=true');
	if (spec.dynamicLayers)
		baseURL.push('dynamicLayers=' + spec.dynamicLayers);
	else if (spec.exportLayers)
		baseURL.push('layers=show:' + spec.exportLayers);

	baseURL = baseURL.join('&');

	return L.GridLayer.extend({
	createTile: function(tileCoords, done)
	{
		var m = earthCircumference / (1 << tileCoords.z); // tile size in meters
		var x = tileOrigin + m*tileCoords.x;
		var y = tileOrigin + m*tileCoords.y;
		var p = 2;

		var tileSize = this.getTileSize();

		var url = [baseURL,
			'size=' + tileSize.x + ',' + tileSize.y,
			'bbox=' + [x.toFixed(p), (-y-m).toFixed(p), (x+m).toFixed(p), (-y).toFixed(p)].join(',')
		].join('&');

		var tile = new Image(tileSize.x, tileSize.y);

		tile.addEventListener('load', function() { done(null, tile); }, false);
		tile.addEventListener('error', function() { done('Failed to load ' + url, tile); }, false);
		tile.src = url;

		return tile;
	}
	});
}
MapServer.newLayer = function(spec)
{
	return new (tileLayer(spec))(spec.options || {zIndex: spec.transparent ? 210 : 200});
};
MapServer.enableQuery = function(map)
{
	var geojson = false;
	var responseFormat = geojson ? 'geojson' : 'json';
	var globalClickID = 0;
	var popupEmpty = false;
	var firstResponse = false;
	var outlines = [];
	var querySpecs = getQuerySpecs();

	function removeOutlines()
	{
		if (outlines) {
			for (var outline of outlines) outline.remove();
			outlines.length = 0;
		}
		if (!popupEmpty) {
			for (var spec of querySpecs)
				spec.popup.div.style.display = 'none';
			popupEmpty = true;
		}
		firstResponse = false;
	}

	var popupDiv = document.createElement('div');
	popupDiv.className = 'popupDiv blmPopup';

	for (var spec of querySpecs)
	{
		spec.outlineCache = {};

		var popupSpec = spec.popup;
		popupSpec.div = document.createElement('div');
		popupSpec.ztf = fitLink(map, popupSpec);
		popupSpec.init(popupSpec.div);
		popupDiv.appendChild(popupSpec.div);

		var baseURL = spec.url + '/' + spec.queryLayer + '/query?f=' + responseFormat;

		spec.queryLL = [baseURL,
			'returnGeometry=false',
			'outFields=' + spec.queryFields.join(','),
			'spatialRel=esriSpatialRelIntersects',
			'inSR=4326', // WGS 84 (EPSG:4326) longitude/latitude
			'geometryType=esriGeometryPoint',
			'geometry='].join('&');
		spec.queryID = [baseURL,
			'returnGeometry=true',
			'geometryPrecision=5',
			'outSR=4326',
			'objectIds='].join('&');
	}

	var popup = L.popup({maxWidth: 600}).setContent(popupDiv);

	function runQuery(url, clickID, ll, spec)
	{
		function showOutline(outline)
		{
			spec.popup.outline = outline;
			spec.popup.ztf.style.display = '';
			popup.update();
			outlines.push(outline.addTo(map));
		}
		loadJSON(url, function(json) {
			if (clickID !== globalClickID) return;
			if (firstResponse) removeOutlines();
			if (json.features.length === 0) return;

			var attr = json.features[0][geojson ? 'properties' : 'attributes'];
			var style = spec.popup.show(attr);

			spec.popup.div.style.display = 'block';
			spec.popup.ztf.style.display = 'none';
			if (popupEmpty) {
				map.openPopup(popup.setLatLng(ll));
				popupEmpty = false;
			} else
				popup.update();

			var outlineID = attr[spec.queryFields[0]];
			var outline = spec.outlineCache[outlineID];
			if (outline) {
				showOutline(outline);
				return;
			}

			loadJSON(spec.queryID + outlineID, function(json) {
				if (json.features.length === 0) return;
				var geometry = json.features[0].geometry;
				if (!geojson) {
					if (json.geometryType !== 'esriGeometryPolygon') return;
					geometry = {type: 'Polygon', coordinates: geometry.rings};
				}
				var outline = L.GeoJSON.geometryToLayer(geometry, style);
				spec.outlineCache[outlineID] = outline;
				if (clickID === globalClickID)
					showOutline(outline);
			});
		}, function() {
			if (clickID !== globalClickID) return;
			if (firstResponse) removeOutlines();
		});
	}

	map.on('click', function(event) {
		globalClickID += 1;
		firstResponse = true;

		var ll = event.latlng;
		var lngCommaLat = ll.lng.toFixed(6) + ',' + ll.lat.toFixed(6);

		for (var spec of querySpecs)
			runQuery(spec.queryLL + lngCommaLat, globalClickID, ll, spec);
	});
};

return MapServer;
})();
