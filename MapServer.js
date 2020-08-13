/* globals document, Image, window, L, pmapShared */
/* exported BaseLayers, TileOverlays, MapServer */

const BaseLayers = {
name: 'Base Layers',
items: {
	mapbox: {
		name: 'Mapbox',
		items: {
			o:   {name: 'Outdoors',          style: 'outdoors-v11'},
			s:   {name: 'Satellite',         style: 'satellite-v9'},
			sts: {name: 'Satellite Streets', style: 'satellite-streets-v11'},
			st:  {name: 'Streets',           style: 'streets-v11'},
		},
		order: ['o', 's', 'sts', 'st'],
	},
	natmap: {
		name: 'National Map',
		items: {
			topo: {
		name: 'Topo',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer',
		attribution: '[USGS The National Map]',
			},
			imgtopo: {
		name: 'Imagery Topo',
		url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer',
		maxZoom: 19,
		attribution: '[USGS The National Map]',
			},
			naip: {
		name: 'NAIP Imagery',
		url: 'https://services.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer',
		attribution: '[USGS The National Map]',
			},
			naipplus: {
		name: 'NAIP Plus',
		url: 'https://services.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/MapServer',
		attribution: '[USGS The National Map]',
			},
		},
		order: ['topo', 'imgtopo', 'naip', 'naipplus'],
	},
	esri: {
		name: 'Esri',
		items: {
			imagery: {
		name: 'Imagery',
		url: 'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer',
		tile: true,
		maxZoom: 19, // why not 23?
		attribution: '[Esri], DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, ' +
			'USDA, USGS, AeroGRID, IGN, and the GIS User Community',
			},
			clarity: {
		name: 'Imagery Clarity',
		url: 'https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer',
		tile: true,
		maxZoom: 19, // why not 23?
		attribution: '[Esri], DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, ' +
			'USDA, USGS, AeroGRID, IGN, and the GIS User Community',
			},
			firefly: {
		name: 'Imagery Firefly',
		url: 'https://fly.maptiles.arcgis.com/arcgis/rest/services/World_Imagery_Firefly/MapServer',
		tile: true,
		maxZoom: 19, // why not 23?
		attribution: '[Esri], DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, ' +
			'USDA, USGS, AeroGRID, IGN, and the GIS User Community',
			},
			usatopo: {
		name: 'USA Topo',
		url: 'https://services.arcgisonline.com/arcgis/rest/services/USA_Topo_Maps/MapServer',
		tile: true,
		maxZoom: 15,
		attribution: '[Esri] | &copy; 2013 National Geographic Society, i-cubed',
			},
		},
		order: ['imagery', 'clarity', 'firefly', 'usatopo'],
	},
	caltopo: {
		name: 'CalTopo',
		url: 'https://caltopo.s3.amazonaws.com/topo/{z}/{x}/{y}.png',
		maxZoom: 16,
		attribution: '<a href="https://caltopo.com/">CalTopo</a>',
	},
	canvec: {
		name: 'Canada Topo',
		url: 'https://maps.geogratis.gc.ca/wms/canvec_en',
		wms: {layers: 'canvec'},
		attribution: '<a href="https://open.canada.ca/en/open-government-licence-canada">' +
			'Natural Resources Canada</a>',
	},
	osm: {
		name: 'OpenStreetMap',
		url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
		// For example: https://a.tile.openstreetmap.org/4/2/2.png
		maxZoom: 19,
		attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
	},
	o: 'mapbox',
	s: 'mapbox',
	sts: 'mapbox',
	st: 'mapbox',
},
order: ['mapbox', 'natmap', 'esri', 'caltopo', 'canvec', 'osm'],
};
const TileOverlays = {
name: 'Tile Overlays',
items: {
	us: {
		name: 'National',
		items: {
			aiannh: {
		name: 'American Indian,|Alaska Native, and|Native Hawaiian Areas',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/AIANNHA/MapServer',
		exportLayers: '47',
		opacity: 0.5,
		queryFields: ['OBJECTID', 'NAME'],
		attribution: '[U.S. Census Bureau]',
			},
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
			blmw: {
		name: 'Wilderness Areas (BLM)',
		url: 'https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_NLCS_WLD_WSA/MapServer',
		exportLayers: '0',
		opacity: 0.5,
		attribution: '[Bureau of Land Management]',
			},
			wsa: {
		name: 'Wilderness Study Areas',
		url: 'https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_NLCS_WLD_WSA/MapServer',
		exportLayers: '1',
		opacity: 0.5,
		queryFields: [
			'nlcs_wsa_poly.OBJECTID',
			'nlcs_wsa_poly.NLCS_NAME',
			'nlcs_wsa_poly.ADMIN_ST',
			'nlcs_wsa_poly.WSA_RCMND',
		],
		attribution: '[Bureau of Land Management]',
			},
			states: {
		name: 'States',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '0,2,4,6,8,10,12,14,15,16', // states only
		queryLayer: '12',
		queryFields: ['OBJECTID', 'NAME', 'STUSAB'],
		attribution: '[U.S. Census Bureau]',
			},
			counties: {
		name: 'Counties',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer',
		exportLayers: '1,3,5,7,9,11,13', // counties only
		queryLayer: '13',
		queryFields: ['OBJECTID', 'NAME'],
		attribution: '[U.S. Census Bureau]',
			},
			countylabels: {
		name: 'County Labels',
		url: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Labels/MapServer',
		exportLayers: '65',
		attribution: '[U.S. Census Bureau]',
			},
			nwr: {
		name: 'FWS Refuges',
		url: 'https://gis.fws.gov/arcgis/rest/services/FWS_Refuge_Boundaries/MapServer',
		exportLayers: '3',
		opacity: 0.5,
		queryFields: ['OBJECTID', 'ORGNAME', 'SUM_GISACRES'],
		attribution: '[U.S. Fish &amp; Wildlife Service]',
			},
			nwrlabels: {
		name: 'FWS Refuge Labels',
		url: 'https://gis.fws.gov/arcgis/rest/services/FWS_Refuge_Boundaries/MapServer',
		exportLayers: '1',
		attribution: '[U.S. Fish &amp; Wildlife Service]',
			},
			fs: {
		name: 'National Forests',
		url: 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_ForestSystemBoundaries_01/MapServer',
		queryLayer: '1',
		queryFields: ['OBJECTID', 'FORESTNAME'],
		attribution: '[U.S. Forest Service]',
			},
			fsrd: {
		name: 'National Forest|Ranger Districts',
		url: 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_RangerDistricts_01/MapServer',
		queryLayer: '1',
		queryFields: ['OBJECTID', 'FORESTNAME', 'DISTRICTNAME'],
		attribution: '[U.S. Forest Service]',
			},
			fsw: {
		name: 'Wilderness Areas (USFS)',
		url: 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_Wilderness_01/MapServer',
		queryFields: ['OBJECTID', 'WILDERNESSNAME', 'GIS_ACRES', 'WID'],
		attribution: '[U.S. Forest Service]',
			},
			fsonda: {
		name: 'USFS Other National|Designated Areas',
		url: 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_OtherNationalDesignatedArea_01/MapServer',
		queryFields: ['OBJECTID', 'AREANAME', 'AREATYPE'],
		attribution: '[U.S. Forest Service]',
			},
			fssima: {
		name: 'USFS Special Interest|Management Areas',
		url: 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_SpecialInterestManagementArea_01/MapServer',
		queryFields: ['OBJECTID', 'AREANAME', 'AREATYPE', 'GIS_ACRES'],
		attribution: '[U.S. Forest Service]',
			},
			nps: {
		name: 'National Parks',
		url: 'https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services' +
			'/NPS_Park_Boundaries/FeatureServer',
		queryFields: ['OBJECTID', 'UNIT_NAME', 'UNIT_CODE'],
		attribution: '[National Park Service]',
			},
			npsimd: {
		name: 'National Parks (IMD)',
		url: 'https://irmaservices.nps.gov/arcgis/rest/services/IMDData/IMD_Boundaries_wgs/MapServer',
		queryFields: ['OBJECTID', 'UNITNAME', 'UNITCODE'],
		attribution: '[NPS Inventory and Monitoring Division]',
			},
			govunits: {
				name: 'USGS National Map',
				items: {
					blm: {
		name: 'BLM Lands',
		url: 'https://carto.nationalmap.gov/arcgis/rest/services/govunits/MapServer',
		exportLayers: '33',
		opacity: 0.5,
		attribution: '[USGS The National Map: National Boundaries Dataset]',
					},
					nps: {
		name: 'National Parks',
		url: 'https://carto.nationalmap.gov/arcgis/rest/services/govunits/MapServer',
		exportLayers: '23',
		opacity: 0.5,
		attribution: '[USGS The National Map: National Boundaries Dataset]',
					},
					usfs: {
		name: 'National Forests',
		url: 'https://carto.nationalmap.gov/arcgis/rest/services/govunits/MapServer',
		exportLayers: '24',
		opacity: 0.5,
		attribution: '[USGS The National Map: National Boundaries Dataset]',
					},
					w: {
		name: 'Wilderness Areas',
		url: 'https://carto.nationalmap.gov/arcgis/rest/services/govunits/MapServer',
		exportLayers: '25',
		opacity: 0.5,
		attribution: '[USGS The National Map: National Boundaries Dataset]',
					},
				},
				order: ['blm', 'nps', 'usfs', 'w'],
			},
			w: {
		name: 'Wilderness Areas',
		url: 'https://tiles.arcgis.com/tiles/ERdCHt0sNM6dENSD/arcgis/rest/services' +
			'/Wilderness_Areas_of_the_United_States_010920/MapServer',
		tile: true,
		opacity: 0.5,
		attribution: 'Wilderness Institute',
			},
			zip: {
		name: 'ZIP Codes',
		url: 'https://gis.usps.com/arcgis/rest/services/EDDM/EDDM_ZIP5/MapServer',
		exportLayers: '0',
		attribution: '[USPS]',
			},
			fires: {
				name: 'Wildfires',
				items: {
					current: {
		name: 'Current Perimeters',
		url: 'https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services' +
			'/Public_Wildfire_Perimeters_View/FeatureServer',
		queryFields: ['OBJECTID', 'IncidentName', 'GISAcres', 'DateCurrent'],
		attribution: '<a href="https://data-nifc.opendata.arcgis.com/datasets/wildfire-perimeters">' +
			'National Interagency Fire Center</a>',
					},
					archived: {
		name: 'Archived Perimeters',
		url: 'https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services' +
			'/Archived_Wildfire_Perimeters2/FeatureServer',
		queryFields: ['OBJECTID', 'IncidentName', 'GISAcres', 'DateCurrent'],
		attribution: '<a href="https://data-nifc.opendata.arcgis.com/datasets/wildfire-perimeters">' +
			'National Interagency Fire Center</a>',
					},
					modis: {
		name: 'MODIS',
		url: 'https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services' +
			'/MODIS_Thermal_v1/FeatureServer',
		attribution: '<a href="https://www.arcgis.com/home/item.html?id=b8f4033069f141729ffb298b7418b653">' +
			'NASA</a>',
					},
					viirs: {
		name: 'VIIRS',
		url: 'https://services9.arcgis.com/RHVPKKiFTONKtxq3/arcgis/rest/services' +
			'/Satellite_VIIRS_Thermal_Hotspots_and_Fire_Activity/FeatureServer',
		attribution: '<a href="https://www.arcgis.com/home/item.html?id=dece90af1a0242dcbf0ca36d30276aa3">' +
			'NASA</a>',
					},
				},
				order: ['current', 'archived', 'modis', 'viirs'],
			},
			glims: {
		name: 'GLIMS Glaciers',
		url: 'https://www.glims.org/mapservice',
		wms: {layers: 'GLIMS_GLACIERS'},
		attribution: '<a href="https://www.glims.org/">GLIMS</a> and <a href="https://nsidc.org/">NSIDC</a>',
			},
		},
		order: [
			'aiannh',
			'blm',
			'nlcs',
			'counties',
			'countylabels',
			'nwr',
			'nwrlabels',
			'glims',
			'fs',
			'fsrd',
			'nps',
			'npsimd',
			'states',
			'fsonda',
			'fssima',
			'govunits',
			'w',
			'blmw',
			'fsw',
			'wsa',
			'fires',
			'zip',
		],
	}, // us
	ca: {
		name: 'California',
		items: {
			counties: {
		name: 'Counties (Color)',
		url: 'https://services.gis.ca.gov/arcgis/rest/services/Boundaries/CA_Counties_Color/MapServer',
		opacity: 0.4,
		attribution: '[services.gis.ca.gov]',
			},
			cpad: {
		name: 'CPAD Holdings',
		url: 'https://gis.cnra.ca.gov/arcgis/rest/services' +
			'/Boundaries/CPAD_AgencyClassification/MapServer',
		opacity: 0.5,
		queryFields: ['OBJECTID', 'MNG_AGNCY', 'SITE_NAME'],
		attribution: '[GreenInfo Network]',
			},
			parks: {
		name: 'State Parks',
		url: 'https://services.gis.ca.gov/arcgis/rest/services/Boundaries/CA_State_Parks/MapServer',
		opacity: 0.5,
		queryFields: ['OBJECTID', 'UNITNAME', 'MgmtStatus', 'GISACRES'],
		attribution: '[services.gis.ca.gov]',
			},
			zip: {
		name: 'ZIP Codes',
		url: 'https://services.gis.ca.gov/arcgis/rest/services/Boundaries/Zips/MapServer',
		queryFields: ['OBJECTID', 'ZIP_CODE', 'NAME', 'STATE', 'POPULATION', 'SQMI'],
		attribution: '[USPS]',
			},
		},
		order: ['counties', 'cpad', 'parks', 'zip'],
	},
	nv: {
		name: 'Nevada',
		items: {
			parks: {
		name: 'State Parks',
		url: 'https://arcgis.shpo.nv.gov/arcgis/rest/services/State_Lands/StateLands_PublicMap/MapServer',
		exportLayers: '52',
		queryFields: ['OBJECTID', 'LandName', 'Acres'],
		attribution: '[Nevada Division of State Lands]',
			},
		},
		order: ['parks'],
	},
	w: 'us',
},
order: ['us', 'ca', 'nv'],
};
const MapServer = (function() {
'use strict';

function latLngToStr(lat, lng)
{
	const deg = '\u00B0';
	return (lat.charAt(0) === '-' ? lat.substring(1) + deg + 'S ' : lat + deg + 'N ') +
		(lng.charAt(0) === '-' ? lng.substring(1) + deg + 'W' : lng + deg + 'E');
}
function degToStr(degrees)
{
	degrees = degrees.toFixed(6);
	let i = degrees.length - 1;
	while (degrees.charAt(i) === '0') --i;
	if (degrees.charAt(i) === '.') --i;
	return degrees.substring(0, i + 1);
}
function getDateTime(millisecondsSinceEpoch)
{
	const date = new Date(millisecondsSinceEpoch);
	const year = date.getFullYear();
	let month = date.getMonth() + 1;
	let day = date.getDate();

	if (month < 10) month = '0' + month;
	if (day < 10) day = '0' + day;

	let h = date.getHours();
	let m = date.getMinutes();
	let s = date.getSeconds();

	if (h < 10) h = h === 0 ? '00' : '0' + h;
	if (m < 10) m = m === 0 ? '00' : '0' + m;
	if (s < 10) s = s === 0 ? '00' : '0' + s;

	return [year, month, day].join('-') + ' ' + [h, m, s].join(':');
}
function fitLink(map, spec)
{
	function fitBounds(event)
	{
		event.preventDefault();
		map.fitBounds(spec.outline.getBounds());
	}
	const img = new Image();
	img.alt = 'Zoom To Fit';
	img.src = 'ztf.svg';
	img.className = 'msZtf';
	img.addEventListener('click', fitBounds);
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
	const symbol = {
		type: 'esriSFS',
		style: 'esriSFSSolid',
		color: color,
	};
	if (outline)
		symbol.outline = outline;
	return symbol;
}
function simpleFillLayer(mapLayerId, color, outline)
{
	return JSON.stringify([{
		id: 101, source: {type: 'mapLayer', mapLayerId: mapLayerId},
		drawingInfo: {renderer: {type: 'simple', symbol: simpleFillSymbol(color, outline)}}
	}]);
}
const {
	us: { items: {
		aiannh: aiannhSpec,
		blm: blmSpec,
		counties: countySpec,
		fires: { items: {
			archived: arfireSpec,
			current: fireSpec,
			modis: modisSpec,
			viirs: viirsSpec,
		}},
		fs: fsSpec,
		fsonda: fsondaSpec,
		fsrd: fsrdSpec,
		fssima: fssimaSpec,
		nlcs: nlcsSpec,
		nps: npsSpec,
		npsimd: npsimdSpec,
		nwr: nwrSpec,
		states: stateSpec,
		wsa: wsaSpec,
	}},
	ca: { items: {
		cpad: cpadSpec,
		parks: caParkSpec,
		zip: caZipSpec,
	}},
	nv: { items: {
		parks: nvParkSpec,
	}},
} = TileOverlays.items;
{
	const blmLayer = simpleFillLayer(3, [0, 0, 0, 0], simpleLineSymbol([138, 43, 226, 255], 2));

	blmSpec.items = {custom: {name: 'Custom Rendering', dynamicLayers: blmLayer}};
	blmSpec.order = ['custom'];

	const fsLayers = (function() {
		const drawingInfo = {showLabels: false,
			renderer: {type: 'simple', symbol: simpleFillSymbol([128, 128, 0, 255])}};
		const layerInfo = id => ({id: 101 + id,
			source: {type: 'mapLayer', mapLayerId: id}, drawingInfo: drawingInfo});
		return JSON.stringify([layerInfo(0), layerInfo(1)]);
	})();

	fsSpec.items = {custom: {name: 'Custom Rendering', dynamicLayers: fsLayers, opacity: 0.5}};
	fsSpec.order = ['custom'];

	fsrdSpec.items = {custom: {name: 'Custom Rendering', dynamicLayers: fsLayers, opacity: 0.5}};
	fsrdSpec.order = ['custom'];

	fsondaSpec.dynamicLayers = simpleFillLayer(0, [255, 105, 180, 255]);
	fsondaSpec.opacity = 0.5;

	fssimaSpec.dynamicLayers = simpleFillLayer(0, [255, 140, 0, 255]);
	fssimaSpec.opacity = 0.5;

	npsSpec.style = () => ({color: '#FFFF00', fillOpacity: 0.5, stroke: false});

	npsimdSpec.dynamicLayers = simpleFillLayer(0, [255, 255, 0, 255]);
	npsimdSpec.opacity = 0.5;
}
function makePopupDiv(spec)
{
	const div = spec.div;
	let linkCount = 0;
	let textCount = 0;
	const makeText = () => spec['textNode' + textCount++] = document.createTextNode('');
	const makeLink = () => {
		const link = document.createElement('a');
		link.appendChild(makeText());
		spec['linkNode' + linkCount++] = link;
		return link;
	};
	const makeNode = type => {
		if (type === 'text')
			return makeText();
		if (type === 'br')
			return document.createElement('br');
		if (type === 'boldtext') {
			const bold = document.createElement('b');
			bold.appendChild(makeText());
			return bold;
		}
		if (type === 'boldlink') {
			const link = makeLink();
			link.style.fontWeight = 'bold';
			return link;
		}
		if (type === 'link')
			return makeLink();
		if (type === 'ztf')
			return spec.ztf;

		return document.createTextNode(type);
	};
	spec.template.split('|').forEach(type => div.appendChild(makeNode(type)));
}
function setPopupText(spec, ...content)
{
	content.forEach((text, i) => spec['textNode' + i].nodeValue = text);
}
function setPopupLink(spec, url)
{
	const link = spec.linkNode0;
	link.href = url;
	return link;
}
function formatAcres(acres, precision = 0)
{
	const p = Math.pow(10, precision);
	return '(' + (Math.round(acres * p) / p).toLocaleString() + ' acres)';
}
aiannhSpec.popup = {
	template: 'boldtext|br|text|ztf',
	show(attr)
	{
		const name = attr.NAME;
		const line2 = ' and Off-Reservation Trust Land';
		const br = this.brNode || (this.brNode = this.textNode1.previousSibling);

		if (name.endsWith(line2)) {
			if (!br.parentNode)
				this.div.insertBefore(br, this.textNode1);
			setPopupText(this, name.substring(0, name.length - line2.length), line2.substring(1));
		} else {
			if (br.parentNode)
				this.div.removeChild(br);
			setPopupText(this, name, '');
		}

		return '#CC33FF';
	}
};
npsSpec.popup = {
	template: 'boldlink|ztf',
	show(attr)
	{
		let [code, name] = this === npsSpec.popup ?
			[attr.UNIT_CODE, attr.UNIT_NAME] : [attr.UNITCODE, attr.UNITNAME];

		code = code.toLowerCase();
		if (code === 'kica' || code === 'sequ') code = 'seki';

		setPopupLink(this, 'https://www.nps.gov/' + code + '/index.htm');
		setPopupText(this, name);

		return '#FFFF00';
	}
};
npsimdSpec.popup = {
	template: npsSpec.popup.template,
	show: npsSpec.popup.show,
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
	template: 'boldlink|br|text|ztf',
	show(attr)
	{
		const name = attr['Monuments_NCAs_SimilarDesignation2015.NCA_NAME'];
		const code = attr['Monuments_NCAs_SimilarDesignation2015.sma_code'];
		const state = attr['Monuments_NCAs_SimilarDesignation2015.STATE_GEOG'];
		const link = setPopupLink(this, attr['nlcs_desc.WEBLINK']);

		if (link.protocol !== 'https:')
			link.protocol = 'https:';
		if (link.host !== 'www.blm.gov')
			link.host = 'www.blm.gov';
		if (!link.href.startsWith('https://www.blm.gov/programs/') &&
			!(link.href.startsWith('https://www.blm.gov/nlcs_web/') && link.href.endsWith('.html')))
			link.href = 'https://www.blm.gov/';

		setPopupText(this, name, '(' + code + ') (' + state + ')');
		return '#800000';
	}
};
fsSpec.popup = {
	template: 'boldtext|ztf',
	show(attr)
	{
		setPopupText(this, attr.FORESTNAME);
		return '#FFFF00';
	}
};
fsrdSpec.popup = {
	template: 'boldtext|br|text|ztf',
	show(attr)
	{
		setPopupText(this, attr.FORESTNAME, '(' + attr.DISTRICTNAME + ')');
		return '#008080';
	}
};
fsondaSpec.popup = {
	template: 'text|br|text|ztf',
	show(attr)
	{
		setPopupText(this, attr.AREANAME, attr.AREATYPE);
		return '#0000CD';
	}
};
fssimaSpec.popup = {
	template: 'text|br|text|br|text|ztf',
	show(attr)
	{
		setPopupText(this, attr.AREANAME, attr.AREATYPE, formatAcres(attr.GIS_ACRES));
		return '#CD0000';
	}
};
nwrSpec.popup = {
	template: 'text|br|text|ztf',
	show(attr)
	{
		setPopupText(this, attr.ORGNAME, formatAcres(attr.SUM_GISACRES));
		return '#FFA07A';
	}
};
const wildernessSpec = {
	name: 'Wilderness Areas',
	url: 'https://services1.arcgis.com/ERdCHt0sNM6dENSD/arcgis/rest/services' +
		'/Wilderness_Areas_in_the_United_States/FeatureServer',
	queryFields: ['OBJECTID_1', 'NAME', 'WID', 'Agency', 'YearDesignated', 'Acreage'],
};
wildernessSpec.popup = {
	outlineColor: {
		BLM: '#0000FF', // Blue   (fill color is #FFFF00)
		FWS: '#FFA500', // Orange (fill color is #FFAA00)
		NPS: '#800080', // Purple (fill color is #A900E6)
		USFS:'#008000', // Green  (fill color is #38A800)
	},
	template: 'boldlink|text|br|text|ztf',
	show(attr)
	{
		let agency = attr.Agency;
		if (agency === 'FS') agency = 'USFS';

		const year = (new Date(attr.YearDesignated)).getUTCFullYear();
		const acres = formatAcres(attr.Acreage);

		setPopupLink(this, 'https://wilderness.net/visit-wilderness/?ID=' + attr.WID);
		setPopupText(this, attr.NAME, ' (' + agency + ')', '(' + year + ') ' + acres);

		return this.outlineColor[agency] || '#000000';
	}
};
wsaSpec.popup = {
	template: 'text|br|text|ztf',
	show(attr)
	{
		setPopupText(this, attr['nlcs_wsa_poly.NLCS_NAME'],
			'(' + attr['nlcs_wsa_poly.ADMIN_ST'] + ') (' + attr['nlcs_wsa_poly.WSA_RCMND'] + ')');
		return '#B22222';
	}
};
caParkSpec.popup = {
	template: 'text|ztf|br|text',
	show(attr)
	{
		setPopupText(this, attr.UNITNAME, '(' + attr.MgmtStatus + ') ' + formatAcres(attr.GISACRES));
		return '#70A800';
	}
};
nvParkSpec.popup = {
	template: 'text|ztf|br|text',
	show(attr)
	{
		setPopupText(this, attr.LandName, formatAcres(attr.Acres));
		return '#70A800';
	}
};
caZipSpec.popup = {
	template: 'text|ztf',
	show(attr)
	{
		setPopupText(this, attr.NAME + ', ' + attr.STATE + ' ' + attr.ZIP_CODE);
		return '#FF1493';
	}
};
countySpec.popup = {
	template: 'text|ztf',
	show(attr)
	{
		setPopupText(this, attr.NAME);
		return '#A52A2A';
	}
};
cpadSpec.popup = {
	template: 'text|br|text|ztf',
	show(attr)
	{
		setPopupText(this, attr.SITE_NAME, '(' + attr.MNG_AGNCY + ')');
		return '#C71585';
	}
};
stateSpec.popup = {
	template: 'text|ztf',
	show(attr)
	{
		setPopupText(this, attr.NAME + ' (' + attr.STUSAB + ')');
		return '#000000';
	}
};
blmSpec.popup = {
	template: 'BLM |link|text|br|text|ztf',
	show(attr)
	{
		let url = attr.ADMU_ST_URL;
		if (url.charAt(0) === '\'')
			url = url.substring(1);

		const link = setPopupLink(this, url);
		if (link.protocol !== 'https:')
			link.protocol = 'https:';
		if (link.host !== 'www.blm.gov')
			link.host = 'www.blm.gov';

		setPopupText(this, attr.ADMU_NAME, ' (' + attr.ADMIN_ST + ')', '(' + attr.PARENT_NAME + ')');
		return '#0000FF';
	}
};
fireSpec.style = () => ({color: '#FF0000', weight: 2});
fireSpec.popup = {
	template: 'text|br|text|ztf|br|text',
	show(attr)
	{
		const name = attr.IncidentName + ' Fire';
		const size = formatAcres(attr.GISAcres, 2);
		const date = getDateTime(attr.DateCurrent);

		setPopupText(this, name, size, '(' + date + ')');
		return '#FF0000';
	}
};
arfireSpec.style = () => ({color: '#FFD700', weight: 2});
arfireSpec.popup = {
	template: fireSpec.popup.template,
	show: fireSpec.popup.show,
};
let querySpecs = [
	aiannhSpec,
	npsSpec,
	npsimdSpec,
	nlcsSpec,
	fsSpec,
	fsrdSpec,
	nwrSpec,
	wildernessSpec,
	wsaSpec,
	fsondaSpec,
	fssimaSpec,
	caParkSpec,
	nvParkSpec,
	caZipSpec,
	countySpec,
	cpadSpec,
	stateSpec,
	blmSpec,
	fireSpec,
	arfireSpec,
];
function esriFeatureLayer(spec)
{
	const options = {
		attribution: getAttribution(spec),
		url: spec.url + '/' + (spec.queryLayer || '0'),
	};
	if (spec.pointToLayer) options.pointToLayer = spec.pointToLayer;
	if (spec.style) options.style = spec.style;

	return L.esri.featureLayer(options);
}
modisSpec.pointToLayer = function(feature, latlng) {
	const frp = feature.properties.FRP;

	return L.circleMarker(latlng, {
		color:
			frp <   1 ? '#8B0000' :
			frp <  10 ? '#FF0000' :
			frp < 100 ? '#FFD700' : '#FFFF00',
		fillOpacity: 0.5,
	});
};
viirsSpec.pointToLayer = function(feature, latlng) {
	const frp = feature.properties.frp;

	return L.circleMarker(latlng, {
		color:
			frp <   1 ? '#8B0000' :
			frp <  10 ? '#FF0000' :
			frp < 100 ? '#FFD700' : '#FFFF00',
		fillOpacity: 0.5,
	});
};
modisSpec.makeLayer = function(spec) {
	const daynight = dn => dn === 'D' ? 'Day' : 'Night';
	const satellite = sat => sat === 'T' ?
		'<a href="https://en.wikipedia.org/wiki/Terra_(satellite)">Terra</a>' : sat === 'A' ?
		'<a href="https://en.wikipedia.org/wiki/Aqua_(satellite)">Aqua</a>' : sat;

	return esriFeatureLayer(spec).bindPopup(function({feature}) {
		const p = feature.properties;
		const [lng, lat] = feature.geometry.coordinates;
		return [
			'<div>' + daynight(p.DAYNIGHT) + ' Fire</div>',
			'<div class="peakDiv">' + getDateTime(p.ACQ_DATE) + '</div>',
			'<div class="peakDiv">' + lat + ',' + lng + '</a>',
			'<div class="peakDiv">Radiative Power: ' + p.FRP + ' MW</div>',
			'<div class="peakDiv">Brightness 21: ' + p.BRIGHTNESS + '&deg;K</div>',
			'<div class="peakDiv">Brightness 31: ' + p.BRIGHT_T31 + '&deg;K</div>',
			'<div class="peakDiv">Confidence: ' + p.CONFIDENCE + '%</div>',
			'<div class="peakDiv">Version: ' + p.VERSION + '</div>',
			'<div class="peakDiv">Scan / Track: ' + p.SCAN + ' / ' + p.TRACK + '</div>',
			'<div class="peakDiv">Satellite: ' + satellite(p.SATELLITE) + '</div>',
		].join('');
	}, {className: 'popupDiv'});
};
viirsSpec.makeLayer = function(spec) {
	const daynight = dn => dn === 'D' ? 'Day' : 'Night';
	const satellite = sat => sat === 'N' ?
		'<a href="https://en.wikipedia.org/wiki/Suomi_NPP">Suomi NPP</a>' : sat === '1' ?
		'<a href="https://en.wikipedia.org/wiki/NOAA-20">NOAA-20</a>' : sat;

	return esriFeatureLayer(spec).bindPopup(function({feature}) {
		const p = feature.properties;
		const [lng, lat] = feature.geometry.coordinates;
		return [
			'<div>' + daynight(p.daynight) + ' Fire</div>',
			'<div class="peakDiv">' + getDateTime(p.esritimeutc) + '</div>',
			'<div class="peakDiv">' + lat + ',' + lng + '</a>',
			'<div class="peakDiv">Radiative Power: ' + p.frp + ' MW</div>',
			'<div class="peakDiv">Confidence: ' + p.confidence + '</div>',
			'<div class="peakDiv">Satellite: ' + satellite(p.satellite) + '</div>',
		].join('');
	}, {className: 'popupDiv'});
};

const earthRadius = 6378137; // WGS 84 equatorial radius in meters
const earthCircumference = 2 * Math.PI * earthRadius;
const tileOrigin = -(Math.PI * earthRadius);

function exportLayer(spec, transparent)
{
	// ESRI:102113 (EPSG:3785) is the deprecated spatial reference identifier for Web Mercator.
	// ESRI:102100 (EPSG:3857) should also work.

	const exportImage = spec.url.endsWith('/ImageServer');
	const command = exportImage ? '/exportImage' : '/export';
	let baseURL = [spec.url + command + '?f=image', 'bboxSR=102113', 'imageSR=102113'];

	if (!exportImage) {
		if (transparent)
			baseURL.push('transparent=true');
		if (spec.dynamicLayers)
			baseURL.push('dynamicLayers=' + encodeURIComponent(spec.dynamicLayers));
		else if (spec.exportLayers)
			baseURL.push('layers=show:' + spec.exportLayers);
	}
	baseURL = baseURL.join('&');

	return L.GridLayer.extend({
	createTile(tileCoords, done)
	{
		const m = earthCircumference / (1 << tileCoords.z); // tile size in meters
		const x = tileOrigin + m*tileCoords.x;
		const y = tileOrigin + m*tileCoords.y;
		const p = 2;

		const tileSize = this.getTileSize();

		const url = [baseURL,
			'size=' + tileSize.x + ',' + tileSize.y,
			'bbox=' + [x.toFixed(p), (-y-m).toFixed(p), (x+m).toFixed(p), (-y).toFixed(p)].join(',')
		].join('&');

		const tile = new Image(tileSize.x, tileSize.y);

		tile.addEventListener('load', function() { done(null, tile); });
		tile.addEventListener('error', function() { done('Failed to load ' + url, tile); });
		tile.src = url;

		return tile;
	}
	});
}
function getAttribution(spec)
{
	let url = spec.url;
	if (spec.tile)
		url += '?f=pjson';
	return spec.attribution.replace(/\[([- &,\.\/:;A-Za-z]+)\]/, '<a href="' + url + '">$1</a>');
}
function makeLayerWMS(spec, options)
{
	options.format = 'image/png';
	options.version = '1.3.0';

	const wms_options = spec.wms;
	for (const prop in wms_options)
		options[prop] = wms_options[prop];

	if (spec.attribution)
		options.attribution = spec.attribution;

	return L.tileLayer.wms(spec.url, options);
}
TileOverlays.makeLayer = function(spec)
{
	if (spec.url.endsWith('/FeatureServer'))
		return esriFeatureLayer(spec);
	const options = {
		minZoom: 0,
		maxZoom: spec.maxZoom || 23,
		zIndex: 210,
	};
	if (spec.wms) {
		options.transparent = true;
		return makeLayerWMS(spec, options);
	}
	if (spec.attribution)
		options.attribution = getAttribution(spec);
	if (spec.opacity)
		options.opacity = spec.opacity;
	if (spec.tile)
		return L.tileLayer(spec.url + '/tile/{z}/{y}/{x}', options);

	return new (exportLayer(spec, true))(options);
};
BaseLayers.makeLayer = function(spec)
{
	const options = {
		minZoom: 0,
		maxZoom: spec.maxZoom || 23,
	};
	if (spec.wms) {
		return makeLayerWMS(spec, options);
	}
	if (spec.url.endsWith('.png')) {
		options.attribution = spec.attribution;
		return L.tileLayer(spec.url, options);
	}
	if (spec.attribution)
		options.attribution = getAttribution(spec);
	if (spec.tile)
		return L.tileLayer(spec.url + '/tile/{z}/{y}/{x}', options);

	return new (exportLayer(spec, false))(options);
};
function addPager(spec, numPages, showPage)
{
	let page = 1;
	const textSuffix = '/' + numPages;

	const div = document.createElement('div');
	const prevSpan = document.createElement('span');
	const nextSpan = document.createElement('span');
	const textSpan = document.createElement('span');
	const textNode = document.createTextNode(page + textSuffix);

	prevSpan.appendChild(document.createTextNode('\u25C4'));
	nextSpan.appendChild(document.createTextNode('\u25BA'));
	textSpan.appendChild(textNode);

	div.appendChild(prevSpan).className = 'pagerPrev';
	div.appendChild(textSpan).className = 'pagerText';
	div.appendChild(nextSpan).className = 'pagerNext';

	prevSpan.addEventListener('click', function() {
		if (spec.toggle.checked && spec.outline)
			spec.outline.remove();

		page = page === 1 ? numPages : page - 1;
		textNode.nodeValue = page + textSuffix;

		showPage(page - 1);
	});
	nextSpan.addEventListener('click', function() {
		if (spec.toggle.checked && spec.outline)
			spec.outline.remove();

		page = page === numPages ? 1 : page + 1;
		textNode.nodeValue = page + textSuffix;

		showPage(page - 1);
	});
	spec.div.appendChild(spec.pager = div);
}
function addOutlineCheckbox(spec, map)
{
	function clickCheckbox()
	{
		if (spec.outline) {
			if (spec.toggle.checked)
				spec.outline.addTo(map);
			else
				spec.outline.remove();
		}
		else if (spec.toggle.checked)
			spec.runGeometryQuery();
	}
	function changeColor()
	{
		spec.style.color = spec.color = spec.colorPicker.value;
		if (spec.outline)
			spec.outline.setStyle(spec.style);
	}
	const nextNode = spec.ztf.nextSibling;
	{
		const input = document.createElement('input');
		input.type = 'checkbox';

		// Check the checkbox if runGeometryQuery was set by AddPointQueries() in pmap-lc.js
		input.checked = spec.runGeometryQuery ? true : false;

		input.addEventListener('click', clickCheckbox);
		spec.div.insertBefore(input, nextNode);
		spec.toggle = input;
	}{
		const input = document.createElement('input');
		input.type = 'color';

		if (spec.color) input.value = spec.color;

		input.addEventListener('change', changeColor);
		spec.div.insertBefore(input, nextNode);
		spec.colorPicker = input;
	}
}
return {
initPointQueries(map)
{
	const loadJSON = pmapShared.loadJSON;
	const geojson = false;
	const responseFormat = geojson ? 'geojson' : 'json';
	const attrKey = geojson ? 'properties' : 'attributes';
	let globalClickID = 0;
	let popupEmpty = true;
	let firstResponse = false;
	const popupSpecs = [];

	const popupDiv = document.createElement('div');
	popupDiv.className = 'popupDiv blmPopup';

	const llSpan = document.createElement('span');
	llSpan.style.cursor = 'pointer';
	llSpan.appendChild(document.createTextNode(''));
	llSpan.addEventListener('click', function() {
		const llText = llSpan.firstChild.nodeValue;
		llSpan.firstChild.nodeValue = llSpan.dataset.ll;
		window.getSelection().selectAllChildren(llSpan);
		document.execCommand('copy');
		llSpan.firstChild.nodeValue = llText;
	});

	const llDiv = document.createElement('div');
	llDiv.appendChild(llSpan);
	popupDiv.appendChild(llDiv);

	const popup = L.popup({maxWidth: 600}).setContent(popupDiv);

	function queryInit(spec)
	{
		const popupSpec = spec.popup;
		popupSpec.div = document.createElement('div');
		popupSpec.ztf = fitLink(map, popupSpec);
		makePopupDiv(popupSpec);
		addOutlineCheckbox(popupSpec, map);
		popupSpec.div.style.display = 'none';

		const queryLayer = spec.queryLayer || spec.exportLayers || '0';
		const baseURL = spec.url + '/' + queryLayer + '/query?f=' + responseFormat;

		popupSpec.queryField0 = spec.queryFields ? spec.queryFields[0] : spec.queryField0 || 'OBJECTID';
		popupSpec.queryByLL = [baseURL,
			'returnGeometry=false',
			'outFields=' + (spec.queryFields ? spec.queryFields.join(',') : '*'),
			'spatialRel=esriSpatialRelIntersects',
			'inSR=4326', // WGS 84 (EPSG:4326) longitude/latitude
			'geometryType=esriGeometryPoint',
			'geometry='].join('&');
		popupSpec.queryByID = [baseURL,
			'returnGeometry=true',
			'geometryPrecision=5',
			'outSR=4326',
			'objectIds='].join('&');

		popupSpec.outline = null;
		popupSpec.outlineID = null;
		popupSpec.outlineCache = {};
		popupSpec.activeQueries = {};
	}
	function queryEnable(spec)
	{
		const popupSpec = spec.popup;
		if (!popupSpec.div)
			queryInit(spec);

		const order = spec.queryOrder;
		const n = querySpecs.length;
		let i = n - 1;

		while (i >= 0 && order < querySpecs[i].queryOrder) --i;

		popupDiv.insertBefore(popupSpec.div, ++i === n ? null : popupSpecs[i].div);
		querySpecs.splice(i, 0, spec);
		popupSpecs.splice(i, 0, popupSpec);

		if (popup.isOpen())
			runQuery(globalClickID, popupSpec, null, llSpan.dataset.ll.split(',').reverse().join(','));
	}
	function queryReset(spec)
	{
		if (spec.toggle.checked && spec.outline)
			spec.outline.remove();

		spec.outline = null;
		spec.outlineID = null;
		spec.div.style.display = 'none';

		if (spec.pager) {
			spec.div.removeChild(spec.pager);
			spec.pager = null;
		}
	}
	function queryDisable(spec)
	{
		let i = querySpecs.length - 1;
		while (i >= 0 && spec !== querySpecs[i]) --i;

		const popupSpec = spec.popup;
		popupDiv.removeChild(popupSpec.div);
		querySpecs.splice(i, 1);
		popupSpecs.splice(i, 1);

		queryReset(popupSpec);
	}
	function makeToggleQuery(spec, index)
	{
		spec.queryOrder = index;
		spec.toggleQuery = function(event) {
			const checkbox = spec.queryToggle;
			if (!event || event.currentTarget !== checkbox)
				checkbox.checked = !checkbox.checked;
			if (checkbox.checked)
				queryEnable(spec);
			else
				queryDisable(spec);
		};
	}
	function removeOutlines()
	{
		if (!popupEmpty) {
			popupSpecs.forEach(queryReset);
			popupEmpty = true;
		}
		firstResponse = false;
	}
	function addOutline(spec, outline)
	{
		spec.outline = outline;
		if (outline.options.color !== spec.style.color)
			outline.setStyle(spec.style);
		if (spec.toggle.checked)
			outline.addTo(map);
		spec.ztf.style.display = '';
		popup.update();
	}

	TileOverlays.items.us.items.w = wildernessSpec;

	querySpecs.forEach(makeToggleQuery);
	querySpecs = [];

	function runQuery(clickID, spec, ll, lngCommaLat)
	{
		function showFeature(attr)
		{
			let style = spec.show(attr);
			if (typeof style === 'string')
				style = {color: style.toLowerCase(), fillOpacity: 0};

			spec.style = style;
			spec.div.style.display = '';
			spec.ztf.style.display = 'none';
			if (spec.color)
				style.color = spec.color;
			else
				spec.colorPicker.value = style.color;

			if (popupEmpty) {
				map.openPopup(popup.setLatLng(ll));
				popupEmpty = false;
			} else
				popup.update();

			const outlineID = attr[spec.queryField0];
			spec.outlineID = outlineID;

			spec.runGeometryQuery = function()
			{
				if (spec.activeQueries[outlineID]) return;

				spec.activeQueries[outlineID] = loadJSON(spec.queryByID + outlineID,
				function(json) {
					delete spec.activeQueries[outlineID];

					if (!(json && json.features && json.features.length)) return;

					let geometry = json.features[0].geometry;
					if (!geojson)
						if (json.geometryType === 'esriGeometryPolygon')
							geometry = {type: 'Polygon', coordinates: geometry.rings};
						else
							return;

					if (clickID !== globalClickID && outlineID === spec.outlineID)
						style = spec.style;
					const outline = L.GeoJSON.geometryToLayer(geometry, style);
					spec.outlineCache[outlineID] = outline;

					if (outlineID === spec.outlineID)
						addOutline(spec, outline);
				},
				function() {
					delete spec.activeQueries[outlineID];
					spec.toggle.checked = false;
				});
			};

			const outline = spec.outlineCache[outlineID];
			if (outline)
				addOutline(spec, outline);
			else if (spec.toggle.checked)
				spec.runGeometryQuery();
		}
		function querySuccess(json)
		{
			if (clickID !== globalClickID) return;
			if (firstResponse) removeOutlines();
			if (!json) return;

			const features = json.features;
			if (!features) return;

			const numFeatures = features.length;
			if (!Number.isInteger(numFeatures) || numFeatures < 1) return;

			const showPage = i => showFeature(features[i][attrKey]);
			if (numFeatures > 1)
				addPager(spec, numFeatures > 99 ? 99 : numFeatures, showPage);

			showPage(0);
		}
		function queryFailed()
		{
			if (clickID !== globalClickID) return;
			if (firstResponse) removeOutlines();
		}
		loadJSON(spec.queryByLL + lngCommaLat, querySuccess, queryFailed);
	}

	map.on('click', function(event) {
		globalClickID += 1;
		firstResponse = true;

		const ll = event.latlng;
		const lng = degToStr(ll.lng);
		const lat = degToStr(ll.lat);
		const lngCommaLat = lng + ',' + lat;

		llSpan.firstChild.nodeValue = latLngToStr(lat, lng);
		llSpan.dataset.ll = lat + ',' + lng;

		for (const spec of popupSpecs)
			runQuery(globalClickID, spec, ll, lngCommaLat);
	});
}};
})();
