"""
アルゴリズムの概要
このスクリプトは、日本のYahoo!ファイナンスの「年初来高値ランキング」ページから株式データを取得し、指定されたデータ項目（名称、証券コード、取引値など）をCSVファイル形式で保存します。
複数ページにわたる株式データを取得するため、ページごとにHTTPリクエストを送信。
各ページのHTMLを解析して、必要なデータを抽出。
データを整形し、CSVファイルに保存。
サーバーへの負荷軽減のため、各ページの取得間に待機時間を挿入。
使用ライブラリの選択理由
BeautifulSoup:
理由: HTMLパースとデータ抽出が簡単に行える軽量なライブラリ。
他の選択肢: Scrapyなどの高度なスクレイピングライブラリ。ただし、Scrapyはセットアップが複雑で、必要以上に機能が多いため採用せず。
requests:
理由: HTTPリクエストを簡潔に扱うことができ、BeautifulSoupとの組み合わせが効率的。
他の選択肢: httpxなどの非同期リクエストライブラリも検討。しかし、このスクリプトでは非同期処理が必須ではないためrequestsを採用。
csv:
理由: Python標準ライブラリであり、追加インストールが不要。
他の選択肢: pandasの使用も検討。pandasはデータフレーム操作に強力ですが、このスクリプトでは簡単なCSV出力のみのためcsvモジュールを選択。
正規表現（re）:
理由: HTMLタグ内の日付などの特定パターンを抽出するために簡潔。
他の選択肢: BeautifulSoupのみで抽出を試みましたが、特定条件のデータ取得が困難だったため正規表現を併用。
"""
import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
import time

def get_stock_data(page=1):
    """
    指定されたYahoo! Financeのページから株式データを取得します。

    Args:
        page (int): 取得するページ番号（デフォルトは1ページ目）。

    Returns:
        list: 取得した株式データのリスト。各要素はリスト形式で
              [名称, 証券コード, 取引値, 前営業日までの年初来高値, 日付, 高値]。
    """
    # リクエストするURLを作成
    url = f"https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily&page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # HTTPリクエストを送信
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # HTTPエラーが発生した場合は例外を発生
    except requests.exceptions.RequestException as e:
        print(f"Error accessing URL {url}: {e}")
        return []
    
    # HTMLレスポンスを解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # 株式データを含む行を選択
    rows = soup.select('tr.RankingTable__row__1Gwp')

    if not rows:
        return []  # データが存在しない場合は空リストを返す

    stock_data = []  # 結果を格納するリスト

    for row in rows:
        try:
            # 名称とコードを取得
            name_element = row.select_one('a')  # 名称のリンクを取得
            name = name_element.text.strip() if name_element else "N/A"  # 名称が存在しない場合は"N/A"
            code_element = row.select_one('li.RankingTable__supplement__vv_m')  # 証券コードを取得
            code = code_element.text.strip() if code_element else "N/A"

            # 数値データを取得
            values = row.select('span.StyledNumber__value__3rXW')  # 株価や高値などの値を含む要素
            current_price = values[0].text.strip().replace(',', '') if len(values) > 0 else "N/A"  # 取引値
            ytd_high = values[1].text.strip().replace(',', '') if len(values) > 1 else "N/A"  # 年初来高値

            # 日付データを正規表現で抽出
            date_pattern = re.compile(r'(\d{4}/\d{2}/\d{2})')  # YYYY/MM/DD形式を検索するパターン
            date_match = date_pattern.search(str(row))
            ytd_high_date = date_match.group(1) if date_match else "N/A"  # 日付が存在しない場合は"N/A"

            # 高値を取得
            high_price = values[-1].text.strip().replace(',', '') if len(values) > 2 else "N/A"

            # データをリストにまとめて結果リストに追加
            stock_data.append([name, code, current_price, ytd_high, ytd_high_date, high_price])
        except Exception as e:
            print(f"Error parsing row: {e}")  # 行解析中のエラーを出力
            continue  # エラーが発生しても次の行を処理する

    return stock_data

def main():
    """
    全ページの株式データを取得し、CSVファイルに保存します。
    """
    all_stock_data = []  # 全データを格納するリスト
    page = 1  # 最初のページ番号

    while True:
        print(f"Scraping page {page}...")  # 現在の処理ページを出力
        stock_data = get_stock_data(page)  # データを取得

        if not stock_data:  # データが取得できなかった場合、終了
            break

        all_stock_data.extend(stock_data)  # 現在のページのデータを全データに追加
        page += 1  # 次のページ番号へ

        time.sleep(1)  # サーバーへの負荷を軽減するため1秒待機

    # 現在の日付を取得してファイル名に使用
    today = datetime.now().strftime("%Y%m%d")
    filename = f"{today}.csv"

    try:
        # CSVファイルに書き込み
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['名称', 'コード', '取引値', '前営業日までの年初来高値', '前営業日までの年初来高値の日付', '高値'])  # ヘッダー行を追加
            writer.writerows(all_stock_data)  # データを書き込み
        print(f"データを {filename} に保存しました。合計 {len(all_stock_data)} 件のデータを取得しました。")
    except Exception as e:
        print(f"Error writing to CSV file: {e}")  # 書き込みエラーを出力

if __name__ == "__main__":
    main()  # メイン関数を実行
