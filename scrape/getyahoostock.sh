#!/bin/zsh
mergestock ()
{
	if [ -z $dryrun ]; then
		python3 script/joinyahoostock.py $1 $2 $3
	else
		echo python3 script/joinyahoostock.py $1 $2 $3
	fi
}

#dryrun=1
untildatefile="/home/jun/stock/untildate"
lastdatefile="/home/jun/stock/lastdate"
stockdatadir="/home/jun/stock/data"
tmpstockdatadir="/home/jun/stock/xd"
continuefile="/home/jun/stock/continue"
retrycodefile="/home/jun/stock/retrycode"

if [ $# -ne 1 ]; then
	echo "Usage:$0 laststockdir"
	exit 1
fi

laststockdir=$1

if [ ! -e $lastdatefile ]; then
	echo $lastdatefile not found
	exit 1
fi

if [ ! -d $laststockdir ]; then
	echo $laststockdir not found
	exit 1
fi

if [ ! -e $continuefile -a -d $stockdatadir ]; then
	echo $stockdatadir exists
	exit
fi

if [ ! -e $untildatefile ]; then
	date +%Y%m%d > $untildatefile
fi

lastdate=`cat $lastdatefile`
untildate=`cat $untildatefile`

if [ ! -e $stockdatadir ]; then
	mkdir $stockdatadir
fi

#First step
echo First step $lastdate to $untildate
if [ -z $dryrun ]; then
	python3 script/getyahoostock.py -s $lastdate -e $untildate
else
	echo python3 script/getyahoostock.py -s $lastdate -e $untildate
fi

#contine step
if [ -e $tmpstockdatadir ]; then
	rm -rf $tmpstockdatadir
fi
mkdir $tmpstockdatadir

mergestock $laststockdir $stockdatadir $tmpstockdatadir
if [ -e $tmpstockdatadir ]; then
	mv $stockdatadir $stockdatadir.$$
	mv $tmpstockdatadir $stockdatadir
fi

retrycode=0
if [ -e $retrycodefile ]; then
	retrycode=`wc -l $retrycodefile | awk '{print $1}'`
fi

if [ $retrycode -gt 0 ]; then
	if [ -z $dryrun ]; then
		python3 script/getyahoostock.py -e $untildate
	else
		echo python3 script/getyahoostock.py -e $untildate
	fi
fi
