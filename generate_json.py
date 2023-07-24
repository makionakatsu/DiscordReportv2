import os
import json
import pytz
import nextcord
from datetime import datetime, timedelta
from nextcord.ext import commands

intents = nextcord.Intents.default()
intents.message_content = True

# GitHub SecretsからAPIキーとDiscord関連の情報を読み込む
summary_channel_name = os.getenv('SUMMARY_CHANNEL_NAME')
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')

# タイムゾーンを取得する関数
'''
def get_start_and_end_times(timezone):
    jst = pytz.timezone(timezone)
    now = datetime.now(jst)
    start = now - timedelta(days=1)
    end = now
    return start, end
'''
def get_start_and_end_times(timezone):
    # 日付と時間の取得
    now = datetime.now(timezone)
    
    # 始点と終点のタイムスタンプの生成
    start_time = datetime(now.year, now.month, now.day-1, 0, 0, 0, tzinfo=timezone)
    end_time = now  # 終点を現在の時刻に設定
    
    return start_time.timestamp(), end_time.timestamp()


# UTCをJSTに変換する関数
def convert_to_jst(dt):
    utc = pytz.timezone('UTC')
    dt = dt.replace(tzinfo=utc)
    jst = pytz.timezone('Asia/Tokyo')
    return dt.astimezone(jst)

# メッセージのログを取得する関数
async def fetch_logs(guild, start_time, end_time, member=None):
    # ログを保存するリストを初期化
    logs = []
    # テキストチャンネルごとにメッセージを取得
    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=10000, after=start_time, before=end_time):
                if member is None or message.author == member:
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

    return logs

# ログをJSON形式で保存する関数
def write_log_to_json(logs, target_date):
    try:
        with open(f'{target_date}_logs.json', 'w') as f:
            json.dump(logs, f, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing logs to json file: {e}")

# Discordにログインする関数
def login_discord():
    bot = commands.Bot(command_prefix='!', intents=intents)
    return bot

# メインの処理
if __name__ == "__main__":
    bot = login_discord()

    @bot.event
    async def on_ready():
        print(f'We have logged in as {bot.user}')

        # 指定されたギルドを取得
        guild = bot.get_guild(int(guild_id))

        # タイムゾーンを指定して開始時間と終了時間を取得
        start_time, end_time = get_start_and_end_times('Asia/Tokyo')

        # メッセージのログを取得
        logs = await fetch_logs(guild, start_time, end_time)

        # ログをJSON形式で保存
        write_log_to_json(logs, start_time.strftime('%Y%m%d'))

        await bot.close()

    # Botを起動
    bot.run(discord_token)
