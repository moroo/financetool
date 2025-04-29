"""
Yahoo!ファイナンス年初来高値データ収集スクリプト

アルゴリズム概要:
1. ページネーションを処理しながら全データ取得
2. HTML解析で必要なデータを抽出
3. クリーニングしたデータをCSVに保存

ライブラリ選択理由:
- BeautifulSoup: HTML解析の定番ライブラリで学習リソースが豊富
- requests: 軽量でシンプルなHTTP通信ライブラリ
- csv: 標準ライブラリのみでCSV生成可能なため選択

不使用ライブラリ理由:
- Selenium: 静的ページなら不要なオーバーヘッドを回避
- pandas: 小規模データ処理では不要な依存関係を削減
- Scrapy: シンプルな収集タスクでは過剰な機能
"""

import requests  # ウェブページ取得用
from bs4 import BeautifulSoup  # HTML解析用
import csv  # CSVファイル操作用
from datetime import datetime  # 日付処理用

def fetch_page(page):
    """
    指定ページのHTMLを取得してBeautifulSoupオブジェクトを返す
    
    Args:
        page (int): 取得するページ番号
    
    Returns:
        BeautifulSoup: 解析済みHTMLオブジェクト
    """
    # URLの動的生成（ページ番号をパラメータに追加）
    url = f'https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily&page={page}'
    
    # ウェブページの取得（GETリクエスト送信）
    response = requests.get(url)
    
    # 取得したHTMLをBeautifulSoupで解析
    return BeautifulSoup(response.text, 'html.parser')

def parse_row(row):
    """
    テーブルの行から必要なデータを抽出する
    
    Args:
        row (bs4.element.Tag): HTMLのtr要素
    
    Returns:
        list: [名称, コード, 取引値, 前営業日高値, 高値日付, 高値]
    """
    # 企業名抽出（aタグのテキストを取得）
    name = row.find('a').text.strip()  # strip()で余白除去
    
    # 証券コード抽出（li要素から取得）
    code = row.find('li', class_='RankingTable__supplement__vv_m').text.strip()
    
    # 数値データ一括取得（span要素をすべて取得）
    numbers = row.find_all('span', class_='StyledNumber__value__3rXW')
    
    # データ位置のインデックス指定（HTML構造に依存）
    # 注意: サイトのHTML変更時に要修正
    trade_value = numbers[0].text.replace(',', '')  # 取引値（カンマ除去）
    prev_high = numbers[1].text.replace(',', '')    # 前営業日高値
    prev_date = numbers[2].text                     # 高値日付（年を含む）
    high = numbers[3].text.replace(',', '')         # 現在の高値
    
    return [name, code, trade_value, prev_high, prev_date, high]

def main():
    """メイン処理: データ収集からCSV保存までの一連の流れを制御"""
    # 当日日付をYYYYMMDD形式で取得（ファイル名用）
    today = datetime.now().strftime('%Y%m%d')
    
    # CSVファイルを書き込みモードで開く（UTF-8エンコーディング指定）
    with open(f'{today}.csv', 'w', newline='', encoding='utf-8') as f:
        # CSVライターオブジェクト作成
        writer = csv.writer(f)
        
        # ヘッダー行書き込み
        writer.writerow(['名称', 'コード', '取引値', '前営業日高値', '高値日付', '高値'])
        
        page = 1  # ページカウンタ初期化
        
        # 無限ループ（データがなくなるまで処理続行）
        while True:
            # 現在のページを取得
            soup = fetch_page(page)
            
            # テーブル行データをCSSセレクタで取得
            rows = soup.select('tr.RankingTable__row__1Gwp')
            
            # データが存在しなくなったらループ脱出
            if not rows:
                break
            
            # 各行ごとにデータ処理
            for row in rows:
                # データ解析とCSV書き込み
                writer.writerow(parse_row(row))
            
            page += 1  # 次のページへ

if __name__ == '__main__':
    # スクリプト直接実行時のみmain()を呼び出し
    main()
