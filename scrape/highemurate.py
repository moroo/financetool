#!/usr//bin/python3
import highvalue
import sys

class stocksimulate:
  def __init__(self):
    datasource=highvalue.stooqstock
    #datasource=highvalue.yahoostock
    self.datainstance = datasource()

  def load(self,code):
    self.datainstance.readdata(code)
    self.datainstance.addmaxvalue()
    self.datainstance.data.sort()
    
def test1():
  t = stocksimulate()
  t.load(int(sys.argv[1]))
  print(t.datainstance.data)

if __name__ == "__main__":
  test1()

