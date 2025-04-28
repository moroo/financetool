import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

def get_stock_data(page):
    url = f"https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily&page={page}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    rows = soup.select('tr.RankingTable__row__1Gwp')
    stock_data = []

    for row in rows:
        try:
            name = row.select_one('a').text.strip()
            code = row.select_one('ul.RankingTable__supplements__15Cu li').text.strip()
            values = row.select('span.StyledNumber__value__3rXW')
            
            trading_price = values[0].text.strip().replace(',', '')  # "," を除去
            ytd_high_price = values[1].text.strip().replace(',', '')  # "," を除去
            ytd_high_date = values[2].text.strip()
            high_price = values[3].text.strip().replace(',', '')  # "," を除去

            stock_data.append([name, code, trading_price, ytd_high_price, ytd_high_date, high_price])
        except (AttributeError, IndexError):
            continue

    return stock_data

def save_to_csv(data, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])
        writer.writerows(data)

def main():
    all_data = []
    page = 1

    while True:
        stock_data = get_stock_data(page)
        if not stock_data:
            break
        all_data.extend(stock_data)
        page += 1

    today = datetime.now().strftime('%Y%m%d')
    filename = f"{today}.csv"
    save_to_csv(all_data, filename)
    print(f"データが {filename} に保存されました！")

if __name__ == "__main__":
    main()

