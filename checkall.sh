#!/bin/bash

script="/usr/local/bin/python3 ./sps_read.py"
diff="/usr/bin/diff"

if $script land | $diff misc/landstats.txt - >/dev/null
then echo "landstats matches"
else echo "landstats doesn't match!"
fi
if $script elev | $diff misc/elevstats.txt - >/dev/null
then echo "elevstats matches"
else echo "elevstats doesn't match!"
fi

for x in dps sps hps ogul lpc gbp npc odp osp ocap owp
do
	if $script html $x | $diff "$x.html" - >/dev/null
	then echo "$x.html matches"
	else echo "$x.html doesn't match!"
	fi
	if $script json $x | $diff "json/peaks/$x.json" - >/dev/null
	then echo "$x.json matches"
	else echo "$x.json doesn't match"
	fi
	if $script check $x | $diff "data/check/$x.out" - >/dev/null
	then echo "$x check matches"
	else echo "$x check doesn't match"
	fi
done
