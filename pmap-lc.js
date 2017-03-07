"use strict";

var BLM_CA_NLCS_Prefix = 'https://www.blm.gov/nlcs_web/sites/ca/st/en/prog/nlcs/';
var USFS_Prefix = 'https://www.fs.usda.gov/';
var USFS_NM_Prefix = 'https://www.fs.fed.us/visit/';
var Wikipedia_Prefix = 'https://en.wikipedia.org/wiki/';
var Wilderness_Prefix = 'http://www.wilderness.net/NWPS/wildView?WID=';

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
	a.appendChild(document.createTextNode('\u25B2'));
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
	a.appendChild(document.createTextNode('\u25BC'));
	a.addEventListener('click', bringToBack, false);
	return a;
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
function assignLayer(item, namePath, layer)
{
	var nextItem;
	var lastName = namePath.pop();

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
		var bounds = layer.getBounds();
		if (item.bounds)
			item.bounds.extend(bounds);
		else
			item.bounds = L.latLngBounds(bounds.getSouthWest(), bounds.getNorthEast());
	}
	if (!(nextItem = item.nameMap[lastName])) {
		console.log('assignLayer failed to get from "' + item.name + '" to "' + lastName + '"');
		return;
	}
	item = nextItem;
	if (item.nameMap) {
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
}
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
		popupDiv.appendChild(popupFitLink(map, layer));
		popupDiv.appendChild(lowerLink(layer));
		popupDiv.appendChild(raiseLink(layer));
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + parent + ')'));

		layer.bindPopup(popupDiv);
		assignLayer(lcItem, [parent, feature.properties.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
}
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
}
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
		popupDiv.appendChild(popupFitLink(map, layer));
		popupDiv.appendChild(lowerLink(layer));
		popupDiv.appendChild(raiseLink(layer));

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
		layer.bindPopup(popupDiv, {maxWidth: 600});
		assignLayer(lcItem, namePath, layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
}
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
		popupDiv.appendChild(popupFitLink(map, layer));
		popupDiv.appendChild(lowerLink(layer));
		popupDiv.appendChild(raiseLink(layer));

		layer.bindPopup(popupDiv, {maxWidth: 600});
		assignLayer(lcItem, namePath, layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
}
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
		popupDiv.appendChild(popupFitLink(map, layer));
		popupDiv.appendChild(lowerLink(layer));
		popupDiv.appendChild(raiseLink(layer));
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('BLM Recommendation: ' + p.rcmnd));

		layer.bindPopup(popupDiv, {maxWidth: 600});
		assignLayer(lcItem, [p.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#000000'}});
}
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
		popupDiv.appendChild(popupFitLink(map, layer));
		popupDiv.appendChild(lowerLink(layer));
		popupDiv.appendChild(raiseLink(layer));

		layer.bindPopup(popupDiv, {maxWidth: 600});
		assignLayer(lcItem, [p.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#A52A2A'/* Brown */}});
}
function makeLink(url, txt)
{
	return '<a href="' + url + '">' + txt + '</a>';
}
function popupHtml(ll, p, htmlFilename)
{
	var g4URL = 'https://mappingsupport.com/p/gmap4.php?ll=' + ll.lat + ',' + ll.lng + '&' + p.G4;

	var suffix = p.HP ? ' HP' : p.emblem ? ' **' : p.mtneer ? ' *' : '';

	var otherName = p.name2 ? '<br>(' + p.name2 + ')' : '';

	var name = makeLink(htmlFilename + p.id.split('.')[0], p.id) + ' '
		+ makeLink(g4URL, p.name) + suffix + otherName;

	var links = [];
	if (p.SP) links.push(makeLink('http://www.summitpost.org/' + p.SP, 'SP'));
	if (p.W) links.push(makeLink('https://en.wikipedia.org/wiki/' + p.W, 'W'));
	if (p.BB) links.push(makeLink('http://www.snwburd.com/dayhikes/peak/' + p.BB, 'BB'));
	if (p.LoJ) links.push(makeLink('http://listsofjohn.com/peak/' + p.LoJ, 'LoJ'));
	if (p.Pb) links.push(makeLink('http://peakbagger.com/peak.aspx?pid=' + p.Pb, 'Pb'));
	if (!p.noWX) links.push(makeLink('http://forecast.weather.gov/MapClick.php?lon='
		+ ll.lng + '&lat=' + ll.lat, 'WX'));

	links = links.length === 0 ? '' : '<br>' + links.join(', ');

	var climbed = p.climbed ? '<br>Climbed ' + p.climbed : '';

	return '<div class="popupDiv"><b>' + name + '</b>'
		+ '<br>Elevation: <div class="elevDiv">' + p.elev + '</div>'
		+ '<br>Prominence: ' + p.prom
		+ '<br>Class ' + p.YDS
		+ links + climbed + '</div>';
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
}
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
function LayerControl(map, currentBaseLayer)
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
	this.currentBaseLayer = currentBaseLayer;
}
LayerControl.prototype.addBaseLayer = function(name, layer)
{
	var ctrl = this;

	var input = document.createElement('input');
	input.type = 'radio';
	input.name = 'baselayer';
	input.checked = (layer === ctrl.currentBaseLayer);

	function changeBaseLayer()
	{
		if (layer === ctrl.currentBaseLayer) return;
		ctrl.currentBaseLayer.remove();
		ctrl.currentBaseLayer = layer.addTo(ctrl.map);
		input.checked = true;
	}

	var nameSpan = document.createElement('span');
	nameSpan.appendChild(document.createTextNode(name));
	nameSpan.addEventListener('click', changeBaseLayer);
	input.addEventListener('click', changeBaseLayer);

	var div = document.createElement('div');
	div.className = 'lcItem';
	div.appendChild(input);
	div.appendChild(nameSpan);

	ctrl.div.appendChild(div);
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
	}
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
	Mobile browsers won't fire a click event "if the contents of the page changes" on the
	preceding mouseenter/mouseover event. Since the mouseenter handler (showZoomToFit)
	would normally append the zoom-to-fit link to the div for the clicked menu item (thus
	preventing the click event), instead intercept the initial touchstart event and add
	the zoom-to-fit link in that handler so that the subsequent mouseenter handler won't
	change the page (since the link was already added), thus allowing the click to fire.
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
	} else {
		item.layer.addTo(map);
		if (extendBounds)
			extendBounds(item.layer.getBounds());
	}
}
function removeLayersFromMap(item)
{
	if (item.order) {
		for (var id of item.order)
		{
			var child = item.items[id];
			if (child.checkbox.checked)
				removeLayersFromMap(child);
		}
	} else if (item.featureGroup) {
		item.featureGroup.remove();
	} else {
		item.layer.remove();
	}
}
function addCheckboxClickHandler(item, map)
{
	var checkbox = item.checkbox;
	var fileParent = item.fileParent;

	function addWrapper(geojson)
	{
		addNameMap(fileParent);
		fileParent.featureGroup = item.add(geojson, map, fileParent);
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
LayerControl.prototype.fillMenu = function(parentDiv, parentItem, path)
{
	for (var id of parentItem.order)
	{
		var item = parentItem.items[id];
		item.parent = parentItem;

		var itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';

		var nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		var parts = item.name.split('|');
		nameSpan.appendChild(document.createTextNode(parts[0]));
		for (var i = 1; i < parts.length; ++i)
		{
			nameSpan.appendChild(document.createElement('br'));
			nameSpan.appendChild(document.createTextNode(parts[i]));
		}
		item.name = parts.join(' ');
		itemDiv.appendChild(nameSpan);

		if (item.add)
		{
			var fnName = 'add' + item.add;
			var fn = addFunctions[fnName];
			if (typeof fn !== 'function') {
				console.log(getPathStr(path, id) + ': "' + fnName + '" is not a function!');
				continue;
			}
			item.add = fn;
		}
		else if (parentItem.add)
			item.add = parentItem.add;

		if (item.size)
		{
			if (item.fileParent) {
				console.log(getPathStr(path, id) + ': Cannot have a file within a file!');
				continue;
			}
			if (!item.add)
				item.add = addFunctions.default;

			var sizeSpan = document.createElement('span');
			sizeSpan.appendChild(document.createTextNode('(' + item.size + ')'));
			itemDiv.appendChild(sizeSpan);

			item.fileName = 'json/' + getPathStr(path, id) + '.json';
			item.fileParent = item;
		}
		else if (parentItem.fileParent)
			item.fileParent = parentItem.fileParent;

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
			this.fillMenu(childDiv, item, path);
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
}
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
function addOverlays(overlays, rootLCD, mapBounds)
{
	for (var pathStr of overlays)
	{
		var item = getItem(pathStr.split('_'), rootLCD);
		if (!item)
			continue;
		if (!item.checkbox) {
			continue;
		}
		if (!item.checkbox.checked) {
			mapBounds.addSetter(item);
			item.checkbox.click();
		}
	}
}
