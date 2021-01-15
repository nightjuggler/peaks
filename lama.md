### lama.py &mdash; a Python script for querying ArcGIS servers

**lama.py** requires [Python 3](https://www.python.org/),
[curl](https://curl.se/), and the file **ppjson.py** from this repo.

It expects **curl** at `/usr/local/opt/curl/bin/curl`
(which is where [Homebrew](https://brew.sh/) installs it),
but this can be overridden with the `--curl` command-line option,
e.g. `--curl /usr/bin/curl`.

**lama.py** expects at least one command-line argument: either the word `none` or
a latitude and longitude separated by a comma, e.g. `37.36144,-118.39526`.

If `none` is specified, a where clause must be specified with the `-w` (or `--where`)
command-line option. In the simplest case, this can be `-w 1=1` to match all features.

If the latitude and longitude are specified, features that intersect an area within
a certain radius from that point will be matched. The default radius is 20 meters.
This can be changed with the `-d` (or `--distance`) command-line option.

The query or queries to execute are specified as a comma-separated list with the `-q`
command-line option. By default, a series of 12 queries will be made. For example:

```
&gt; python3 lama.py 37.36144,-118.39526
----- State (TIGERweb)
California (CA)
----- County (TIGERweb)
Inyo County
----- ZIP Code (California)
Bishop, CA 93514 / Population: 13,999 (2014) / 1,505.21 square miles
----- USGS 7.5' Topo
Bishop, CA
----- National Park Service Unit
----- USFS Ranger District
----- National Landscape Conservation System
----- BLM Administrative Unit
Bishop Field Office (CA) (Central California District)
----- Surface Management Agency
Unit Name Not Specified (LG)
----- Wilderness Areas
----- Wilderness Study Areas
```

To execute only the **USFS Ranger District** query (`rd`) and the **Wilderness Areas** query (`w`),
you would specify `-q rd,w`:

```
&gt; python3 lama.py -q rd,w 38.87757,-120.16102
----- USFS Ranger District
Eldorado National Forest (Pacific Ranger District)
----- Wilderness Areas
Desolation Wilderness (USFS) (1969)
```

The name/abbreviation used to reference a query on the command-line is mapped to a class
object (subclassed from the `Query` class) that defines the query specs &ndash; the components
of the URL for the ArcGIS service (`home`, `service`, `serverType`, and `layer`), which fields
to return, and how to display the results.

For example, `w` is mapped to the `WildernessQuery` class:

```
class WildernessQuery(Query):
        name = "Wilderness Areas"
        home = "https://services1.arcgis.com/ERdCHt0sNM6dENSD/arcgis/rest/services"
        service = "Wilderness_Areas_in_the_United_States"
        serverType = "Feature"
        layer = 0
        fields = [
                ("NAME", "name"),
                ("Agency", "agency"),
                ("Designated", "year"),
        ]
        printSpec = "{name} ({agency}) ({year})"

        @classmethod
        def processFields(self, fields):
                if fields["agency"] == "FS":
                        fields["agency"] = "USFS"
```

With the `--raw` command-line option, you can display all fields, not just the ones specified
in the `fields` attribute. `printSpec` and `processFields` are then ignored. For example:

```
&gt; python3 lama.py -q w --raw 38.87757,-120.16102
----- Wilderness Areas
{
	"Acreage": 64041,
	"Agency": "FS",
	"Comment": null,
	"Description": "The Desolation Wilderness, encompassing 63,475 acres of rugged alpine terrain, is a spectacular area of subalpine and alpine forests, jagged granitic peaks, and glacially formed valleys and lake basins....",
	"Designated": 1969,
	"ImagePath": "https://www.wilderness.net/images/NWPS/Desolation.jpg",
	"NAME": "Desolation Wilderness",
	"NAME_ABBREV": "Desolation",
	"OBJECTID_1": 42885,
	"STATE": "CA",
	"Shape__Area": 428790433.082031,
	"Shape__Length": 112914.775656308,
	"URL": "https://wilderness.net/visit-wilderness/?ID=155",
	"WID": 155,
	"dateLastModified": 1551139200000,
	"joinerID": "155FS"
}
```

With the `--count` command-line option, you can display just the number of features that
match the where clause. For example:

```
&gt; python3 lama.py -q airnow_current --count -w "StateName='CA' AND PM25_AQI<>null" none
----- Air Now - Current
{"count": 121
}
```

You can make group-by queries with the `-g` (or `--group-by`) command-line option.
For example, the following shows the number of wilderness areas managed by each agency:

```
&gt; python3 lama.py -q w -w 1=1 -g Agency//count:Agency none
----- Wilderness Areas
BLM 259
FS 448
FWS 71
NPS 61
```

In addition to `count`, you can also use the following functions in group-by queries:
`avg`, `min`, `max`, `stddev`, `sum`, and `var`. For example:

```
&gt; python3 lama.py -q w -w 1=1 -g Agency//sum:Acreage none
----- Wilderness Areas
BLM 9956369
FS 36172614
FWS 20703042
NPS 44337407
```

You can specify a format spec for the output. In the following example, the agency is displayed
in a field of width 4, and the sum of the acreage is displayed with commas in a field of width 12.
By default, strings are left-aligned and numbers are right-aligned within a field, but this can
be changed by specifying `&gt;` or `&lt;` at the beginning of the format spec. Fields are
always separated by a single space.

```
&gt; python3 lama.py -q w -w 1=1 -g Agency:4//sum:Acreage:12, none
----- Wilderness Areas
BLM     9,956,369
FS     36,172,614
FWS    20,703,042
NPS    44,337,407
```
