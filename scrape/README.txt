Yahoo株価取得方法

1) 現在のdataをdata-日付(以下dir1)に変更
2) script/getyahoostock.sh dir1

デフォルトデータ
stocklist.csv 取得株価コードデータ
形式
銘柄コード,銘柄名,市場名,業種分類,単元株数,日経225採用銘柄
1301,(株)極洋,東証1部,水産・農林業,100,

pythonの場合
1) 現在のdataをdata-日付(以下dir1)に変更
  最新の日付を取得(20201113など) 以下date1
2) python3 script/getyahoostock.py -s date1 -e 20201130 20201130は昨日の日付を実行
4) python3 script/joinyahoostock.py dir1 data xd を実行
5) mv data dir2
6) wc retrycode > 0なら
  3) 以下を実行


コード一覧一括取得
https://stockdatacenter.com/stockdata/companylist.csv

usage: getyahoostock.py [-h] [-v] [-c CODEFILE] [-s STARTDATE] [-e ENDDATE]

Conjuction yahoo stock. create retrycode file to reget

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         vorbose
  -c CODEFILE, --codefile CODEFILE
                        get stock code list file default:stocklist.csv
  -s STARTDATE, --startdate STARTDATE
                        get stock from date default:20100101
  -e ENDDATE, --enddate ENDDATE
                        get stock to date default:20201113
