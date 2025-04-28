import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import re
import time

def scrape_stock_data():
    """
    Yahoo!ファイナンスから年初来高値の株式データをスクレイピングし、CSVファイルに保存する。
    複数ページに対応。JavaScriptで生成されるページネーションに対応。
    """

    base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"
    data = []
    page_num = 1
    max_pages = 10  # 念のため最大ページ数を設定（無限ループ防止）

    while page_num <= max_pages:
        url = base_url
        if page_num > 1:
            url += f"&page={page_num}"

        try:
            response = requests.get(url)
            response.raise_for_status()  # エラーが発生した場合に例外を発生させる
            soup = BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"Error accessing URL {url}: {e}")
            break

        table = soup.find("div", id="item").find("table")
        rows = table.find_all("tr")

        if not rows:
            print("No table rows found on this page. Stopping.")
            break  # テーブルがない場合はループを抜ける

        # ヘッダー行はスキップ
        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue  # 空の行をスキップ

            try:
                # 名称とコードの抽出
                name_code_cell = cells[0]
                name_element = name_code_cell.find("a")
                code_element = name_code_cell.find("li", class_="RankingTable__supplement__vv_m")
                name = name_element.text.strip() if name_element else ""
                code = code_element.text.strip() if code_element else ""

                # 取引値の抽出
                price_cell = cells[1]
                price_element = price_cell.find("span", class_="StyledNumber__value__3rXW")
                price = price_element.text.replace(",", "").strip() if price_element else ""
                if price:
                    price = price.replace(",", "")  # カンマを除去

                # 前営業日までの年初来高値と日付の抽出
                prev_high_cell = cells[2]
                prev_high_value_element = prev_high_cell.find("span", class_="StyledNumber__value__3rXW")
                prev_high_date_element = prev_high_cell.find("span", class_="StyledNumber__value__3rXW", string=re.compile(r'\d{4}/\d{2}/\d{2}'))

                prev_high_value = prev_high_value_element.text.replace(",", "").strip() if prev_high_value_element else ""
                if prev_high_value:
                    prev_high_value = prev_high_value.replace(",", "")  # カンマを除去
                prev_high_date = prev_high_date_element.text.strip() if prev_high_date_element else ""

                # 高値の抽出
                high_cell = cells[3]
                high_value_element = high_cell.find("span", class_="StyledNumber__value__3rXW")
                high_value = high_value_element.text.replace(",", "").strip() if high_value_element else ""
                if high_value:
                    high_value = high_value.replace(",", "")  # カンマを除去

                data.append([name, code, price, prev_high_value, prev_high_date, high_value])

            except Exception as e:
                print(f"Error processing row: {e}")
                continue

        # 次のページが存在するか確認
        # ページネーションがJavaScriptで生成されるため、単純なリンク抽出は難しい
        # ここでは、表示されている件数から次のページがあるかを判断する
        paging_info = soup.find("div", id="pagertop").find("p")
        if paging_info:
            match = re.search(r'(\d+)〜(\d+)件 / (\d+)件中', paging_info.text)
            if match:
                start, end, total = map(int, match.groups())
                if end < total:
                    page_num += 1
                    print(f"Processed page {page_num - 1}.  Moving to next page.")
                else:
                    print("Reached the last page.")
                    break
            else:
                print("Could not determine paging information. Stopping.")
                break
        else:
            print("Could not find paging information. Stopping.")
            break

        time.sleep(1)  # 1秒待機 (負荷軽減)

    # CSVファイルへの書き込み
    today = datetime.now().strftime("%Y%m%d")
    filename = f"{today}.csv"

    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])  # ヘッダー行
            csv_writer.writerows(data)
        print(f"Data successfully written to {filename}")

    except Exception as e:
        print(f"Error writing to CSV file: {e}")


if __name__ == "__main__":
    scrape_stock_data()
