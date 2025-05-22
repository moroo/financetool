import os
import argparse
import pandas as pd
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="条件に合う銘柄コードを抽出")
    parser.add_argument('-p', '--period', type=int, default=10, help='基準営業日からの期間 (例: 10営業日前)')
    parser.add_argument('-d', '--datadir', type=str, default='/hddhome/home/jun/stock/newhigh', help='CSVファイルが保存されているディレクトリ')
    parser.add_argument('-t', '--past_high_threshold', type=int, default=30, help='前営業日までの年初来高値日からの日数しきい値')
    parser.add_argument('-m', '--min_appearance', type=int, default=8, help='指定期間内に銘柄が出現すべき最小営業日数')
    parser.add_argument('-o', '--output', type=str, help='結果を保存するCSVファイルのパス')
    return parser.parse_args()

def main():
    args = parse_args()

    # CSVファイルの一覧を日付順に取得
    files = sorted([f for f in os.listdir(args.datadir) if f.endswith('.csv')])
    if len(files) <= args.period:
        print("ファイル数が足りません")
        return

    # 日付のリスト
    dates = [f.replace('.csv', '') for f in files]

    # 銘柄出現記録と日付→データフレームキャッシュ
    stock_presence = {}
    data_by_date = {}

    for f in files:
        date_str = f.replace('.csv', '')
        filepath = os.path.join(args.datadir, f)
        df = pd.read_csv(filepath)
        df['日付'] = date_str
        data_by_date[date_str] = df

        for code in df['コード']:
            stock_presence.setdefault(str(code), []).append(date_str)

    # 最新日付と基準日
    latest_date = dates[-1]
    target_date = dates[-(args.period + 1)]

    df_target = data_by_date[target_date]
    result = []

    for _, row in df_target.iterrows():
        code = str(row['コード'])
        high_date_str = row['前営業日までの年初来高値の日付']
        try:
            high_date = datetime.strptime(high_date_str, '%Y/%m/%d')
        except ValueError:
            continue
        current_date = datetime.strptime(target_date, '%Y%m%d')

        # 条件2: 年初来高値の日付が過去past_high_threshold日以上前
        if (current_date - high_date).days < args.past_high_threshold:
            continue

        # 条件3: 最新データに存在
        if code not in data_by_date[latest_date]['コード'].astype(str).values:
            continue

        # 条件4: 直近period営業日中にmin_appearance回以上出現
        recent_days = dates[-args.period:]
        count = sum(code in data_by_date[d]['コード'].astype(str).values for d in recent_days)
        if count >= args.min_appearance:
            result.append({'コード': code, '抽出基準日': target_date})

    # 結果表示
    print("条件を満たす銘柄コード:")
    for item in result:
        print(item['コード'])

    # 出力オプション
    if args.output:
        df_out = pd.DataFrame(result)
        df_out.to_csv

if __name__ == '__main__':
    main()
