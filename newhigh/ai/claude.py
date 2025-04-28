import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
import logging
import os
from typing import List, Dict, Optional, Tuple, Any

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class YahooFinanceScraper:
    """Yahoo!ファイナンスから株価データをスクレイピングするクラス"""

    BASE_URL = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    def __init__(self, market: str = "all", term: str = "daily", sleep_time: int = 1, max_retries: int = 3, max_pages: int = 100):
        """
        初期化
        
        Args:
            market: 市場（'all'=全市場）
            term: 期間（'daily'=日次）
            sleep_time: リクエスト間の待機時間（秒）
            max_retries: 最大リトライ回数
            max_pages: 最大ページ数（無限ループ防止）
        """
        self.market = market
        self.term = term
        self.sleep_time = sleep_time
        self.max_retries = max_retries
        self.max_pages = max_pages
        self.all_data = []

    def get_url(self, page: int = 1) -> str:
        """ページURLを生成"""
        params = {
            "market": self.market,
            "term": self.term
        }
        
        url = f"{self.BASE_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        if page > 1:
            url += f"&page={page}"
        
        return url

    def fetch_page(self, page: int) -> Optional[BeautifulSoup]:
        """指定ページのHTMLを取得し、BeautifulSoupオブジェクトを返す"""
        url = self.get_url(page)
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"ページ {page} を取得中... (試行 {attempt + 1}/{self.max_retries})")
                response = requests.get(url, headers=self.HEADERS, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, "html.parser")
                return soup
                
            except requests.exceptions.RequestException as e:
                logger.error(f"ページ取得エラー ({url}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * self.sleep_time
                    logger.info(f"{wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"最大リトライ回数に達しました。ページ {page} のスクレイピングを中止します。")
                    return None
        
        return None

    def extract_stock_data(self, soup: BeautifulSoup) -> List[List[str]]:
        """BeautifulSoupオブジェクトから株価データを抽出"""
        data = []
        
        # 複数のセレクタを試す (HTML構造の変更に対応)
        rows = soup.select('tr.RankingTable__row__1Gwp')
        if not rows:
            rows = soup.select('div#item tr')
            if not rows:
                table = soup.find("div", id="item")
                if table:
                    table_element = table.find("table")
                    if table_element:
                        rows = table_element.find_all("tr")[1:]  # ヘッダー行をスキップ
        
        if not rows:
            logger.warning("テーブルの行が見つかりません。HTML構造が変更された可能性があります。")
            return []
        
        for row in rows:
            try:
                # 名称とコードの抽出 (複数の抽出方法を試す)
                name = code = ""
                name_element = row.select_one('a')
                if name_element:
                    name = name_element.text.strip()
                
                code_element = row.select_one('li.RankingTable__supplement__vv_m')
                if code_element:
                    code = code_element.text.strip()
                elif row.select_one('ul.RankingTable__supplements__15Cu li'):
                    code = row.select_one('ul.RankingTable__supplements__15Cu li').text.strip()
                
                # 数値データの抽出
                values = row.select('span.StyledNumber__value__3rXW')
                
                if len(values) < 4:
                    logger.warning(f"行のデータが不完全です: {name} ({code})")
                    continue
                
                # データの取得とカンマ除去
                trading_price = values[0].text.strip().replace(',', '')
                ytd_high_price = values[1].text.strip().replace(',', '')
                ytd_high_date = values[2].text.strip()
                high_price = values[3].text.strip().replace(',', '')
                
                data.append([name, code, trading_price, ytd_high_price, ytd_high_date, high_price])
                
            except Exception as e:
                logger.error(f"データ抽出エラー: {e}")
                continue
        
        return data

    def check_more_pages(self, soup: BeautifulSoup, current_page: int) -> bool:
        """次のページが存在するか確認"""
        # 方法1: ページネーション情報のテキストを解析
        paging_info = soup.find("div", id="pagertop")
        if paging_info and paging_info.find("p"):
            text = paging_info.find("p").text
            import re
            match = re.search(r'(\d+)〜(\d+)件 / (\d+)件中', text)
            if match:
                start, end, total = map(int, match.groups())
                return end < total
        
        # 方法2: 「次へ」ボタンの存在確認
        next_button = soup.select_one('button.ymuiPagination__button--next:not([disabled])')
        if next_button:
            return True
        
        # 方法3: データ件数による判断
        if len(self.extract_stock_data(soup)) >= 50:  # 通常1ページに50件表示
            return True
            
        return False

    def scrape_all_pages(self) -> List[List[str]]:
        """全ページのデータをスクレイピング"""
        all_data = []
        page = 1
        
        while page <= self.max_pages:
            soup = self.fetch_page(page)
            if not soup:
                break
            
            data = self.extract_stock_data(soup)
            if not data:
                logger.info(f"ページ {page} にデータがありません。終了します。")
                break
            
            all_data.extend(data)
            logger.info(f"ページ {page} から {len(data)} 件のデータを取得しました")
            
            has_more_pages = self.check_more_pages(soup, page)
            if not has_more_pages:
                logger.info("最終ページに到達しました。")
                break
            
            page += 1
            time.sleep(self.sleep_time)  # サーバー負荷軽減のための待機
            
        return all_data

    def save_to_csv(self, data: List[List[str]], filename: Optional[str] = None) -> str:
        """データをCSVファイルに保存"""
        if filename is None:
            today = datetime.now().strftime("%Y%m%d")
            filename = f"{today}.csv"
        
        try:
            with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])
                csv_writer.writerows(data)
            
            logger.info(f"データを {filename} に保存しました（合計 {len(data)} 件）")
            return filename
            
        except Exception as e:
            logger.error(f"CSVファイル保存エラー: {e}")
            # バックアップとして別名で保存を試みる
            backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            logger.info(f"バックアップファイル {backup_filename} に保存を試みます")
            
            try:
                with open(backup_filename, "w", newline="", encoding="utf-8-sig") as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])
                    csv_writer.writerows(data)
                logger.info(f"バックアップデータを {backup_filename} に保存しました")
                return backup_filename
            except Exception as e2:
                logger.critical(f"バックアップファイル保存にも失敗しました: {e2}")
                return ""

    def run(self) -> str:
        """スクレイピングを実行し、CSVファイルを保存"""
        logger.info("Yahoo!ファイナンス年初来高値ランキングのスクレイピングを開始します")
        
        try:
            data = self.scrape_all_pages()
            
            if not data:
                logger.warning("データが取得できませんでした")
                return ""
            
            return self.save_to_csv(data)
            
        except Exception as e:
            logger.error(f"予期せぬエラーが発生しました: {e}")
            return ""


def main():
    """メイン関数"""
    try:
        scraper = YahooFinanceScraper(
            sleep_time=1,      # サーバー負荷軽減のための待機時間
            max_retries=3,     # 接続失敗時の最大リトライ回数
            max_pages=100      # 最大ページ数（無限ループ防止）
        )
        
        output_file = scraper.run()
        
        if output_file:
            logger.info(f"処理が完了しました。出力ファイル: {output_file}")
        else:
            logger.error("処理が失敗しました")
            
    except KeyboardInterrupt:
        logger.info("ユーザーによって処理が中断されました")
    except Exception as e:
        logger.critical(f"クリティカルエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
