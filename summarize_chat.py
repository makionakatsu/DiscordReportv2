import os
import pandas as pd
import openai
import json

# GitHub SecretsからAPIキーを読み込む
openai.api_key = os.getenv('OPENAI_API_KEY')

# GPT-3.5-turboを使ってテキストを要約する関数を定義
def summarize_with_gpt(text):
    # GPT-3.5-turboを使ってテキストを要約
    response_summary = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": "You are an assistant who summarizes discord chat in Japanese."},
            {"role": "user", "content": f"Here's a discord chat: {text}. Can you summarize it for me in japanese?"},
        ],
        max_tokens=300
    )

    # 要約結果を取得
    summary = response_summary['choices'][0]['message']['content']

    return summary

# Discordチャットの要約を作成する関数を定義
def summarize_discord_chat(csv_file):
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)

    # データをチャンネルと絵文字数でソート
    df_sorted = df.sort_values(['Channel', 'Emoji Count'], ascending=[True, False])

    # コメントが存在し、かつ絵文字数が多い順にソート
    df_sorted = df_sorted[df_sorted['Content'].notna()].sort_values(['Channel', 'Emoji Count'], ascending=[True, False])

    channel_summary_dict = {}
    for channel, group in df_sorted.groupby('Channel'):
        # チャンネル内の上位コメントを取得
        top_comments = group.head(5)

        # コメント数が5つに満たない場合、ランダムにコメントを選んで補う
        if len(top_comments) < 5:
            remaining_comments = group.drop(top_comments.index)
            additional_comments = remaining_comments.sample(5 - len(top_comments))
            top_comments = pd.concat([top_comments, additional_comments])

        # チャンネル内の上位コメントをすべて連結
        text = ' '.join(top_comments['Content'].values)

        # GPT-3.5-turboを使ってチャットを要約
        summary = summarize_with_gpt(text)

        # 要約結果と上位コメントを保存
        channel_summary_dict[channel] = {'summary': summary, 'top_comments': top_comments[['Content', 'Message URL']].values.tolist()}
    
    return channel_summary_dict

# メインの処理
if __name__ == "__main__":
    # 環境変数からCSVファイル名を取得
    csv_file = os.getenv('CSV_FILE')
    # デバッグ用にCSV_FILEの値を出力
    print(f'CSV_FILE: {csv_file}')
    # CSVファイルを読み込んでDiscordチャットを要約
    summaries = summarize_discord_chat(csv_file)

    # 結果をJSON形式で保存
    with open('summaries.json', 'w') as f:
        json.dump(summaries, f)

