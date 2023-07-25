import os
import json
import nextcord as discord
from discord.ext import commands

# 環境変数から必要な情報を取得します。
bot_token = os.getenv('DISCORD_TOKEN')
summary_channel_id = os.getenv('SUMMARY_CHANNEL_NAME')  # ここでIDを取得します。

# Botのインスタンスを作成します。
intents = discord.Intents.default()  # デフォルトのIntentsオブジェクトを作成します。
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
        message = f"======================\n"
        message += f"Channel: {channel}\n"
        message += data['summary'] + "\n"
        message += "【話題ピックアップ】\n"
        
        # トップコメント
        for comment, url in data['top_comments']:
            message += f"・{comment} ({url})\n"
        
        message += f"======================\n"
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
    
    # 各チャンネルの要約をサマリーチャンネルに投稿します。
    for channel, data in summary.items():
        messages = generate_messages(channel, data)
        if messages is not None:
            for message in messages:
                try:
                    await summary_channel.send(message)
                except Exception as e:
                    print(f"Error sending message: {e}")

    # Botを明示的に閉じます。
    await bot.close()

try:
    bot.run(bot_token)
except SystemExit:
    print("Bot closed.")
except:
    print("Error occurred.")
