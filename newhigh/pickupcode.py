import os
import pandas as pd
from datetime import datetime, timedelta

# ディレクトリのパス
DATA_DIR = '/hddhome/home/jun/stock/newhigh'

# CSVファイルの一覧を日付順に取得
files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.csv')])

# 日付のリスト（営業日として扱う）
dates = [f.replace('.csv', '') for f in files]

# 銘柄ごとの出現記録を保持
stock_presence = {}

# 日付→データフレームのキャッシュ
data_by_date = {}

# 各ファイルを読み込み、情報を格納
for f in files:
    date_str = f.replace('.csv', '')
    filepath = os.path.join(DATA_DIR, f)
    df = pd.read_csv(filepath)
    df['日付'] = date_str
    data_by_date[date_str] = df

    for code in df['コード']:
        if code not in stock_presence:
            stock_presence[code] = []
        stock_presence[code].append(date_str)

# 最新日付と10営業日前の取得
latest_date = dates[-1]
date_10_days_ago = dates[-11]  # 0-based indexing

# 10営業日前のデータ
df_10_days_ago = data_by_date[date_10_days_ago]

# 条件を満たす銘柄コードのリスト
result_codes = []

for _, row in df_10_days_ago.iterrows():
    code = str(row['コード'])
    high_date_str = row['前営業日までの年初来高値の日付']
    high_date = datetime.strptime(high_date_str, '%Y/%m/%d')
    current_date = datetime.strptime(date_10_days_ago, '%Y%m%d')

    # 条件2: 年初来高値の日付が30日以上前
    if (current_date - high_date).days < 30:
        continue

    # 条件3: 最新のデータに存在すること
    if code not in data_by_date[latest_date]['コード'].astype(str).values:
        continue

    # 条件4: 直近10営業日中8日以上出現していること
    recent_10_days = dates[-10:]
    presence_count = sum([1 for d in recent_10_days if code in data_by_date[d]['コード'].astype(str).values])
    if presence_count >= 8:
        result_codes.append(code)

# 結果の表示
print("条件を満たす銘柄コード:")
for code in result_codes:
    print(code)
