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
def get_start_and_end_times(timezone):
    jst = pytz.timezone(timezone)
    now = datetime.now(jst)
    start = now - timedelta(days=1)
    end = now
    return start, end

# UTCをJSTに変換する関数
def convert_to_jst(dt):
    utc = pytz.timezone('UTC')
    dt = dt.replace(tzinfo=utc)
    jst = pytz.timezone('Asia/Tokyo')
    return dt.astimezone(jst)

# メッセージのログを取得する関数
async def fetch_logs(guild, start_time, end_time, member=None):
    logs = []
    for channel in guild.text_channels:
        async for message in channel.history(after=start_time, before=end_time):
            if member is None or message.author == member:
                reactions = [{str(reaction.emoji): reaction.count} for reaction in message.reactions]
                logs.append({
                    "Timestamp": convert_to_jst(message.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                    "Channel": str(channel),
                    "Author": str(message.author),
                    "Content": message.content,
                    "Message URL": f"https://discord.com/channels/{guild.id}/{channel.id}/{message.id}",
                    "Reaction count": reactions
                })
    return logs

# ログをJSON形式で保存する関数
def write_log_to_json(logs, target_date):
    with open(f'{target_date}_logs.json', 'w') as f:
        json.dump(logs, f, ensure_ascii=False)

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
