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
<br>(California desert peaks not on any of the above lists)
<li><b><a href="https://nightjuggler.com/nature/osp.html">Other Sierra Peaks</a></b>
<br>(Sierra peaks not on any of the above lists)
<li><b><a href="https://nightjuggler.com/nature/ocap.html">Other California Peaks</a></b>
<br>(California peaks not on any of the above lists)
<li><b><a href="https://nightjuggler.com/nature/owp.html">Other Western Peaks</a></b>
<br>(Peaks in other western states not on any of the above lists)
</ul>

I've also started compiling a list of [Sierra Mountain Passes](https://nightjuggler.com/nature/SierraPasses.html)

## P-Map

* [P-Map built on Leaflet](https://nightjuggler.com/nature/pmap.html?o=sps)
* [P-Map built on Mapbox.js](https://nightjuggler.com/nature/pmapmb.html?o=sps)
* [P-Map built on Mapbox GL JS](https://nightjuggler.com/nature/pmapgl.html?o=sps)

Many parameters can be specified in the URL. For example, the following link
opens the map at zoom level 10 (**z=10**),
centered at 37.81082&deg;N 119.4855&deg;W (the Olmsted Point parking area in Yosemite)
(**ll=37.81082,-119.4855**),
loads a GeoJSON file with data for the peaks of the Sierra Peaks Section list (see above)
which are shown as clickable triangular markers (**o=sps**),
loads a layer which shows land managed by the National Park Service in semi-transparent yellow
(**ot=us_nps**),
enables what I call "point queries" and "geometry queries" for the National Park Service layer
with outlines shown in red (**q=us_nps&qg=us_nps:ff0000**), and
then simulates a click on the map center (**clk**) which runs the "point query" and "geometry query"
for that point's latitude and longitude and opens a popup with the result.

[https://nightjuggler.com/nature/pmapmb.html?o=sps&ot=us_nps&q=us_nps&qg=us_nps:ff0000&ll=37.81082,-119.4855&z=10&clk](https://nightjuggler.com/nature/pmapmb.html?o=sps&ot=us_nps&q=us_nps&qg=us_nps:ff0000&ll=37.81082,-119.4855&z=10&clk)

