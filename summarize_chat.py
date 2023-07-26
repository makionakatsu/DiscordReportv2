import os
import json
import openai
from operator import itemgetter

# 必要な環境変数を取得
openai.api_key = os.getenv('OPENAI_API_KEY')

# GPT-3.5-turboを使ってテキストを要約する関数
def summarize_with_gpt(text):
    try:
        response_summary = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "This is CHIPS-kun, an assistant who summarizes Discord chats in Japanese, and CHIPS-kun always tries to summarize in a cheerful and fun atmosphere. He also occasionally uses pictograms."},
                {"role": "user", "content": f" {text}. Could you please summarize the following sentence in Japanese so that it is within 200 characters? If the original message is short, please summarize it even shorter."},
            ],
            max_tokens=300
        )
        summary = response_summary['choices'][0]['message']['content']
        return summary
    except Exception as e:
        print(f"Error occurred while summarizing with GPT-3.5-turbo: {e}")
        return None

# JSONファイルからメッセージを読み込む関数
def load_messages():
    try:
        with open('logs.json', 'r', encoding='utf-8') as f:
            messages = json.load(f)
        return messages
    except Exception as e:
        print(f"Error occurred while loading messages from JSON: {e}")
        return []

# メッセージをチャンネルごとに分類する関数
def categorize_messages_by_channel(messages):
    categorized_messages = {}
    for message in messages:
        channel_name = message['Channel']
        if channel_name not in categorized_messages:
            categorized_messages[channel_name] = []
        categorized_messages[channel_name].append(message)
    return categorized_messages

# メッセージを要約する関数
def summarize_messages(categorized_messages):
    summarized_messages = {}
    for channel, messages in categorized_messages.items():
        # リアクション数でソート
        sorted_messages = sorted(messages, key=itemgetter('ReactionCount'), reverse=True)

        # 上位10件のメッセージを要約
        top10_messages = sorted_messages[:min(10, len(sorted_messages))]
        channel_summary = summarize_with_gpt(' '.join([message['Content'] for message in top10_messages]))

        # 上位5件のメッセージを要約
        top5_messages = sorted_messages[:min(5, len(sorted_messages))]
        top5_summaries = []
        for message in top5_messages:
            summary = summarize_with_gpt(message['Content'])
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

# 要約をJSONファイルに出力する関数
def output_summary_to_json(summarized_messages):
    try:
        with open('summary.json', 'w', encoding='utf-8') as f:
            json.dump(summarized_messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error occurred while writing to JSON: {e}")

# メインの処理
def main():
    messages = load_messages()
    if messages:
        categorized_messages = categorize_messages_by_channel(messages)
        summarized_messages = summarize_messages(categorized_messages)
        output_summary_to_json(summarized_messages)

if __name__ == '__main__':
    main()
    
    
    
'''
import os
import nextcord
import nextcord as discord
from nextcord.ext import commands

# 環境変数から必要な情報を取得
discord_token = os.getenv('DISCORD_TOKEN')
summary_channel_id = os.getenv('SUMMARY_CHANNEL_NAME')

# Botのインスタンスを作成します。
intents = discord.Intents.default()  # デフォルトのIntentsオブジェクトを作成します。
bot = commands.Bot(command_prefix='!', intents=intents)  # Botのインスタンスを作成します。

# Botを作成
bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    # サマリーチャンネルをIDで直接取得
    summary_channel = bot.get_channel(int(summary_channel_id))
    if not summary_channel:
        print(f"No channel found with id {summary_channel_id}. Check the channel id.")
        return

    # summary.jsonを送信
    await summary_channel.send(file=nextcord.File('summary.json'))

    # 全ての操作が完了した後でbotを閉じる
    await bot.loop.run_until_complete(bot.close())

# Botを起動
bot.run(discord_token)
'''
