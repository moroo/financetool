#!/usr/bin/python3
import sys
import os
import csv
import argparse
import codecs
import datetime

def counttime(args):
    st=int(args.startdate)
    et=int(args.enddate)

    maxcount=[0] * (et-st + 1)
    mincount=[0] * (et-st + 1)

    with codecs.open(args.codefile,encoding='utf-8') as cfp:
        cfpreader = csv.reader(cfp)
        cfpreader.__next__()
        c=0
        for line in cfpreader:
            #if c > 10:
            #    break
            c += 1
            code=int(line[0])
            stockfilename = os.path.join(args.datadir,"%d.csv" % code)
            if os.path.exists(stockfilename):
                with open(stockfilename,"r") as sfp:
                    stockreader=csv.reader(sfp)
                    maxd=[0,0]
                    mind=[0,1e99]
                    for sdata in stockreader:
                        d=int(sdata[0]) * 10000 + int(sdata[1]) * 100 + int(sdata[2])
                        if st <= d <= et:
                            v=float(sdata[8])
                            if maxd[1] < v:
                                maxd=[d,v]
                            if mind[1] > v:
                                mind=[d,v]
                    maxcount[maxd[0] - st] += 1
                    mincount[mind[0] - st] += 1
    for d in range(et-st):
        t=d+st
        month=int(t % 10000) // 100
        day=int(t % 100)
        if day == 0:
            continue
        if month == 2 and day > 29:
            continue
        if month in (1,3,5,7,8,10,12) and day > 31:
            continue
        if month in (4,6,9,11) and day > 30:
            continue
        print(d+st,mincount[d],maxcount[d])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Conjuction yahoo stock.\n create retrycode file to reget")
    ap.add_argument("-v","--verbose",help="vorbose",action="count", default=0)
    ap.add_argument("-c","--codefile",help="get stock code list file default:%(default)s",default="stocklist.csv")
    ap.add_argument("-d","--datadir",help="data dir default:%(default)s",default="data")
    ap.add_argument("-s","--startdate",help="from date default:%(default)s",default="20100101")
    ap.add_argument("-e","--enddate",help="to date default:%(default)s",default="20201113")
    args=ap.parse_args()
    if args.verbose > 0:
        print(args)
    counttime(args)
