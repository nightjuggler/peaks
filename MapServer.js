/* globals document, Image, L, loadJSON */
/* exported addWildernessTileLayer */

function addWildernessTileLayer(map)
{
	"use strict";

	var earthRadius = 6378137; // WGS 84 equatorial radius in meters
	var earthCircumference = 2 * Math.PI * earthRadius;
	var tileOrigin = -(Math.PI * earthRadius);

	var wildernessMapServer = 'https://gisservices.cfc.umt.edu/arcgis/rest/services/ProtectedAreas/National_Wilderness_Preservation_System/MapServer';

	var WildernessTileLayer = L.GridLayer.extend({
	createTile: function(tileCoords, done)
	{
		var m = earthCircumference / (1 << tileCoords.z); // tile size in meters
		var x = tileOrigin + m*tileCoords.x;
		var y = tileOrigin + m*tileCoords.y;

		var tileSize = this.getTileSize();

		var url = wildernessMapServer + '/export?' + [
			'bbox=' + [x.toFixed(4), (-y-m).toFixed(4), (x+m).toFixed(4), (-y).toFixed(4)].join(','),
			'layers=0',
			'size=' + tileSize.x + ',' + tileSize.y,
			'format=png',
			'transparent=true',
			'f=image'].join('&');

		var tile = new Image(tileSize.x, tileSize.y);

		tile.addEventListener('load', function() { done(null, tile); }, false);
		tile.addEventListener('error', function() { done("Failed to load " + url, tile); }, false);
		tile.src = url;

		return tile;
	}
	});

	map.addLayer(new WildernessTileLayer({opacity: 0.5, zIndex: 210}));

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

	map.on('click', function(event) {
		var size = map.getSize();
		var bounds = map.getBounds();
		var sw = bounds.getSouthWest();
		var ne = bounds.getNorthEast();
		var ll = event.latlng;

		var url = wildernessMapServer + '/identify?' + [
			'geometry=' + ll.lng.toFixed(6) + ',' + ll.lat.toFixed(6),
			'geometryType=esriGeometryPoint',
			'sr=4326',
			'tolerance=4',
			'mapExtent=' + [
				sw.lng.toFixed(6), sw.lat.toFixed(6),
				ne.lng.toFixed(6), ne.lat.toFixed(6)].join(','),
			'imageDisplay=' + size.x + ',' + size.y + ',96',
			'returnGeometry=true',
			'geometryPrecision=5',
			'returnUnformattedValues=false',
			'returnFieldName=false',
			'f=json'].join('&');

		loadJSON(url, function(json) {
			if (outline) { outline.remove(); outline = null; }
			if (json.results.length === 0) return;

			json = json.results[0];
			var attr = json.attributes;
			var agency = attr.Agency;
			if (agency === 'FS') agency = 'USFS';

			wildernessLink.href = attr.URL;
			wildernessName.nodeValue = attr.NAME;
			wildernessYear.nodeValue = '(' + agency + ') (' + attr.YearDesignated + ')';

			map.openPopup(popup.setLatLng(ll));

			if (json.geometryType !== 'esriGeometryPolygon') return;

			var objectId = attr.OBJECTID_1;

			outline = outlineCache[objectId];
			if (!outline)
				outlineCache[objectId] = outline = L.GeoJSON.geometryToLayer(
					{type: 'Polygon', coordinates: json.geometry.rings},
					{color: outlineColor[agency] || '#000000', fillOpacity: 0});

			outline.addTo(map);
		});
	});
}
