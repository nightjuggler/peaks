/* globals document, Image, L, loadJSON */
/* exported MapServer */

var MapServer = (function() {
'use strict';

var MapServer = {
	// Spatial Reference: 102100 (EPSG:3857) (WGS 84 / Pseudo-Mercator) unless otherwise specified.

	wildernessSpec: {
		// Spatial Reference: 102113 (EPSG:3785) (Popular Visualisation CRS / Mercator (deprecated))
		alias: 'w',
		url: 'https://gisservices.cfc.umt.edu/arcgis/rest/services/ProtectedAreas/National_Wilderness_Preservation_System/MapServer',
		exportLayers: '0',
		transparent: true,
		options: {opacity: 0.5, zIndex: 210},
		queryLayer: '0',
		queryFields: ['OBJECTID_1', 'NAME', 'URL', 'Agency', 'YearDesignated'],
	},
	topoSpec: {
		alias: 't',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer',
		exportLayers: '0',
		transparent: false,
		options: {zIndex: 210},
	},
	imageryTopoSpec: {
		alias: 'it',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer',
		exportLayers: '0',
		transparent: false,
		options: {zIndex: 210},
	},
	stateCountySpec: {
		alias: 'sc',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16', // states and counties
		transparent: true,
		options: {zIndex: 210},
		queryLayer: '12',
		queryFields: ['OBJECTID', 'NAME', 'STUSAB'],
	},
	countySpec: {
		alias: 'c',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '1,3,5,7,9,11,13', // counties only
		transparent: true,
		options: {zIndex: 210},
		queryLayer: '13',
		queryFields: ['OBJECTID', 'NAME'],
	},
	countyLabelsSpec: {
		alias: 'cl',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Labels/MapServer',
		exportLayers: '65',
		transparent: true,
		options: {zIndex: 210},
	},
	zipcodeSpec: {
		alias: 'z',
		url: 'https://gis.usps.com/arcgis/rest/services/EDDM/EDDM_ZIP5/MapServer',
		exportLayers: '0',
		transparent: true,
		options: {zIndex: 210},
	},
};

var earthRadius = 6378137; // WGS 84 equatorial radius in meters
var earthCircumference = 2 * Math.PI * earthRadius;
var tileOrigin = -(Math.PI * earthRadius);

function tileLayer(spec)
{
	var baseURL = [spec.url + '/export?f=image',
		'format=png',
		'layers=show:' + spec.exportLayers,
		'transparent=' + spec.transparent,
		'bboxSR=102113',
		'imageSR=102113'].join('&');

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
MapServer.addLayer = function(map, spec)
{
	map.addLayer(new (tileLayer(spec))(spec.options));
};
MapServer.enableQuery = function(map)
{
	var wildernessLink = document.createElement('a');
	var wildernessName = document.createTextNode('');
	var wildernessYear = document.createTextNode('');

	wildernessLink.appendChild(wildernessName);

	var popupDiv = document.createElement('div');
	popupDiv.className = 'popupDiv blmPopup';
	popupDiv.appendChild(wildernessLink);
	popupDiv.appendChild(document.createElement('br'));
	popupDiv.appendChild(wildernessYear);
	var popup = L.popup({maxWidth: 600}).setContent(popupDiv);

	var outline = null;
	var outlineCache = {};
	var outlineColor = {
		BLM: '#0000FF', // Blue   (fill color is #FFFF00)
		FWS: '#FFA500', // Orange (fill color is #FFAA00)
		NPS: '#800080', // Purple (fill color is #A900E6)
		USFS:'#008000', // Green  (fill color is #38A800)
	};
	var geojson = false;

	var spec = MapServer.wildernessSpec;

	var baseURL = spec.url + '/' + spec.queryLayer + '/query?f=' + (geojson ? 'geojson' : 'json');
	var queryLL = [baseURL,
		'returnGeometry=false',
		'outFields=' + spec.queryFields.join(','),
		'spatialRel=esriSpatialRelIntersects',
		'inSR=4326', // WGS 84 (EPSG:4326) longitude/latitude
		'geometryType=esriGeometryPoint',
		'geometry='].join('&');
	var queryID = [baseURL,
		'returnGeometry=true',
		'geometryPrecision=5',
		'outSR=4326',
		'objectIds='].join('&');

	function removeOutline()
	{
		if (outline) { outline.remove(); outline = null; }
	}

	map.on('click', function(event) {

	var ll = event.latlng;
	var url = queryLL + ll.lng.toFixed(6) + ',' + ll.lat.toFixed(6);

	function openPopup(json)
	{
		removeOutline();
		if (json.features.length === 0) return;
		json = json.features[0];
		var attr = geojson ? json.properties : json.attributes;
		var agency = attr.Agency;
		if (agency === 'FS') agency = 'USFS';

		wildernessLink.href = attr.URL;
		wildernessName.nodeValue = attr.NAME;
		wildernessYear.nodeValue = '(' + agency + ') (' + attr.YearDesignated + ')';

		map.openPopup(popup.setLatLng(ll));

		var outlineID = attr[spec.queryFields[0]];
		outline = outlineCache[outlineID];
		if (outline) { outline.addTo(map); return; }

		function addOutline(json)
		{
			if (json.features.length === 0) return;
			var geometry = json.features[0].geometry;
			if (!geojson)
			{
				if (json.geometryType !== 'esriGeometryPolygon') return;
				geometry = {type: 'Polygon', coordinates: geometry.rings};
			}
			var layer = L.GeoJSON.geometryToLayer(geometry,
				{color: outlineColor[agency] || '#000000', fillOpacity: 0});
			outlineCache[outlineID] = layer;
			if (!outline)
				outline = layer.addTo(map);
		}

		loadJSON(queryID + outlineID, addOutline);
	}

	loadJSON(url, openPopup, removeOutline);
	});
};

return MapServer;
})();
