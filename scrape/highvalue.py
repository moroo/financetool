import os
import datetime
import csv
import sys
import copy

class highvalue:
  def __init__(self):
    self.span=7*52
    pass

  def readdata(self,code):
    self.rawdata=[]
    with open(os.path.join(self.datapath,"%d.csv" % code)) as cfp:
      reader = csv.reader(cfp)
      for d in reader:
        ad=self.convertcsvline(d)
        if ad:
          self.rawdata.append(ad)
      cfp.close()
    self.sortdata()

  def sortdata(self):
    pass

  def convertcsvline(self,d):
    return d

  def addmaxvalue(self):
    """Add max value in span maxspan"""
    maxspan=datetime.timedelta(self.span)
    maxlist=[]
    self.data=copy.deepcopy(self.rawdata)
    i=len(self.data)
    startdate=self.data[-1][0]
    maxlist.append((self.data[-1][2],startdate))
  
    for i in range(len(self.data)-1,0,-1):
      dt=self.data[i][0]
      maxlist.append((self.data[i][2],dt))
      self.data[i].append(-1)
      if dt - startdate > maxspan:
        break

    maxlist.sort(reverse=True)
    #At this point maxlist contains maxspan maxvalue
    #for pp in maxlist:
    #  print(pp)
    #print(maxlist)
    #sys.exit(1)
    i -= 1
    while i >= 0:
      dt=self.data[i][0]
      self.data[i].append(maxlist[0][0])
      maxlist.append((self.data[i][2],dt))
      maxlist.sort(reverse=True)
      lt = dt - maxspan
      for j in range(len(maxlist)):
        if maxlist[j][1] >= lt:
          break
      if j > 0:
        maxlist[:j] = []
      
      i -= 1
  
  def addmaxvaluecode(self,code):
    with open(os.path.join("/home/jun/stock/data","%d.csv" % code),"r") as cfp:
      data=[]
      reader = csv.reader(cfp)
      for d in reader:
        data.append([
          int(d[0]),int(d[1]),int(d[2]),
          float(d[3]), float(d[4]), float(d[5]), float(d[6]),
          int(d[7])])
      cfp.close()
      addmaxvalue(data)

  def finddateforward(self,startdate):
    for i,n in enumerate(self.data):
      if n[0] >= startdate:
        break
    return i
 
  def finddatebackward(self,startdate):
    i=len(self.data) - 1
    while i >= 0:
      if self.data[i][0] <= startdate:
        break
      i = i - 1
    return i

  def csvwrite(self,filename):
    with open(filename,"w") as fp:
      writer = csv.writer(fp)
      writer.writerows(self.data)
      fp.close()
 
class yahoostock(highvalue):
  def __init__(self):
    highvalue.__init__(self)
    self.datapath="/home/jun/stock/data"

  def convertcsvline(self,d):
    dt = datetime.date(int(d[0]),int(d[1]),int(d[2]))
    r = float(d[8]) / float(d[6])
    return [
      dt,
      float(d[3])*r, float(d[4])*r, float(d[5])*r, float(d[6])*r,
      int(d[7])/r]

class stooqstock(highvalue):
  def __init__(self):
    highvalue.__init__(self)
    self.datapath="/home/jun/stock/stooqdata"

  def convertcsvline(self,d):
    if d[0] == "Date":
      return None
    dd=d[0].split("-")
    dt = datetime.date(int(dd[0]),int(dd[1]),int(dd[2]))
    return [
      dt,
      float(d[1]), float(d[2]), float(d[3]), float(d[4]),
      int(d[5])]

  def sortdata(self):
    self.rawdata.reverse()

def buynextopensellnextweekopen(data):
  keepposition=0
  keepspan=datetime.timedelta(7)
  buynextday=0
  for d in data:
    if d[6] == -1:
      continue
    if not keepposition:
      if d[6] < d[2]:
        buynextday = 1
        continue
      if buynextday == 1:
        buyprice=d[1]
        buyday=d[0]
        keepposition = 1
        buynextday=0
        continue
    else:
      if d[0] - buyday < keepspan:
        continue
      else:
        sellprice = d[1]
        print(buyday,buyprice,sellprice)
        keepposition=0

def commonrange(y,s):
  if y.rawdata[0][0] > s.rawdata[0][0]:
    enddate=s.rawdata[0][0]
  else:
    enddate=y.rawdata[0][0]
  if y.rawdata[-1][0] > s.rawdata[-1][0]:
    startdate=y.rawdata[-1][0]
  else:
    startdate=s.rawdata[-1][0]
  print(startdate,y.rawdata[-1][0],s.rawdata[-1][0])
  print(enddate,y.rawdata[0][0],s.rawdata[0][0])
  ys=y.finddateforward(startdate)
  ye=y.finddatebackward(enddate)
  ss=s.finddateforward(startdate)
  se=s.finddatebackward(enddate)
  print(ys,ye)
  print(ss,se)
  print(y.rawdata[ys])
  print(s.rawdata[ss])
  print(y.rawdata[ye])
  print(s.rawdata[se])
  print(y.data[ys])
  print(s.data[ss])
  print(y.data[ye])
  print(s.data[se])

if __name__ == "__main__":
  datasource=stooqstock
  #datasource=yahoostock
  datainstance = datasource()
  datainstance.readdata(int(sys.argv[1]))
  datainstance.addmaxvalue()
  datainstance.data.sort()
  datainstance.csvwrite("xaddmaxs%s.csv" % sys.argv[1])
    
  #buynextopensellnextweekopen(y.data)
