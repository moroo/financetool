#!/usr/bin/python3
"""
http://kabusapo.com/dl-file/dl-stocklist.php
https://stooq.com/q/d/l/?s=6758.jp&i=d
"""
import urllib.parse
import urllib.request
import io
import re
import codecs
import csv
import os
import time
import sys

requestcount = 0

def send(code):
    """send query to yahoo api"""
    global requestcount
    url = getcodeurl(code)
    try:
        response = urllib.request.urlopen(url)
    except urllib.error.HTTPError:
        print("Request count %d" % requestcount)
        return -1
    print(response)
    data = response.read()
    requestcount += 1
    return data

def getcodeurl(code):
    """
    market="T"
    sy=2018
    sm=1
    sd=1
    ey=2020
    em=5
    ed=1
    """
    url="https://stooq.com/q/d/l/?s=%s.jp&i=d" % code
    return url

def getcodedata(code):
    url=getcodeurl(code)
    print(url)
    data= send(url)
    
def getstock(codefile="stocklist.csv"):
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
                stockfilename = os.path.join("stooqdata","%d.csv" % code)
                if os.path.exists(stockfilename):
                    continue
                data=getcodedata(code)
                print(code)
                print(data)
                sys.exit(1)
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
