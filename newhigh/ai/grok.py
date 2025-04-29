"""
アルゴリズムの概要:
このスクリプトは、Yahoo! Finance Japanの年初来高値ランキングページから株情報を取得し、CSVファイルに保存します。
以下の手順で動作します：
1. ページ番号を指定してウェブページのHTMLを取得（1ページ目から順に）。
2. 取得したHTMLを解析し、表形式のデータ（名称、コード、取引値、前営業日までの年初来高値、日付、高値）を抽出。
3. 全ページのデータを収集するまで、ページを巡回（次のページが存在しない場合に終了）。
4. 収集したデータをCSVファイルに保存（ファイル名はYYYYMMDD.csv、例: 20250429.csv）。
5. 株価データのカンマ（例: 1,234 → 1234）を削除して数値として扱いやすくする。
6. エラー処理とログを活用して、問題が発生しても処理を適切に管理。

使用パッケージと選択理由:
1. **requests**:
   - 選択理由: ウェブページのHTMLを簡単に取得できる。軽量で高速、かつシンプルなAPIを提供。
   - 代替案: urllib (標準ライブラリ)、httpx。
   - 代替案を採用しなかった理由:
     - urllibは低レベルでコードが複雑になりがち。
     - httpxは非同期処理に優れるが、このスクリプトでは同期処理で十分。
2. **BeautifulSoup (beautifulsoup4)**:
   - 選択理由: HTMLの解析が簡単で、CSSセレクタやタグ検索が直感的。初心者にも扱いやすい。
   - 代替案: lxml、pyquery。
   - 代替案を採用しなかった理由:
     - lxmlは高速だが、Cライブラリの依存があり、インストールが複雑な場合がある。
     - pyqueryはjQuery風だが、BeautifulSoupの方がPythonコミュニティで広く使われている。
3. **pandas**:
   - 選択理由: 表形式データの処理とCSV保存が簡単。データフレーム形式でデータを整理しやすく、Excel互換の出力が可能。
   - 代替案: csvモジュール（標準ライブラリ）。
   - 代替案を採用しなかった理由: csvモジュールは低レベルで、データフレームの操作やエンコーディング管理が面倒。
4. **logging**:
   - 選択理由: 処理の進捗やエラーを記録するのに便利。標準ライブラリで依存関係がない。
   - 代替案: print文、loguru。
   - 代替案を採用しなかった理由:
     - print文はログ管理が難しい。
     - loguruは機能豊富だが、外部ライブラリを追加する必要がある。
5. **Seleniumを検討したが不採用**:
   - 検討理由: 動的ページ（JavaScriptで生成されるコンテンツ）のスクレイピングに強い。
   - 不採用理由: Yahoo! Financeの対象ページは静的HTMLで、requestsとBeautifulSoupで十分。Seleniumはブラウザ起動が必要で、処理が遅く、リソースを多く消費する。

その他の考慮:
- **非同期ライブラリ (aiohttp)**: 複数ページを並列取得すると高速化可能だが、初心者にとって非同期プログラミングは複雑。
- **データベース (sqlite3)**: 大量データの保存に適すが、今回はCSV出力が要件のため不要。
"""

import requests  # ウェブページを取得するためのライブラリ
from bs4 import BeautifulSoup  # HTMLを解析するためのライブラリ
import pandas as pd  # データを表形式で扱い、CSVに保存するためのライブラリ
from datetime import datetime  # 現在の日付を取得するためのライブラリ
import time  # 処理の間に待機時間を入れるためのライブラリ
import logging  # 処理の進捗やエラーを記録するためのライブラリ

# ロギングの設定（処理の状況を分かりやすく表示）
logging.basicConfig(
    level=logging.INFO,  # INFO以上のログを表示
    format='%(asctime)s - %(levelname)s - %(message)s'  # ログの形式（時間 - レベル - メッセージ）
)

# スクレイピングするページの基本URL
BASE_URL = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"

# ウェブサイトにアクセスする際のヘッダー（ブロックされないようにブラウザを装う）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_page(page_num):
    """
    指定されたページ番号のウェブページのHTMLを取得する関数。

    Args:
        page_num (int): 取得するページ番号（1から始まる）。

    Returns:
        str or None: 成功時はHTML文字列、失敗時はNone。
    """
    # ページ番号が1の場合は基本URL、2以降はページ指定を追加
    url = f"{BASE_URL}&page={page_num}" if page_num > 1 else BASE_URL
    try:
        # ウェブページを取得（ヘッダーとタイムアウトを設定）
        response = requests.get(url, headers=HEADERS, timeout=10)
        # エラーがあれば例外を発生させる
        response.raise_for_status()
        # 取得したHTMLを返す
        return response.text
    except requests.RequestException as e:
        # エラーが発生したらログに記録
        logging.error(f"ページ {page_num} の取得に失敗: {e}")
        # 失敗した場合はNoneを返す
        return None

def parse_page(html):
    """
    HTMLから株情報を抽出する関数。

    Args:
        html (str): 解析するHTML文字列。

    Returns:
        list: 抽出されたデータ（辞書のリスト）。
    """
    # HTMLを解析しやすい形に変換
    soup = BeautifulSoup(html, 'html.parser')
    # 表の行（<tr>タグ）を全て取得
    rows = soup.select('tbody tr.RankingTable__row__1Gwp')
    # データを格納するリスト
    data = []

    # 各行を処理
    for row in rows:
        try:
            # 名称を取得（<a>タグの中のテキスト）
            name_elem = row.select_one('td.RankingTable__detail__P452 a')
            # 名称が存在する場合はテキストを取得、なければ空文字
            name = name_elem.text.strip() if name_elem else ""
            # コードを取得（<li>タグの中のテキスト）
            code_elem = row.select_one('ul.RankingTable__supplements__15Cu li.RankingTable__supplement__vv_m')
            # コードが存在する場合はテキストを取得、なければ空文字
            code = code_elem.text.strip() if code_elem else ""

            # 数値データ（取引値、前営業日までの高値、日付、高値）を取得
            values = row.select('span.StyledNumber__value__3rXW')
            # 必要なデータが揃っているか確認（4つ以上必要）
            if len(values) >= 4:
                # 取引値を取得し、カンマを削除（例: 1,234 → 1234）
                trade_value = values[0].text.strip().replace(',', '')
                # 前営業日までの高値を取得し、カンマを削除
                prev_high = values[1].text.strip().replace(',', '')
                # 日付を取得（カンマなし）
                date = values[2].text.strip()
                # 高値を取得し、カンマを削除
                high = values[3].text.strip().replace(',', '')
            else:
                # データが不足している場合はこの行をスキップ
                continue

            # 抽出したデータを辞書形式でリストに追加
            data.append({
                "名称": name,
                "コード": code,
                "取引値": trade_value,
                "前営業日までの年初来高値": prev_high,
                "前営業日までの年初来高値の日付": date,
                "高値": high
            })
        except Exception as e:
            # 行の解析中にエラーがあればログに記録し、次の行へ
            logging.warning(f"行の解析中にエラー: {e}")
            continue

    # 抽出されたデータを返す
    return data

def main():
    """
    メイン処理：全ページからデータを収集し、CSVに保存。
    """
    # 全データを格納するリスト
    all_data = []
    # ページ番号を1から開始
    page_num = 1

    # 無限ループでページを順に処理
    while True:
        # 現在のページ番号をログに記録
        logging.info(f"ページ {page_num} を処理中...")
        # ページのHTMLを取得
        html = fetch_page(page_num)
        # HTMLが取得できなかった場合（ページ不存在など）は終了
        if not html:
            logging.info("ページが存在しないか、エラーが発生したため終了")
            break

        # HTMLからデータを抽出
        data = parse_page(html)
        # データがなければ（空のページ）終了
        if not data:
            logging.info(f"ページ {page_num} にデータがありません。終了")
            break

        # 抽出したデータを全体のリストに追加
        all_data.extend(data)
        # 次のページへ進む
        page_num += 1
        # サーバーに負担をかけないよう1秒待機
        time.sleep(1)

    # データが取得できた場合
    if all_data:
        # データを表形式（データフレーム）に変換
        df = pd.DataFrame(all_data)
        # 現在の日付をYYYYMMDD形式で取得（例: 20250429）
        today = datetime.now().strftime("%Y%m%d")
        # CSVファイル名を作成
        filename = f"{today}.csv"
        # データをCSVに保存（Excelで開けるようUTF-8 with BOMを使用）
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        # 保存成功をログに記録（データ件数も表示）
        logging.info(f"フェイシャルデータが {filename} に保存されました。{len(df)} 件")
    else:
        # データがなかった場合の警告
        logging.warning("データが取得できませんでした。")

if __name__ == "__main__":
    # スクリプトを実行
    main()
