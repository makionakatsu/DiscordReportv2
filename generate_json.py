import os
import json
import pytz
import nextcord
from datetime import datetime, timedelta
from nextcord.ext import commands

# GitHub Secretsから情報を読み込む
summary_channel_name = os.getenv('SUMMARY_CHANNEL_ID')
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')

# Intentsオブジェクトを作成
intents = nextcord.Intents.default()
intents.message_content = True

from datetime import timedelta

# タイムゾーンを指定して開始時間と終了時間を取得
jst = pytz.timezone('Asia/Tokyo')
now = datetime.now(jst)
start_date = now - timedelta(days=1)
start_time = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=jst)
end_time = datetime(start_date.year, start_date.month, start_date.day, 23, 59, 59, tzinfo=jst)

# チャンネルスキップリストを読み込む
with open('config.json', 'r') as file:
    config = json.load(file)
skip_channels = {channel['channel_id'] for channel in config['skip_channels']}

# メッセージのログを取得する関数
async def fetch_logs(guild, start_time, end_time):
    logs = []
    for channel in guild.text_channels:
        # チャンネルがスキップリストにある場合はスキップ
        if str(channel.id) in skip_channels:
            continue
        try:
            async for message in channel.history(limit=10000, after=start_time, before=end_time):
                logs.append({
                    "Timestamp": message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "Channel": channel.name,
                    "Channel URL": f"https://discord.com/channels/{guild.id}/{channel.id}",
                    "Author": str(message.author),
                    "Content": message.clean_content,
                    "Message URL": f"https://discord.com/channels/{guild.id}/{channel.id}/{message.id}",
                    "ReactionCount": len(message.reactions)
                })
        except Exception as e:
            print(f"Error fetching messages from channel {channel.name}: {e}")
    if not logs:
        print("No logs fetched. Check the date range and channel permissions.")
    return logs

# ログをJSON形式で保存する関数
def write_log_to_json(logs, filename):
    try:
        with open(filename, 'w') as f:
            json.dump(logs, f, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing logs to json file: {e}")

# Botを作成
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    guild = bot.get_guild(int(guild_id))
    if not guild:
        print(f"No guild found with id {guild_id}. Check the guild id.")
        return
    logs = await fetch_logs(guild, start_time, end_time)
    filename = "logs.json"
    write_log_to_json(logs, filename)
    
    # 全ての操作が完了した後でbotを閉じる
    await bot.close()

# Botを起動
bot.run(discord_token)
