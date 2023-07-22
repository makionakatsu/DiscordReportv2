import os
import datetime
import nextcord as discord
from nextcord.ext import commands
import pytz
import csv

# GitHub Secretsから各種キーを読み込む
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')

# CSVファイルに出力する項目
fieldnames = ['Timestamp', 'Channel', 'Author', 'Content', 'Message URL', 'Emoji Count']

# CSVファイルを作成する関数を定義
async def write_chat_to_csv():
    # 現在の日付を取得し、それを文字列形式に変換
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 現在の日付を含むCSVファイル名を設定
    csv_file = f"discord_log_{current_date}.csv"

    with open(csv_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for guild in bot.guilds:
            for channel in guild.text_channels:
                # 各メッセージに対して処理
                async for message in channel.history(limit=None):
                    writer.writerow({
                        'Timestamp': message.created_at.astimezone(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S'),
                        'Channel': channel.name,
                        'Author': message.author.name,
                        'Content': message.content,
                        'Message URL': message.jump_url,
                        'Emoji Count': len(message.reactions)
                    })

# メインの処理
if __name__ == "__main__":
    # Botの準備
    bot = commands.Bot(command_prefix='!')

    @bot.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(bot))

        # CSVファイルを作成
        await write_chat_to_csv()

        # チャンネルにメッセージを送信
        target_channel = bot.get_channel(int(guild_id))
        await target_channel.send("CSVファイルの作成が完了しました。")

    # Botを起動
    bot.run(discord_token)
