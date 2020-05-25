#!/bin/bash

function zipall {
	local br="/usr/local/bin/brotli --best --keep"
	local gz="/usr/local/bin/zopfli"

	local infile insize oldsize newsize maxlen prefix
	local arg do_info=0 do_html=0 do_json=0 rezip=0 info_calc=0

	for arg in $*
	do
		if test "$arg" == info; then do_info=1
		elif test "$arg" == html; then do_html=1
		elif test "$arg" == json; then do_json=1
		elif test "$arg" == rezip; then rezip=1
		elif test "$arg" == gzip; then gz="/usr/bin/gzip --best --keep --no-name"
		elif [[ "$arg" == infocalc=[01234] ]]; then info_calc=${arg:9}
		fi
	done

function print_info {
	local percent

	printf "%${maxlen}s: %8u | " $infile $insize

	if test -z "$newsize"
	then
		echo "$1 doesn't exist"
		return

	elif test $info_calc == 0
	then
		percent=$((1000000 * newsize / insize))
		printf -v percent "%u.%04u" $((percent / 10000)) $((percent % 10000))

	elif test $info_calc == 1
	then
		percent=$(((100000 * newsize / insize + 5) / 10))
		printf -v percent "%u.%02u" $((percent / 100)) $((percent % 100))

	elif test $info_calc == 2; then percent=$(echo "6 k 100 $newsize * $insize / p" | /usr/bin/dc)

	elif test $info_calc == 3; then percent=$(/usr/bin/dc -e "6 k 100 $newsize * $insize / p")

	elif test $info_calc == 4; then percent=$(echo "scale=6; 100 * $newsize / $insize" | /usr/bin/bc -l)
	fi

	printf "$1: %7u = %5.2f%%" $newsize $percent
	if test "$oldsize"
	then
		printf " (%+d)" $((newsize - oldsize))
	fi
	printf "\n"
}
function process {
	local -r x=$1
	local -r command="${!x}"
	local -r outfile="$prefix$infile.$x"

	if test -f $outfile
	then oldsize=`/usr/bin/stat -f "%z" $outfile`
	else oldsize=""
	fi

	if ((do_info))
	then
		newsize="$oldsize"
		oldsize=""
		print_info $x

	elif test $infile -nt $outfile -o $rezip == 1
	then
		echo $command $infile
		$command $infile
		/bin/mv "$infile.$x" $outfile
		newsize=`/usr/bin/stat -f "%z" $outfile`
		print_info $x
	fi
}
function ziphtml {
	local peaklist

	maxlen=10
	prefix=zipped/

	for peaklist in dps sps hps ogul lpc gbp npc odp osp ocap owp
	do
		infile="$peaklist.html"
		insize=`/usr/bin/stat -f "%z" $infile`

		process br
		process gz
	done
}
function zipjson {

	maxlen=18
	prefix=""

	for infile in \
		blm/ca/{aa,nm,w,wsa,wsar}.json \
		nps/*.json \
		peaks/*.json \
		pmap/*.json
	do
		insize=`/usr/bin/stat -f "%z" $infile`

		process br
		process gz
	done
}
	test $do_html == 1 -o $do_json == 0 && ziphtml
	test $do_json == 1 && { cd json; zipjson; cd ..; }
}
zipall $*
unset zipall print_info process ziphtml zipjson
