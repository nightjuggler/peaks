/* globals document, Image, L, loadJSON */
/* exported addWildernessTileLayer */

function addWildernessTileLayer(map)
{
	"use strict";

	var earthRadius = 6378137.0; // WGS 84 equatorial radius in meters
	var earthCircumference = 2 * Math.PI * earthRadius;
	var tileOrigin = -(Math.PI * earthRadius);

	var WildernessServer = 'https://gisservices.cfc.umt.edu/arcgis/rest/services/ProtectedAreas/National_Wilderness_Preservation_System/MapServer';

	var WildernessTileLayer = L.GridLayer.extend({
	createTile: function(tileCoords, done)
	{
		var m = earthCircumference / (1 << tileCoords.z); // tile size in meters
		var x = tileOrigin + m*tileCoords.x;
		var y = tileOrigin + m*tileCoords.y;

		var tileSize = this.getTileSize();

		var url = WildernessServer + '/export?' + [
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

	map.addLayer(new WildernessTileLayer({opacity: 0.5}));

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

	map.on('click', function(event) {
		var size = map.getSize();
		var bounds = map.getBounds();
		var sw = bounds.getSouthWest();
		var ne = bounds.getNorthEast();
		var ll = event.latlng;

		var url = WildernessServer + '/identify?' + [
			'geometry=' + ll.lng.toFixed(6) + ',' + ll.lat.toFixed(6),
			'geometryType=esriGeometryPoint',
			'sr=4326',
			'tolerance=4',
			'mapExtent=' + [
				sw.lng.toFixed(6), sw.lat.toFixed(6),
				ne.lng.toFixed(6), ne.lat.toFixed(6)].join(','),
			'imageDisplay=' + size.x + ',' + size.y + ',96',
			'returnGeometry=false',
			'geometryPrecision=6',
			'returnUnformattedValues=false',
			'returnFieldName=false',
			'f=json'].join('&');

		loadJSON(url, function(json) {
			if (json.results.length === 0) return;

			var attr = json.results[0].attributes;

			wildernessLink.href = attr.URL;
			wildernessName.nodeValue = attr.NAME;
			wildernessYear.nodeValue = ' (' + attr.Agency + ') (' + attr.YearDesignated + ')';

			map.openPopup(popup.setLatLng(ll));
		});
	});
}
