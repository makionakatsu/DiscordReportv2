import os
import json
from datetime import datetime, timedelta
import nextcord as discord
from discord.ext import commands

# 環境変数から必要な情報を取得します。
bot_token = os.getenv('DISCORD_TOKEN')
summary_channel_id = os.getenv('SUMMARY_CHANNEL_ID') 

# Botのインスタンスを作成します。
intents = discord.Intents.default()  # デフォルトのIntentsオブジェクトを作成します。
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)  # Botのインスタンスを作成します。

# 要約を読み込む関数を定義します。
def load_summary():
    try:
        with open('summary.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading summary: {e}")
        return None

# 送信メッセージを生成する関数を定義します。
def generate_messages(channel, data):
    try:
        # チャンネルサマリーが空ならNoneを返す
        if not data['Channel Summary']:
            return None

        message = f"⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨\n\n"
        message += f"{data['Channel URL']}\n"
        message += data['Channel Summary'] + "\n"
        message += "＜TOP TOPIX＞\n"

        # トップコメント
        for summary in data['Top 5 Message Summaries']:
            message += f"・{summary['Summary']}\n{summary['URL']}\n\n"

        if len(message) > 2000:
            print(f"Error: Summary for channel {channel} is too long.")
            return None
        return [message]
    except Exception as e:
        print(f"Error generating message: {e}")
        return None

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

    # サマリーチャンネルをIDで直接取得します。
    try:
        summary_channel = bot.get_channel(int(summary_channel_id))
    except Exception as e:
        print(f"Error getting summary channel: {e}")
        return

    # 要約を読み込みます。
    summary = load_summary()
    if summary is None:
        return
    
    # 前日の日付を取得します。
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime("%m月%d日")

    # 開始の挨拶を送信します。日付を組み込んでいます。
    greeting_start = f"__**pNouns⚡日報｜{yesterday_str}**__\n\ngngn〜\n{yesterday_str}のpNounsまとめを始めるよ〜〜\n"
    await summary_channel.send(greeting_start)

    # 各チャンネルの要約をサマリーチャンネルに投稿します。
    for channel, data in summary.items():
        messages = generate_messages(channel, data)
        # メッセージがNoneならスキップ
        if messages is None:
            continue
        for message in messages:
            try:
                await summary_channel.send(message)
            except Exception as e:
                print(f"Error sending message: {e}")

    # 終了の挨拶を送信します。
    greeting_end = "⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨\n\nこれでおしまい〜！\nみんなの活動がみんなの世界を変えていく！Nounishなライフを、Have a Nounish day!\n＼⌐◨-◨／✨＼◨-◨¬／✨"
    await summary_channel.send(greeting_end)

    # Botを明示的に閉じます。
    await bot.close()

try:
    bot.run(bot_token)
except SystemExit:
    print("Bot closed.")
except Exception as e:
    print(f"Error occurred: {e}")
