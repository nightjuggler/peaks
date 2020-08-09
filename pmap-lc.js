/* globals console, document, Image, window, L */
/* globals enableTooltips, loadJSON, popupHTML, setPopupGlobals, weatherLink */
/* exported pmapLayerControl */

var pmapLayerControl = (function() {
'use strict';

const BLM_CA_NLCS_Prefix = 'https://www.blm.gov/nlcs_web/sites/ca/st/en/prog/nlcs/';
const USFS_Prefix = 'https://www.fs.usda.gov/';
const USFS_NM_Prefix = 'https://www.fs.fed.us/visit/';
const Wikipedia_Prefix = 'https://en.wikipedia.org/wiki/';
const Wilderness_Prefix = 'https://wilderness.net/visit-wilderness/?ID=';

let globalMap = null;
let currentBaseLayer = null;
let lcItemFitLink = null;

const lcItemHoverColor = 'rgb(255, 255, 224)';
const menuDisplayedIcon = ' \u25BC';
/*
	\uFE0E is a variation selector to indicate that the preceding character - the
	black right-pointing triangle (\u25B6) - should be rendered text-style rather
	than emoji-style. If the variation selector isn't specified, desktop browsers
	seem to default to text-style while mobile browsers seem to default to emoji-
	style. [http://www.unicode.org/Public/UNIDATA/StandardizedVariants.txt]
*/
const menuCollapsedIcon = ' \u25B6\uFE0E';
const addFunctions = {};

function textLink(url, text)
{
	const link = document.createElement('a');
	link.href = url;
	link.appendChild(document.createTextNode(text));
	return link;
}
function wikipediaLink(w)
{
	return textLink(Wikipedia_Prefix + w, 'W');
}
function fitLink(fitBounds, className)
{
	const img = new Image();
	img.alt = 'Zoom To Fit';
	img.src = 'ztf.svg';
	img.className = className;
	img.addEventListener('click', fitBounds, false);
	return img;
}
function popupFitLink(layer)
{
	function fitBounds(event)
	{
		event.preventDefault();
		globalMap.fitBounds(layer.closePopup().getBounds());
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
	const a = document.createElement('a');
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
	const a = document.createElement('a');
	a.href = '#';
	a.className = 'bringToBack';
	a.appendChild(document.createTextNode('\u2B07\uFE0F'));
	a.addEventListener('click', bringToBack, false);
	return a;
}
function dynamicWeatherLink(layer)
{
	const a = document.createElement('a');

	function setWxLink()
	{
		const ll = layer.getPopup().getLatLng();
		a.href = weatherLink(ll.lng.toFixed(6), ll.lat.toFixed(6));
	}

	a.href = '#';
	a.className = 'wxLink';
	a.appendChild(document.createTextNode('\u26C5'));
	a.addEventListener('click', setWxLink, false);
	return a;
}
function bindPopup(popupDiv, layer)
{
	popupDiv.appendChild(document.createElement('br'));
	popupDiv.appendChild(popupFitLink(layer));
	popupDiv.appendChild(dynamicWeatherLink(layer));
	popupDiv.appendChild(lowerLink(layer));
	popupDiv.appendChild(raiseLink(layer));
	layer.bindPopup(popupDiv, {maxWidth: 600});
}
function addNameMap(item)
{
	if (item.order)
	{
		item.nameMap = {};
		for (const id of item.order)
		{
			const child = item.items[id];
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
		for (const id of item.order)
			delNameMap(item.items[id]);
	}
}
function extendBounds(item, layer)
{
	const bounds = layer.getBounds();
	if (item.bounds)
		item.bounds.extend(bounds);
	else
		item.bounds = L.latLngBounds(bounds.getSouthWest(), bounds.getNorthEast());
}
function assignLayer(item, namePath, layer, featureProperties)
{
	let nextItem;
	const lastName = namePath.pop();

	const flags = featureProperties && featureProperties.flags || 0;
	const setBounds = (flags & 1) !== 0;
	const skipBounds = (flags & 2) !== 0;

	if (!item.nameMap) {
		console.log('assignLayer failed: "' + item.name + '" doesn\'t have a name map!');
		return;
	}
	for (const name of namePath)
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
addFunctions.default = function(geojson)
{
	return L.geoJSON(geojson, {style: {color: '#FF4500'/* OrangeRed */}});
};
addFunctions.add_BLM_CA_Districts = function(geojson, lcItem)
{
	const style = {
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
		const name = feature.properties.name.slice(0, -13); // strip trailing " Field Office"
		const parent = feature.properties.parent;

		const bold = document.createElement('b');
		bold.appendChild(document.createTextNode('BLM ' + name));

		const popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + parent + ')'));

		bindPopup(popupDiv, layer);
		assignLayer(lcItem, [parent, feature.properties.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
};
function officeIcon()
{
	return L.divIcon({
		className: 'officeIcon',
		iconSize: [26, 20],
		popupAnchor: [0, -4],
		html: '<svg xmlns="http://www.w3.org/2000/svg" width="26" height="20" viewBox="0 0 26 20">' +
			'<path fill="cyan" stroke="blue" stroke-width="2" ' +
			'd="M 13,1 L 1,10 3,10 3,19 11,19 11,10 15,10 15,19 23,19 23,10 25,10 Z" /></svg>'
	});
}
function zoomTo(ll)
{
	return function() {
		globalMap.setView(ll, Math.min(globalMap.getMaxZoom(), 18));
	};
}
addFunctions.add_BLM_Offices = function(geojson)
{
	function addPopup(feature, latlng)
	{
		const name = feature.properties.name;
		const html = '<div class="popupDiv blmPopup"><b>BLM ' + name + '</b></div>';
		return L.marker(latlng, {icon: officeIcon()})
			.bindPopup(html, {maxWidth: 600})
			.on('dblclick', zoomTo(latlng));
	}
	return L.geoJSON(geojson, {pointToLayer: addPopup});
};
addFunctions.add_BLM_Lands = function(geojson, lcItem)
{
	const USFS_Style = {color: '#008000'}; // Green
	const BLM_Style = {color: '#00008B'}; // DarkBlue

	function getStyle(feature)
	{
		if (feature.properties.agency === 'USFS')
			return USFS_Style;
		return BLM_Style;
	}
	function addPopup(feature, layer)
	{
		const p = feature.properties;
		const name = p.name;
		const agency = p.agency;

		const link = document.createElement('a');
		link.href = BLM_CA_NLCS_Prefix + p.BLM;
		if (name.length < 23) {
			link.appendChild(document.createTextNode(name + ' ' + p.D));
		} else {
			link.appendChild(document.createTextNode(name));
			link.appendChild(document.createElement('br'));
			link.appendChild(document.createTextNode(p.D));
		}

		const bold = document.createElement('b');
		bold.appendChild(link);
		bold.appendChild(document.createTextNode(' ['));
		bold.appendChild(wikipediaLink(p.W));
		bold.appendChild(document.createTextNode(']'));

		const popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);

		const namePath = [name + ' ' + p.D];
		if (agency) {
			popupDiv.appendChild(document.createElement('br'));
			if (agency === 'USFS') {
				namePath.push('Forest Service Lands');
				if (p.FS) {
					popupDiv.appendChild(document.createTextNode(
						'This part is managed by the '));
					popupDiv.appendChild(textLink(USFS_NM_Prefix + p.FS, 'Forest Service'));
					popupDiv.appendChild(document.createTextNode(':'));
				} else
					popupDiv.appendChild(document.createTextNode(
						'This part is managed by the Forest Service:'));

				popupDiv.appendChild(document.createElement('br'));
				popupDiv.appendChild(textLink(USFS_Prefix + p.NF, p.NFW.replace(/_/g, ' ')));
				popupDiv.appendChild(document.createTextNode(' ['));
				popupDiv.appendChild(wikipediaLink(p.NFW));
				popupDiv.appendChild(document.createTextNode(']'));
			} else {
				namePath.push(agency + ' Lands');
				popupDiv.appendChild(document.createTextNode(
					'This part is managed by the ' + agency + '.'));
			}
		}

		bindPopup(popupDiv, layer);
		assignLayer(lcItem, namePath, layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
};
addFunctions.add_BLM_Wilderness = function(geojson, lcItem)
{
	const style = {
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
		const p = feature.properties;
		const name = p.name + ' Wilderness';
		const agency = p.agency;
		const date = p.D;
		const namePath = [name];
		if (p.m)
			namePath.push(date + ' ' + agency);

		const bold = document.createElement('b');
		bold.appendChild(textLink(Wilderness_Prefix + p.id, name));

		const popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createTextNode(' (' + agency + ')'));
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('Designated ' + date));

		bindPopup(popupDiv, layer);
		assignLayer(lcItem, namePath, layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: getStyle});
};
addFunctions.add_BLM_WSA = function(geojson, lcItem)
{
	function addPopup(feature, layer)
	{
		const p = feature.properties;
		const bold = document.createElement('b');
		bold.appendChild(document.createTextNode(p.name + ' Wilderness Study Area'));

		const popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + p.code + ')'));
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('BLM Recommendation: ' + p.rcmnd));

		bindPopup(popupDiv, layer);
		assignLayer(lcItem, [p.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#000000'}});
};
addFunctions.add_BLM_WSA_Released = function(geojson, lcItem)
{
	function addPopup(feature, layer)
	{
		const p = feature.properties;
		const bold = document.createElement('b');
		bold.appendChild(document.createTextNode(p.name + ' WSA (Released)'));

		const popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + p.code + ')'));

		bindPopup(popupDiv, layer);
		assignLayer(lcItem, [p.name], layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#A52A2A'/* Brown */}});
};
function appendName(name, node)
{
	const parts = name.split('|');
	let lineBreak = node.lastChild !== null;
	for (const part of parts)
	{
		if (lineBreak)
			node.appendChild(document.createElement('br'));
		else
			lineBreak = true;
		node.appendChild(document.createTextNode(part));
	}
	return parts.join(' ');
}
addFunctions.add_NPS = function(geojson, lcItem)
{
	function addPopup(feature, layer)
	{
		const p = feature.properties;

		const link = document.createElement('a');
		link.href = 'https://www.nps.gov/' + p.code + '/index.htm';
		p.name = appendName(p.name, link);

		const bold = document.createElement('b');
		bold.appendChild(link);
		bold.appendChild(document.createTextNode(' ['));
		bold.appendChild(wikipediaLink(p.W || p.name.replace(/ /g, '_')));
		bold.appendChild(document.createTextNode(']'));

		const popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);

		const namePath = [p.name];
		if (p.name2) {
			p.name2 = appendName(p.name2, popupDiv);
			namePath.push(p.name2);
			if (p.W2) {
				popupDiv.appendChild(document.createTextNode(' ['));
				popupDiv.appendChild(wikipediaLink(p.W2));
				popupDiv.appendChild(document.createTextNode(']'));
			}
		}

		bindPopup(popupDiv, layer);
		assignLayer(lcItem, namePath, layer, p);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#FFFF00'/* Yellow */}});
};
function peakIcon(p)
{
	const fill = p.emblem ? 'magenta' : p.mtneer ? 'cyan' : 'white';
	const stroke = p.climbed ? 'green' : 'red';

	return L.divIcon({
		className: 'peakIcon',
		iconSize: [20, 26],
		popupAnchor: [0, -8],
		html: '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="26" viewBox="0 0 20 26">' +
			'<path fill="' + fill + '" stroke="' + stroke + '" stroke-width="3" ' +
			'd="M 10,2 L 1,19 19,19 Z" /></svg>'
	});
}
addFunctions.addPeakOverlay = function(geojson)
{
	setPopupGlobals(geojson);

	function addPeak(feature, latlng)
	{
		const p = feature.properties;
		return L.marker(latlng, {icon: peakIcon(p)})
			.bindPopup(popupHTML(latlng.lng, latlng.lat, p))
			.on('popupopen', enableTooltips)
			.on('dblclick', zoomTo(latlng));
	}

	return L.geoJSON(geojson, {pointToLayer: addPeak});
};
addFunctions.add_UC_Reserve = function(geojson)
{
	function addPopup(feature, layer)
	{
		const p = feature.properties;
		const bold = document.createElement('b');
		bold.appendChild(document.createTextNode(p.name));
		if (p.name2) {
			bold.appendChild(document.createElement('br'));
			bold.appendChild(document.createTextNode(p.name2));
		}
		const popupDiv = document.createElement('div');
		popupDiv.className = 'popupDiv blmPopup';
		popupDiv.appendChild(bold);
		popupDiv.appendChild(document.createElement('br'));
		popupDiv.appendChild(document.createTextNode('(' + p.campus + ')'));

		bindPopup(popupDiv, layer);
	}

	return L.geoJSON(geojson, {onEachFeature: addPopup, style: {color: '#FF00FF'/* Magenta */}});
};
function getTop(div)
{
	let top = div.offsetTop;

	while (div.offsetParent !== document.body)
	{
		div = div.offsetParent;
		top += div.offsetTop;
	}

	return top;
}
function toggleLayerMenu(event)
{
	const arrow = event.currentTarget;
	const menu = arrow.parentNode.nextSibling;

	const lcDiv = document.getElementById('layerControl');
	const scDiv = document.getElementById('scaleControl');
	const lcTop = getTop(lcDiv);
	const scTop = getTop(scDiv);
	const maxHeight = Math.max(scTop - lcTop - 20, 100);
	const scrollTop = lcDiv.scrollTop;

	lcDiv.style.height = 'auto';

	if (menu.style.display === 'block') {
		menu.style.display = 'none';
		arrow.firstChild.nodeValue = menuCollapsedIcon;
	} else {
		menu.style.display = 'block';
		arrow.firstChild.nodeValue = menuDisplayedIcon;
	}

	if (lcDiv.offsetHeight > maxHeight) {
		lcDiv.style.height = maxHeight + 'px';
		lcDiv.scrollTop = scrollTop;
	}
}
function clickArrow(event)
{
	event.currentTarget.parentNode.firstChild.click();
}
function addArrow(nameSpan)
{
	const arrow = document.createElement('span');
	arrow.className = 'lcArrow';
	arrow.appendChild(document.createTextNode(menuCollapsedIcon));
	arrow.addEventListener('click', toggleLayerMenu);

	const parent = nameSpan.parentNode;
	parent.insertBefore(arrow, parent.firstChild);
	nameSpan.addEventListener('click', clickArrow);
}
function menuHeader(parent, text)
{
	const span = document.createElement('span');
	span.className = 'lcName';
	span.appendChild(document.createTextNode(text));

	const header = parent.appendChild(document.createElement('div'));
	header.className = 'lcHeader lcItem';
	header.appendChild(span);
	addArrow(span);

	const section = parent.appendChild(document.createElement('div'));
	section.className = 'lcSection';
	return section;
}
function lcItemFitBounds(event)
{
	event.preventDefault();

	const item = event.currentTarget.parentNode.lcItem;
	if (item.bounds)
		globalMap.fitBounds(item.bounds);
	else if (item.layer)
		globalMap.fitBounds(item.layer.closePopup().getBounds());
	else if (item.featureGroup)
		globalMap.fitBounds(item.featureGroup.getBounds());
}
function showZoomToFit(event)
{
	const div = event.currentTarget;
	if (lcItemFitLink.parentNode !== div)
	{
		div.style.paddingRight = '8px';
		div.appendChild(lcItemFitLink);
	}
}
function hideZoomToFit(event)
{
	const div = event.currentTarget;
	if (lcItemFitLink.parentNode === div)
	{
		div.style.paddingRight = '23px';
		div.removeChild(lcItemFitLink);
	}
}
function addZoomToFitHandlers(item)
{
	const itemDiv = item.div;

	const bgColor = window.getComputedStyle(itemDiv).backgroundColor;
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
		for (const id of item.order)
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
	for (const id of topItem.order)
	{
		const item = topItem.items[id];
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
function addLayersToMap(item, extendBounds)
{
	if (item.layer) {
		item.layer.addTo(globalMap);
		if (extendBounds)
			extendBounds(item.layer.getBounds());
	}
	if (item.order) {
		for (const id of item.order)
		{
			const child = item.items[id];
			if (child.checkbox.checked)
				addLayersToMap(child, extendBounds);
		}
	} else if (item.featureGroup) {
		item.featureGroup.addTo(globalMap);
		if (extendBounds)
			extendBounds(item.featureGroup.getBounds());
	}
}
function removeLayersFromMap(item)
{
	if (item.layer)
		item.layer.remove();
	if (item.order) {
		for (const id of item.order)
		{
			const child = item.items[id];
			if (child.checkbox.checked)
				removeLayersFromMap(child);
		}
	} else if (item.featureGroup)
		item.featureGroup.remove();
}
function addCheckboxClickHandler(item)
{
	const checkbox = item.checkbox;
	const fileParent = item.fileParent;

	function addWrapper(geojson)
	{
		addNameMap(fileParent);
		fileParent.featureGroup = fileParent.add(geojson, fileParent);
		delNameMap(fileParent);

		const sizeSpan = fileParent.div.lastChild;
		sizeSpan.parentNode.removeChild(sizeSpan);

		if (!lcItemFitLink)
			lcItemFitLink = fitLink(lcItemFitBounds, 'lcZtf');

		addZoomToFitHandlers(fileParent);
		if (fileParent.checkbox.checked)
			if (item.mapBounds) {
				addLayersToMap(fileParent, item.mapBounds.extend);
				item.mapBounds.delSetter(item);
			} else
				addLayersToMap(fileParent);
	}
	function clickHandler()
	{
		if (fileParent.featureGroup)
		{
			if (!isCheckedToFileParent(item))
				return;
			if (checkbox.checked)
				addLayersToMap(item);
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

			const progressBar = document.createElement('progress');
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
	const pathStr = path.join('/');
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
		const funcName = 'add' + item.add;
		const addFunc = addFunctions[funcName];

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
function addOverlays(parentItem, parentDiv, path)
{
	for (const id of parentItem.order)
	{
		const item = parentItem.items[id];
		item.parent = parentItem;

		if (!validateItem(item, path, id)) continue;

		const nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		item.name = appendName(item.name, nameSpan);

		const itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';
		itemDiv.appendChild(nameSpan);

		if (item.size)
		{
			const sizeSpan = document.createElement('span');
			sizeSpan.appendChild(document.createTextNode('(' + item.size + ')'));
			itemDiv.appendChild(sizeSpan);
		}
		if (item.fileParent)
		{
			const checkbox = document.createElement('input');
			checkbox.type = 'checkbox';
			checkbox.checked = false;
			itemDiv.insertBefore(checkbox, nameSpan);

			if (!item.items)
				itemDiv.style.paddingLeft = '18px';

			itemDiv.lcItem = item;
			item.div = itemDiv;
			item.checkbox = checkbox;

			addCheckboxClickHandler(item);
		}

		parentDiv.appendChild(itemDiv);

		if (item.items)
		{
			const childDiv = document.createElement('div');
			childDiv.className = 'lcMenu';

			path.push(id);
			addOverlays(item, childDiv, path);
			path.pop();

			parentDiv.appendChild(childDiv);
			addArrow(nameSpan);
		}
	}
}
function getItem(path, item)
{
	for (const id of path)
	{
		if (!item.items)
			return null;

		let nextItem = item.items[id];
		if (!nextItem)
			return null;

		if (typeof nextItem === 'string') {
			const subPath = nextItem.split('/');
			subPath.push(id);
			nextItem = getItem(subPath, item);
			if (!nextItem)
				return null;
		}
		item = nextItem;
	}
	return item;
}
function selectOverlays(rootLCD, overlays, mapBounds)
{
	for (const pathStr of overlays)
	{
		const item = getItem(pathStr.split('_'), rootLCD);
		if (item && item.checkbox && !item.checkbox.checked) {
			mapBounds.addSetter(item);
			item.checkbox.click();
		}
	}
}
function makeChangeBaseLayer(item)
{
	return function() {
		if (currentBaseLayer === item.layer) return;
		if (currentBaseLayer)
			currentBaseLayer.remove();
		currentBaseLayer = item.layer.addTo(globalMap);
		globalMap.setMaxZoom(item.maxZoom || 23);
		item.input.checked = true;
	};
}
function addBaseLayers(parentItem, parentDiv, path, parentMakeLayer)
{
	for (const id of parentItem.order)
	{
		const item = parentItem.items[id];
		if (!item) continue;

		const nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		appendName(item.name, nameSpan);

		const itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';
		itemDiv.appendChild(nameSpan);

		parentDiv.appendChild(itemDiv);

		const makeLayer = item.makeLayer || parentMakeLayer;

		if (item.items) {
			const childDiv = document.createElement('div');
			childDiv.className = 'lcMenu';

			path.push(id);
			addBaseLayers(item, childDiv, path, makeLayer);
			path.pop();

			parentDiv.appendChild(childDiv);
			addArrow(nameSpan);
		} else {
			const input = document.createElement('input');
			input.type = 'radio';
			input.name = 'baselayer';
			input.checked = false;
			itemDiv.insertBefore(input, nameSpan);

			item.input = input;
			item.layer = makeLayer(item);

			if (item.layer) {
				const changeBaseLayer = makeChangeBaseLayer(item);
				nameSpan.addEventListener('click', changeBaseLayer);
				input.addEventListener('click', changeBaseLayer);
			} else {
				input.disabled = true;
				nameSpan.style.color = 'rgb(128,128,128)';
			}
		}
	}
}
function selectBaseLayer(rootLCD, path, defaultPath)
{
	let item = getItem(path.split('_'), rootLCD);
	if (!item || !item.layer) {
		item = getItem(defaultPath.split('_'), rootLCD);
		if (!item || !item.layer) return;
	}
	item.input.click();
}
function makeVersionSpec(parent, version)
{
	const spec = {};
	for (const k of ['attribution', 'dynamicLayers', 'exportLayers', 'opacity', 'url'])
	{
		if (version.hasOwnProperty(k))
			spec[k] = version[k];
		else if (parent.hasOwnProperty(k))
			spec[k] = parent[k];
	}
	return spec;
}
function makeChangeVersion(parent, version)
{
	return function() {
		if (parent.layer === version.layer) return;
		if (parent.input.checked) {
			parent.layer.remove();
			version.layer.addTo(globalMap);
		}
		parent.layer = version.layer;
		version.input.checked = true;
	};
}
function makeToggleTileOverlay(item)
{
	const input = item.input;

	return function(event)
	{
		if (event.currentTarget !== input)
			input.checked = !input.checked;
		if (input.checked)
			item.layer.addTo(globalMap);
		else
			item.layer.remove();
	};
}
function addTileOverlays(parentItem, parentDiv, path, parentMakeLayer, versionParent)
{
	for (const id of parentItem.order)
	{
		const item = parentItem.items[id];
		if (!item) continue;

		const nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		appendName(item.name, nameSpan);

		const itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';
		itemDiv.appendChild(nameSpan);

		const makeLayer = item.makeLayer || parentMakeLayer;

		if (versionParent) {
			if (!item.items) {
				const input = document.createElement('input');
				input.type = 'radio';
				input.name = versionParent.versionID;
				item.input = input;

				if (item.layer) {
					input.checked = true;
				} else {
					input.checked = false;
					item.layer = makeLayer(makeVersionSpec(versionParent, item));
				}

				const changeVersion = makeChangeVersion(versionParent, item);
				input.addEventListener('click', changeVersion);
				nameSpan.addEventListener('click', changeVersion);

				itemDiv.insertBefore(input, nameSpan);
				itemDiv.style.paddingLeft = '18px';
			}
		} else if (item.url) {
			const input = document.createElement('input');
			input.type = 'checkbox';
			input.checked = false;
			item.input = input;
			item.layer = makeLayer(item);

			const toggleOverlay = makeToggleTileOverlay(item);
			input.addEventListener('click', toggleOverlay);

			itemDiv.insertBefore(input, nameSpan);
			if (!item.items) {
				itemDiv.style.paddingLeft = '18px';
				nameSpan.addEventListener('click', toggleOverlay);
			}
		}

		parentDiv.appendChild(itemDiv);

		if (item.items) {
			const childDiv = document.createElement('div');
			childDiv.className = 'lcMenu';

			path.push(id);
			if (versionParent)
				addTileOverlays(item, childDiv, path, makeLayer, versionParent);
			else if (item.url) {
				item.versionID = 'V_' + path.join('_');
				item.items[''] = {name: item.versionName || 'Default Rendering', layer: item.layer};
				item.order.unshift('');
				addTileOverlays(item, childDiv, path, makeLayer, item);
			} else
				addTileOverlays(item, childDiv, path, makeLayer);
			path.pop();

			parentDiv.appendChild(childDiv);
			addArrow(nameSpan);
		}
	}
}
function selectTileOverlays(rootLCD, overlays)
{
	for (const pathStr of overlays)
	{
		const item = getItem(pathStr.split('_'), rootLCD);
		if (item && item.input && !item.input.checked)
			item.input.click();
	}
}
function addPointQueries(parentItem, parentDiv)
{
	let hasInput = false;

	for (const id of parentItem.order)
	{
		const item = parentItem.items[id];
		if (!item || !item.toggleQuery && !(item.items && !item.url)) continue;

		const nameSpan = document.createElement('span');
		nameSpan.className = 'lcName';
		appendName(item.name, nameSpan);

		const itemDiv = document.createElement('div');
		itemDiv.className = 'lcItem';
		itemDiv.appendChild(nameSpan);

		if (item.toggleQuery) {
			const input = document.createElement('input');
			input.type = 'checkbox';
			input.checked = false;
			item.queryToggle = input;

			itemDiv.insertBefore(input, nameSpan);
			itemDiv.style.paddingLeft = '18px';
			parentDiv.appendChild(itemDiv);

			nameSpan.addEventListener('click', item.toggleQuery);
			input.addEventListener('click', item.toggleQuery);
			hasInput = true;
		} else {
			const childDiv = document.createElement('div');
			childDiv.className = 'lcMenu';

			if (!addPointQueries(item, childDiv)) continue;

			parentDiv.appendChild(itemDiv);
			parentDiv.appendChild(childDiv);
			addArrow(nameSpan);
		}
	}

	return hasInput;
}
function selectGeometryQueries(rootLCD, geometryQueries)
{
	for (const [id, color] of geometryQueries)
	{
		const item = getItem(id.split('_'), rootLCD);
		if (item && item.popup) {
			item.popup.runGeometryQuery = true;
			if (color)
				item.popup.color = '#' + color.toLowerCase();
		}
	}
}
function selectPointQueries(rootLCD, pointQueries)
{
	for (const id of pointQueries)
	{
		const item = getItem(id.split('_'), rootLCD);
		if (item && item.queryToggle && !item.queryToggle.checked)
			item.toggleQuery();
	}
}
return function(map)
{
	globalMap = map;
	const div = document.getElementById('layerControl');
	const icon = document.getElementById('layerControlIcon');

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
		let node = event.target;
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

	return {
		addBaseLayers: function(rootLCD, path, defaultPath)
		{
			addBaseLayers(rootLCD, menuHeader(div, 'Base Layers'), [], rootLCD.makeLayer);
			selectBaseLayer(rootLCD, path, defaultPath);
		},
		addTileOverlays: function(rootLCD, overlays)
		{
			addTileOverlays(rootLCD, menuHeader(div, 'Tile Overlays'), [], rootLCD.makeLayer);
			selectTileOverlays(rootLCD, overlays);
		},
		addPointQueries: function(rootLCD, pointQueries, geometryQueries)
		{
			addPointQueries(rootLCD, menuHeader(div, 'Point Queries'));
			selectGeometryQueries(rootLCD, geometryQueries);
			selectPointQueries(rootLCD, pointQueries);
		},
		addOverlays: function(rootLCD, overlays, mapBounds)
		{
			addOverlays(rootLCD, menuHeader(div, 'GeoJSON Overlays'), []);
			selectOverlays(rootLCD, overlays, mapBounds);
		},
	};
};
})();
