#!/usr/bin/python3
"""
https://qiita.com/cupnoodlegirl/items/e20f353b5c369de1f5ed
https://info.finance.yahoo.co.jp/history/?code=1301.T&sy=1983&sm=4&sd=24&ey=2020&em=5&ed=24&tm=d
https://info.finance.yahoo.co.jp/history/?code=1301.T&sy=1983&sm=4&sd=24&ey=2020&em=5&ed=24&tm=d&p=2
http://kabusapo.com/dl-file/dl-stocklist.php
"""
import urllib.parse
import urllib.request
import io
import re
import codecs
import csv
import os
import time

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


def getstock(codefile="retrycode"):
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

    with codecs.open(codefile,encoding='utf-8') as cfp:
        reader = csv.reader(cfp)
        for line in reader:
            if line[2] in marketdict:
                code=int(line[0])
                market=marketdict[line[2]]
                stockfilename = os.path.join("data","%d.csv" % code)
                if os.path.exists(stockfilename):
                    continue
                data=getcodedataperiod(code,market,2010,1,4,2020,9,18)
                if data:
                    with open(stockfilename,"w") as wfp:
                        writer=csv.writer(wfp)
                        writer.writerows(data)
                        wfp.close()
                        print(code)
                        time.sleep(1)
        cfp.close()

if __name__ == '__main__':
    getstock()
