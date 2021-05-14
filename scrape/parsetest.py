import getyahoostock
import json
import re

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
