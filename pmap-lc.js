"use strict";
/* globals console, document, Image, window */
/* globals L */
/* globals enableTooltips */
/* globals loadJSON */

var BLM_CA_NLCS_Prefix = 'https://www.blm.gov/nlcs_web/sites/ca/st/en/prog/nlcs/';
var USFS_Prefix = 'https://www.fs.usda.gov/';
var USFS_NM_Prefix = 'https://www.fs.fed.us/visit/';
var Weather_Prefix = 'https://forecast.weather.gov/MapClick.php';
var Wikipedia_Prefix = 'https://en.wikipedia.org/wiki/';
var Wilderness_Prefix = 'https://www.wilderness.net/NWPS/wildView?WID=';

var lcItemFitLink;
var lcItemHoverColor = 'rgb(232, 232, 232)';
var menuDisplayedIcon = ' \u25BC';
/*
	\uFE0E is a variation selector to indicate that the preceding character - the
	black right-pointing triangle (\u25B6) - should be rendered text-style rather
	than emoji-style. If the variation selector isn't specified, desktop browsers
	seem to default to text-style while mobile browsers seem to default to emoji-
	style. [http://www.unicode.org/Public/UNIDATA/StandardizedVariants.txt]
*/
var menuCollapsedIcon = ' \u25B6\uFE0E';
var addFunctions = {};

function wikipediaLink(w)
{
	var link = document.createElement('a');
	link.href = Wikipedia_Prefix + w;
	link.appendChild(document.createTextNode('W'));
	return link;
}
function fitLink(fitBounds, className)
{
	var img = new Image();
	img.alt = 'Zoom To Fit';
	img.src = 'ztf.svg';
	img.className = className;
	img.addEventListener('click', fitBounds, false);
	return img;
}
function popupFitLink(map, layer)
{
	function fitBounds(event)
	{
		event.preventDefault();
		layer.closePopup();
		map.fitBounds(layer.getBounds());
	}
	return fitLink(fitBounds, 'popupZtf');
}
function raiseLink(layer)
{
	function bringToFront(event)
	{
		event.preventDefault();
		layer.closePopup().bringToFront();
	}
	var a = document.createElement('a');
	a.href = '#';
	a.className = 'bringToFront';
	a.appendChild(document.createTextNode('\u2B06\uFE0F'));
	a.addEventListener('click', bringToFront, false);
	return a;
}
function lowerLink(layer)
{
	function bringToBack(event)
	{
		event.preventDefault();
		layer.closePopup().bringToBack();
	}
	var a = document.createElement('a');
	a.href = '#';
	a.className = 'bringToBack';
	a.appendChild(document.createTextNode('\u2B07\uFE0F'));
	a.addEventListener('click', bringToBack, false);
	return a;
}
function weatherLink(layer)
{
	var a = document.createElement('a');

	function setWxLink()
	{
		var ll = layer.getPopup().getLatLng();
		a.href = Weather_Prefix +
			'?lon=' + ll.lng.toFixed(6) +
			'&lat=' + ll.lat.toFixed(6);
	}

	a.href = '#';
	a.className = 'wxLink';
	a.appendChild(document.createTextNode('\u26C5'));
	a.addEventListener('click', setWxLink, false);

	return a;
}
function bindPopup(popupDiv, map, layer)
{
	popupDiv.appendChild(document.createElement('br'));
	popupDiv.appendChild(popupFitLink(map, layer));
	popupDiv.appendChild(weatherLink(layer));
	popupDiv.appendChild(lowerLink(layer));
	popupDiv.appendChild(raiseLink(layer));
	layer.bindPopup(popupDiv, {maxWidth: 600});
}
function addNameMap(item)
{
	if (item.order)
	{
		item.nameMap = {};
		for (var id of item.order)
		{
			var child = item.items[id];
			item.nameMap[child.name] = child;
			addNameMap(child);
		}
	}
}
function delNameMap(item)
{
	if (item.order)
	{
		delete item.nameMap;
		for (var id of item.order)
			delNameMap(item.items[id]);
	}
}
function extendBounds(item, layer)
{
	var bounds = layer.getBounds();
	if (item.bounds)
		item.bounds.extend(bounds);
	else
		item.bounds = L.latLngBounds(bounds.getSouthWest(), bounds.getNorthEast());
}
function assignLayer(item, namePath, layer, featureProperties)
{
	var nextItem;
	var lastName = namePath.pop();

	var setBounds = false;
	var skipBounds = false;

	if (featureProperties && featureProperties.flags) {
		if (featureProperties.flags & 1) setBounds = true;
		if (featureProperties.flags & 2) skipBounds = true;
	}

	if (!item.nameMap) {
		console.log('assignLayer failed: "' + item.name + '" doesn\'t have a name map!');
		return;
	}
	for (var name of namePath)
	{
		if (!(nextItem = item.nameMap[name])) {
			console.log('assignLayer failed to get from "' + item.name + '" to "' + name + '"');
			return;
		}
		item = nextItem;
		if (!item.nameMap) {
			console.log('assignLayer failed: "' + item.name + '" doesn\'t have a name map!');
			return;
		}
		if (!skipBounds)
			extendBounds(item, layer);
	}
	if (!(nextItem = item.nameMap[lastName])) {
		console.log('assignLayer failed to get from "' + item.name + '" to "' + lastName + '"');
		return;
	}
	item = nextItem;
	if (setBounds) {
		if (!item.nameMap) {
			console.log('assignLayer failed: "' + item.name + '" doesn\'t have a name map!');
			return;
		}
		extendBounds(item, layer);
	}
	else if (item.nameMap) {
		console.log('assignLayer failed: "' + item.name + '" has a name map!');
		return;
	}
	if (item.layer) {
		console.log('assignLayer failed: "' + item.name + '" already has a layer!');
		return;
	}
	item.layer = layer;
}
addFunctions.default = function(geojson, map, lcItem)
{
	return L.geoJSON(geojson, {style: {color: '#FF4500'/* OrangeRed */}});
};
addFunctions.add_BLM_CA_Districts = function(geojson, map, lcItem)
{
	var style = {
		'Northern California District': {color: '#4169E1'}, // RoyalBlue
		'Central California District': {color: '#1E90FF'}, // DodgerBlue
		'California Desert District': {color: '#00BFFF'}, // DeepSkyBlue
	};
	function getStyle(feature)
	{
		return style[feature.properties.parent] || {};
	}
	function addPopup(feature, layer)
	{
		var name = feature.properties.name.slice(0, -13); // strip trailing " Field Office"
		var parent = feature.properties.parent;

		var popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		var bold = document.createElement('b');
		bold.appendChild(document.createTextNode('BLM ' + name));
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + parent + ')'));

		bindPopup(popupDiv, map, layer);
		assignLayer(lcItem, [parent, feature.properties.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
};
function officeIcon()
{
	var fill = 'cyan';
	var stroke = 'blue';

	var o = {iconSize: [26, 20], className: 'officeIcon', popupAnchor: [0, -4]};
	o.html = '<svg xmlns="http://www.w3.org/2000/svg" width="26" height="20" viewBox="0 0 26 20">'
		+ '<path fill="' + fill + '" stroke="' + stroke + '" stroke-width="2" '
		+ 'd="M 13,1 L 1,10 3,10 3,19 11,19 11,10 15,10 15,19 23,19 23,10 25,10 Z" /></svg>';
	return L.divIcon(o);
}
addFunctions.add_BLM_Offices = function(geojson, map, lcItem)
{
	function addPopup(feature, latlng)
	{
		var name = feature.properties.name;
		var html = '<div class="popupDiv blmPopup"><b>BLM ' + name + '</b></div>';
		return L.marker(latlng, {icon: officeIcon()})
			.bindPopup(html, {maxWidth: 600})
			.on('dblclick', function() {
				map.setView(latlng, map.getMaxZoom() - 5);
			});
	}

	return L.geoJSON(geojson, {pointToLayer: addPopup});
};
addFunctions.add_BLM_Lands = function(geojson, map, lcItem)
{
	var USFS_Style = {color: '#008000'}; // Green
	var BLM_Style = {color: '#00008B'}; // DarkBlue

	function getStyle(feature)
	{
		if (feature.properties.agency === 'USFS')
			return USFS_Style;
		return BLM_Style;
	}
	function addPopup(feature, layer)
	{
		var name = feature.properties.name;
		var agency = feature.properties.agency;

		var popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';

		var bold = document.createElement('b');
		var link = document.createElement('a');

		link.href = BLM_CA_NLCS_Prefix + feature.properties.BLM;
		if (name.length < 23) {
			link.appendChild(document.createTextNode(name + ' ' + feature.properties.D));
		} else {
			link.appendChild(document.createTextNode(name));
			link.appendChild(document.createElement('br'));
			link.appendChild(document.createTextNode(feature.properties.D));
		}
		bold.appendChild(link);
		bold.appendChild(document.createTextNode(' ['));
		bold.appendChild(wikipediaLink(feature.properties.W));
		bold.appendChild(document.createTextNode(']'));
		popupDiv.appendChild(bold);

		var namePath = [name + ' ' + feature.properties.D];
		if (agency)
		{
			popupDiv.appendChild(document.createElement('br'));
			if (agency === 'USFS')
			{
				namePath.push('Forest Service Lands');
				if (feature.properties.FS)
				{
					popupDiv.appendChild(document.createTextNode(
						'This part is managed by the '));
					link = document.createElement('a');
					link.href = USFS_NM_Prefix + feature.properties.FS;
					link.appendChild(document.createTextNode('Forest Service'));
					popupDiv.appendChild(link);
					popupDiv.appendChild(document.createTextNode(':'));
				}
				else
					popupDiv.appendChild(document.createTextNode(
						'This part is managed by the Forest Service:'));

				var forestName = feature.properties.NFW.replace(/_/g, ' ');
				link = document.createElement('a');
				link.href = USFS_Prefix + feature.properties.NF;
				link.appendChild(document.createTextNode(forestName));

				popupDiv.appendChild(document.createElement('br'));
				popupDiv.appendChild(link);
				popupDiv.appendChild(document.createTextNode(' ['));
				popupDiv.appendChild(wikipediaLink(feature.properties.NFW));
				popupDiv.appendChild(document.createTextNode(']'));
			} else {
				namePath.push(agency + ' Lands');
				popupDiv.appendChild(document.createTextNode(
					'This part is managed by the ' + agency + '.'));
			}
		}

		bindPopup(popupDiv, map, layer);
		assignLayer(lcItem, namePath, layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
};
addFunctions.add_BLM_Wilderness = function(geojson, map, lcItem)
{
	var style = {
		BLM: {color: '#FF8C00'}, // DarkOrange
		FWS: {color: '#FFA07A'}, // LightSalmon
		NPS: {color: '#FFD700'}, // Gold
		USFS: {color: '#808000'}, // Olive
	};
	function getStyle(feature)
	{
		return style[feature.properties.agency] || {};
	}
	function addPopup(feature, layer)
	{
		var name = feature.properties.name + ' Wilderness';
		var agency = feature.properties.agency;
		var date = feature.properties.D;
		var namePath = [name];
		if (feature.properties.m)
			namePath.push(date + ' ' + agency);

		var popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		var bold = document.createElement('b');
		bold.appendChild(document.createTextNode(name));
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createTextNode(' (' + agency + ')'));
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('Designated ' + date));
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('['));
		var wildLink = document.createElement('a');
		wildLink.href = Wilderness_Prefix + feature.properties.id;
		wildLink.appendChild(document.createTextNode('Wilderness.net'));
		popupDiv.appendChild(wildLink);
		popupDiv.appendChild(document.createTextNode(']'));

		bindPopup(popupDiv, map, layer);
		assignLayer(lcItem, namePath, layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
};
addFunctions.add_BLM_WSA = function(geojson, map, lcItem)
{
	function addPopup(feature, layer)
	{
		var p = feature.properties;

		var popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		var bold = document.createElement('b');
		bold.appendChild(document.createTextNode(p.name + ' Wilderness Study Area'));
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + p.code + ')'));
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('BLM Recommendation: ' + p.rcmnd));

		bindPopup(popupDiv, map, layer);
		assignLayer(lcItem, [p.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#000000'}});
};
addFunctions.add_BLM_WSA_Released = function(geojson, map, lcItem)
{
	function addPopup(feature, layer)
	{
		var p = feature.properties;

		var popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		var bold = document.createElement('b');
		bold.appendChild(document.createTextNode(p.name + ' WSA (Released)'));
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + p.code + ')'));

		bindPopup(popupDiv, map, layer);
		assignLayer(lcItem, [p.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#A52A2A'/* Brown */}});
};
function appendName(name, node)
{
	var parts = name.split('|');
	var lineBreak = node.lastChild !== null;
	for (var part of parts)
	{
		if (lineBreak)
			node.appendChild(document.createElement('br'));
		else
			lineBreak = true;
		node.appendChild(document.createTextNode(part));
	}
	return parts.join(' ');
}
addFunctions.add_NPS = function(geojson, map, lcItem)
{
	function addPopup(feature, layer)
	{
		var p = feature.properties;
		var bold = document.createElement('b');
		var link = document.createElement('a');
		link.href = 'https://www.nps.gov/' + p.code + '/index.htm';

		p.name = appendName(p.name, link);

		bold.appendChild(link);
		bold.appendChild(document.createTextNode(' ['));
		bold.appendChild(wikipediaLink(p.W || p.name.replace(/ /g, '_')));
		bold.appendChild(document.createTextNode(']'));

		var popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);

		var namePath = [p.name];
		if (p.name2) {
			p.name2 = appendName(p.name2, popupDiv);
			namePath.push(p.name2);
			if (p.W2) {
				popupDiv.appendChild(document.createTextNode(' ['));
				popupDiv.appendChild(wikipediaLink(p.W2));
				popupDiv.appendChild(document.createTextNode(']'));
			}
		}

		bindPopup(popupDiv, map, layer);
		assignLayer(lcItem, namePath, layer, p);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#FFFF00'/* Yellow */}});
};
function makeLink(url, txt)
{
	return '<a href="' + url + '">' + txt + '</a>';
}
function popupHtml(ll, p, htmlFilename)
{
	var g4Params = p.G4.split('&');
	var z = g4Params[0];
	var b = g4Params[1];
	b = b === 't=t4' ? 'b=t&o=r&n=0.2' : 'b=mbh';

	var topoLink = 'https://caltopo.com/map.html#ll=' + ll.lat + ',' + ll.lng + '&' + z + '&' + b;

	var suffix = p.HP ? ' HP' : p.emblem ? ' **' : p.mtneer ? ' *' : '';

	var otherName = p.name2 ? '<br>(' + p.name2 + ')' : '';

	var name = makeLink(htmlFilename + p.id.split('.')[0], p.id) + ' ' +
		makeLink(topoLink, p.name) + suffix + otherName;

	var links = [];
	if (p.SP) links.push(makeLink('https://www.summitpost.org/' + p.SP, 'SP'));
	if (p.W) links.push(makeLink(Wikipedia_Prefix + p.W, 'W'));
	if (p.BB) links.push(makeLink('http://www.snwburd.com/dayhikes/peak/' + p.BB, 'BB'));
	if (p.LoJ) links.push(makeLink('https://listsofjohn.com/peak/' + p.LoJ, 'LoJ'));
	if (p.Pb) links.push(makeLink('http://peakbagger.com/peak.aspx?pid=' + p.Pb, 'Pb'));
	if (!p.noWX) links.push(makeLink(Weather_Prefix + '?lon=' + ll.lng + '&lat=' + ll.lat, 'WX'));

	links = links.length === 0 ? '' : '<br>' + links.join(', ');

	var yds = p.YDS ? '<br>Class ' + p.YDS : '';
	var climbed = p.climbed ? '<br>Climbed <div class="elevDiv">' + p.climbed + '</div>' : '';

	return '<div class="popupDiv"><b>' + name + '</b>'
		+ '<br>Elevation: <div class="elevDiv">' + p.elev + '</div>'
		+ '<br>Prominence: <div class="elevDiv">' + p.prom + '</div>'
		+ yds + links + climbed + '</div>';
}
function peakIcon(p)
{
	var fill = p.emblem ? 'magenta' : p.mtneer ? 'cyan' : 'white';
	var stroke = p.climbed ? 'green' : 'red';

	var o = {iconSize: [20, 26], className: 'peakIcon', popupAnchor: [0, -8]};
	o.html = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="26" viewBox="0 0 20 26">'
		+ '<path fill="' + fill + '" stroke="' + stroke + '" stroke-width="3" '
		+ 'd="M 10,2 L 1,19 19,19 Z" /></svg>';
	return L.divIcon(o);
}
addFunctions.addPeakOverlay = function(geojson, map, lcItem)
{
	var id = geojson.id;
	var htmlFilename = id.toLowerCase() + '.html#' + id;

	function addPeak(feature, latlng)
	{
		var p = feature.properties;
		return L.marker(latlng, {icon: peakIcon(p)})
			.bindPopup(popupHtml(latlng, p, htmlFilename))
			.on('popupopen', enableTooltips)
			.on('dblclick', function() {
				map.setView(latlng, map.getMaxZoom() - 5);
			});
	}

	return L.geoJSON(geojson, {pointToLayer: addPeak});
};
addFunctions.add_UC_Reserve = function(geojson, map, lcItem)
{
	function addPopup(feature, layer)
	{
		var p = feature.properties;

		var popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		var bold = document.createElement('b');
		bold.appendChild(document.createTextNode(p.name));
		if (p.name2) {
			bold.appendChild(document.createElement('br'));
			bold.appendChild(document.createTextNode(p.name2));
		}
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + p.campus + ')'));

		bindPopup(popupDiv, map, layer);
//		assignLayer(lcItem, [p.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#FF00FF'/* Magenta */}});
};
function getTop(div)
{
	var top = div.offsetTop;

	while (div.offsetParent !== document.body)
	{
		div = div.offsetParent;
		top += div.offsetTop;
	}

	return top;
}
function toggleLayerMenu(event)
{
	var arrowSpan = event.currentTarget;
	var menu = arrowSpan.parentNode.nextSibling;

	var lcDiv = document.getElementById('layerControl');
	var scDiv = document.getElementById('scaleControl');
	var lcTop = getTop(lcDiv);
	var scTop = getTop(scDiv);
	var maxHeight = Math.max(scTop - lcTop - 20, 100);
	var scrollTop = lcDiv.scrollTop;

	lcDiv.style.height = 'auto';

	if (menu.style.display === 'block') {
		menu.style.display = 'none';
		arrowSpan.firstChild.nodeValue = menuCollapsedIcon;
	} else {
		menu.style.display = 'block';
		arrowSpan.firstChild.nodeValue = menuDisplayedIcon;
	}

	if (lcDiv.offsetHeight > maxHeight) {
		lcDiv.style.height = maxHeight + 'px';
		lcDiv.scrollTop = scrollTop;
	}
}
function LayerControl(map)
{
	var div = document.getElementById('layerControl');
	var icon = document.getElementById('layerControlIcon');

	function show()
	{
		div.style.display = 'block';
	}
	function hide()
	{
		div.style.display = 'none';
	}
	function documentTouch(event)
	{
		var node = event.target;
		while (node && node !== div)
			node = node.parentNode;
		if (!node) {
			document.removeEventListener('touchstart', documentTouch);
			icon.addEventListener('touchstart', iconTouch);
			hide();
		}
	}
	function iconTouch(event)
	{
		event.preventDefault();
		event.stopPropagation();
		icon.removeEventListener('touchstart', iconTouch);
		document.addEventListener('touchstart', documentTouch);
		show();
	}
	icon.addEventListener('mouseenter', show);
	icon.addEventListener('mouseleave', hide);
	icon.addEventListener('touchstart', iconTouch);

	this.map = map;
	this.div = div;
}
function clickArrow(event)
{
	event.currentTarget.parentNode.firstChild.click();
}
function lcItemFitBounds(map)
{
	return function(event)
	{
		event.preventDefault();

		var item = event.currentTarget.parentNode.lcItem;
		if (item.bounds) {
			map.fitBounds(item.bounds);
		} else if (item.layer) {
			item.layer.closePopup();
			map.fitBounds(item.layer.getBounds());
		} else if (item.featureGroup) {
			map.fitBounds(item.featureGroup.getBounds());
		}
	};
}
function showZoomToFit(event)
{
	var div = event.currentTarget;
	if (lcItemFitLink.parentNode !== div)
	{
		div.style.paddingRight = '8px';
		div.appendChild(lcItemFitLink);
	}
}
function hideZoomToFit(event)
{
	var div = event.currentTarget;
	if (lcItemFitLink.parentNode === div)
	{
		div.style.paddingRight = '23px';
		div.removeChild(lcItemFitLink);
	}
}
function addZoomToFitHandlers(item)
{
	var itemDiv = item.div;

	var bgColor = window.getComputedStyle(itemDiv).backgroundColor;
	if (bgColor === lcItemHoverColor)
		itemDiv.appendChild(lcItemFitLink);
	else
		itemDiv.style.paddingRight = '23px';

	itemDiv.addEventListener('mouseenter', showZoomToFit, false);
	itemDiv.addEventListener('mouseleave', hideZoomToFit, false);
/*
	Tapping an element in a mobile browser triggers the following sequence
	of events: touchstart, touchmove, touchend, mouseover, mouseenter,
	mousemove, mousedown, mouseup, and click. However, "if the contents of
	the page changes" during the handling of the mouseover, mouseenter, or
	mousemove events, the subsequent events (mousedown, mouseup, and click)
	are not fired!

	So in a mobile environment, when a menu item is first tapped, the
	mouseenter handler (showZoomToFit) would append the zoom-to-fit link
	to the menu item's div, and since that changes the contents of the
	page, the click event would not occur and any associated submenu would
	not open or close. When the item is tapped again, the zoom-to-fit link
	will already have been added, and so the click will fire, and the
	submenu will open or close.

	To avoid having to tap twice, we'll handle the initial touchstart event
	and add the zoom-to-fit link in that handler so that the subsequent
	mouseenter handler won't change the page, thus allowing the click to fire.

	Note that currently (3/10/2017), it is sometimes possible to tap an
	element such that only the mouse events fire but not the touch events!
	This occurs in mobile versions of both Firefox and Safari (I haven't
	checked other browsers), and it appears to occur only with menu items
	whose text spans more than one line, e.g. Berryessa Snow Mountain
	National Monument, and especially when tapping the second line of such
	items. When that happens, a second tap will be necessary to open or
	close any associated submenu.
*/
	itemDiv.addEventListener('touchstart', showZoomToFit, false);

	if (item.order)
		for (var id of item.order)
			addZoomToFitHandlers(item.items[id]);
}
function checkUpToFileParent(item)
{
	while (item !== item.fileParent)
	{
		item = item.parent;
		item.checkbox.checked = true;
	}
}
function checkSubtree(topItem)
{
	for (var id of topItem.order)
	{
		var item = topItem.items[id];
		if (item.order)
			checkSubtree(item);
		item.checkbox.checked = true;
	}
}
function isCheckedToFileParent(item)
{
	while (item !== item.fileParent)
	{
		item = item.parent;
		if (!item.checkbox.checked)
			return false;
	}
	return true;
}
function addLayersToMap(item, map, extendBounds)
{
	if (item.layer) {
		item.layer.addTo(map);
		if (extendBounds)
			extendBounds(item.layer.getBounds());
	}
	if (item.order) {
		for (var id of item.order)
		{
			var child = item.items[id];
			if (child.checkbox.checked)
				addLayersToMap(child, map, extendBounds);
		}
	} else if (item.featureGroup) {
		item.featureGroup.addTo(map);
		if (extendBounds)
			extendBounds(item.featureGroup.getBounds());
	}
}
function removeLayersFromMap(item)
{
	if (item.layer)
		item.layer.remove();
	if (item.order) {
		for (var id of item.order)
		{
			var child = item.items[id];
			if (child.checkbox.checked)
				removeLayersFromMap(child);
		}
	} else if (item.featureGroup)
		item.featureGroup.remove();
}
function addCheckboxClickHandler(item, map)
{
	var checkbox = item.checkbox;
	var fileParent = item.fileParent;

	function addWrapper(geojson)
	{
		addNameMap(fileParent);
		fileParent.featureGroup = fileParent.add(geojson, map, fileParent);
		delNameMap(fileParent);

		var sizeSpan = fileParent.div.lastChild;
		sizeSpan.parentNode.removeChild(sizeSpan);

		if (!lcItemFitLink)
			lcItemFitLink = fitLink(lcItemFitBounds(map), 'lcZtf');

		addZoomToFitHandlers(fileParent);
		if (fileParent.checkbox.checked)
			if (item.mapBounds) {
				addLayersToMap(fileParent, map, item.mapBounds.extend);
				item.mapBounds.delSetter(item);
			} else
				addLayersToMap(fileParent, map);
	}
	function clickHandler()
	{
		if (fileParent.featureGroup)
		{
			if (!isCheckedToFileParent(item))
				return;
			if (checkbox.checked)
				addLayersToMap(item, map);
			else
				removeLayersFromMap(item);
		}
		else if (!checkbox.checked)
			return;
		else if (fileParent.featureGroup === undefined)
		{
			checkUpToFileParent(item);
			if (item.order)
				checkSubtree(item);

			var progressBar = document.createElement('progress');
			fileParent.div.insertBefore(progressBar, fileParent.div.lastChild);

			progressBar.max = 100;
			progressBar.value = 0;

			loadJSON(fileParent.fileName, addWrapper, undefined, progressBar);
			fileParent.featureGroup = null;
		}
		else if (item.mapBounds)
			item.mapBounds.delSetter(item);
	}

	checkbox.addEventListener('click', clickHandler, false);
}
function getPathStr(path, id)
{
	path.push(id);
	var pathStr = path.join('/');
	path.pop();
	return pathStr;
}
function validateItem(item, path, id)
{
	if (item.parent.fileParent)
	{
		if (item.add) {
			console.log(getPathStr(path, id) + ': Cannot have an add function within a file!');
			return false;
		}
		if (item.size) {
			console.log(getPathStr(path, id) + ': Cannot have a file within a file!');
			return false;
		}
		item.fileParent = item.parent.fileParent;
		return true;
	}

	if (item.add)
	{
		var funcName = 'add' + item.add;
		var addFunc = addFunctions[funcName];

		if (typeof addFunc !== 'function') {
			console.log(getPathStr(path, id) + ': "' + funcName + '" is not a function!');
			return false;
		}
		item.add = addFunc;
	}
	else if (item.parent.add)
		item.add = item.parent.add;

	if (item.size)
	{
		item.fileName = 'json/' + getPathStr(path, id) + '.json';
		item.fileParent = item;
		if (!item.add)
			item.add = addFunctions.default;
	}
	return true;
}
LayerControl.prototype.addOverlays = function(parentDiv, parentItem, path)
{
	for (var id of parentItem.order)
	{
		var item = parentItem.items[id];
		item.parent = parentItem;

		if (!validateItem(item, path, id)) continue;

		var nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		item.name = appendName(item.name, nameSpan);

		var itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';
		itemDiv.appendChild(nameSpan);

		if (item.size)
		{
			var sizeSpan = document.createElement('span');
			sizeSpan.appendChild(document.createTextNode('(' + item.size + ')'));
			itemDiv.appendChild(sizeSpan);
		}
		if (item.fileParent)
		{
			var checkbox = document.createElement('input');
			checkbox.type = 'checkbox';
			checkbox.checked = false;
			itemDiv.insertBefore(checkbox, nameSpan);

			if (!item.items)
				itemDiv.style.paddingLeft = '18px';

			itemDiv.lcItem = item;
			item.div = itemDiv;
			item.checkbox = checkbox;

			addCheckboxClickHandler(item, this.map);
		}

		parentDiv.appendChild(itemDiv);

		if (item.items)
		{
			var childDiv = document.createElement('div');
			childDiv.className = 'lcMenu';

			path.push(id);
			this.addOverlays(childDiv, item, path);
			path.pop();

			parentDiv.appendChild(childDiv);

			var arrowSpan = document.createElement('span');
			arrowSpan.className = 'lcArrow';
			arrowSpan.appendChild(document.createTextNode(menuCollapsedIcon));
			arrowSpan.addEventListener('click', toggleLayerMenu, false);

			itemDiv.insertBefore(arrowSpan, itemDiv.firstChild);
			nameSpan.addEventListener('click', clickArrow, false);
		}
	}
};
function getItem(path, item)
{
	for (var id of path)
	{
		if (!item.items) {
			return null;
		}
		var nextItem = item.items[id];
		if (!nextItem) {
			return null;
		}
		if (typeof nextItem === 'string') {
			var subPath = nextItem.split('/');
			subPath.push(id);
			nextItem = getItem(subPath, item);
			if (!nextItem)
				return null;
		}
		item = nextItem;
	}
	return item;
}
LayerControl.prototype.setOverlays = function(overlays, rootLCD, mapBounds)
{
	for (var pathStr of overlays)
	{
		var item = getItem(pathStr.split('_'), rootLCD);
		if (item && item.checkbox && !item.checkbox.checked) {
			mapBounds.addSetter(item);
			item.checkbox.click();
		}
	}
};
function makeChangeBaseLayer(ctrl, item)
{
	return function() {
		if (ctrl.currentBaseLayer === item.layer) return;
		if (ctrl.currentBaseLayer)
			ctrl.currentBaseLayer.remove();
		ctrl.currentBaseLayer = item.layer.addTo(ctrl.map);
		item.input.checked = true;
	};
}
LayerControl.prototype.addBaseLayers = function(parentDiv, parentItem, path, parentMakeLayer)
{
	for (var id of parentItem.order)
	{
		var item = parentItem.items[id];

		var nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		item.name = appendName(item.name, nameSpan);

		var itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';
		itemDiv.appendChild(nameSpan);

		parentDiv.appendChild(itemDiv);

		var makeLayer = this.baseLayerMakers[getPathStr(path, id)] || parentMakeLayer;

		if (item.items) {
			var childDiv = document.createElement('div');
			childDiv.className = 'lcMenu';

			path.push(id);
			this.addBaseLayers(childDiv, item, path, makeLayer);
			path.pop();

			parentDiv.appendChild(childDiv);

			var arrowSpan = document.createElement('span');
			arrowSpan.className = 'lcArrow';
			arrowSpan.appendChild(document.createTextNode(menuCollapsedIcon));
			arrowSpan.addEventListener('click', toggleLayerMenu, false);

			itemDiv.insertBefore(arrowSpan, itemDiv.firstChild);
			nameSpan.addEventListener('click', clickArrow, false);
		} else {
			var input = document.createElement('input');
			input.type = 'radio';
			input.name = 'baselayer';
			input.checked = false;
			itemDiv.insertBefore(input, nameSpan);

			item.input = input;
			item.layer = makeLayer(item);

			var changeBaseLayer = makeChangeBaseLayer(this, item);
			nameSpan.addEventListener('click', changeBaseLayer);
			input.addEventListener('click', changeBaseLayer);
		}
	}
};
LayerControl.prototype.setBaseLayer = function(pathStr, rootLCD)
{
	var item = getItem(pathStr.split('_'), rootLCD);
	if (!item || !item.input) return;

	this.currentBaseLayer = item.layer.addTo(this.map);
	item.input.checked = true;
};
function addTileOverlayClickHandler(ctrl, item)
{
	var input = item.input;

	function clickCheckbox()
	{
		if (input.checked)
			item.layer.addTo(ctrl.map);
		else
			item.layer.remove();
	}
	function clickName()
	{
		input.checked = !input.checked;
		clickCheckbox();
	}

	input.addEventListener('click', clickCheckbox);
	input.nextSibling.addEventListener('click', clickName);
}
LayerControl.prototype.addTileOverlays = function(parentDiv, parentItem, path, makeLayer)
{
	for (var id of parentItem.order)
	{
		var item = parentItem.items[id];

		var nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		item.name = appendName(item.name, nameSpan);

		var itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';
		itemDiv.appendChild(nameSpan);

		parentDiv.appendChild(itemDiv);

		if (item.items) {
			var childDiv = document.createElement('div');
			childDiv.className = 'lcMenu';

			path.push(id);
			this.addTileOverlays(childDiv, item, path, makeLayer);
			path.pop();

			parentDiv.appendChild(childDiv);

			var arrowSpan = document.createElement('span');
			arrowSpan.className = 'lcArrow';
			arrowSpan.appendChild(document.createTextNode(menuCollapsedIcon));
			arrowSpan.addEventListener('click', toggleLayerMenu, false);

			itemDiv.insertBefore(arrowSpan, itemDiv.firstChild);
			nameSpan.addEventListener('click', clickArrow, false);
		} else {
			var input = document.createElement('input');
			input.type = 'checkbox';
			input.checked = false;
			itemDiv.insertBefore(input, nameSpan);

			item.input = input;
			item.layer = makeLayer(item);

			addTileOverlayClickHandler(this, item);
		}
	}
};
LayerControl.prototype.setTileOverlays = function(overlays, rootLCD)
{
	for (var pathStr of overlays)
	{
		var item = getItem(pathStr.split('_'), rootLCD);
		if (item && item.input && !item.input.checked)
			item.input.click();
	}
};
