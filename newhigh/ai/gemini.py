"""
スクレイピングアルゴリズム概要:

1.  **URL生成:**
    * ベースとなるURLと、ページ番号を組み合わせて、スクレイピング対象のURLを生成します。
2.  **Webページ取得:**
    * `requests` ライブラリを使用して、指定されたURLからHTMLコンテンツを取得します。
3.  **HTML解析:**
    * `BeautifulSoup` ライブラリを使用して、取得したHTMLコンテンツを解析し、必要な情報を抽出できるようにします。
4.  **データ抽出:**
    * 解析されたHTMLから、株価の「名称」「コード」「取引値」などの情報を、CSSセレクタや正規表現を用いて抽出します。
5.  **ページネーション処理:**
    * Webページに複数のページがある場合、次のページへのリンクを特定し、上記のステップを繰り返して全てのページのデータを取得します。
6.  **データ整形:**
    * 抽出したデータから不要な文字（例：カンマ）を削除したり、データ型を変換したりします。
7.  **CSVファイル出力:**
    * 抽出・整形したデータを `csv` ライブラリを使用してCSVファイルに書き込みます。

ライブラリ選択理由:

* **requests:**
    * 理由: WebページからHTMLコンテンツを取得するために、シンプルで使いやすい`requests`ライブラリを選択しました。`urllib`なども考えられましたが、`requests`の方がより高レベルで、記述が簡潔になるため、こちらを採用しました。
    * 使わなかった理由: `urllib`
* **BeautifulSoup:**
    * 理由: 取得したHTMLを解析するために、`BeautifulSoup`ライブラリを選択しました。HTML構造を簡単に操作でき、必要な情報を抽出するのに便利です。`lxml`なども考えられましたが、`BeautifulSoup`は標準ライブラリにも含まれており、扱いやすいためこちらを採用しました。
    * 使わなかった理由: `lxml`
* **csv:**
    * 理由: 抽出したデータをCSVファイルに書き込むために、標準ライブラリの`csv`モジュールを選択しました。特別なインストールも不要で、CSVファイルの読み書きを簡単に行えます。`pandas`も考えられましたが、今回はCSVファイルの基本的な書き込みのみなので、`csv`で十分と判断しました。
    * 使わなかった理由: `pandas`
* **Selenium:**
    * 理由: 今回のスクレイピング対象のWebサイトは、`requests`と`BeautifulSoup`の組み合わせで必要な情報を取得できたため、使用しませんでした。Seleniumは、JavaScriptで動的に生成されるWebページを扱う場合に強力ですが、オーバーヘッドが大きく、速度も遅くなるため、今回はより軽量な方法を選択しました。
    * 使った場合: JavaScriptで生成されるページを扱う必要がある場合

"""

import requests  # Webページを取得するためのライブラリ
from bs4 import BeautifulSoup  # HTMLを解析するためのライブラリ
import csv  # CSVファイルを扱うためのライブラリ
from datetime import datetime  # 日付と時刻を扱うためのライブラリ
import re  # 正規表現を扱うためのライブラリ
import time  # 時間を制御するためのライブラリ
import logging  # ログを記録するためのライブラリ

# ロギングの設定（エラーの詳細を記録）
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


def scrape_stock_data(base_url, max_pages=10):
    """
    Yahoo!ファイナンスから年初来高値の株式データをスクレイピングし、CSVファイルに保存する。
    複数ページに対応。ページネーションをよりロバストに処理。

    Args:
        base_url (str): スクレイピングするURLのベース部分。
        max_pages (int, optional): 最大ページ数。無限ループを防ぐための安全策。デフォルトは10。

    Returns:
        list: 抽出した株価データのリスト。各要素は株価情報を表すリスト。
    """

    data = []  # 抽出したデータを格納するリスト
    page_num = 1  # 現在処理中のページ番号
    session = requests.Session()  # セッションを利用して接続を維持（効率のため）
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })  # User-Agentを設定（Webサイトに人間だと思わせるため）

    while page_num <= max_pages:  # 最大ページ数までループ
        url = f"{base_url}&page={page_num}" if page_num > 1 else base_url  # ページ番号をURLに追加
        print(f"Scraping page {page_num}: {url}")  # どのページを処理しているかを表示

        try:
            response = session.get(url, timeout=10)  # URLからHTMLを取得 (10秒でタイムアウト)
            response.raise_for_status()  # HTTPエラーが発生した場合に例外を発生させる
            soup = BeautifulSoup(response.content, "html.parser")  # HTMLを解析
        except requests.exceptions.RequestException as e:  # requests関連のエラーをキャッチ
            logging.error(f"Error accessing URL {url}: {e}")  # エラーをログに記録
            print(f"Failed to retrieve data from {url}. Skipping page.")  # エラーメッセージを表示
            page_num += 1  # エラーが発生しても次のページへ
            continue  # 次のループへ

        table = soup.find("div", id="item").find("table")  # 'item' IDのdiv内のtable要素を取得
        if not table:  # table要素が見つからなかった場合
            logging.error(f"No table found on {url}. Stopping.")  # エラーをログに記録
            print(f"No data table found on this page. Stopping.")  # エラーメッセージを表示
            break  # ループを抜ける

        rows = table.find_all("tr")  # table内の全てのtr要素（行）を取得
        if not rows:  # 行が見つからなかった場合
            logging.warning(f"No table rows found on {url}. Skipping page.")  # 警告をログに記録
            print(f"No data rows found on page {page_num}. Skipping.")  # 警告メッセージを表示
            page_num += 1  # 次のページへ
            continue  # 次のループへ

        for row in rows[1:]:  # ヘッダー行をスキップして、各行を処理
            cells = row.find_all("td")  # 行内の全てのtd要素（セル）を取得
            if not cells:  # セルがない場合はスキップ
                continue

            try:
                # 各セルからデータを抽出
                (
                    name,  # 株の名称
                    code,  # 株のコード
                    price,  # 現在の株価
                    prev_high_value,  # 前営業日までの年初来高値
                    prev_high_date,  # 前営業日までの年初来高値の日付
                    high_price,  # 年初来高値
                ) = extract_row_data(cells)  # 抽出処理を行う関数を呼び出し
                data.append([name, code, price, prev_high_value, prev_high_date, high_price])  # 抽出したデータをリストに追加
            except ValueError as e:  # データ抽出時にエラーが発生した場合
                logging.error(f"Failed to extract data from row: {e}")  # エラーをログに記録
                print(f"Error processing a row. Skipping.")  # エラーメッセージを表示

        # ページネーション（次のページがあるか確認）
        next_page_exists = check_next_page(soup)  # 次のページがあるか確認する関数を呼び出し
        if next_page_exists:  # 次のページがある場合
            page_num += 1  # ページ番号をインクリメント
            print(f"Moving to next page: {page_num}")  # 次のページへ移動するメッセージを表示
            time.sleep(1)  # 1秒待機 (Webサイトへの負荷軽減)
        else:  # 次のページがない場合
            print("Reached the last page.")  # 最後のページに到達したメッセージを表示
            break  # ループを抜ける

    return data  # 抽出したデータを返す


def extract_row_data(cells):
    """
    テーブルの行（tr要素）から、株価データを抽出する。

    Args:
        cells (list): テーブルの行内の各セル（td要素）のリスト。

    Returns:
        tuple: 抽出した株価データのタプル (name, code, price, prev_high_value, prev_high_date, high_price)。

    Raises:
        ValueError: セルの数が足りない場合に発生する例外。
    """
    if len(cells) < 4:  # セルの数が4未満の場合（必要なデータが揃っていない）
        raise ValueError("Not enough cells in row")  # 例外を発生させる

    name_code_cell = cells[0]  # 1番目のセル（名称・コード）
    name_element = name_code_cell.find("a")  # セル内のa要素（名称）
    code_element = name_code_cell.find("li", class_="RankingTable__supplement__vv_m")  # セル内のli要素（コード）
    name = name_element.text.strip() if name_element else "N/A"  # a要素があればテキストを取得、なければ"N/A"
    code = code_element.text.strip() if code_element else "N/A"  # li要素があればテキストを取得、なければ"N/A"

    price_cell = cells[1]  # 2番目のセル（取引値）
    price_element = price_cell.find("span", class_="StyledNumber__value__3rXW")  # セル内のspan要素（取引値）
    price = price_element.text.replace(",", "").strip() if price_element else "N/A"  # span要素があればテキストを取得、カンマを除去、なければ"N/A"

    prev_high_cell = cells[2]  # 3番目のセル（前営業日までの年初来高値、日付）
    prev_high_value_element = prev_high_cell.find("span", class_="StyledNumber__value__3rXW")  # セル内のspan要素（前営業日までの年初来高値）
    prev_high_date_element = prev_high_cell.find("span", class_="StyledNumber__value__3rXW", string=re.compile(r'\d{4}/\d{2}/\d{2}'))  # セル内の日付を含むspan要素
    prev_high_value = prev_high_value_element.text.replace(",", "").strip() if prev_high_value_element else "N/A"  # span要素があればテキストを取得、カンマを除去、なければ"N/A"
    prev_high_date = prev_high_date_element.text.strip() if prev_high_date_element else "N/A"  # 日付を含むspan要素があればテキストを取得、なければ"N/A"

    high_cell = cells[3]  # 4番目のセル（高値）
    high_value_element = high_cell.find("span", class_="StyledNumber__value__3rXW")  # セル内のspan要素（高値）
    high_price = high_value_element.text.replace(",", "").strip() if high_value_element else "N/A"  # span要素があればテキストを取得、カンマを除去、なければ"N/A"

    return name, code, price, prev_high_value, prev_high_date, high_price  # 抽出したデータを返す


def check_next_page(soup):
    """
    BeautifulSoupオブジェクトから、次のページが存在するかどうかを判定する。

    Args:
        soup (BeautifulSoup): 解析済みのHTMLを表すBeautifulSoupオブジェクト。

    Returns:
        bool: 次のページが存在する場合はTrue、存在しない場合はFalse。
    """
    paging_div = soup.find("div", id="pagertop")  # ページネーション情報を含むdiv要素を取得
    if not paging_div:  # ページネーション情報がない場合
        return False  # 次のページはないと判定
    next_button = paging_div.find("button", {"data-cl-params": "_cl_link:next;_cl_position:0"})  # "次のページ"ボタンを取得
    return next_button is not None and "disabled" not in next_button.attrs  # ボタンが存在し、disabled属性がなければTrue


def save_to_csv(data, filename="stock_data.csv"):
    """
    抽出した株価データをCSVファイルに保存する。

    Args:
        data (list): 抽出した株価データのリスト。
        filename (str, optional): 保存するCSVファイルの名前。デフォルトは"stock_data.csv"。
    """
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:  # CSVファイルを開く
            csv_writer = csv.writer(csvfile)  # CSVライターオブジェクトを作成
            csv_writer.writerow(  # ヘッダー行を書き込む
                ["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"]
            )
            csv_writer.writerows(data)  # データ行を書き込む
        print(f"Data successfully written to {filename}")  # 保存成功メッセージを表示
    except Exception as e:  # ファイル書き込み中にエラーが発生した場合
        logging.error(f"Error writing to CSV file: {e}")  # エラーをログに記録
        print(f"Error writing to CSV file: {e}")  # エラーメッセージを表示


def main():
    """
    スクリプトのメイン処理を実行する。
    """
    base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"  # スクレイピング対象のURL
    all_data = scrape_stock_data(base_url)  # 株価データをスクレイピング
    if all_data:  # データが取得できた場合
        today = datetime.now().strftime("%Y%m%d")  # 現在の日付を取得
        save_to_csv(all_data, f"{today}_stock_data.csv")  # CSVファイルに保存
    else:  # データが取得できなかった場合
        print("No data to save.")  # メッセージを表示


if __name__ == "__main__":
    main()  # スクリプトが直接実行された場合にmain関数を呼び出す
