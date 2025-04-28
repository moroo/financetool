import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
import time

def get_stock_data(page=1):
    """
    指定されたYahoo! Financeのページから株式データを取得。
    """
    url = f"https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily&page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # HTTPエラーが発生した場合に例外をスロー
    except requests.exceptions.RequestException as e:
        print(f"Error accessing URL {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.select('tr.RankingTable__row__1Gwp')

    if not rows:
        return []

    stock_data = []

    for row in rows:
        try:
            # 名称の取得
            name_element = row.select_one('a')
            name = name_element.text.strip() if name_element else "N/A"

            # コードの取得
            code_element = row.select_one('li.RankingTable__supplement__vv_m')
            code = code_element.text.strip() if code_element else "N/A"

            # 数値データの取得（取引値、年初来高値、高値）
            values = row.select('span.StyledNumber__value__3rXW')
            current_price = values[0].text.strip().replace(',', '') if len(values) > 0 else "N/A"
            ytd_high = values[1].text.strip().replace(',', '') if len(values) > 1 else "N/A"

            # 日付の抽出（正規表現で解析）
            date_pattern = re.compile(r'(\d{4}/\d{2}/\d{2})')
            date_match = date_pattern.search(str(row))
            ytd_high_date = date_match.group(1) if date_match else "N/A"

            # 高値の抽出
            high_price = values[-1].text.strip().replace(',', '') if len(values) > 2 else "N/A"

            stock_data.append([name, code, current_price, ytd_high, ytd_high_date, high_price])
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue

    return stock_data

def main():
    """
    株式データを取得し、CSVファイルに保存する。
    """
    all_stock_data = []
    page = 1

    while True:
        print(f"Scraping page {page}...")
        stock_data = get_stock_data(page)

        if not stock_data:
            break  # データがない場合、ループ終了

        all_stock_data.extend(stock_data)
        page += 1

        # サーバーへの負荷軽減
        time.sleep(1)

    # 現在の日付をファイル名に使用
    today = datetime.now().strftime("%Y%m%d")
    filename = f"{today}.csv"

    # CSVファイルに書き込み
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['名称', 'コード', '取引値', '前営業日までの年初来高値', '前営業日までの年初来高値の日付', '高値'])
            writer.writerows(all_stock_data)
        print(f"データを {filename} に保存しました。合計 {len(all_stock_data)} 件のデータを取得しました。")
    except Exception as e:
        print(f"Error writing to CSV file: {e}")

if __name__ == "__main__":
    main()
