import os
import json
import nextcord as nc
from nextcord.ext import commands

# 環境変数から必要な情報を取得
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')

# 環境変数が設定されていることを確認
if not discord_token or not guild_id:
    print("Error: DISCORD_TOKEN and GUILD_ID environment variables must be set.")
    exit(1)

# Botのインスタンスを作成します
bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    guild = nc.utils.get(bot.guilds, id=int(guild_id))
    if not guild:
        print(f"No guild found with id {guild_id}. Check the guild id.")
        return

    # チャンネルのリストを作成
    channels = [
        {"channel_id": str(channel.id),
         "channel_name": channel.name
        } 
        for channel in guild.channels
    ]

    # JSON形式で出力
    try:
        with open('channels.json', 'w') as f:
            json.dump({"skip_channels": channels}, f, indent=2)
    except Exception as e:
        print(f"Error occurred while writing to JSON: {e}")

    # Botを終了
    await bot.close()

# Botを起動
bot.run(discord_token)
