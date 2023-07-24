import os
import json
import nextcord as discord
from nextcord.ext import commands

# GitHub SecretsからAPIキーとDiscord関連の情報を読み込む
summary_channel_name = os.getenv('SUMMARY_CHANNEL_NAME')
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')  # 環境変数からギルドIDを取得

# Discordにログインする関数
def login_discord():
    client = commands.Bot(command_prefix='!')
    return client

# summaries.jsonから要約を読み込む関数
def load_summaries():
    with open('summaries.json', 'r') as f:
        summaries = json.load(f)
    return summaries

# 要約を投稿するチャンネルを見つける関数
def find_summary_channel(guild, summary_channel_name):
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
    client = login_discord()

    @client.event
    async def on_ready():
        print(f'We have logged in as {client.user}')

        # 指定されたギルドを取得
        guild = client.get_guild(int(guild_id))

        # summaries.jsonから要約を読み込む
        summaries = load_summaries()

        # 要約を投稿するチャンネルを探す
        summary_channel = find_summary_channel(guild, summary_channel_name)

        # 各チャンネルの要約と上位コメントをフォーマットに従ってメッセージに変換し、要約チャンネルに投稿
        for channel, data in summaries.items():
            message = generate_message(channel, data)
            await summary_channel.send(message)

    # Botを起動
    client.run(discord_token)
