#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Yahoo!ファイナンス「年初来高値」ランキングを全ページ巡回してCSV化
- 取得項目: 名称, コード, 取引値, 前営業日までの年初来高値,
            前営業日までの年初来高値の日付, 高値
- 数値はカンマ区切りを除去、小数点も保持
- 外部ライブラリ不使用（標準ライブラリのみ）
- Python 3.10.12 / Linux 想定
"""

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

ROW_BLOCK_RE = re.compile(
    r'(<tr[^>]+class="RankingTable__row__1Gwp"[^>]*>.*?</tr>)',
    re.S | re.I
)
NAME_RE = re.compile(
    r'<a[^>]+href="https://finance\.yahoo\.co\.jp/quote/[^"]+"[^>]*>(.*?)</a>',
    re.S | re.I
)
CODE_RE = re.compile(
    r'<li[^>]*class="RankingTable__supplement__vv_m"[^>]*>\s*([0-9]{4})\s*</li>',
    re.S | re.I
)
SPAN_VAL_RE = re.compile(
    r'<span[^>]*class="StyledNumber__value__3rXW"[^>]*>\s*(.*?)\s*</span>',
    re.S | re.I
)
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
        return resp.read().decode(charset, errors="replace")

def load_local(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def clean_text(s: str) -> str:
    s = unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def normalize_number(s: str) -> str:
    """
    数値らしければ桁区切りカンマだけ除去して返す。
    小数点あり/なし、符号付きに対応。ダッシュ類は空に。
    """
    s = s.strip()
    if s in {'-', '—', '–'}:
        return ''
    s_no_commas = s.replace(',', '')
    if re.fullmatch(r'[-+]?\d+(?:\.\d+)?', s_no_commas):
        return s_no_commas
    return s_no_commas  # 数値でない場合もカンマ除去版を返す

def parse_row_block(block: str) -> Optional[RowItem]:
    name_m = NAME_RE.search(block)
    code_m = CODE_RE.search(block)
    if not name_m or not code_m:
        return None
    name = clean_text(name_m.group(1))
    code = clean_text(code_m.group(1))
    spans = [clean_text(x) for x in SPAN_VAL_RE.findall(block)]

    price = prev_high = prev_high_date = high = ""
    date_match = DATE_RE.search(block)
    date_text = date_match.group(1) if date_match else ""

    def looks_like_date(x: str) -> bool:
        return bool(DATE_RE.fullmatch(x))

    if len(spans) >= 4 and looks_like_date(spans[2]):
        price, prev_high, prev_high_date, high = spans[0], spans[1], spans[2], spans[3]
    else:
        if len(spans) >= 2:
            price = spans[0]
            prev_high = spans[1]
        prev_high_date = date_text or (spans[2] if len(spans) >= 3 and looks_like_date(spans[2]) else "")
        if len(spans) >= 4:
            high = spans[-1]
        elif len(spans) == 3 and not looks_like_date(spans[2]):
            high = spans[2]

    return RowItem(
        name=name,
        code=code,
        price=normalize_number(price),
        prev_ytd_high=normalize_number(prev_high),
        prev_ytd_high_date=prev_high_date,
        high=normalize_number(high)
    )

def parse_page(html: str) -> List[RowItem]:
    return [item for block in ROW_BLOCK_RE.findall(html)
            if (item := parse_row_block(block))]

def build_url(page: int) -> str:
    return BASE_URL if page == 1 else f"{BASE_URL}&page={page}"

def crawl_all(from_file: Optional[str] = None, max_pages: int = 200, sleep_sec: float = 0.7) -> List[RowItem]:
    all_rows: List[RowItem] = []
    page = 1
    while page <= max_pages:
        try:
            html = load_local(from_file) if page == 1 and from_file else fetch(build_url(page))
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                break
            break
        except Exception:
            break

        items = parse_page(html)
        if not items:
            break
        all_rows.extend(items)
        page += 1
        time.sleep(sleep_sec)

    # 重複除去
    seen, unique = set(), []
    for r in all_rows:
        key = (r.code, r.name, r.price, r.prev_ytd_high, r.prev_ytd_high_date, r.high)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

def today_str_jst() -> str:
    return datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")

def save_csv(rows: List[RowItem], filename: Optional[str] = None) -> str:
    filename = filename or f"{today_str_jst()}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["名称", "コード", "取引値", "前営業日までの年初来高値",
                         "前営業日までの年初来高値の日付", "高値"])
        for r in rows:
            writer.writerow([r.name, r.code, r.price, r.prev_ytd_high,
                             r.prev_ytd_high_date, r.high])
    return filename

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-file", help="1ページ目をローカルHTMLから読み込む")
    parser.add_argument("--out", help="出力ファイル名")
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=0.7)
    args = parser.parse_args()

    rows = crawl_all(from_file=args.from_file, max_pages=args.max_pages, sleep_sec=args.sleep)
    if not rows:
        print("データが取得できませんでした。")
        sys.exit(1)

    outpath = save_csv(rows, filename=args.out)
    print(f"{len(rows)}件を {outpath} に保存しました。")

if __name__ == "__main__":
    main()
