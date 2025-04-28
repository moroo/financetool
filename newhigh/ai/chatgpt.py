import csv
import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# 出力ファイル名 (今日の日付)
today = datetime.datetime.now().strftime('%Y%m%d')
output_file = f"{today}.csv"

# Yahooファイナンス 年初来高値ランキングページ
base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"

# Chromeドライバー設定
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# ドライバー起動
driver = webdriver.Chrome(options=options)

# データ格納
all_data = []

page = 1

while True:
    # URL設定
    if page == 1:
        url = base_url
    else:
        url = f"{base_url}&page={page}"
    
    print(f"ページ {page} を取得中...")

    driver.get(url)
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    rows = soup.select('div#item tr.RankingTable__row__1Gwp')

    if not rows:
        print(f"ページ {page} にデータがありません。終了します。")
        break

    for row in rows:
        try:
            name_tag = row.select_one('td.RankingTable__detail__P452 a')
            name = name_tag.text.strip()
            code = row.select_one('ul.RankingTable__supplements__15Cu li').text.strip()

            # 取引値、前営業日までの高値、前営業日までの高値日付、高値
            values = row.select('td.RankingTable__detail__P452 span.StyledNumber__value__3rXW')

            # 数値からカンマを除去
            trading_value = values[0].text.strip().replace(',', '')
            previous_high_value = values[1].text.strip().replace(',', '')
            previous_high_date = values[2].text.strip()
            high_value = values[3].text.strip().replace(',', '')

            all_data.append([name, code, trading_value, previous_high_value, previous_high_date, high_value])

        except Exception as e:
            print(f"エラー行スキップ: {e}")
            continue

    page += 1

driver.quit()

# CSVファイル出力
with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['名称', 'コード', '取引値', '前営業日までの年初来高値', '前営業日までの年初来高値の日付', '高値'])
    writer.writerows(all_data)

print(f"CSVファイル '{output_file}' を作成しました。")

