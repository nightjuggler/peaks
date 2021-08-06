## Peak Lists

* **[Desert Peaks Section](https://nightjuggler.com/nature/dps.html)** (Sierra Club)
* **[Great Basin Peaks List](https://nightjuggler.com/nature/gbp.html)** (Sierra Club)
* **[Hundred Peaks Section](https://nightjuggler.com/nature/hps.html)** (Sierra Club) (incomplete)
* **[Lower Peaks Committee](https://nightjuggler.com/nature/lpc.html)** (Sierra Club) (incomplete)
* **[Nevada Peaks Club](https://nightjuggler.com/nature/npc.html)**
* **[Sierra Peaks Section](https://nightjuggler.com/nature/sps.html)** (Sierra Club)
* **[Tahoe Ogul Peaks List](https://nightjuggler.com/nature/ogul.html)** (ex-Sierra Club)

<ul>
<li><b><a href="https://nightjuggler.com/nature/odp.html">Other Desert Peaks</a></b>
(California desert peaks not on any of the above lists)
<li><b><a href="https://nightjuggler.com/nature/osp.html">Other Sierra Peaks</a></b>
(Sierra peaks not on any of the above lists)
<li><b><a href="https://nightjuggler.com/nature/ocap.html">Other California Peaks</a></b>
(California peaks not on any of the above lists)
<li><b><a href="https://nightjuggler.com/nature/owp.html">Other Western Peaks</a></b>
(Peaks in other western states not on any of the above lists)
</ul>

I've also started compiling a list of [Sierra Mountain Passes](https://nightjuggler.com/nature/SierraPasses.html).

## P-Map

* [P-Map built on Leaflet](https://nightjuggler.com/nature/pmap.html?o=sps)
* [P-Map built on Mapbox.js](https://nightjuggler.com/nature/pmapmb.html?o=sps)
* [P-Map built on Mapbox GL JS](https://nightjuggler.com/nature/pmapgl.html?o=sps)

In the [Leaflet](https://leafletjs.com/) and [Mapbox.js](https://docs.mapbox.com/mapbox.js/) versions of P-Map,
base layers and overlays can be selected and point queries can be enabled via the layers menu
in the top-left corner.

Many parameters can be specified in the URL. For example, the following link
opens the map at zoom level 10 (**z=10**),
centered at a given latitude and longitude (**ll=37.81082,-119.4855**),
loads a GeoJSON file with data from the Sierra Peaks Section list (see above),
shows those peaks as clickable triangular markers (**o=sps**),
loads a layer showing land managed by the National Park Service in semi-transparent yellow
(**ot=us_nps**),
enables "point queries" and "geometry queries" for the National Park Service layer
with outlines shown in red (**q=us_nps&qg=us_nps:ff0000**), and
simulates a click on the map center (**clk**) which runs the enabled queries
for the center point and opens a popup with the results.

[https://nightjuggler.com/nature/pmapmb.html?o=sps&ot=us_nps&q=us_nps&qg=us_nps:ff0000&ll=37.81082,-119.4855&z=10&clk](https://nightjuggler.com/nature/pmapmb.html?o=sps&ot=us_nps&q=us_nps&qg=us_nps:ff0000&ll=37.81082,-119.4855&z=10&clk)

