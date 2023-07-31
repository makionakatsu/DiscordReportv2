import os
import json
import nextcord as nc
from nextcord.ext import commands

# 環境変数から必要な情報を取得
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')
output_channel_id = '1100924556585226310' 

# 環境変数が設定されていることを確認
if not discord_token or not guild_id: 
    print("Error: DISCORD_TOKEN, GUILD_ID environment variables must be set.") 
    exit(1)

# Botのインスタンスを作成します
intents = nc.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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

    # 追加: メッセージを送信するチャンネルを取得
    output_channel = bot.get_channel(int(output_channel_id))
    if output_channel is None:
        print(f"No channel found with id {output_channel_id}. Check the output channel id.")
        return

    # 追加: メッセージとファイルを送信
    await output_channel.send("Here are the channel IDs:", file=nc.File('channels.json'))

    # Botを終了
    await bot.close()

# Botを起動
bot.run(discord_token)
