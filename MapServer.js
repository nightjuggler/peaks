/* globals document, Image, window, L, loadJSON */
/* exported BaseLayers, TileOverlays, MapServer */

var BaseLayers = {
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
var TileOverlays = {
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
		url: 'https://irmaservices.nps.gov/arcgis/rest/services/IMDData/IMD_Boundaries_WebMercator/MapServer',
		queryFields: ['OBJECTID', 'UNIT_NAME', 'UNIT_CODE'],
		attribution: '[National Park Service]',
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
			'/Archived_Wildfire_Perimeters/FeatureServer',
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
		url: 'https://arcgis.shpo.nv.gov/arcgis/rest/services/NV_StateManagedLands/MapServer',
		exportLayers: '52',
		queryFields: ['OBJECTID', 'LandName', 'Acres'],
		attribution: '[Nevada Department of Conservation &amp; Natural Resources]',
			},
		},
		order: ['parks'],
	},
	w: 'us',
},
order: ['us', 'ca', 'nv'],
};

var MapServer = (function() {
'use strict';

function latLngToStr(lat, lng)
{
	var deg = '\u00B0';
	return (lat.charAt(0) === '-' ? lat.substring(1) + deg + 'S ' : lat + deg + 'N ') +
		(lng.charAt(0) === '-' ? lng.substring(1) + deg + 'W' : lng + deg + 'E');
}
function degToStr(degrees)
{
	degrees = degrees.toFixed(6);
	var len = degrees.length - 1;
	while (degrees.charAt(len) === '0') --len;
	if (degrees.charAt(len) === '.') --len;
	return degrees.substring(0, len + 1);
}
function getDateTime(millisecondsSinceEpoch)
{
	var date = new Date(millisecondsSinceEpoch);
	var year = date.getFullYear();
	var month = date.getMonth() + 1;
	var day = date.getDate();

	if (month < 10) month = '0' + month;
	if (day < 10) day = '0' + day;

	var h = date.getHours();
	var m = date.getMinutes();
	var s = date.getSeconds();

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

var aiannhSpec = TileOverlays.items.us.items.aiannh;
var arfireSpec = TileOverlays.items.us.items.fires.items.archived;
var blmSpec = TileOverlays.items.us.items.blm;
var caParkSpec = TileOverlays.items.ca.items.parks;
var caZipSpec = TileOverlays.items.ca.items.zip;
var countySpec = TileOverlays.items.us.items.counties;
var cpadSpec = TileOverlays.items.ca.items.cpad;
var fireSpec = TileOverlays.items.us.items.fires.items.current;
var fsondaSpec = TileOverlays.items.us.items.fsonda;
var fssimaSpec = TileOverlays.items.us.items.fssima;
var fsSpec = TileOverlays.items.us.items.fs;
var fsrdSpec = TileOverlays.items.us.items.fsrd;
var nlcsSpec = TileOverlays.items.us.items.nlcs;
var npsSpec = TileOverlays.items.us.items.nps;
var nvParkSpec = TileOverlays.items.nv.items.parks;
var nwrSpec = TileOverlays.items.us.items.nwr;
var stateSpec = TileOverlays.items.us.items.states;
var wildernessSpec = {};
var wsaSpec = TileOverlays.items.us.items.wsa;

(function() {
	blmSpec.items = {
		custom: {
			name: 'Custom Rendering',
			dynamicLayers: dynamicLayer(101, 3, {
				type: 'simple',
				symbol: simpleFillSymbol([0, 0, 0, 0], simpleLineSymbol([138, 43, 226, 255], 2))
			}),
		},
	};
	blmSpec.order = ['custom'];

	fsondaSpec.dynamicLayers = dynamicLayer(101, 0, {
		type: 'simple',
		symbol: simpleFillSymbol([255, 105, 180, 255])
	});
	fsondaSpec.opacity = 0.5;

	fssimaSpec.dynamicLayers = dynamicLayer(101, 0, {
		type: 'simple',
		symbol: simpleFillSymbol([255, 140, 0, 255])
	});
	fssimaSpec.opacity = 0.5;

	var renderer = {
		type: 'simple',
		symbol: simpleFillSymbol([128, 128, 0, 255])
	};

	fsrdSpec.items = {
		custom: {
			name: 'Custom Rendering',
			dynamicLayers: JSON.stringify([{
				id: 101, source: {type: 'mapLayer', mapLayerId: 0},
				drawingInfo: {showLabels: false, renderer: renderer}
			},{
				id: 102, source: {type: 'mapLayer', mapLayerId: 1},
				drawingInfo: {showLabels: false, renderer: renderer}
			}]),
			opacity: 0.5,
		},
	};
	fsrdSpec.order = ['custom'];

	fsSpec.items = {
		custom: {
			name: 'Custom Rendering',
			dynamicLayers: fsrdSpec.items.custom.dynamicLayers,
			opacity: 0.5,
		},
	};
	fsSpec.order = ['custom'];

	npsSpec.dynamicLayers = dynamicLayer(101, 0, {
		type: 'simple',
		symbol: simpleFillSymbol([255, 255, 0, 255])
	});
	npsSpec.opacity = 0.5;

	wildernessSpec.items = {
		dl1: {
			name: 'Custom Colors|(by Agency)',
			dynamicLayers: dynamicLayer(101, 0, {
				type: 'uniqueValue', field1: 'Agency',
				uniqueValueInfos: [
					uniqueValueInfo('BLM', [0, 255, 255, 255]), // Aqua
					uniqueValueInfo('FWS', [255, 160, 122, 255]), // LightSalmon
					uniqueValueInfo('FS', [50, 205, 50, 255]), // LimeGreen
					uniqueValueInfo('NPS', [255, 0, 255, 255]), // Fuchsia / Magenta
				]}),
		},
		dl2: {
			name: 'Custom Colors|(by Year Designated)',
			dynamicLayers: dynamicLayer(101, 0, {

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
				]}),
		},
	};
	wildernessSpec.order = ['dl1', 'dl2'];
	wildernessSpec.versionName = 'Default Colors|(by Agency)';
})();

aiannhSpec.popup = {
	init: function(div)
	{
		var boldNode = document.createElement('b');
		boldNode.appendChild(this.nameNode = document.createTextNode(''));
		this.brNode = document.createElement('br');

		div.appendChild(boldNode);
		div.appendChild(this.textNode2 = document.createTextNode(''));
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		var name = attr.NAME;
		var line2 = ' and Off-Reservation Trust Land';

		if (name.endsWith(line2)) {
			if (!this.brNode.parentNode)
				this.div.insertBefore(this.brNode, this.textNode2);
			this.nameNode.nodeValue = name.substring(0, name.length - line2.length);
			this.textNode2.nodeValue = line2.substring(1);
		} else {
			if (this.brNode.parentNode)
				this.div.removeChild(this.brNode);
			this.nameNode.nodeValue = name;
			this.textNode2.nodeValue = '';
		}

		return '#CC33FF';
	},
};
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

		return '#FFFF00';
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
		if (!this.linkNode.href.startsWith('https://www.blm.gov/programs/') &&
			!(this.linkNode.href.startsWith('https://www.blm.gov/nlcs_web/') &&
			this.linkNode.href.endsWith('.html')))
			this.linkNode.href = 'https://www.blm.gov/';

		this.nameNode.nodeValue = name;
		this.textNode.nodeValue = '(' + code + ') (' + state + ')';

		return '#800000';
	},
};
fsSpec.popup = {
	init: function(div)
	{
		var boldNode = document.createElement('b');
		this.textNode = document.createTextNode('');

		boldNode.appendChild(this.textNode);
		div.appendChild(boldNode);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode.nodeValue = attr.FORESTNAME;
		return '#FFFF00';
	},
};
fsrdSpec.popup = {
	init: function(div)
	{
		var boldNode = document.createElement('b');
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');

		boldNode.appendChild(this.textNode1);
		div.appendChild(boldNode);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode1.nodeValue = attr.FORESTNAME;
		this.textNode2.nodeValue = '(' + attr.DISTRICTNAME + ')';
		return '#008080';
	},
};
fsondaSpec.popup = {
	init: function(div)
	{
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');

		div.appendChild(this.textNode1);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode1.nodeValue = attr.AREANAME;
		this.textNode2.nodeValue = attr.AREATYPE;
		return '#0000CD';
	},
};
fssimaSpec.popup = {
	init: function(div)
	{
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');
		this.textNode3 = document.createTextNode('');

		div.appendChild(this.textNode1);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode3);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode1.nodeValue = attr.AREANAME;
		this.textNode2.nodeValue = attr.AREATYPE;
		this.textNode3.nodeValue = '(' + Math.round(attr.GIS_ACRES).toLocaleString() + ' acres)';
		return '#CD0000';
	},
};
nwrSpec.popup = {
	init: function(div)
	{
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');

		div.appendChild(this.textNode1);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode1.nodeValue = attr.ORGNAME;
		this.textNode2.nodeValue = '(' + Math.round(attr.SUM_GISACRES).toLocaleString() + ' acres)';
		return '#FFA07A';
	},
};
wildernessSpec = {
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

		let year = (new Date(attr.YearDesignated)).getUTCFullYear();
		let acres = attr.Acreage.toLocaleString();

		this.linkNode.href = 'https://wilderness.net/visit-wilderness/?ID=' + attr.WID;
		this.nameNode.nodeValue = attr.NAME;
		this.textNode1.nodeValue = ' (' + agency + ')';
		this.textNode2.nodeValue = '(' + year + ') (' + acres + ' acres)';

		return this.outlineColor[agency] || '#000000';
	},
};
wsaSpec.popup = {
	init: function(div)
	{
		this.textNode1 = document.createTextNode('');
		this.textNode2 = document.createTextNode('');

		div.appendChild(this.textNode1);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2);
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode1.nodeValue = attr['nlcs_wsa_poly.NLCS_NAME'];
		this.textNode2.nodeValue = '(' + attr['nlcs_wsa_poly.ADMIN_ST'] + ') (' +
			attr['nlcs_wsa_poly.WSA_RCMND'] + ')';
		return '#B22222';
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

		return '#70A800';
	},
};
nvParkSpec.popup = {
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
		this.textNode1.nodeValue = attr.LandName;
		this.textNode2.nodeValue = '(' + Math.round(attr.Acres).toLocaleString() + ' acres)';
		return '#70A800';
	},
};
caZipSpec.popup = {
	init: function(div)
	{
		div.appendChild(this.textNode = document.createTextNode(''));
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode.nodeValue = attr.NAME + ', ' + attr.STATE + ' ' + attr.ZIP_CODE;
		return '#FF1493';
	},
};
countySpec.popup = {
	init: function(div)
	{
		div.appendChild(this.nameNode = document.createTextNode(''));
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.nameNode.nodeValue = attr.NAME;
		return '#A52A2A';
	},
};
cpadSpec.popup = {
	init: function(div)
	{
		div.appendChild(this.textNode1 = document.createTextNode(''));
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2 = document.createTextNode(''));
		div.appendChild(this.ztf);
	},
	show: function(attr)
	{
		this.textNode1.nodeValue = attr.SITE_NAME;
		this.textNode2.nodeValue = '(' + attr.MNG_AGNCY + ')';
		return '#C71585';
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
		return '#000000';
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

		return '#0000FF';
	},
};
fireSpec.popup = {
	init: function(div)
	{
		div.appendChild(this.nameNode = document.createTextNode(''));
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode1 = document.createTextNode(''));
		div.appendChild(this.ztf);
		div.appendChild(document.createElement('br'));
		div.appendChild(this.textNode2 = document.createTextNode(''));
	},
	show: function(attr)
	{
		var name = attr.IncidentName + ' Fire';
		var size = (Math.round(attr.GISAcres * 100) / 100).toLocaleString();
		var date = getDateTime(attr.DateCurrent);

		this.nameNode.nodeValue = name;
		this.textNode1.nodeValue = '(' + size + ' acres)';
		this.textNode2.nodeValue = '(' + date + ')';
		return '#FF0000';
	},
};
arfireSpec.popup = {
	init: fireSpec.popup.init,
	show: fireSpec.popup.show,
};

var querySpecs = [
	aiannhSpec,
	npsSpec,
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
		attribution: spec.attribution,
		url: spec.url + '/' + (spec.queryLayer || '0'),
	};
	if (spec.pointToLayer) options.pointToLayer = spec.pointToLayer;
	if (spec.style) options.style = spec.style;

	return L.esri.featureLayer(options);
}

fireSpec.style = () => ({color: '#FF0000', weight: 2});
arfireSpec.style = () => ({color: '#FFD700', weight: 2});

const modisSpec = TileOverlays.items.us.items.fires.items.modis;
const viirsSpec = TileOverlays.items.us.items.fires.items.viirs;

modisSpec.pointToLayer = function(feature, latlng) {
	const p = feature.properties;
	const frp = p.FRP;

	return L.circleMarker(latlng, {
		color:
			frp <   1 ? '#8B0000' :
			frp <  10 ? '#FF0000' :
			frp < 100 ? '#FFD700' : '#FFFF00',
		fillOpacity: 0.5,
	});
};
viirsSpec.pointToLayer = function(feature, latlng) {
	const p = feature.properties;
	const frp = p.frp;

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

	const layer = esriFeatureLayer(spec);

	layer.bindPopup(function(e) {
		const p = e.feature.properties;
		const [lng, lat] = e.feature.geometry.coordinates;
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

	return layer;
};
viirsSpec.makeLayer = function(spec) {
	const daynight = dn => dn === 'D' ? 'Day' : 'Night';
	const satellite = sat => sat === 'N' ?
		'<a href="https://en.wikipedia.org/wiki/Suomi_NPP">Suomi NPP</a>' : sat === '1' ?
		'<a href="https://en.wikipedia.org/wiki/NOAA-20">NOAA-20</a>' : sat;

	const layer = esriFeatureLayer(spec);

	layer.bindPopup(function(e) {
		const p = e.feature.properties;
		const [lng, lat] = e.feature.geometry.coordinates;
		return [
			'<div>' + daynight(p.daynight) + ' Fire</div>',
			'<div class="peakDiv">' + getDateTime(p.esritimeutc) + '</div>',
			'<div class="peakDiv">' + lat + ',' + lng + '</a>',
			'<div class="peakDiv">Radiative Power: ' + p.frp + ' MW</div>',
			'<div class="peakDiv">Confidence: ' + p.confidence + '</div>',
			'<div class="peakDiv">Satellite: ' + satellite(p.satellite) + '</div>',
		].join('');
	}, {className: 'popupDiv'});

	return layer;
};

const earthRadius = 6378137; // WGS 84 equatorial radius in meters
const earthCircumference = 2 * Math.PI * earthRadius;
const tileOrigin = -(Math.PI * earthRadius);

function exportLayer(spec, transparent)
{
	// ESRI:102113 (EPSG:3785) is the deprecated spatial reference identifier for Web Mercator.
	// ESRI:102100 (EPSG:3857) should also work.

	var exportImage = spec.url.endsWith('/ImageServer');
	var command = exportImage ? '/exportImage' : '/export';
	var baseURL = [spec.url + command + '?f=image', 'bboxSR=102113', 'imageSR=102113'];

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
	var url = spec.url;
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
	var options = {
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
function addOutlineCheckbox(spec, map)
{
	var nextNode = spec.ztf.nextSibling;

	var input = document.createElement('input');
	input.type = 'checkbox';
	input.checked = spec.runGeometryQuery ? true : false;
	input.addEventListener('click', function() {
		if (spec.outline) {
			if (spec.toggle.checked)
				spec.outline.addTo(map);
			else
				spec.outline.remove();
		}
		else if (spec.toggle.checked)
			spec.runGeometryQuery();
	}, false);
	spec.div.insertBefore(input, nextNode);
	spec.toggle = input;

	input = document.createElement('input');
	input.type = 'color';
	if (spec.color)
		input.value = spec.color;
	input.addEventListener('change', function() {
		spec.style.color = spec.color = spec.colorInput.value;
		if (spec.outline)
			spec.outline.setStyle(spec.style);
	}, false);
	spec.div.insertBefore(input, nextNode);
	spec.colorInput = input;
}
var MapServer = {};
MapServer.initPointQueries = function(map)
{
	var geojson = false;
	var responseFormat = geojson ? 'geojson' : 'json';
	var globalClickID = 0;
	var popupEmpty = true;
	var firstResponse = false;
	var outlines = [];
	var popupSpecs = [];

	var popupDiv = document.createElement('div');
	popupDiv.className = 'popupDiv blmPopup';

	var llSpan = document.createElement('span');
	llSpan.style.cursor = 'pointer';
	llSpan.appendChild(document.createTextNode(''));
	llSpan.addEventListener('click', function() {
		var llText = llSpan.firstChild.nodeValue;
		llSpan.firstChild.nodeValue = llSpan.dataset.ll;
		window.getSelection().selectAllChildren(llSpan);
		document.execCommand('copy');
		llSpan.firstChild.nodeValue = llText;
	});

	var llDiv = document.createElement('div');
	llDiv.appendChild(llSpan);
	popupDiv.appendChild(llDiv);

	var popup = L.popup({maxWidth: 600}).setContent(popupDiv);

	function queryInit(spec)
	{
		var popupSpec = spec.popup;
		popupSpec.div = document.createElement('div');
		popupSpec.ztf = fitLink(map, popupSpec);
		popupSpec.init(popupSpec.div);
		addOutlineCheckbox(popupSpec, map);
		popupSpec.div.style.display = 'none';

		var queryLayer = spec.queryLayer || spec.exportLayers || '0';
		var baseURL = spec.url + '/' + queryLayer + '/query?f=' + responseFormat;

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
		let popupSpec = spec.popup;
		if (!popupSpec.div)
			queryInit(spec);

		let order = spec.queryOrder;
		let n = querySpecs.length;
		let i = n - 1;

		while (i >= 0 && order < querySpecs[i].queryOrder) --i;

		popupDiv.insertBefore(popupSpec.div, ++i === n ? null : popupSpecs[i].div);
		querySpecs.splice(i, 0, spec);
		popupSpecs.splice(i, 0, popupSpec);

		if (popup.isOpen())
			runQuery(globalClickID, popupSpec, null, llSpan.dataset.ll.split(',').reverse().join(','));
	}
	function queryDisable(spec)
	{
		let i = querySpecs.length - 1;
		while (i >= 0 && spec !== querySpecs[i]) --i;

		let popupSpec = spec.popup;
		popupDiv.removeChild(popupSpec.div);
		querySpecs.splice(i, 1);
		popupSpecs.splice(i, 1);

		popupSpec.outline = null;
		popupSpec.outlineID = null;
		popupSpec.div.style.display = 'none';
	}
	function makeToggleQuery(spec)
	{
		return function(event) {
			let checkbox = spec.queryToggle;
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
		if (outlines) {
			for (var outline of outlines) outline.remove();
			outlines.length = 0;
		}
		if (!popupEmpty) {
			for (var spec of popupSpecs) {
				spec.outline = null;
				spec.outlineID = null;
				spec.div.style.display = 'none';
			}
			popupEmpty = true;
		}
		firstResponse = false;
	}

	TileOverlays.items.us.items.w = wildernessSpec;

	let queryOrder = 0;
	for (let spec of querySpecs)
	{
		spec.queryOrder = ++queryOrder;
		spec.toggleQuery = makeToggleQuery(spec);
	}
	querySpecs = [];

	function runQuery(clickID, spec, ll, lngCommaLat)
	{
		function showOutline(outline)
		{
			spec.outline = outline;
			outlines.push(outline);
			if (outline.options.color !== spec.style.color)
				outline.setStyle(spec.style);
			if (spec.toggle.checked)
				outline.addTo(map);
			spec.ztf.style.display = '';
			popup.update();
		}
		loadJSON(spec.queryByLL + lngCommaLat, function(json) {
			if (clickID !== globalClickID) return;
			if (firstResponse) removeOutlines();
			if (json.features.length === 0) return;

			var attr = json.features[0][geojson ? 'properties' : 'attributes'];
			var style = spec.show(attr);
			if (typeof style === 'string')
				style = {color: style.toLowerCase(), fillOpacity: 0};

			spec.style = style;
			spec.div.style.display = '';
			spec.ztf.style.display = 'none';
			if (spec.color)
				style.color = spec.color;
			else
				spec.colorInput.value = style.color;
			if (popupEmpty) {
				map.openPopup(popup.setLatLng(ll));
				popupEmpty = false;
			} else
				popup.update();

			var outlineID = attr[spec.queryField0];
			spec.outlineID = outlineID;

			spec.runGeometryQuery = function()
			{
				if (spec.activeQueries[outlineID]) return;

				spec.activeQueries[outlineID] = loadJSON(spec.queryByID + outlineID,
				function(json) {
					delete spec.activeQueries[outlineID];

					if (!json || !json.features) return;
					if (json.features.length === 0) return;

					var geometry = json.features[0].geometry;
					if (!geojson)
						if (json.geometryType === 'esriGeometryPolygon')
							geometry = {type: 'Polygon', coordinates: geometry.rings};
						else
							return;

					if (clickID !== globalClickID && outlineID === spec.outlineID)
						style = spec.style;
					var outline = L.GeoJSON.geometryToLayer(geometry, style);
					spec.outlineCache[outlineID] = outline;

					if (outlineID === spec.outlineID)
						showOutline(outline);
				},
				function() {
					delete spec.activeQueries[outlineID];
					spec.toggle.checked = false;
				});
			};

			var outline = spec.outlineCache[outlineID];
			if (outline)
				showOutline(outline);
			else if (spec.toggle.checked)
				spec.runGeometryQuery();

		}, function() {
			if (clickID !== globalClickID) return;
			if (firstResponse) removeOutlines();
		});
	}

	map.on('click', function(event) {
		globalClickID += 1;
		firstResponse = true;

		var ll = event.latlng;
		var lng = degToStr(ll.lng);
		var lat = degToStr(ll.lat);
		var lngCommaLat = lng + ',' + lat;

		llSpan.firstChild.nodeValue = latLngToStr(lat, lng);
		llSpan.dataset.ll = lat + ',' + lng;

		for (var spec of popupSpecs)
			runQuery(globalClickID, spec, ll, lngCommaLat);
	});
};

return MapServer;
})();
