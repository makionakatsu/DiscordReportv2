import os
import json
import openai
from operator import itemgetter


guild_id = os.getenv('GUILD_ID')
openai.api_key = os.getenv('OPENAI_API_KEY')

# GPT-3.5-turboを使ってテキストを要約する関数
def summarize_with_gpt(text):
    response_summary = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": "You are an assistant who summarizes discord chat in Japanese."},
            {"role": "user", "content": f"Here's a discord chat: {text}. Can you summarize it for me in japanese?"},
        ],
        max_tokens=300
    )
    summary = response_summary['choices'][0]['message']['content']
    return summary

# JSONファイルからメッセージを読み込む関数
def load_messages():
    try:
        with open('logs.json', 'r', encoding='utf-8') as f:
            messages = json.load(f)
        return messages
    except FileNotFoundError:
        print("Error: 'logs.json' file not found.")
        return None
    except Exception as e:
        print(f"Error loading messages: {e}")
        return None


# メッセージをチャンネルごとに分類する関数
def categorize_messages_by_channel(messages):
    categorized_messages = {}
    for message in messages:
        channel_name = message['Channel']
        if channel_name not in categorized_messages:
            categorized_messages[channel_name] = []
        categorized_messages[channel_name].append(message)
    return categorized_messages

# メッセージを要約する関数
def summarize_messages(categorized_messages):
    summarized_messages = {}
    for channel, messages in categorized_messages.items():
        # リアクション数でソート
        sorted_messages = sorted(messages, key=lambda msg: msg.get('ReactionCount', 0), reverse=True)
        top_messages = sorted_messages[:10]
        # メッセージのテキスト部分を取得
        texts = [message['Content'] for message in top_messages]
        # メッセージを要約
        channel_summary = summarize_with_gpt(' '.join(texts))

        # 上位5件のメッセージを要約
        top5_summaries = []
        for i in range(min(5, len(sorted_messages))):
            top_message = sorted_messages[i]
            top_summary = summarize_with_gpt(top_message['Content'])
            top_summary_url = top_message['Message URL'] 
            top5_summaries.append({
                f"Top {i+1} Message Summary": top_summary,
                f"Top {i+1} Message Summary URL": top_summary_url,
            })


        # 要約を保存
        summarized_messages[channel] = {
            "Channel Name": channel,
            "Channel ID": messages[0]['Channel ID'],  # 任意のメッセージからチャンネルIDを取得
            "Channel Summary": channel_summary,
            "Top 5 Messages": top5_summaries
        }
    return summarized_messages


# 要約をJSONファイルに出力する関数
def output_summary_to_json(summarized_messages):
    with open('summary.json', 'w', encoding='utf-8') as f:
        json.dump(summarized_messages, f, ensure_ascii=False, indent=2)

# メインの処理
def main():
    messages = load_messages()
    categorized_messages = categorize_messages_by_channel(messages)
    summarized_messages = summarize_messages(categorized_messages)
    output_summary_to_json(summarized_messages)

if __name__ == '__main__':
    main()
