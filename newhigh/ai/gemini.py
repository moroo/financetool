import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import re
import time
import logging

# ロギングの設定（エラーの詳細を記録）
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_stock_data(base_url, max_pages=10):
    """
    Yahoo!ファイナンスから年初来高値の株式データをスクレイピングし、CSVファイルに保存する。
    複数ページに対応。ページネーションをよりロバストに処理。
    """

    data = []
    page_num = 1
    session = requests.Session()  # セッションを利用して接続を維持
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })  # User-Agentを設定

    while page_num <= max_pages:
        url = f"{base_url}&page={page_num}" if page_num > 1 else base_url
        print(f"Scraping page {page_num}: {url}")  # どのページを処理しているかを表示

        try:
            response = session.get(url, timeout=10)  # タイムアウトを設定
            response.raise_for_status()  # HTTPエラーをチェック
            soup = BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error accessing URL {url}: {e}")
            print(f"Failed to retrieve data from {url}. Skipping page.")
            page_num += 1  # エラーが発生しても次のページへ
            continue

        table = soup.find("div", id="item").find("table")
        if not table:
            logging.error(f"No table found on {url}. Stopping.")
            print(f"No data table found on this page. Stopping.")
            break

        rows = table.find_all("tr")
        if not rows:
            logging.warning(f"No table rows found on {url}. Skipping page.")
            print(f"No data rows found on page {page_num}. Skipping.")
            page_num += 1
            continue

        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all("td")
            if not cells:
                continue

            try:
                (
                    name,
                    code,
                    price,
                    prev_high_value,
                    prev_high_date,
                    high_price,
                ) = extract_row_data(cells)
                data.append([name, code, price, prev_high_value, prev_high_date, high_price])
            except ValueError as e:
                logging.error(f"Failed to extract data from row: {e}")
                print(f"Error processing a row. Skipping.")

        # ページネーションのロバストな処理
        next_page_exists = check_next_page(soup)
        if next_page_exists:
            page_num += 1
            print(f"Moving to next page: {page_num}")
            time.sleep(1)  # 負荷軽減
        else:
            print("Reached the last page.")
            break

    return data

def extract_row_data(cells):
    """
    テーブルの行からデータを抽出する。
    """
    if len(cells) < 4:
        raise ValueError("Not enough cells in row")

    name_code_cell = cells[0]
    name_element = name_code_cell.find("a")
    code_element = name_code_cell.find("li", class_="RankingTable__supplement__vv_m")
    name = name_element.text.strip() if name_element else "N/A"
    code = code_element.text.strip() if code_element else "N/A"

    price_cell = cells[1]
    price_element = price_cell.find("span", class_="StyledNumber__value__3rXW")
    price = price_element.text.replace(",", "").strip() if price_element else "N/A"

    prev_high_cell = cells[2]
    prev_high_value_element = prev_high_cell.find("span", class_="StyledNumber__value__3rXW")
    prev_high_date_element = prev_high_cell.find("span", class_="StyledNumber__value__3rXW", string=re.compile(r'\d{4}/\d{2}/\d{2}'))
    prev_high_value = prev_high_value_element.text.replace(",", "").strip() if prev_high_value_element else "N/A"
    prev_high_date = prev_high_date_element.text.strip() if prev_high_date_element else "N/A"

    high_cell = cells[3]
    high_value_element = high_cell.find("span", class_="StyledNumber__value__3rXW")
    high_price = high_value_element.text.replace(",", "").strip() if high_value_element else "N/A"

    return name, code, price, prev_high_value, prev_high_date, high_price

def check_next_page(soup):
    """
    次のページが存在するかどうかをより確実に判定する。
    """
    paging_div = soup.find("div", id="pagertop")
    if not paging_div:
        return False
    next_button = paging_div.find("button", {"data-cl-params": "_cl_link:next;_cl_position:0"})
    return next_button is not None and "disabled" not in next_button.attrs

def save_to_csv(data, filename="stock_data.csv"):
    """
    データをCSVファイルに保存する。
    """
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(
                ["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"]
            )
            csv_writer.writerows(data)
        print(f"Data successfully written to {filename}")
    except Exception as e:
        logging.error(f"Error writing to CSV file: {e}")
        print(f"Error writing to CSV file: {e}")

def main():
    base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"
    all_data = scrape_stock_data(base_url)
    if all_data:
        today = datetime.now().strftime("%Y%m%d")
        save_to_csv(all_data, f"{today}_stock_data.csv")
    else:
        print("No data to save.")

if __name__ == "__main__":
    main()
