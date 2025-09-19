# chatgpt.py
"""
【概要】
Yahoo!ファイナンス「年初来高値ランキング」から
名称・コード・取引値・年初来高値・日付・高値 を取得し、CSV保存します。
Selenium（Firefox優先→Chromiumフォールバック）で動的描画に対応。

【前提（Ubuntu 24.04 / venv不可環境向け）】
- selenium は apt の python3-selenium を使用
- Firefox/Chromium は snap、ドライバはそれぞれ下記前提
  - geckodriver: /snap/bin/geckodriver
  - chromedriver: /usr/bin/chromedriver
"""

import csv
import datetime
import time
import random
import os
import tempfile
import atexit
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# 設定
# =========================
BASE_URL = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
)
WAIT_SEC = 15          # 初回レンダリング待ち
RETRY = 3              # ページ取得リトライ回数
SLEEP_MIN, SLEEP_MAX = 0.8, 1.6  # アクセス間ランダム待機


# =========================
# データ構造
# =========================
@dataclass
class StockRow:
    name: str
    code: str
    trading_price: str
    ytd_high_price: str
    ytd_high_date: str
    high_price: str

    def as_list(self) -> List[str]:
        return [
            self.name, self.code, self.trading_price,
            self.ytd_high_price, self.ytd_high_date, self.high_price
        ]


# =========================
# WebDriver 構築
# =========================
def _build_firefox(headless: bool = True) -> webdriver.Firefox:
    os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

    ff_bin = "/snap/firefox/current/usr/lib/firefox/firefox"  # snap 実体
    prof_base = Path.home() / "snap/firefox/common/selenium-profiles"
    prof_base.mkdir(parents=True, exist_ok=True)
    prof = tempfile.mkdtemp(prefix="ff-prof-", dir=str(prof_base))
    atexit.register(lambda: shutil.rmtree(prof, ignore_errors=True))

    opts = FirefoxOptions()
    opts.binary_location = ff_bin
    if headless:
        opts.add_argument("-headless")
    opts.add_argument("-profile")
    opts.add_argument(prof)
    # UA を上書き（Bot検知の軽減に寄与）
    opts.set_preference("general.useragent.override", DEFAULT_UA)

    drv = webdriver.Firefox(
        service=FirefoxService("/snap/bin/geckodriver"),
        options=opts
    )
    drv.set_page_load_timeout(WAIT_SEC)
    return drv


def _build_chromium(headless: bool = False) -> webdriver.Chrome:
    # snap 実体パス（wrapper だと不安定なケースがある）
    ch_real = "/snap/chromium/current/usr/lib/chromium-browser/chromium"
    bin_path = ch_real if os.path.exists(ch_real) else "/snap/bin/chromium"

    ud_base = Path.home() / "snap/chromium/common/selenium-profiles"
    ud_base.mkdir(parents=True, exist_ok=True)
    tmp_ud = tempfile.mkdtemp(prefix="profile-", dir=str(ud_base))
    atexit.register(lambda: shutil.rmtree(tmp_ud, ignore_errors=True))

    opts = ChromeOptions()
    opts.binary_location = bin_path
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--remote-debugging-port=0")
    opts.add_argument(f"--user-data-dir={tmp_ud}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(f"user-agent={DEFAULT_UA}")
    if headless:
        # Ubuntu 24.04 の Chromium は new ヘッドレス対応
        opts.add_argument("--headless=new")

    drv = webdriver.Chrome(
        service=ChromeService("/usr/bin/chromedriver"),
        options=opts
    )
    drv.set_page_load_timeout(WAIT_SEC)
    return drv


def setup_driver(prefer: str = "firefox", headless: bool = True):
    """
    Firefox（snap）を優先し、失敗時に Chromium（snap）へフォールバック。
    """
    builders = []
    if prefer.lower().startswith("f"):
        builders = [_build_firefox, _build_chromium]
    else:
        builders = [_build_chromium, _build_firefox]

    last_err: Optional[Exception] = None
    for builder in builders:
        try:
            drv = builder(headless=headless)
            return drv
        except Exception as e:
            print(f"[setup_driver] {builder.__name__} failed: {e}")
            last_err = e
    raise RuntimeError(f"WebDriver setup failed: {last_err}")


# =========================
# 取得 & 解析
# =========================
def fetch_page(driver, url: str, retries: int = RETRY) -> Optional[str]:
    """
    指定URLを開き、主要要素が現れるまで待機して HTML を返す。
    """
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            WebDriverWait(driver, WAIT_SEC).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div#item'))
            )
            time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
            return driver.page_source
        except (TimeoutException, WebDriverException) as e:
            print(f"[fetch_page] fail {attempt}/{retries}: {e}")
            time.sleep(min(2 ** attempt, 8))
    print(f"[fetch_page] giving up: {url}")
    return None


def _sel_first_text(node, selector: str, default: str = "N/A") -> str:
    el = node.select_one(selector)
    return el.text.strip() if el else default


def parse_stock_data(page_source: str) -> List[StockRow]:
    """
    HTML からランキング行を抽出。クラス名末尾の揺れに強い CSS を使用。
    """
    soup = BeautifulSoup(page_source, "html.parser")
    rows = soup.select('div#item tr[class*="RankingTable__row"]')
    out: List[StockRow] = []

    for row in rows:
        try:
            name = _sel_first_text(row, 'td[class*="RankingTable__detail"] a')
            code = _sel_first_text(row, 'ul[class*="RankingTable__supplements"] li')

            nums = row.select('td[class*="RankingTable__detail"] span[class*="StyledNumber__value"]')
            def num_at(i, default="N/A"):
                return nums[i].text.strip().replace(",", "") if len(nums) > i else default

            trading_price = num_at(0)
            ytd_high_price = num_at(1)
            ytd_high_date  = _sel_first_text(row, 'td[class*="RankingTable__detail"] span[class*="StyledNumber__date"]', "N/A") \
                             if len(nums) <= 2 else num_at(2)  # 後方互換
            high_price     = num_at(3)

            out.append(StockRow(
                name=name, code=code, trading_price=trading_price,
                ytd_high_price=ytd_high_price, ytd_high_date=ytd_high_date,
                high_price=high_price
            ))
        except Exception as e:
            print(f"[parse] row skipped: {e}")
            continue
    return out


# =========================
# 保存
# =========================
def save_to_csv(rows: List[StockRow], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])
        for r in rows:
            w.writerow(r.as_list())
    print(f"[save] {out_path} ({len(rows)} rows)")


# =========================
# メイン
# =========================
def main():
    driver = setup_driver(prefer="firefox", headless=True)
    all_rows: List[StockRow] = []
    page = 1

    try:
        while True:
            url = BASE_URL if page == 1 else f"{BASE_URL}&page={page}"
            print(f"[crawl] page={page} -> {url}")
            html = fetch_page(driver, url)
            if not html:
                break
            rows = parse_stock_data(html)
            if not rows:
                print("[crawl] no rows; stop.")
                break
            all_rows.extend(rows)
            page += 1
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    today = datetime.datetime.now().strftime("%Y%m%d")
    out = Path(f"{today}.csv")
    save_to_csv(all_rows, out)


if __name__ == "__main__":
    main()
