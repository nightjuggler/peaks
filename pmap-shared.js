/* exported popupHTML, setPopupGlobals */
'use strict';

var defaultPeakList;
var topoMaps;

const verticalDatums = [' (NGVD 29)', ' (MSL)', ''];
const topoSeries = ['7.5', '7.5x15', '15', '30', '60'];
const topoScale = ['24,000', '25,000', '62,500', '125,000', '250,000'];

function setPopupGlobals(geojson)
{
	defaultPeakList = geojson.id;
	topoMaps = geojson.topomaps;
}
function fillTopo(f, topoID)
{
	const [seriesID, vdatumID, name, year, linkSuffix] = topoMaps[topoID];

	f[1] = 'https://ngmdb.usgs.gov/ht-bin/tv_browse.pl?id=' + linkSuffix;

	f[5] += verticalDatums[vdatumID] + ' USGS ' + topoSeries[seriesID] + '\' Quad (1:' + topoScale[seriesID] +
		') &quot;' + name + '&quot; (' + year + ')';
}
function fillElevation(f, elevFeet, elevOrig, range, unitAbbr)
{
	if (range === 0) {
		f[3] = elevFeet.toLocaleString();
		f[5] = elevOrig.toString() + unitAbbr;
	} else {
		f[3] = elevFeet.toLocaleString() + '+';
		f[5] = elevOrig.toString() + '-' + (elevOrig + range - 1).toString() + unitAbbr;
	}
}
function elevationHTML(elevations)
{
	if (typeof elevations === 'string')
		return elevations;

	const a = [];
	const f = ['<span><a href="', '', '">', '', '</a><div class="tooltip">', '', '</div></span>'];

	for (var e of elevations)
	{
		if (typeof e === 'string') { a.push(e); continue; }

		const elevType = e[0];

		if (elevType === 0)
		{
			fillElevation(f, e[1], e[1], e[2], '\'');
			fillTopo(f, e[3]);
		}
		else if (elevType === 1)
		{
			fillElevation(f, Math.round(e[1] / 0.3048), e[1], e[2], 'm');
			fillTopo(f, e[3]);
		}
		else if (elevType === 2)
		{
			const [, meters, stationID, stationName] = e;

			f[1] = 'https://www.ngs.noaa.gov/cgi-bin/ds_mark.prl?PidBox=' + stationID;
			f[3] = Math.round(meters * 39.37 / 12).toLocaleString();
			f[5] = meters.toString() + 'm (NAVD 88) NGS Data Sheet &quot;' + stationName +
				'&quot; (' + stationID + ')';
		}
		else continue;

		if (e.length > 4)
			f[5] += e[4]; // extraLines

		a.push(f.join(''));
	}

	return a.join('<br>');
}
function makePLL(listID, peakID)
{
	let url = listID.toLowerCase() + '.html';
	let txt = listID;

	const section = peakID.substring(0, peakID.indexOf('.'));
	const suffix = peakID.charAt(peakID.length - 1);

	if (suffix === 'd') {
		url += '?showDelisted';
		txt = 'ex-' + listID;
	}
	else if (suffix === 's') {
		url += '?showSuspended';
		txt = '(' + listID + ')';
	}

	return '<a href="' + url + '#' + listID + section + '">' + txt + '</a>';
}
function getPLL(peakID) // PLL = Peak List Link(s)
{
	if (typeof peakID === 'string')
		return makePLL(defaultPeakList, peakID);

	const links = [];

	for (var id of peakID)
	{
		var i = id.indexOf('.');
		links.push(makePLL(id.substring(0, i), id.substring(i + 1)));
	}

	return links.join(' ');
}
function weatherLink(lng, lat)
{
	return 'https://forecast.weather.gov/MapClick.php?lon=' + lng + '&lat=' + lat;
}
function makeLink(url, txt)
{
	return '<a href="' + url + '">' + txt + '</a>';
}
function makeDiv(className, content)
{
	return '<div class="' + className + '">' + content + '</div>';
}
function inlineDiv(prefix, content)
{
	return prefix + ' <div class="inline">' + content + '</div>';
}
function popupHTML(lng, lat, p)
{
	const z = p.z || 15;
	const b = p.noWX ? 'oo' : 't&o=r&n=0.2';

	const topoLink = 'https://caltopo.com/map.html#ll=' + lat + ',' + lng + '&z=' + z + '&b=' + b;

	let name = makeLink(topoLink, p.name);
	if (p.HP)
		name += ' HP';
	else if (p.emblem)
		name += ' **';
	else if (p.mtneer)
		name += ' *';
	if (p.name2)
		name += '<br>(' + p.name2 + ')';

	let html = makeDiv('peakName', name);

	html += makeDiv('pll', getPLL(p.id));
	html += makeDiv('peakDiv', inlineDiv('Elevation:', elevationHTML(p.elev)));
	html += makeDiv('peakDiv', inlineDiv('Prominence:', p.prom));
	if (p.YDS)
		html += makeDiv('peakDiv', 'Class ' + p.YDS);

	const links = [];
	if (p.SP) links.push(makeLink('https://www.summitpost.org/' + p.SP, 'SP'));
	if (p.W) links.push(makeLink('https://en.wikipedia.org/wiki/' + p.W, 'W'));
	if (p.BB) links.push(makeLink('https://www.snwburd.com/dayhikes/peak/' + p.BB, 'BB'));
	if (p.LoJ) links.push(makeLink('https://listsofjohn.com/peak/' + p.LoJ, 'LoJ'));
	if (p.Pb) links.push(makeLink('https://peakbagger.com/peak.aspx?pid=' + p.Pb, 'Pb'));
	if (!p.noWX) links.push(makeLink(weatherLink(lng, lat), 'WX'));
	if (links.length)
		html += makeDiv('peakDiv', links.join(', '));

	if (p.climbed)
		html += makeDiv('peakDiv', inlineDiv('Climbed', p.climbed));

	return makeDiv('popupDiv', html);
}
