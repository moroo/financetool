#!/usr/bin/env python3
import os
import sys
import csv

DATA_DIR = "/hddhome/home/jun/stock/newhigh"

def get_latest_file():
    """最新日付のCSVファイルを取得"""
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError("CSVファイルが見つかりません")
    files.sort(reverse=True)  # 日付降順
    return os.path.join(DATA_DIR, files[0])

def read_csv(filepath):
    """CSVファイルから (名称, コード) リストを取得"""
    result = []
    with open(filepath, newline="", encoding="utf-8-sig") as csvfile:  # BOM対応
        reader = csv.DictReader(csvfile)
        # ヘッダー名を正規化（空白削除）
        fieldnames = {name.strip(): name for name in reader.fieldnames}
        name_col = fieldnames.get("名称")
        code_col = fieldnames.get("コード")

        if name_col is None or code_col is None:
            raise KeyError(f"ヘッダーに '名称' または 'コード' が見つかりません: {reader.fieldnames}")

        for row in reader:
            result.append((row[name_col].strip(), row[code_col].strip()))
    return result

def count_newhigh_days(codes):
    """全ファイルから各コードの新高値日数をカウント"""
    counts = {code: {"name": name, "days": 0} for name, code in codes}
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    for f in files:
        with open(os.path.join(DATA_DIR, f), newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = {name.strip(): name for name in reader.fieldnames}
            code_col = fieldnames.get("コード")
            if code_col is None:
                continue
            file_codes = {row[code_col].strip() for row in reader}
            for code in counts:
                if code in file_codes:
                    counts[code]["days"] += 1
    return counts

def main():
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        target_file = get_latest_file()

    if not os.path.exists(target_file):
        raise FileNotFoundError(f"{target_file} が存在しません")

    codes = read_csv(target_file)
    counts = count_newhigh_days(codes)

    for code, info in counts.items():
        print(f"{info['name']} {code} {info['days']}")

if __name__ == "__main__":
    main()
