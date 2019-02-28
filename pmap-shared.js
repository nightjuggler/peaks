/* exported popupHTML, topoMaps */
'use strict';

var topoMaps;
var verticalDatums = [' (NGVD 29)', ' (MSL)', ''];
var topoSeries = ['7.5', '7.5x15', '15', '30', '60'];
var topoScale = ['24,000', '25,000', '62,500', '125,000', '250,000'];

function fillTopo(f, topoID)
{
	let [seriesID, vdatumID, name, year, linkSuffix] = topoMaps[topoID];

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

	var a = [];
	var f = ['<span><a href="', '', '">', '', '</a><div class="tooltip">', '', '</div></span>'];

	for (var e of elevations)
	{
		if (typeof e === 'string') { a.push(e); continue; }

		var elevType = e[0];

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
			let meters = e[1];
			let stationID = e[2];
			let stationName = e[3];

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
function weatherLink(lng, lat)
{
	return 'https://forecast.weather.gov/MapClick.php?lon=' + lng + '&lat=' + lat;
}
function makeLink(url, txt)
{
	return '<a href="' + url + '">' + txt + '</a>';
}
function popupHTML(lng, lat, p, htmlFilename)
{
	var z = p.z || 15;
	var b = p.noWX ? 'oo' : 't&o=r&n=0.2';

	var topoLink = 'https://caltopo.com/map.html#ll=' + lat + ',' + lng + '&z=' + z + '&b=' + b;

	var suffix = p.HP ? ' HP' : p.emblem ? ' **' : p.mtneer ? ' *' : '';

	var otherName = p.name2 ? '<br>(' + p.name2 + ')' : '';

	var name = makeLink(htmlFilename + p.id.split('.')[0], p.id) + ' ' +
		makeLink(topoLink, p.name) + suffix + otherName;

	var links = [];
	if (p.SP) links.push(makeLink('https://www.summitpost.org/' + p.SP, 'SP'));
	if (p.W) links.push(makeLink('https://en.wikipedia.org/wiki/' + p.W, 'W'));
	if (p.BB) links.push(makeLink('https://www.snwburd.com/dayhikes/peak/' + p.BB, 'BB'));
	if (p.LoJ) links.push(makeLink('https://listsofjohn.com/peak/' + p.LoJ, 'LoJ'));
	if (p.Pb) links.push(makeLink('https://peakbagger.com/peak.aspx?pid=' + p.Pb, 'Pb'));
	if (!p.noWX) links.push(makeLink(weatherLink(lng, lat), 'WX'));

	links = links.length === 0 ? '' : '<br>' + links.join(', ');

	var yds = p.YDS ? '<br>Class ' + p.YDS : '';
	var climbed = p.climbed ? '<br>Climbed <div class="elevDiv">' + p.climbed + '</div>' : '';

	return '<div class="popupDiv"><b>' + name + '</b>' +
		'<br>Elevation: <div class="elevDiv">' + elevationHTML(p.elev) + '</div>' +
		'<br>Prominence: <div class="elevDiv">' + p.prom + '</div>' +
		yds + links + climbed + '</div>';
}
