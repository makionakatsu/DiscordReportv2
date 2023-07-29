import os
import json
import nextcord as nc
from nextcord.ext import commands

# 環境変数から必要な情報を取得
discord_token = os.getenv('DISCORD_TOKEN')
server_id = os.getenv('GUILD_ID')

# Botのインスタンスを作成します
bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    guild = nc.utils.get(bot.guilds, id=int(server_id))
    if not guild:
        print(f"No guild found with id {server_id}. Check the guild id.")
        return

    # チャンネルのリストを作成
    channels = [{"server_id": str(guild.id), "channel_id": str(channel.id)} for channel in guild.channels]

    # JSON形式で出力
    with open('channels.json', 'w') as f:
        json.dump({"skip_channels": channels}, f, indent=2)

    # Botを終了
    await bot.close()

# Botを起動
bot.run(discord_token)
