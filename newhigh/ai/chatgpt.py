"""
【スクリプト概要】

このPythonスクリプトは、Yahooファイナンスの年初来高値ランキングページから
株式データ（名称、コード、取引値、前営業日までの年初来高値、年初来高値の日付、高値）を
自動的に取得し、CSVファイルとして保存します。

複数ページに渡るランキングも自動巡回して取得し、
ネットワークエラーなどにもリトライ対応します。

データ取得には、ページがJavaScriptで生成されるため、
通常のrequestsではなく、Seleniumでブラウザをエミュレートしています。

【使用ライブラリの選定理由】

- Selenium:
    -> YahooファイナンスのページはJavaScriptで描画されるため。
       requestsでは動的に生成されるデータが取得できないため、実際にブラウザ操作を模倣できるSeleniumを採用。
- BeautifulSoup:
    -> ページ内のHTML構造を解析し、特定のデータ要素を簡単に抽出できるため。
- pandas:
    -> 本スクリプトでは使用していないが、将来的にデータ加工や集計をする場合には非常に便利なため、検討対象に。
       ただし今回は、単純なデータ保存だけのため、軽量なcsvモジュールを採用。

【他に検討したが使用しなかったライブラリ】

- requests単独:
    -> JavaScript描画後のデータを取得できないため却下。
- Scrapy:
    -> 大規模スクレイピング向けのフレームワークだが、今回は単純なページ巡回のみなのでオーバースペックと判断。
- Playwright:
    -> 次世代ブラウザ自動化ツールだが、Seleniumが十分安定しているため今回は採用せず。

【注意点】

- このスクリプトはGoogle Chromeとchromedriverがインストールされている必要があります。
"""

import csv
import datetime
import time
import random
from selenium import webdriver
import os, tempfile, atexit, shutil
from pathlib import Path
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException

def setup_driver():
    """
    Chromeブラウザをヘッドレス（画面を表示せずに）で起動する関数。
    User-Agentを偽装して、bot検知を回避します。
    """
    # 1) Firefox(snap) + geckodriver(snap) を優先
    try:
        os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        ff_bin = "/snap/firefox/current/usr/lib/firefox/firefox"  # snap の実体
        base = Path.home() / "snap/firefox/common/selenium-profiles"
        base.mkdir(parents=True, exist_ok=True)
        prof = tempfile.mkdtemp(prefix="ff-prof-", dir=str(base))
        atexit.register(lambda: shutil.rmtree(prof, ignore_errors=True))

        ff_opts = FirefoxOptions()
        ff_opts.binary_location = ff_bin
        ff_opts.add_argument("-headless")   # GUI なし想定なので有効化
        ff_opts.add_argument("-profile")
        ff_opts.add_argument(prof)

        return webdriver.Firefox(
            service=FirefoxService("/snap/bin/geckodriver"),
            options=ff_opts
        )
    except Exception as e:
        print(f"[setup_driver] Firefox failed: {e}")

    # 2) 失敗時は Chromium(snap) + chromedriver(apt) にフォールバック
    ch_opts = ChromeOptions()
    # snap の実体パス（wrapperだと挙動が不安定なことがある）
    ch_real = "/snap/chromium/current/usr/lib/chromium-browser/chromium"
    ch_opts.binary_location = ch_real if os.path.exists(ch_real) else "/snap/bin/chromium"
    ch_opts.add_argument("--no-sandbox")
    ch_opts.add_argument("--disable-dev-shm-usage")
    ch_opts.add_argument("--remote-debugging-port=0")
    # 毎回ユニークな user-data-dir を snap 配下に用意して競合回避
    ud_base = Path.home() / "snap/chromium/common/selenium-profiles"
    ud_base.mkdir(parents=True, exist_ok=True)
    tmp_ud = tempfile.mkdtemp(prefix="profile-", dir=str(ud_base))
    atexit.register(lambda: shutil.rmtree(tmp_ud, ignore_errors=True))
    ch_opts.add_argument(f"--user-data-dir={tmp_ud}")
    # 必要ならヘッドレス:
    # ch_opts.add_argument("--headless=new")

    return webdriver.Chrome(
        service=ChromeService("/usr/bin/chromedriver"),
        options=ch_opts
    )
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 画面を表示しないモード
    chrome_options.add_argument('--no-sandbox')  # セキュリティサンドボックスを無効化
    chrome_options.add_argument('--disable-dev-shm-usage')  # メモリ共有無効化（Linux対策）
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # bot検知回避
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')  # 人間のブラウザを装う
    return webdriver.Chrome(options=chrome_options)

def fetch_page(driver, url, retries=3):
    """
    指定したURLのページを取得する。
    取得に失敗した場合、最大retries回リトライする。
    
    Args:
        driver: SeleniumのWebDriverインスタンス
        url: 取得対象のURL
        retries: 最大リトライ回数

    Returns:
        ページのHTMLソース（文字列）またはNone
    """
    for attempt in range(retries):
        try:
            driver.get(url)  # 指定URLへアクセス
            time.sleep(random.uniform(1.5, 3.0))  # 1.5〜3秒ランダムに待機
            return driver.page_source  # ページソースを返す
        except WebDriverException as e:
            print(f"ページ取得失敗 (試行{attempt+1}/{retries}): {e}")
            time.sleep(2)  # 2秒待機して再試行
    print(f"ページ取得失敗: {url}")
    return None

def parse_stock_data(page_source):
    """
    ページソースから株式データを抽出する関数。
    
    Args:
        page_source: HTML文字列

    Returns:
        抽出した株式データリスト
    """
    soup = BeautifulSoup(page_source, 'html.parser')  # HTML解析
    rows = soup.select('div#item tr.RankingTable__row__1Gwp')  # 株式リスト行を取得
    stock_data = []

    for row in rows:
        try:
            name_tag = row.select_one('td.RankingTable__detail__P452 a')  # 名称を取得
            name = name_tag.text.strip() if name_tag else "N/A"  # テキスト取り出し

            code_tag = row.select_one('ul.RankingTable__supplements__15Cu li')  # 証券コード取得
            code = code_tag.text.strip() if code_tag else "N/A"

            values = row.select('td.RankingTable__detail__P452 span.StyledNumber__value__3rXW')  # 数値データ抽出
            trading_price = values[0].text.strip().replace(',', '') if len(values) > 0 else "N/A"  # 取引値
            ytd_high_price = values[1].text.strip().replace(',', '') if len(values) > 1 else "N/A"  # 年初来高値
            ytd_high_date = values[2].text.strip() if len(values) > 2 else "N/A"  # 年初来高値日
            high_price = values[3].text.strip().replace(',', '') if len(values) > 3 else "N/A"  # 高値

            stock_data.append([name, code, trading_price, ytd_high_price, ytd_high_date, high_price])  # データをリストへ追加
        except Exception as e:
            print(f"データ抽出エラー: {e}")  # 何か問題があればスキップ
            continue

    return stock_data

def save_to_csv(data, filename):
    """
    データをCSVファイルに保存する関数。
    
    Args:
        data: 保存するリスト形式のデータ
        filename: 出力するファイル名
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])  # ヘッダー行
            writer.writerows(data)  # 本体データ
        print(f"CSVファイル '{filename}' に保存しました。")
    except Exception as e:
        print(f"CSV保存エラー: {e}")

def main():
    """
    スクリプトのメイン関数。
    ページを巡回し、株式データをすべて取得してCSVに保存します。
    """
    driver = setup_driver()  # ブラウザ起動
    base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"
    all_stock_data = []  # データをまとめるリスト
    page = 1

    try:
        while True:
            url = base_url if page == 1 else f"{base_url}&page={page}"  # ページURLを組み立て
            print(f"ページ {page} を取得中...")

            page_source = fetch_page(driver, url)  # ページ取得
            if not page_source:
                break  # ページ取得失敗で終了

            stock_data = parse_stock_data(page_source)  # データ抽出
            if not stock_data:
                print("データが見つかりません。終了します。")
                break  # データが無ければ終了

            all_stock_data.extend(stock_data)  # データを追加
            page += 1  # 次のページへ
    finally:
        driver.quit()  # ブラウザを必ず終了

    today = datetime.datetime.now().strftime("%Y%m%d")  # 今日の日付を取得
    filename = f"{today}.csv"  # ファイル名作成
    save_to_csv(all_stock_data, filename)  # CSV出力

if __name__ == "__main__":
    main()
