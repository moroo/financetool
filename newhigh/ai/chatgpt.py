import csv
import datetime
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    # User-Agent偽装
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    return webdriver.Chrome(options=chrome_options)

def fetch_page(driver, url, retries=3):
    for attempt in range(retries):
        try:
            driver.get(url)
            time.sleep(random.uniform(1.5, 3.0))  # 適度なsleepでBAN回避
            return driver.page_source
        except WebDriverException as e:
            print(f"ページ取得失敗 (試行{attempt+1}/{retries}): {e}")
            time.sleep(2)
    print(f"ページ取得失敗: {url}")
    return None

def parse_stock_data(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')
    rows = soup.select('div#item tr.RankingTable__row__1Gwp')
    stock_data = []

    for row in rows:
        try:
            name_tag = row.select_one('td.RankingTable__detail__P452 a')
            name = name_tag.text.strip() if name_tag else "N/A"
            code_tag = row.select_one('ul.RankingTable__supplements__15Cu li')
            code = code_tag.text.strip() if code_tag else "N/A"

            values = row.select('td.RankingTable__detail__P452 span.StyledNumber__value__3rXW')
            trading_price = values[0].text.strip().replace(',', '') if len(values) > 0 else "N/A"
            ytd_high_price = values[1].text.strip().replace(',', '') if len(values) > 1 else "N/A"
            ytd_high_date = values[2].text.strip() if len(values) > 2 else "N/A"
            high_price = values[3].text.strip().replace(',', '') if len(values) > 3 else "N/A"

            stock_data.append([name, code, trading_price, ytd_high_price, ytd_high_date, high_price])

        except Exception as e:
            print(f"データ抽出エラー: {e}")
            continue

    return stock_data

def save_to_csv(data, filename):
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])
            writer.writerows(data)
        print(f"CSVファイル '{filename}' に保存しました。")
    except Exception as e:
        print(f"CSV保存エラー: {e}")

def main():
    driver = setup_driver()
    base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"
    all_stock_data = []
    page = 1

    try:
        while True:
            url = base_url if page == 1 else f"{base_url}&page={page}"
            print(f"ページ {page} を取得中...")

            page_source = fetch_page(driver, url)
            if not page_source:
                break

            stock_data = parse_stock_data(page_source)
            if not stock_data:
                print("データが見つかりません。終了します。")
                break

            all_stock_data.extend(stock_data)
            page += 1

    finally:
        driver.quit()

    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"{today}.csv"
    save_to_csv(all_stock_data, filename)

if __name__ == "__main__":
    main()
