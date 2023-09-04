import requests
import json
import pytz
from datetime import datetime, timedelta
import openai
import os

# タイムゾーンを指定して開始時間と終了時間を取得
jst = pytz.timezone('Asia/Tokyo')
now = datetime.now(jst)
start_date = now - timedelta(days=1)
start_time = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=jst)
end_time = datetime(start_date.year, start_date.month, start_date.day, 23, 59, 59, tzinfo=jst)

def fetch_messages(channel_id, token, last_message_id=None):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}
    params = {"limit": 100}
    if last_message_id:
        params["before"] = last_message_id
    response = requests.get(url, headers=headers, params=params)
    return json.loads(response.text)

# 初期設定
proposal_summary_channel_id = os.getenv('PROPOSAL_SUMMARY_CHANNEL_ID')
bot_token = os.getenv('DISCORD_TOKEN')
emojis = ["\U0001F5E3\U0000FE0F", "\U0001F9E0", "\U0001F916"]
filtered_messages = []
last_message_id = None

# メッセージを取得してフィルタリング
while True:
    messages = fetch_messages(proposal_summary_channel_id, bot_token, last_message_id)
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

openai.api_key = os.getenv('OPENAI_API_KEY')

# GPT-3.5-turboを使ってテキストを要約する関数
def summarize_with_gpt(text):
    if not text:
        return None
    try:
        response_summary = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "あなたはCHIPSくんという名前です。Discordの毎日のチャットログを確認し、日本語でトピックの包括的な要約を提供する役割を担うアシスタントです。"},
                {"role": "user", "content": f"以下のtextをもとに、(1)議論の要点、(2)反論、(3)議論の総合的なまとめを出力してください。 日本語で全部で200字程度で出力してください。 text: {text}"},
            ],
            max_tokens=600
        )
        summary = response_summary['choices'][0]['message']['content']
        return summary
    except Exception as e:
        print(f"Error occurred while summarizing with GPT-3.5-turbo: {e}")
        return None

# JSONファイルからメッセージを読み込む関数
def load_messages():
    try:
        with open('filtered_messages.json', 'r', encoding='utf-8') as f:
            messages = json.load(f)
        return messages
    except Exception as e:
        print(f"Error occurred while loading messages from JSON: {e}")
        return []

# メイン処理
if __name__ == "__main__":
    messages = load_messages()
    if messages:
        # メッセージ内容を連結
        text_to_summarize = " ".join([msg['Content'] for msg in messages])
        # 要約を取得
        summary = summarize_with_gpt(text_to_summarize)
        if summary:
            print(f"CHIPSくんだよ！議論のサマリーを開始するよー:\n{summary}\n\n議論まとめはこれでおしまい！\n🗣️,🤖,🧠のいずれかのリアクションがあるメッセージを対象に議論のまとめを行っているよ。\n議論に関係あるメッセージにはリアクションをつけてね！")
        else:
            print("Could not generate a summary.")
    else:
        print("No messages to summarize.")