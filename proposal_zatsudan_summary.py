import requests
import json
import pytz
from datetime import datetime, timedelta
from openai import OpenAI
import os

# 環境変数の設定
channel_ids = os.getenv('CHANNEL_IDS').split(',')  # 複数のチャンネルIDをリストとして取得
bot_token = os.getenv('DISCORD_TOKEN')
openai_api_key = os.getenv('OPENAI_API_KEY')
emojis = os.getenv('EMOJIS', "\U0001F5E3\U0000FE0F,\U0001F9E0,\U0001F916").split(',')

# 環境変数のチェック
for var, name in [(channel_ids, 'CHANNEL_IDS'), (bot_token, 'DISCORD_TOKEN'), (openai_api_key, 'OPENAI_API_KEY')]:
    if not var:
        print(f"Error: {name} is not set")
        exit(1)

# OpenAI API キーの設定
client = OpenAI()

# タイムゾーンの設定
jst = pytz.timezone('Asia/Tokyo')
now = datetime.now(jst)
start_date = now - timedelta(days=1)
start_time = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=jst)
end_time = datetime(start_date.year, start_date.month, start_date.day, 23, 59, 59, tzinfo=jst)

# Discordからメッセージを取得する関数
def fetch_messages(channel_id, token, last_message_id=None):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}
    params = {"limit": 100}
    if last_message_id:
        params["before"] = last_message_id
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch messages: {response.text}")
        return []
    return json.loads(response.text)

# Discordに要約を投稿する関数
def post_summary_to_discord(channel_id, summary, token):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "content": summary
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print("Successfully posted the summary to Discord.")
    else:
        print(f"Failed to post the summary to Discord: {response.text}, Status Code: {response.status_code}")

# GPT-3.5-turboを使ってテキストを要約する関数
def summarize_with_gpt(text):
    if not text:
        return None
    try:
        response_summary = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role":"system","content":f"""以下のtextをもとに、
                 各話題ごとに、(1)議題、(2)反論、(3)議論の総合的なまとめを出力してください。
                 日本語で全部で200字程度で出力してください。"""},
                {"role":"user","content":f"text:{text}"},
                ],
            max_tokens=600
        )
        summary = response_summary.choices[0].message.content
        return summary
    except Exception as e:
        print(f"Error occurred while summarizing with GPT-3.5-turbo: {e}")
        return None


# メイン処理
if __name__ == "__main__":
    for channel_id in channel_ids:
        filtered_messages = []
        last_message_id = None

        # メッセージを取得してフィルタリング
        while True:
            messages = fetch_messages(channel_id, bot_token, last_message_id)
            if not messages:
                break
            for msg in messages:
                msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')).astimezone(jst)
                if start_time <= msg_time <= end_time:
                    if 'reactions' in msg:
                        if any(emoji in reaction['emoji']['name'] for reaction in msg['reactions'] for emoji in emojis):
                            filtered_messages.append({
                                "Message_Date": msg['timestamp'],
                                "Author_Name": msg['author']['username'],
                                "Content": msg['content'],
                                "Reaction_Type": [reaction['emoji']['name'] for reaction in msg['reactions']]
                            })
            if messages:
                try:
                    last_message_id = messages[-1]['id']
                except KeyError:
                    print("Could not find 'id' key in the last message.")
                    break

        # メッセージ日時でソート
        filtered_messages.sort(key=lambda x: datetime.fromisoformat(x['Message_Date'].replace('Z', '+00:00')))

        # 抽出されたメッセージをJSONに出力
        with open('filtered_messages.json', 'w', encoding='utf-8') as jsonfile:
            json.dump(filtered_messages, jsonfile, ensure_ascii=False, indent=4)

        #  メッセージ内容を連結して要約を作成
        text_to_summarize = " ".join([msg['Content'] for msg in filtered_messages])
        summary = summarize_with_gpt(text_to_summarize)

        # 要約とその他の情報をDiscordに投稿
        if summary:
            full_message = f"CHIPSくんだよ！議論のサマリーを開始するよー:\n{summary}\n\n議論まとめはこれでおしまい！\n🗣️,🤖,🧠のいずれかのリアクションがあるメッセージを対象に議論のまとめを行っているよ。\n議論に関係あるメッセージにはリアクションをつけてね！"
            print(full_message)
            post_summary_to_discord(channel_id, full_message, bot_token)
        else:
            print("要約を生成できませんでした。")
