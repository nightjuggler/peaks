#!/bin/bash

function print_stats {
	newsize=`/usr/bin/stat -f "%z" $outfile`
#
#	1a. Shell arithmetic evaluation
#
#	ratio=$(((100000 * newsize / htmlsize + 5) / 10))
#	printf -v ratio "%u.%02u" $((ratio / 100)) $((ratio % 100))
#
#	1b. Shell arithmetic evaluation
#
	ratio=$((1000000 * newsize / htmlsize))
	printf -v ratio "%u.%04u" $((ratio / 10000)) $((ratio % 10000))
#
#	2a. Using dc
#
#	ratio=`echo "6 k 100 $newsize * $htmlsize / p" | /usr/bin/dc`
#
#	2b. Using dc
#
#	ratio=`/usr/bin/dc -e "6 k 100 $newsize * $htmlsize / p"`
#
#	3. Using bc
#
#	ratio=`echo "scale=6; 100 * $newsize / $htmlsize" | /usr/bin/bc -l`
#
	format="%4s.html: %6u old_$1: %5u $1: %5u $1/html: %5.2f%%\\n"
	printf "$format" $peaklist $htmlsize $oldsize $newsize $ratio
}
function process {
	x=$1
	command="$2"
	outfile="zipped/$infile.$x"

	if test -f $outfile
	then oldsize=`/usr/bin/stat -f "%z" $outfile`
	else oldsize=0
	fi

	if test "$stats"
	then print_stats $x
	elif test $infile -nt $outfile
	then
		echo $command $infile
		$command $infile
		/bin/mv "$infile.$x" $outfile
		print_stats $x
	fi
}

if test "$1" == stats
then stats=1
else stats=""
fi

for peaklist in dps sps gbp hps lpc npc ogul odp osp ocap owp
do
	infile="$peaklist.html"
	htmlsize=`/usr/bin/stat -f "%z" $infile`

	process br "/usr/local/bin/brotli --best --keep"
#	process gz "/usr/bin/gzip --best --keep --no-name"
	process gz /usr/local/bin/zopfli
done
