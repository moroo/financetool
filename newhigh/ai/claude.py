"""
Yahoo!ファイナンス年初来高値ランキングスクレイパー

【アルゴリズムの概要】
1. Yahoo!ファイナンスの年初来高値ランキングページに接続する
2. 各ランキングページから株式データ（銘柄名、コード、価格情報など）を抽出する
3. 複数ページにわたってデータを収集する（ページネーション処理）
4. 収集したデータをCSVファイルに保存する
5. エラー処理（接続失敗、HTML構造変更など）に対応する

【使用パッケージの選択理由】
- requests: 
  選択理由: HTTPリクエストを簡潔に扱えるPythonの標準的なライブラリ。簡単な使用方法でWebページの取得が可能。
  比較検討: Seleniumと比較して、JavaScriptが少ないサイトでは処理が軽量で高速。

- BeautifulSoup: 
  選択理由: HTMLの解析に特化した強力で使いやすいライブラリ。CSSセレクタやタグ検索などの機能が充実。
  比較検討: lxmlと比較して、より直感的で初心者にも扱いやすいAPI。

- csv: 
  選択理由: Pythonの標準ライブラリで、シンプルなCSV操作が可能。
  比較検討: pandasと比較して依存関係が少なく、この程度のデータ量では十分な機能を提供。

【選択しなかったパッケージと理由】
- Selenium: 
  選択しなかった理由: JavaScript実行が必要なページや複雑な操作が必要なサイトに有効だが、
  Yahoo!ファイナンスの年初来高値ランキングページはrequestsでも十分にデータ取得可能。
  また、WebDriverの設定や実行速度の遅さなどのオーバーヘッドがある。

- pandas: 
  選択しなかった理由: 大規模なデータ操作や分析が必要な場合は非常に強力だが、
  単純なCSV保存だけであればPythonの標準csvモジュールで十分。
  依存関係を減らし、スクリプトをより軽量に保つためpandasは使用しなかった。

- scrapy: 
  選択しなかった理由: 大規模な分散クローリングプロジェクトには適しているが、
  単一サイトの特定ページ群をスクレイピングする今回のケースではオーバースペック。
  学習曲線が急で初心者には扱いづらい。
"""

import requests  # Webページを取得するためのライブラリ
from bs4 import BeautifulSoup  # HTMLを解析するためのライブラリ
import csv  # CSVファイルを操作するためのライブラリ
from datetime import datetime  # 日付と時刻を扱うためのライブラリ
import time  # 時間操作や待機のためのライブラリ
import logging  # ログ出力を管理するためのライブラリ
import os  # ファイルやディレクトリを操作するためのライブラリ
from typing import List, Dict, Optional, Tuple, Any  # 型ヒントを提供するためのライブラリ

# ロギングの設定
# logging.basicConfigで、ログの出力レベルやフォーマット、出力先を設定します
logging.basicConfig(
    level=logging.INFO,  # INFO以上のログレベルを出力（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    format='%(asctime)s - %(levelname)s - %(message)s',  # ログの出力形式を設定（時刻、レベル、メッセージ）
    handlers=[
        logging.FileHandler("stock_scraper.log"),  # ログをファイルに出力
        logging.StreamHandler()  # ログをコンソールにも出力
    ]
)
# loggerオブジェクトを作成して、後で使用できるようにします
logger = logging.getLogger(__name__)

class YahooFinanceScraper:
    """
    Yahoo!ファイナンスから株価データをスクレイピングするクラス
    
    このクラスは、Yahoo!ファイナンスの年初来高値ランキングページから
    株価データを取得し、CSVファイルに保存する機能を提供します。
    複数ページにわたるデータを収集し、エラー処理や再試行機能も備えています。
    """

    # クラス変数として基本URLとHTTPリクエストヘッダーを定義
    BASE_URL = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh"  # スクレイピング対象の基本URL
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        # User-Agentを設定して、ブラウザからのアクセスに見せかけます（サイトによってはBot判定を避けるため）
    }
    
    def __init__(self, market: str = "all", term: str = "daily", sleep_time: int = 1, max_retries: int = 3, max_pages: int = 100):
        """
        YahooFinanceScraperクラスの初期化メソッド
        
        Args:
            market (str): 取得対象の市場（'all'=全市場、'prime'=プライム市場など）
            term (str): 期間（'daily'=日次）
            sleep_time (int): リクエスト間の待機時間（秒）、サーバーに負荷をかけないための配慮
            max_retries (int): 接続失敗時の最大リトライ回数
            max_pages (int): スクレイピングする最大ページ数（無限ループ防止）
        """
        # 初期化時に渡されたパラメータをインスタンス変数として保存
        self.market = market  # 市場設定を保存
        self.term = term  # 期間設定を保存
        self.sleep_time = sleep_time  # リクエスト間の待機時間を保存
        self.max_retries = max_retries  # 最大リトライ回数を保存
        self.max_pages = max_pages  # 最大ページ数を保存
        self.all_data = []  # 収集したデータを保存するリスト（初期値は空）

    def get_url(self, page: int = 1) -> str:
        """
        スクレイピング対象のURLを生成するメソッド
        
        Args:
            page (int): ページ番号（デフォルトは1ページ目）
            
        Returns:
            str: スクレイピング対象の完全なURL
        
        例:
            page=1の場合：https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily
            page=2の場合：https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily&page=2
        """
        # URLパラメータを辞書として準備
        params = {
            "market": self.market,  # 市場パラメータ
            "term": self.term  # 期間パラメータ
        }
        
        # 基本URLとパラメータを結合してURLを生成
        # 各パラメータを&で連結し、その前に?をつける
        url = f"{self.BASE_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        
        # 2ページ目以降なら、page=Xパラメータを追加
        if page > 1:
            url += f"&page={page}"
        
        # 完成したURLを返す
        return url

    def fetch_page(self, page: int) -> Optional[BeautifulSoup]:
        """
        指定したページのHTMLを取得し、BeautifulSoupオブジェクトに変換するメソッド
        
        Args:
            page (int): 取得するページ番号
            
        Returns:
            Optional[BeautifulSoup]: 解析済みのBeautifulSoupオブジェクト、または失敗時はNone
            
        注意:
            - 接続エラー時は自動的に再試行します
            - 最大リトライ回数に達しても失敗した場合はNoneを返します
        """
        # get_url()メソッドで対象ページのURLを取得
        url = self.get_url(page)
        
        # 最大リトライ回数だけ試行
        for attempt in range(self.max_retries):
            try:
                # 試行についてログに記録
                logger.info(f"ページ {page} を取得中... (試行 {attempt + 1}/{self.max_retries})")
                
                # requestsライブラリを使ってHTTP GETリクエストを送信
                # headers: ブラウザからのアクセスに見せかけるためのヘッダー情報
                # timeout: 30秒以内に応答がない場合はタイムアウト
                response = requests.get(url, headers=self.HEADERS, timeout=30)
                
                # HTTPステータスコードが200番台以外の場合は例外を発生
                response.raise_for_status()
                
                # 取得したHTMLをBeautifulSoupで解析
                # html.parserはPythonの標準HTMLパーサー
                soup = BeautifulSoup(response.content, "html.parser")
                
                # 解析済みのBeautifulSoupオブジェクトを返す
                return soup
                
            except requests.exceptions.RequestException as e:
                # リクエストに関する例外が発生した場合
                logger.error(f"ページ取得エラー ({url}): {e}")
                
                # 最大リトライ回数に達していなければ再試行
                if attempt < self.max_retries - 1:
                    # 待機時間を計算（試行回数が増えるごとに待機時間を増加）
                    wait_time = (attempt + 1) * self.sleep_time
                    logger.info(f"{wait_time}秒後にリトライします...")
                    time.sleep(wait_time)  # 指定した秒数だけ処理を一時停止
                else:
                    # 最大リトライ回数に達した場合はエラーログを出力してNoneを返す
                    logger.error(f"最大リトライ回数に達しました。ページ {page} のスクレイピングを中止します。")
                    return None
        
        # 試行回数分ループしても成功しなかった場合はNoneを返す
        return None

    def extract_stock_data(self, soup: BeautifulSoup) -> List[List[str]]:
        """
        BeautifulSoupオブジェクトから株価データを抽出するメソッド
        
        Args:
            soup (BeautifulSoup): 解析済みのWebページ（BeautifulSoupオブジェクト）
            
        Returns:
            List[List[str]]: 抽出した株価データのリスト
            各要素は[名称, コード, 取引値, 年初来高値, 年初来高値の日付, 高値]の形式
            
        注意:
            - HTML構造の変更に対応するため、複数のセレクタを試みます
            - データ抽出に失敗した行はスキップされます
        """
        # 抽出したデータを格納するリストを初期化
        data = []
        
        # 複数のセレクタを試す (HTML構造の変更に対応するため)
        # 最初のセレクターを試す
        rows = soup.select('tr.RankingTable__row__1Gwp')
        
        # 最初のセレクターでデータが見つからなければ別のセレクターを試す
        if not rows:
            rows = soup.select('div#item tr')
            
            # それでも見つからなければさらに別の方法を試す
            if not rows:
                table = soup.find("div", id="item")
                if table:
                    table_element = table.find("table")
                    if table_element:
                        rows = table_element.find_all("tr")[1:]  # ヘッダー行をスキップ
        
        # すべての方法でデータが見つからなかった場合は警告を出力して空リストを返す
        if not rows:
            logger.warning("テーブルの行が見つかりません。HTML構造が変更された可能性があります。")
            return []
        
        # 見つかった各行からデータを抽出
        for row in rows:
            try:
                # 名称とコードの抽出 (複数の抽出方法を試す)
                name = code = ""  # 初期値として空文字列を設定
                
                # 銘柄名は通常aタグ内にある
                name_element = row.select_one('a')
                if name_element:
                    name = name_element.text.strip()  # テキストを取得して前後の空白を削除
                
                # 証券コードの抽出（複数のパターンに対応）
                code_element = row.select_one('li.RankingTable__supplement__vv_m')
                if code_element:
                    code = code_element.text.strip()
                elif row.select_one('ul.RankingTable__supplements__15Cu li'):
                    code = row.select_one('ul.RankingTable__supplements__15Cu li').text.strip()
                
                # 数値データの抽出（取引値、年初来高値など）
                values = row.select('span.StyledNumber__value__3rXW')
                
                # 必要なデータ（通常4つ以上）がない場合はスキップ
                if len(values) < 4:
                    logger.warning(f"行のデータが不完全です: {name} ({code})")
                    continue
                
                # データの取得とカンマ除去（数値として扱えるようにするため）
                trading_price = values[0].text.strip().replace(',', '')  # 取引値
                ytd_high_price = values[1].text.strip().replace(',', '')  # 年初来高値
                ytd_high_date = values[2].text.strip()  # 年初来高値の日付
                high_price = values[3].text.strip().replace(',', '')  # 高値
                
                # 抽出したデータをリストに追加
                data.append([name, code, trading_price, ytd_high_price, ytd_high_date, high_price])
                
            except Exception as e:
                # データ抽出中にエラーが発生した場合はログに記録して次の行に進む
                logger.error(f"データ抽出エラー: {e}")
                continue
        
        # 抽出したすべてのデータを返す
        return data

    def check_more_pages(self, soup: BeautifulSoup, current_page: int) -> bool:
        """
        次のページが存在するかどうかを確認するメソッド
        
        Args:
            soup (BeautifulSoup): 現在のページのBeautifulSoupオブジェクト
            current_page (int): 現在のページ番号
            
        Returns:
            bool: 次のページが存在する場合はTrue、存在しない場合はFalse
            
        注意:
            - 複数の判定方法を使用して、次のページの存在を確認します
            - ページネーション情報、「次へ」ボタン、データ件数などを総合的に判断します
        """
        # 方法1: ページネーション情報のテキストを解析
        # 「XX〜YY件 / ZZ件中」のような形式のテキストを探す
        paging_info = soup.find("div", id="pagertop")
        if paging_info and paging_info.find("p"):
            text = paging_info.find("p").text
            import re  # 正規表現を使用するためにインポート
            
            # 正規表現でページネーション情報を抽出
            match = re.search(r'(\d+)〜(\d+)件 / (\d+)件中', text)
            if match:
                # 表示開始位置、終了位置、全体件数を取得
                start, end, total = map(int, match.groups())
                # 現在表示されている最後の項目が全体件数より少なければ次のページがある
                return end < total
        
        # 方法2: 「次へ」ボタンの存在確認
        # 無効化されていない「次へ」ボタンがあれば次のページがある
        next_button = soup.select_one('button.ymuiPagination__button--next:not([disabled])')
        if next_button:
            return True
        
        # 方法3: データ件数による判断
        # 通常1ページに50件表示されるので、50件あれば次のページがある可能性が高い
        if len(self.extract_stock_data(soup)) >= 50:  # 通常1ページに50件表示
            return True
            
        # どの方法でも次のページが見つからなければFalseを返す
        return False

    def scrape_all_pages(self) -> List[List[str]]:
        """
        全ページのデータをスクレイピングするメソッド
        
        Returns:
            List[List[str]]: 全ページから収集した株価データのリスト
            
        注意:
            - 最大ページ数（self.max_pages）を超えた場合は処理を終了します
            - 次のページが存在しない場合も処理を終了します
            - リクエスト間には待機時間（self.sleep_time）を設けています
        """
        # 全データを格納するリストを初期化
        all_data = []
        
        # ページ番号を1から開始
        page = 1
        
        # 最大ページ数まで繰り返す
        while page <= self.max_pages:
            # 現在のページのHTMLを取得
            soup = self.fetch_page(page)
            
            # ページの取得に失敗した場合はループを終了
            if not soup:
                break
            
            # ページからデータを抽出
            data = self.extract_stock_data(soup)
            
            # データがない場合はループを終了
            if not data:
                logger.info(f"ページ {page} にデータがありません。終了します。")
                break
            
            # 抽出したデータを全データリストに追加
            all_data.extend(data)
            
            # 取得したデータ件数をログに記録
            logger.info(f"ページ {page} から {len(data)} 件のデータを取得しました")
            
            # 次のページが存在するかを確認
            has_more_pages = self.check_more_pages(soup, page)
            
            # 次のページがなければループを終了
            if not has_more_pages:
                logger.info("最終ページに到達しました。")
                break
            
            # 次のページへ進む
            page += 1
            
            # サーバー負荷軽減のために待機（次のリクエストまでの間）
            time.sleep(self.sleep_time)  
            
        # 収集したすべてのデータを返す
        return all_data

    def save_to_csv(self, data: List[List[str]], filename: Optional[str] = None) -> str:
        """
        収集したデータをCSVファイルに保存するメソッド
        
        Args:
            data (List[List[str]]): 保存するデータのリスト
            filename (Optional[str]): 保存先のファイル名（Noneの場合は日付から自動生成）
            
        Returns:
            str: 保存したファイル名、またはエラー時は空文字列
            
        注意:
            - 保存に失敗した場合はバックアップファイルへの保存を試みます
            - CSVはUTF-8 with BOMで保存され、Excelで文字化けせず開けます
        """
        # ファイル名が指定されていない場合は現在の日付をファイル名に使用
        if filename is None:
            today = datetime.now().strftime("%Y%m%d")  # YYYYMMDDの形式で日付を取得
            filename = f"{today}.csv"  # 日付.csv の形式でファイル名を生成
        
        try:
            # CSVファイルを書き込みモードで開く
            # newline="" は改行コードの自動変換を防ぐため
            # encoding="utf-8-sig" はBOMつきUTF-8でExcelでも文字化けしないようにするため
            with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
                # CSVライターオブジェクトを作成
                csv_writer = csv.writer(csvfile)
                
                # ヘッダー行を書き込む
                csv_writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])
                
                # データ行を書き込む
                csv_writer.writerows(data)
            
            # 保存成功をログに記録
            logger.info(f"データを {filename} に保存しました（合計 {len(data)} 件）")
            
            # 保存したファイル名を返す
            return filename
            
        except Exception as e:
            # 保存時にエラーが発生した場合
            logger.error(f"CSVファイル保存エラー: {e}")
            
            # バックアップとして別名でファイルを保存する試み
            # 日時を含めたファイル名でバックアップファイルを作成
            backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            logger.info(f"バックアップファイル {backup_filename} に保存を試みます")
            
            try:
                # バックアップファイルに保存を試みる
                with open(backup_filename, "w", newline="", encoding="utf-8-sig") as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"])
                    csv_writer.writerows(data)
                
                # バックアップ保存成功をログに記録
                logger.info(f"バックアップデータを {backup_filename} に保存しました")
                
                # バックアップファイル名を返す
                return backup_filename
                
            except Exception as e2:
                # バックアップファイルの保存にも失敗した場合
                logger.critical(f"バックアップファイル保存にも失敗しました: {e2}")
                
                # 失敗を示す空文字列を返す
                return ""

    def run(self) -> str:
        """
        スクレイピングの全処理を実行するメソッド
        
        Returns:
            str: 保存したCSVファイル名、またはエラー時は空文字列
            
        注意:
            - このメソッドは他のすべてのメソッドを順番に呼び出して処理を実行します
            - 予期せぬエラーが発生しても、できる限りキャッチしてログに記録します
        """
        # スクレイピング開始をログに記録
        logger.info("Yahoo!ファイナンス年初来高値ランキングのスクレイピングを開始します")
        
        try:
            # 全ページのデータをスクレイピング
            data = self.scrape_all_pages()
            
            # データが取得できなかった場合は空文字列を返す
            if not data:
                logger.warning("データが取得できませんでした")
                return ""
            
            # 取得したデータをCSVファイルに保存して、ファイル名を返す
            return self.save_to_csv(data)
            
        except Exception as e:
            # 予期せぬエラーが発生した場合はログに記録して空文字列を返す
            logger.error(f"予期せぬエラーが発生しました: {e}")
            return ""


def main():
    """
    メイン関数 - スクリプト実行時のエントリーポイント
    
    この関数は、YahooFinanceScraperクラスのインスタンスを作成し、
    スクレイピングを実行します。また、キーボード割り込みなどの
    例外処理も行います。
    """
    try:
        # YahooFinanceScraperクラスのインスタンスを作成
        # パラメータを指定して初期化
        scraper = YahooFinanceScraper(
            sleep_time=1,      # サーバー負荷軽減のための待機時間（秒）
            max_retries=3,     # 接続失敗時の最大リトライ回数
            max_pages=100      # 最大ページ数（無限ループ防止）
        )
        
        # スクレイピングを実行し、出力ファイル名を取得
        output_file = scraper.run()
        
        # 処理結果をログに記録
        if output_file:
            # 成功した場合の出力
            logger.info(f"処理が完了しました。出力ファイル: {output_file}")
        else:
            # 失敗した場合の出力
            logger.error("処理が失敗しました")
            
    except KeyboardInterrupt:
        # Ctrl+Cなどのキーボード割り込みが発生した場合
        logger.info("ユーザーによって処理が中断されました")
        
    except Exception as e:
        # その他の予期せぬエラーが発生した場合
        logger.critical(f"クリティカルエラーが発生しました: {e}")


# スクリプトが直接実行された場合（インポートされた場合は実行されない）
if __name__ == "__main__":
    # main関数を呼び出して処理を開始
    main()
