#!/bin/sh
#https://stooq.com/q/d/l/?s=6758.jp&i=d
codefile=stocklist.csv
codefile=codefile
while IFS= read -r code
do
  of=stooqdata/$code.csv
  if [ -e $of ]; then
    continue
  fi
  redo=1
  while [ $redo -eq 1 ] 
  do 
    wget -O stooqdata/$code.csv 'https://stooq.com/q/d/l/?s='$code'.jp&i=d'
    if [ $? -ne 0 ]; then
      echo some error
      sleep 86400
    elif grep 'Exceeded the daily hits limit' $of ; then
      echo $code exceeded
      sleep 86400
    else
      redo=0
    fi
  done
  sleep 10
done < "$codefile"
