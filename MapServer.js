/* globals document, Image, L, loadJSON */
/* exported BaseLayers, TileOverlays, MapServer */

var BaseLayers = {
name: 'Base Layers',
items: {
	mapbox: {
		name: 'Mapbox',
		items: {
			o: {name: 'Outdoors'},
			rbh: {name: 'Run Bike Hike'},
			s: {name: 'Satellite'},
			sts: {name: 'Streets Satellite'},
			st: {name: 'Streets'},
			pencil: {name: 'Pencil'},
			emerald: {name: 'Emerald'},
		},
		order: ['o', 'rbh', 's', 'sts', 'st', 'pencil', 'emerald'],
	},
	natmap: {
		name: 'National Map',
		items: {
			topo: {
		name: 'Topo',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer',
		attribution: '&copy; [USGS The National Map]; U.S. Census Bureau; HERE Road Data',
			},
			imgtopo: {
		name: 'Imagery Topo',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer',
		attribution: '&copy; [USGS The National Map]',
			},
			naipplus: {
		name: 'NAIP Plus',
		url: 'https://services.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/MapServer',
		attribution: '&copy; [USGS The National Map]',
			},
		},
		order: ['topo', 'imgtopo', 'naipplus'],
	},
	esri: {
		name: 'Esri',
		items: {
			usatopo: {
		name: 'USA Topo',
		url: 'https://services.arcgisonline.com/arcgis/rest/services/USA_Topo_Maps/MapServer',
		attribution: '[Esri] | &copy; 2013 National Geographic Society, i-cubed',
			},
		},
		order: ['usatopo'],
	},

	o: 'mapbox',
	rbh: 'mapbox',
	s: 'mapbox',
	sts: 'mapbox',
	st: 'mapbox',
},
order: ['mapbox', 'natmap', 'esri'],
};
var TileOverlays = {
name: 'Tile Overlays',
items: {
	us: {
		name: 'National',
		items: {
			blm: {
		name: 'BLM Districts',
		url: 'https://gis.blm.gov/arcgis/rest/services/admin_boundaries/BLM_Natl_AdminUnit/MapServer',
		exportLayers: '3', // 1=State, 2=District, 3=Field Office, 4=Other
		queryFields: ['OBJECTID', 'ADMU_NAME', 'ADMIN_ST', 'ADMU_ST_URL', 'PARENT_NAME'],
		attribution: '[Bureau of Land Management]',
			},
			nlcs: {
		name: 'BLM NLCS',
		url: 'https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_NLCS_NM_NCA_poly/MapServer',
		// Layer 0 renders outlines (color:[255,77,0,255], width:1) with labels.
		// Layer 1 renders solid fills (color:[255,128,0,255]) without labels.
		exportLayers: '1',
		opacity: 0.5,
		queryFields: [
			'Monuments_NCAs_SimilarDesignation2015.OBJECTID',
			'Monuments_NCAs_SimilarDesignation2015.sma_code',
			'Monuments_NCAs_SimilarDesignation2015.NCA_NAME',
			'Monuments_NCAs_SimilarDesignation2015.STATE_GEOG',
			'nlcs_desc.WEBLINK',
		],
		attribution: '[Bureau of Land Management]',
			},
			states: {
		name: 'States',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '0,2,4,6,8,10,12,14,15,16', // states only
		queryLayer: '12',
		queryFields: ['OBJECTID', 'NAME', 'STUSAB'],
			},
			counties: {
		name: 'Counties',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '1,3,5,7,9,11,13', // counties only
		queryLayer: '13',
		queryFields: ['OBJECTID', 'NAME'],
			},
			countylabels: {
		name: 'County Labels',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Labels/MapServer',
		exportLayers: '65',
			},
			nps: {
		name: 'National Parks',
		url: 'https://mapservices.nps.gov/arcgis/rest/services' +
			'/LandResourcesDivisionTractAndBoundaryService/MapServer',
		exportLayers: '2',
		queryFields: ['OBJECTID', 'UNIT_NAME', 'UNIT_CODE'],
			},
			w: {
		name: 'Wilderness Areas',
		url: 'https://gisservices.cfc.umt.edu/arcgis/rest/services' +
			'/ProtectedAreas/National_Wilderness_Preservation_System/MapServer',
		opacity: 0.5,
		queryFields: ['OBJECTID_1', 'NAME', 'WID', 'Agency', 'YearDesignated', 'Acreage'],
			},
			zip: {
		name: 'ZIP Codes',
		url: 'https://gis.usps.com/arcgis/rest/services/EDDM/EDDM_ZIP5/MapServer',
		exportLayers: '0',
			},
		},
		order: ['blm', 'nlcs', 'counties', 'countylabels', 'nps', 'states', 'w', 'zip'],
	}, // us
	ca: {
		name: 'California',
		items: {
			counties: {
		name: 'Counties (Color)',
		url: 'https://services.gis.ca.gov/arcgis/rest/services/Boundaries/CA_Counties_Color/MapServer',
		opacity: 0.4,
			},
			parks: {
		name: 'State Parks',
		url: 'https://services.gis.ca.gov/arcgis/rest/services/Boundaries/CA_State_Parks/MapServer',
		opacity: 0.5,
		queryFields: ['OBJECTID', 'UNITNAME', 'MgmtStatus', 'GISACRES'],
			},
		},
		order: ['counties', 'parks'],
	},
	w: 'us',
},
order: ['us', 'ca'],
};

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

var blmSpec = TileOverlays.items.us.items.blm;
var caParkSpec = TileOverlays.items.ca.items.parks;
var countySpec = TileOverlays.items.us.items.counties;
var nlcsSpec = TileOverlays.items.us.items.nlcs;
var npsSpec = TileOverlays.items.us.items.nps;
var stateSpec = TileOverlays.items.us.items.states;
var wildernessSpec = TileOverlays.items.us.items.w;

if (false)
	wildernessSpec.dynamicLayers = dynamicLayer(101, 0, {
		type: 'uniqueValue', field1: 'Agency',
		uniqueValueInfos: [
			uniqueValueInfo('BLM', [0, 255, 255, 255]), // Aqua
			uniqueValueInfo('FWS', [255, 160, 122, 255]), // LightSalmon
			uniqueValueInfo('FS', [50, 205, 50, 255]), // LimeGreen
			uniqueValueInfo('NPS', [255, 0, 255, 255]), // Fuchsia / Magenta
		]});
if (false)
	wildernessSpec.dynamicLayers = dynamicLayer(101, 0, {

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
	blmSpec.dynamicLayers = dynamicLayer(101, 3, {
		type: 'simple',
		symbol: simpleFillSymbol([0, 0, 0, 0], simpleLineSymbol([138, 43, 226, 255], 2))
	});
if (true) {
	npsSpec.dynamicLayers = dynamicLayer(101, 2, {
		type: 'simple',
		symbol: simpleFillSymbol([255, 255, 0, 255])
	});
	npsSpec.opacity = 0.5;
}
npsSpec.popup = {
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
nlcsSpec.popup = {
	designation: {
		'BLM_CMPA': 'Cooperative Management and Protection Area', // Steens Mountain (OR)
		'BLM_FR': 'Forest Reserve',
		'BLM_MON': 'National Monument', // e.g. Vermilion Cliffs (AZ)
		'BLM_NA': 'Outstanding Natural Area',
		'BLM_NCA': 'National Conservation Area',
		'BLM_NM': 'National Monument',
	},
	init: function(div)
	{
		this.linkNode = document.createElement('a');
		this.nameNode = document.createTextNode('');
		this.textNode = document.createTextNode('');

		this.linkNode.style.fontWeight = 'bold';
		this.linkNode.appendChild(this.nameNode);
		div.appendChild(this.linkNode);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		var name = attr['Monuments_NCAs_SimilarDesignation2015.NCA_NAME'];
		var code = attr['Monuments_NCAs_SimilarDesignation2015.sma_code'];
		var state = attr['Monuments_NCAs_SimilarDesignation2015.STATE_GEOG'];
		var url = attr['nlcs_desc.WEBLINK'];

		this.linkNode.href = url;
		if (this.linkNode.protocol !== 'https:')
			this.linkNode.protocol = 'https:';
		if (this.linkNode.host !== 'www.blm.gov')
			this.linkNode.host = 'www.blm.gov';

		this.nameNode.nodeValue = name;
		this.textNode.nodeValue = '(' + code + ') (' + state + ')';

		return {color: '#800000', fillOpacity: 0};
	},
};
wildernessSpec.popup = {
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
caParkSpec.popup = {
	init: function(div)
	{
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');

		div.appendChild(this.textNode1);
		div.appendChild(this.ztf);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
	},
	show: function(attr)
	{
		this.textNode1.nodeValue = attr.UNITNAME;
		this.textNode2.nodeValue = '(' + attr.MgmtStatus + ') (' +
			Math.round(attr.GISACRES).toLocaleString() + ' acres)';

		return {color: '#70A800', fillOpacity: 0};
	},
};
countySpec.popup = {
	init: function(div)
	{
		this.nameNode = document.createTextNode('');

		div.appendChild(this.nameNode);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.nameNode.nodeValue = attr.NAME;

		return {color: '#A52A2A', fillOpacity: 0};
	},
};
stateSpec.popup = {
	init: function(div)
	{
		div.appendChild(this.nameNode = document.createTextNode(''));
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.nameNode.nodeValue = attr.NAME + ' (' + attr.STUSAB + ')';

		return {color: '#000000', fillOpacity: 0};
	},
};
blmSpec.popup = {
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
		if (this.linkNode.host !== 'www.blm.gov')
			this.linkNode.host = 'www.blm.gov';

		this.nameNode.nodeValue = attr.ADMU_NAME;
		this.textNode1.nodeValue = ' (' + attr.ADMIN_ST + ')';
		this.textNode2.nodeValue = '(' + attr.PARENT_NAME + ')';

		return {color: '#0000FF', fillOpacity: 0};
	},
};

var allQuerySpecs = [
	npsSpec,
	nlcsSpec,
	wildernessSpec,
	caParkSpec,
	countySpec,
	stateSpec,
	blmSpec,
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

function tileLayer(spec, transparent)
{
	// 102113 (EPSG:3785) is the deprecated spatial reference identifier for Web Mercator.
	// Would the updated identifier 102100 (EPSG:3857) also work?

	var baseURL = [spec.url + '/export?f=image', 'bboxSR=102113', 'imageSR=102113'];

	if (transparent)
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
function getAttribution(spec)
{
	return spec.attribution.replace(/\[([- A-Za-z]+)\]/, '<a href="' + spec.url + '">$1</a>');
}
var MapServer = {};
MapServer.newOverlay = function(spec)
{
	var options = {
		zIndex: 210,
	};
	if (spec.attribution)
		options.attribution = getAttribution(spec);
	if (spec.opacity)
		options.opacity = spec.opacity;

	return new (tileLayer(spec, true))(options);
};
MapServer.newBaseLayer = function(spec)
{
	var options = {
	};
	if (spec.attribution)
		options.attribution = getAttribution(spec);

	return new (tileLayer(spec, false))(options);
};
function addOutlineCheckbox(spec, map)
{
	var input = document.createElement('input');
	input.type = 'checkbox';
	input.checked = false;
	input.addEventListener('click', function() {
		if (input.checked)
			spec.outline.addTo(map);
		else
			spec.outline.remove();
	}, false);

	spec.div.insertBefore(input, spec.ztf.nextSibling);
	spec.toggle = input;
}
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
		addOutlineCheckbox(popupSpec, map);
		popupDiv.appendChild(popupSpec.div);

		var queryLayer = spec.queryLayer || spec.exportLayers || '0';
		var baseURL = spec.url + '/' + queryLayer + '/query?f=' + responseFormat;

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
		var popupSpec = spec.popup;

		function showOutline(outline)
		{
			popupSpec.outline = outline;
			popupSpec.ztf.style.display = '';
			popupSpec.toggle.style.display = '';
			popupSpec.toggle.checked = true;
			popup.update();
			outlines.push(outline.addTo(map));
		}
		loadJSON(url, function(json) {
			if (clickID !== globalClickID) return;
			if (firstResponse) removeOutlines();
			if (json.features.length === 0) return;

			var attr = json.features[0][geojson ? 'properties' : 'attributes'];
			var style = popupSpec.show(attr);

			popupSpec.div.style.display = 'block';
			popupSpec.ztf.style.display = 'none';
			popupSpec.toggle.style.display = 'none';
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
