import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

def fetch_page(page):
    url = f'https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily&page={page}'
    response = requests.get(url)
    return BeautifulSoup(response.text, 'html.parser')

def parse_row(row):
    name = row.find('a').text.strip()
    code = row.find('li', class_='RankingTable__supplement__vv_m').text.strip()
    
    numbers = row.find_all('span', class_='StyledNumber__value__3rXW')
    trade_value = numbers[0].text.replace(',', '')
    prev_high = numbers[1].text.replace(',', '')
    prev_date = numbers[2].text  # インデックス2から直接取得
    high = numbers[3].text.replace(',', '')
    
    return [name, code, trade_value, prev_high, prev_date, high]

def main():
    today = datetime.now().strftime('%Y%m%d')
    with open(f'{today}.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['名称', 'コード', '取引値', '前営業日高値', '高値日付', '高値'])
        
        page = 1
        while True:
            soup = fetch_page(page)
            rows = soup.select('tr.RankingTable__row__1Gwp')
            if not rows:
                break
                
            for row in rows:
                writer.writerow(parse_row(row))
            
            page += 1

if __name__ == '__main__':
    main()
