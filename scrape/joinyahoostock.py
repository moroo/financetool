#!/usr/bin/python3
"""
https://qiita.com/cupnoodlegirl/items/e20f353b5c369de1f5ed
https://info.finance.yahoo.co.jp/history/?code=1301.T&sy=1983&sm=4&sd=24&ey=2020&em=5&ed=24&tm=d
https://info.finance.yahoo.co.jp/history/?code=1301.T&sy=1983&sm=4&sd=24&ey=2020&em=5&ed=24&tm=d&p=2
http://kabusapo.com/dl-file/dl-stocklist.php
"""
import urllib.parse
import urllib.request
import sys
import io
import re
import codecs
import csv
import os
import time
import argparse

requestcount = 0

def getpricedata(code,market,sy,sm,sd,ey,em,ed,p):
    global requestcount
    #datare="<td>2020年4月8日</td><td>2,556</td><td>2,631</td><td>2,532</td><td>2,597</td><td>40,500</td><td>2,597</td>"
    datare=re.compile("<td>(\d+)年(\d+)月(\d+)日</td><td>([0-9,.]+)</td><td>([0-9,.]+)</td><td>([0-9,.]+)</td><td>([0-9,.]+)</td><td>([0-9,]+)</td><td>([0-9,.]+)</td>")
    sdata=[]
    tryrepeat = 1
    while tryrepeat == 1:
        data=send(code,market,sy,sm,sd,ey,em,ed,p)
        if data != -1:
            tryrepat = 0
            break
        time.sleep(60*60*24)
        requestcount = 0
    vdata=data.split("\n")
    divkey="stocksHistoryPageing"
    for i in range(len(vdata)):
        if vdata[i].find(divkey) >= 0:
            break
    while i < len(vdata):
        if vdata[i].find("<td>") >= 0:
            break
        i += 1
    if i < len(vdata):
        ddata=vdata[i].split("</tr><tr>")
        for d in ddata:
            t=datare.search(d)
            if t:
                vl=[ int(t.group(1)), int(t.group(2)), int(t.group(3)),
                     float(t.group(4).replace(",","")),
                     float(t.group(5).replace(",","")),
                     float(t.group(6).replace(",","")),
                     float(t.group(7).replace(",","")),
                     int(t.group(8).replace(",","")),
                     float(t.group(9).replace(",","")) ]
                sdata.append(vl)
    return sdata
   
def send(code,market,sy,sm,sd,ey,em,ed,p):
    """send query to yahoo api"""
    global requestcount
    url = getcodeurl(code,market,sy,sm,sd,ey,em,ed,p)
    try:
        response = urllib.request.urlopen(url)
    except urllib.error.HTTPError:
        print("Request count %d" % requestcount)
        return -1
    data = response.read().decode('utf-8')
    requestcount += 1
    return data

def getcodeurl(code,market,sy,sm,sd,ey,em,ed,p):
    """
    market="T"
    sy=2018
    sm=1
    sd=1
    ey=2020
    em=5
    ed=1
    """
    url="https://info.finance.yahoo.co.jp/history/?code=%4.4d.%s&sy=%d&sm=%d&sd=%d&ey=%d&em=%d&ed=%d&tm=d&p=%d" % (code,market,sy,sm,sd,ey,em,ed,p)
    return url

def getcodedataperiod(code,market,sy,sm,sd,ey,em,ed):
    p=1
    stockdata=[]
    while p < 500:
        data = getpricedata(code,market,sy,sm,sd,ey,em,ed,p)
        if not data:
            break
        stockdata += data
        p += 1
    return(stockdata)


def joinstock(src1dir,src2dir,destdir,codefile="stocklist.csv"):
    marketdict={
        "東証1部":"T",
        "マザーズ":"T",
        "札証":"S",
        "札幌ア":"S",
        "東証":"T",
        "東証1部":"T",
        "東証2部":"T",
        "東証JQG":"T",
        "東証JQS":"T",
        "東証外国":"T",
        "福岡Q":"F",
        "福証":"F",
        "名古屋セ":"N",
        "名証1部":"N",
        "名証2部":"N",
        }

    if not os.path.exists(src1dir):
        sys.stderr.write("%s doesn't exists\n" % src1dir)
        return
    
    if not os.path.exists(src2dir):
        sys.stderr.write("%s doesn't exists\n" % src2dir)
        return

    if not os.path.exists(destdir):
        os.mkdir(destdir)

    with codecs.open(codefile,encoding='utf-8') as cfp:
        retrycodefp=open("retrycode","w")
        retrycodewriter=csv.writer(retrycodefp)
        reader = csv.reader(cfp)
        for line in reader:
            if line[2] in marketdict:
                code=int(line[0])
                market=marketdict[line[2]]
                stock1filename = os.path.join(src1dir,"%d.csv" % code)
                stock2filename = os.path.join(src2dir,"%d.csv" % code)
                stockfilename = os.path.join(destdir,"%d.csv" % code)
                data1=[]
                if not os.path.exists(stock1filename):
                    continue
                with open(stock1filename) as sfp1:
                    reader=csv.reader(sfp1)
                    for d in reader:
                        data1.append(d)
                    sfp1.close()
                if not data1:
                    continue
                data2=[]
                if not os.path.exists(stock2filename):
                    continue
                with open(stock2filename) as sfp2:
                    reader=csv.reader(sfp2)
                    for d in reader:
                        data2.append(d)
                    sfp2.close()
                if not data2:
                    continue
                if data1[0][0:3] == data2[-1][0:3]:
                    if data1[0][3:] != data2[-1][3:]:
                        #Retry code
                        retrycodewriter.writerow(line)
                        continue
                    else:
                        data2.pop()
                
                with open(stockfilename,"w") as wfp:
                    writer=csv.writer(wfp)
                    writer.writerows(data2)
                    writer.writerows(data1)
                    wfp.close()
                    print(code)
        cfp.close()
        retrycodefp.close()

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Conjuction yahoo stock.\n create retrycode file to reget")
    ap.add_argument("-v","--verbose",help="vorbose",action="count", default=0)
    ap.add_argument("srcpre",help="Source directory previous got")
    ap.add_argument("srcpost",help="Source directory post got")
    ap.add_argument("dest",help="Destination directory")
    args=ap.parse_args()
    if args.verbose > 0:
        print(args)
    joinstock(args.srcpre,args.srcpost,args.dest)
    #joinstock(args.srcpre,sys.argv[2],sys.argv[3])
