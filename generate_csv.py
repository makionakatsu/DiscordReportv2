import os
import datetime
from nextcord.ext import commands
import pytz
import csv

# GitHub Secretsから各種キーを読み込む
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')
summary_channel_id = os.getenv('SUMMARY_CHANNEL_ID')

# CSVファイルに出力する項目
fieldnames = ['Timestamp', 'Channel', 'Author', 'Content', 'Message URL', 'Emoji Count']

# メッセージの情報を取得する関数を定義
def get_messages_info(messages, channel):
    # メッセージ情報を保存するための空リストを作成
    messages_info = []
    for message in messages:
        # 各メッセージの情報を辞書形式で取得し、リストに追加
        messages_info.append({
            'Timestamp': message.created_at.astimezone(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S'),
            'Channel': channel.name,
            'Author': message.author.name,
            'Content': message.content,
            'Message URL': message.jump_url,
            'Emoji Count': len(message.reactions)
        })
    return messages_info

# CSVファイルを作成する関数を定義
async def write_chat_to_csv():
    # 現在の日付を取得し、それを文字列形式に変換
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 現在の日付を含むCSVファイル名を設定
    csv_file = f"discord_log_{current_date}.csv"

    with open(csv_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        # メッセージを一旦メモリ上に保存するリストを作成
        all_messages = []

        # 前日の日付を取得
        previous_date = datetime.datetime.now() - datetime.timedelta(days=1)
        start_time = previous_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + datetime.timedelta(days=1)

        # ギルドごとにループを行う
        for guild in bot.guilds:
            # チャンネルごとにループを行う
            for channel in guild.text_channels:

                # メッセージの情報を取得し、一旦メモリ上に保存
                all_messages.extend(get_messages_info(channel.history(after=start_time, before=end_time), channel))
                
                if len(all_messages) >= 1000:  # メッセージが1000件たまったら
                    writer.writerows(all_messages)  # まとめて書き込み
                    all_messages = []  # メッセージリストをリセット
        if all_messages:  # 残ったメッセージがあれば
            writer.writerows(all_messages)  # 書き込み

# メインの処理
if __name__ == "__main__":
    # Botの準備
    bot = commands.Bot(command_prefix='!')

    @bot.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(bot))

        try:
            # CSVファイルを作成
            await write_chat_to_csv()

            # チャンネルにメッセージを送信
            if summary_channel_id is None:
                print("Summary channel ID is not set.")
                return
            try:
                summary_channel_id = int(summary_channel_id)
            except ValueError:
                print("Summary channel ID is not a valid integer.")
                return

            target_channel = bot.get_channel(summary_channel_id)
            if target_channel is None:
                print(f"Channel with ID {summary_channel_id} does not exist.")
            else:
                await target_channel.send("CSVファイルの作成が完了しました。")
        except Exception as e:
            print(f"An error occurred: {e}")


    # Botを起動
    bot.run(discord_token)