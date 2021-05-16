import getyahoostock
import json
import re
import argparse

def test1():
    fp=open("/home/jun/stock/stsample.html","r")
    #fp=open("/home/jun/stock/st.wind.json","r")
    pat=re.compile('window.__PRELOADED_STATE__ = ')
    #pat=re.compile('"mainStocksHistory":[^[]*"histories":(\[[^]*\])')
    #pat=re.compile('mainStocksHistory.*')
    for line in fp:
        t=pat.search(line)
        if t:
            ep=t.end()
            print(t.end())
            break
    jdata=line[ep:]
    j=json.loads(jdata)
    #print(j['mainStocksHistory']['history']["histories"])
    for datedata in j['mainStocksHistory']['history']["histories"]:
        print(datedata)
        #print(t)
        #print(t.groups())
    #args=1
    #getyahoostock.dataparse(data,args)

if __name__=="__main__":
    ap = argparse.ArgumentParser(description="Conjuction yahoo stock.\n create retrycode file to reget")
    ap.add_argument("-v","--verbose",help="vorbose",action="count", default=0)
    args=ap.parse_args()
    code=6702
    market="T"
    sy=2010
    sm=1
    sd=1
    ey=2010
    em=2
    ed=1
    args.verbose=1
    data=getyahoostock.getcodedataperiod(code,market,sy,sm,sd,ey,em,ed,args)
