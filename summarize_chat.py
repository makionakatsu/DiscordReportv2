import os
import json
import openai
from operator import itemgetter

# 必要な環境変数を取得
openai.api_key = os.getenv('OPENAI_API_KEY')

# GPTを使ってテキストを要約する関数を定義
def summarize_with_gpt(text):
    # テキストが存在するかどうかチェック
    if not text:
        return None

    try:
        response_summary = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "You are CHIPS, an assistant who is responsible for reviewing Discord's daily chat logs and providing comprehensive summaries of topics in Japanese."},
                {"role": "user", "content": f"Based on the following text, please explain in Japanese what topics were discussed. Please limit your commentary to 80 characters or less, 200 characters at most. text: {text}"},
            ],
            max_tokens=300
        )
        summary = response_summary['choices'][0]['message']['content']
        return summary
    except Exception as e:
        print(f"GPT-3.5-turboでの要約中にエラーが発生しました: {e}")
        return None

# JSONファイルからメッセージを読み込む関数を定義
def load_messages():
    try:
        with open('logs.json', 'r', encoding='utf-8') as f:
            messages = json.load(f)
        return messages
    except Exception as e:
        print(f"JSONからのメッセージの読み込み中にエラーが発生しました: {e}")
        return []

# メッセージをチャンネルごとに分類する関数を定義
def categorize_messages_by_channel(messages):
    categorized_messages = {}
    for message in messages:
        channel_name = message['Channel']
        if channel_name not in categorized_messages:
            categorized_messages[channel_name] = []
        categorized_messages[channel_name].append(message)
    return categorized_messages

# スキップするチャンネルを設定ファイルから取得
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    skip_channels = [channel_dict['channel_id'] for channel_dict in config['skip_channels']]
except FileNotFoundError:
    print("エラー: config.json ファイルが見つかりませんでした。")
    skip_channels = []
except KeyError as e:
    print(f"エラー: 設定ファイルに {str(e)} というキーが見つかりませんでした。")
    skip_channels = []
except Exception as e:
    print(f"エラー: 予期しないエラーが発生しました: {e}")
    skip_channels = []

# メッセージを要約する関数を定義
def summarize_messages(categorized_messages):
    summarized_messages = {}
    for channel, messages in categorized_messages.items():
        # スキップするチャンネルをスキップ
        if channel in skip_channels:
            continue
        # メッセージをリアクション数でソート
        sorted_messages = sorted(messages, key=itemgetter('ReactionCount'), reverse=True)
        # トップ10のメッセージを要約
        top10_messages = sorted_messages[:min(10, len(sorted_messages))]
        channel_summary = summarize_with_gpt(' '.join([message['Content'] for message in top10_messages]))
        # 要約がNoneの場合、このチャンネルをスキップ
        if channel_summary is None:
            continue
        # トップ5のメッセージを要約
        top5_messages = sorted_messages[:min(5, len(sorted_messages))]
        top5_summaries = []
        for message in top5_messages:
            summary = summarize_with_gpt(message['Content'])
            # 要約がNoneの場合、このメッセージをスキップ
            if summary is None:
                continue
            top5_summaries.append({
                "Summary": summary,
                "URL": message['Message URL']
            })
        # 要約を保存
        summarized_messages[channel] = {
            "Channel Name": channel,
            "Channel URL": messages[0]['Channel URL'],  # 任意のメッセージからチャンネルURLを取得
            "Channel Summary": channel_summary,
            "Top 5 Message Summaries": top5_summaries
        }
    return summarized_messages

# 要約をJSONファイルに出力する関数を定義
def output_summary_to_json(summarized_messages):
    try:
        with open('summary.json', 'w', encoding='utf-8') as f:
            json.dump(summarized_messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"JSONへの書き込み中にエラーが発生しました: {e}")

# メイン処理を定義
def main():
    messages = load_messages()
    if messages:
        categorized_messages = categorize_messages_by_channel(messages)
        summarized_messages = summarize_messages(categorized_messages)
        output_summary_to_json(summarized_messages)

# メイン処理を実行
if __name__ == '__main__':
    main()





import nextcord
from nextcord.ext import commands

# 環境変数から必要な情報を取得
discord_token = os.getenv('DISCORD_TOKEN')
summary_channel_id = "1100924556585226310"  # サマリーチャンネルのID

# Botのインスタンスを作成
intents = nextcord.Intents.default()  # デフォルトのIntentsオブジェクトを作成
bot = commands.Bot(command_prefix='!', intents=intents)  # Botのインスタンスを作成

@bot.event
async def on_ready():
    # サマリーチャンネルをIDで直接取得
    summary_channel = bot.get_channel(int(summary_channel_id))
    if not summary_channel:
        print(f"ID {summary_channel_id} のチャンネルが見つかりません。チャンネルIDを確認してください。")
        return

    # summary.jsonを送信
    await summary_channel.send(file=nextcord.File('summary.json'))

    # 全ての操作が完了した後でbotを閉じる
    await bot.loop.run_until_complete(bot.close())

# Botを起動
bot.run(discord_token)
