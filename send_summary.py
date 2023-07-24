import os
import json
import nextcord as discord
from nextcord.ext import commands

# GitHub SecretsからAPIキーとDiscord関連の情報を読み込む
summary_channel_name = os.getenv('SUMMARY_CHANNEL_NAME')
discord_token = os.getenv('DISCORD_TOKEN')

# Discordにログインする関数
def login_discord(token):
    client = commands.Bot(command_prefix='!')
    client.run(token)

# summaries.jsonから要約を読み込む関数
def load_summaries():
    with open('summaries.json', 'r') as f:
        summaries = json.load(f)
    return summaries

# 要約を投稿するチャンネルを見つける関数
def find_summary_channel(client, summary_channel_name):
    for guild in client.guilds:
        for channel in guild.channels:
            if channel.name == summary_channel_name:
                return channel
    return None

# メッセージを生成する関数
def generate_message(channel, data):
    message = f"======================\n"
    message += f"Channel: {channel}\n"
    message += data['summary'] + "\n"
    message += "【話題ピックアップ】\n"
    for comment, url in data['top_comments']:
        message += f"・{comment} ({url})\n"
    message += f"======================\n"
    return message

# メインの処理
if __name__ == "__main__":
    # Discordにログイン
    client = login_discord(discord_token)

    @client.event
    async def on_ready():
        print(f'We have logged in as {client.user}')

        # summaries.jsonから要約を読み込む
        summaries = load_summaries()

        # 要約を投稿するチャンネルを探す
        summary_channel = find_summary_channel(client, summary_channel_name)

        # 各チャンネルの要約と上位コメントをフォーマットに従ってメッセージに変換し、要約チャンネルに投稿
        for channel, data in summaries.items():
            message = generate_message(channel, data)
            await summary_channel.send(message)
