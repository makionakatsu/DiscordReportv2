import os
import json
import nextcord as discord
from nextcord.ext import commands

# GitHub SecretsからAPIキーとDiscord関連の情報を読み込む
summary_channel_id = os.getenv('SUMMARY_CHANNEL_ID')
discord_token = os.getenv('DISCORD_TOKEN')

# Discordチャンネルにメッセージを送信する関数を定義
async def send_message_to_discord(bot, channel_id, message):
    # チャンネルIDからチャンネルオブジェクトを取得
    target_channel = bot.get_channel(int(channel_id))

    # メッセージを送信
    await target_channel.send(message)

# メインの処理
if __name__ == "__main__":
    # Botの準備
    bot = commands.Bot(command_prefix='!')

    @bot.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(bot))

        # 要約結果を読み込む
        with open('summaries.json', 'r') as f:
            summaries = json.load(f)

        # 各チャンネルの要約結果をDiscordチャンネルに送信
        for channel, data in summaries.items():
            message = f"======================\n"
            message += f"Channel: {channel}\n"
            message += data['summary'] + "\n"
            message += "【話題ピックアップ】\n"
            for comment, url in data['top_comments']:
                message += f"・{comment} ({url})\n"
            message += f"======================\n"

            await send_message_to_discord(bot, summary_channel_id, message)

        # CSVファイルを添付
        file_path = f"discord_log_{datetime.datetime.now().strftime('%Y-%m-%d')}.csv"
        await target_channel.send(file=discord.File(file_path))

    # Botを起動
    bot.run(discord_token)
