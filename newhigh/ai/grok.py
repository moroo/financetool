import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ベースURL
BASE_URL = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"

# ヘッダー（ユーザーエージェントを指定してブロック回避）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_page(page_num):
    """指定されたページ番号のHTMLを取得"""
    url = f"{BASE_URL}&page={page_num}" if page_num > 1 else BASE_URL
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"ページ {page_num} の取得に失敗: {e}")
        return None

def parse_page(html):
    """HTMLからデータを抽出"""
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select('tbody tr.RankingTable__row__1Gwp')
    data = []

    for row in rows:
        try:
            # 名称とコード
            name_elem = row.select_one('td.RankingTable__detail__P452 a')
            name = name_elem.text.strip() if name_elem else ""
            code_elem = row.select_one('ul.RankingTable__supplements__15Cu li.RankingTable__supplement__vv_m')
            code = code_elem.text.strip() if code_elem else ""

            # 他のデータ（取引値、前営業日までの高値、日付、高値）
            values = row.select('span.StyledNumber__value__3rXW')
            if len(values) >= 4:
                trade_value = values[0].text.strip().replace(',', '')  # カンマ削除
                prev_high = values[1].text.strip().replace(',', '')   # カンマ削除
                date = values[2].text.strip()
                high = values[3].text.strip().replace(',', '')        # カンマ削除
            else:
                continue  # データが不足している場合はスキップ

            data.append({
                "名称": name,
                "コード": code,
                "取引値": trade_value,
                "前営業日までの年初来高値": prev_high,
                "前営業日までの年初来高値の日付": date,
                "高値": high
            })
        except Exception as e:
            logging.warning(f"行の解析中にエラー: {e}")
            continue

    return data

def main():
    # データ格納用リスト
    all_data = []
    page_num = 1

    while True:
        logging.info(f"ページ {page_num} を処理中...")
        html = fetch_page(page_num)
        if not html:
            logging.info("ページが存在しないか、エラーが発生したため終了")
            break

        data = parse_page(html)
        if not data:
            logging.info(f"ページ {page_num} にデータがありません。終了")
            break

        all_data.extend(data)
        page_num += 1
        time.sleep(1)  # サーバー負荷軽減のため1秒待機

    # データフレームに変換
    if all_data:
        df = pd.DataFrame(all_data)
        # CSVファイル名（YYYYMMDD.csv）
        today = datetime.now().strftime("%Y%m%d")
        filename = f"{today}.csv"
        # CSV保存（UTF-8 with BOM）
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logging.info(f"データが {filename} に保存されました。{len(df)} 件")
    else:
        logging.warning("データが取得できませんでした。")

if __name__ == "__main__":
    main()
