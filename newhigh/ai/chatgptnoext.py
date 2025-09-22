#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Yahoo!ファイナンス「年初来高値」ランキングを全ページ巡回してCSV化
- 取得項目: 名称, コード, 取引値, 前営業日までの年初来高値, 前営業日までの年初来高値の日付, 高値
- 1ページ50件、2ページ目以降は ?page=N
- 外部ライブラリ不使用（標準ライブラリのみ）
- Python 3.10.12 / Linux 想定
"""

from __future__ import annotations
import csv
import sys
import re
import time
import urllib.request
import urllib.error
from html import unescape
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse

BASE_URL = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh?market=all&term=daily"
ROW_START_RE = re.compile(r'<tr[^>]+class="RankingTable__row__1Gwp"[^>]*>', re.I)
ROW_BLOCK_RE = re.compile(
    r'(<tr[^>]+class="RankingTable__row__1Gwp"[^>]*>.*?</tr>)',
    re.S | re.I
)

# 名称
NAME_RE = re.compile(
    r'<a[^>]+href="https://finance\.yahoo\.co\.jp/quote/[^"]+"[^>]*>(.*?)</a>',
    re.S | re.I
)
# 証券コード（ul/li内）
CODE_RE = re.compile(
    r'<li[^>]*class="RankingTable__supplement__vv_m"[^>]*>\s*([0-9]{4})\s*</li>',
    re.S | re.I
)
# 値（取引値/年初来高値/日付/高値）※順序で拾う
SPAN_VAL_RE = re.compile(
    r'<span[^>]*class="StyledNumber__value__3rXW"[^>]*>\s*(.*?)\s*</span>',
    re.S | re.I
)
# 日付パターン
DATE_RE = re.compile(r'(\d{4}/\d{2}/\d{2})')

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

@dataclass
class RowItem:
    name: str
    code: str
    price: str
    prev_ytd_high: str
    prev_ytd_high_date: str
    high: str

def fetch(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read().decode(charset, errors="replace")
        return html

def load_local(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def clean_text(s: str) -> str:
    # HTMLアンエスケープ + タグ内テキスト整形
    s = unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def parse_row_block(block: str) -> Optional[RowItem]:
    """
    1つの<tr class="RankingTable__row__1Gwp"> ... </tr> を解析してRowItemを返す
    期待順序（サンプルに基づく）:
      <a>名称</a>
      <li>コード</li>
      <span>取引値</span>
      <span>前営業日までの年初来高値</span>
      <span>前営業日までの年初来高値の日付</span>  ※日付span。まれに崩れていてもDATE_REで拾う
      <span>高値</span>
    """
    name_m = NAME_RE.search(block)
    code_m = CODE_RE.search(block)
    if not name_m or not code_m:
        return None

    name = clean_text(name_m.group(1))
    code = clean_text(code_m.group(1))

    spans = [clean_text(x) for x in SPAN_VAL_RE.findall(block)]

    # 取引値/前営業日までの年初来高値/日付/高値 を順序で想定
    price = prev_high = prev_high_date = high = ""

    # 日付は崩れ対策として別途抽出も試す
    date_match = DATE_RE.search(block)
    date_text = date_match.group(1) if date_match else ""

    # 通常は spans[0]=取引値, spans[1]=前営業日までの年初来高値, spans[2]=日付, spans[3]=高値
    # ただし広告やDOM変更で数がずれる可能性があるため、数と日付を確認して柔軟に対応
    # 数字はカンマを残す（ユーザー要件に明示無し）。必要なら削除可。
    def looks_like_date(x: str) -> bool:
        return bool(DATE_RE.fullmatch(x))

    # まず4つ連続で取れるケースを優先
    if len(spans) >= 4 and looks_like_date(spans[2]):
        price, prev_high, prev_high_date, high = spans[0], spans[1], spans[2], spans[3]
    else:
        # バックアップ：最初の2つは価格想定、日付はDATE_REで、最後を高値に
        if len(spans) >= 2:
            price = spans[0]
            prev_high = spans[1]
        prev_high_date = date_text or (spans[2] if len(spans) >= 3 and looks_like_date(spans[2]) else "")
        if len(spans) >= 4:
            high = spans[-1]  # 一番最後を高値とみなす
        elif len(spans) == 3 and not looks_like_date(spans[2]):
            high = spans[2]

    return RowItem(
        name=name,
        code=code,
        price=price,
        prev_ytd_high=prev_high,
        prev_ytd_high_date=prev_high_date,
        high=high
    )

def parse_page(html: str) -> List[RowItem]:
    rows: List[RowItem] = []
    for block in ROW_BLOCK_RE.findall(html):
        item = parse_row_block(block)
        if item:
            rows.append(item)
    return rows

def build_url(page: int) -> str:
    if page <= 1:
        return BASE_URL
    return f"{BASE_URL}&page={page}"

def crawl_all(from_file: Optional[str] = None, max_pages: int = 200, sleep_sec: float = 0.7) -> List[RowItem]:
    all_rows: List[RowItem] = []
    page = 1
    while page <= max_pages:
        try:
            if page == 1 and from_file:
                html = load_local(from_file)
            else:
                url = build_url(page)
                html = fetch(url)
        except urllib.error.HTTPError as e:
            # 404/410などで終了
            if e.code in (404, 410):
                break
            # 一時的なエラーはスキップ/終了判断
            break
        except Exception:
            # ネットワーク・DNS等のエラーはループ終了
            break

        items = parse_page(html)
        if not items:
            # データが取れないページが来たら終了
            break

        all_rows.extend(items)
        page += 1
        time.sleep(sleep_sec)

    # 重複除去（コード+名称+取引値などで一応キー化）
    seen = set()
    unique_rows: List[RowItem] = []
    for r in all_rows:
        key = (r.code, r.name, r.price, r.prev_ytd_high, r.prev_ytd_high_date, r.high)
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)
    return unique_rows

def today_str_jst() -> str:
    jst = ZoneInfo("Asia/Tokyo")
    return datetime.now(jst).strftime("%Y%m%d")

def save_csv(rows: List[RowItem], filename: Optional[str] = None) -> str:
    if filename is None:
        filename = f"{today_str_jst()}.csv"
    header = ["名称", "コード", "取引値", "前営業日までの年初来高値", "前営業日までの年初来高値の日付", "高値"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in rows:
            writer.writerow([r.name, r.code, r.price, r.prev_ytd_high, r.prev_ytd_high_date, r.high])
    return filename

def main():
    parser = argparse.ArgumentParser(
        description="Yahoo!ファイナンス年初来高値ランキングを全件取得してCSV出力（標準ライブラリのみ）"
    )
    parser.add_argument("--from-file", help="テスト用：ローカルHTML（例: yahoohigh.html）を1ページ目として解析", default=None)
    parser.add_argument("--max-pages", type=int, default=200, help="最大ページ数（デフォルト200）")
    parser.add_argument("--sleep", type=float, default=0.7, help="ページ間スリープ秒（デフォルト0.7s）")
    parser.add_argument("--out", default=None, help="出力CSV名（省略時はJSTで今日のYYYYMMDD.csv）")
    args = parser.parse_args()

    rows = crawl_all(from_file=args.from_file, max_pages=args.max_pages, sleep_sec=args.sleep)
    if not rows:
        print("取得結果が空でした。HTML構造の変更やアクセス制限の可能性があります。")
        sys.exit(1)

    outpath = save_csv(rows, filename=args.out)
    print(f"保存しました: {outpath}  （{len(rows)}件）")

if __name__ == "__main__":
    main()
