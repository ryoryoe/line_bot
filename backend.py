"""
役割:
1. LINEのWebhookを受け取り、ユーザーが送った「不要なご飯の番号（1: 朝, 2: 昼, 3: 夜）」を解析
2. Googleカレンダーに「ご飯不要」の予定を追加する
"""

from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime
import requests
import schedule
import time
from threading import Thread
from googleapiclient.discovery import build
from google.oauth2 import service_account
from tqdm import tqdm  # 変更部分！！ for文で進捗を可視化

app = Flask(__name__)

# Google Calendar API の設定
SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "linecalenderconnect-fea7489c120c.json"  # Google CloudからダウンロードしたJSONキー
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("calendar", "v3", credentials=credentials)


# LINE API 設定
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"
push_url = "https://api.line.me/v2/bot/message/push"
LINE_ACCESS_TOKEN = "nZr8J+fYviQIbVZI8m/Q+5rMM8MREuiOlktU2oEDcHD2L5KMPz2CQ7rCOrlmL0CDcqaJpvbo    qoJYfm57Vv3QRH2nujvSbBNxAJziLCXVQQNCeRq9RHZXev7i0oW07RpGKpy1M63Lf9Sa45N+2rEdPgdB04t89/1O/w1cDnyil    FU="  # 発行したアクセストークンを記入

# LINEのユーザーIDと名前を対応づける辞書（手動で設定）
USER_DICT = {
    "U2cee263dd19d383fed6fc20e5158be79": "遼",
    #"Ubbf7780f762b4b1b4644543a77f32e72": "真弓",
    "U638fe389ce03b28ecce99d363857c8f8": "マイ",
}
TARGET_USER_ID = "Ubbf7780f762b4b1b4644543a77f32e72"
#TARGET_USER_ID = "U2cee263dd19d383fed6fc20e5158be79"  # 通知先のユーザーID

# 食事タイプのマッピング
MEAL_MAP = {"1": "朝", "2": "昼", "3": "夜"}

# 最後に返信した日を保存する辞書
last_reply_date = {user_id: None for user_id in USER_DICT.keys()}

def delete_existing_events(calendar_id, color_id, date):
    """
    指定した日付と colorId のイベントを削除
    """
    # 日本時間の開始・終了時刻を UTC に変換
    jst_midnight = datetime.datetime.strptime(date, "%Y-%m-%d")  # YYYY-MM-DD の日付を datetime に変換
    utc_midnight = jst_midnight - datetime.timedelta(hours=9)  # UTC に変換

    time_min = utc_midnight.isoformat() + "Z"
    time_max = (utc_midnight + datetime.timedelta(days=1)).isoformat() + "Z"

    print(f"取得範囲 (UTC): {time_min} 〜 {time_max}")  # デバッグ用

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
    ).execute()

    events = events_result.get("items", [])
    print(f"削除対象: {len(events)}件")
    print(f"{events=}")

    for event in events:
        if event.get("colorId") == color_id:  # colorId が一致するイベントのみ削除
            service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
            print(f"削除: {event['summary']} (colorId={color_id})")

def add_meal_event(user_name, meal_types, date):
    """
    Googleカレンダーに「ご飯不要」イベントを登録
    """
    calendar_id = "f59fe4057a49516a7712d5674722e0b12e5db99e78bb2a3099d9ef0787bd1494@group.calendar.google.com"
    user_colors = {
        "遼": "1",  # 青
        "伸": "2",  # 緑
        "舞": "4",  # 赤
        "潤": "6",  # オレンジ
    }

    # ユーザー名が辞書にない場合のデフォルト色
    default_color = "8"  # グレー

    # colorId を決定
    color_id = user_colors.get(user_name, default_color)

    # ===== 既存の同じ色のイベントを削除 =====
    delete_existing_events(calendar_id, color_id, date)
    for meal in meal_types:
        event = {
            "summary": f"{user_name} の {meal}ご飯不要",
            "start": {"date": date},
            "end": {"date": date},
            "colorId": color_id  # 色を設定
        }
        service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Googleカレンダーに登録: {user_name} の {meal}ご飯不要")

def reply_message(user_id, text):
    """
    指定したユーザーにLINEメッセージを送信する
    """
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    response = requests.post(push_url, headers=headers, json=data)
    print(f"送信: {user_id}, ステータス: {response.status_code}, 内容: {response.text}")

@app.route("/check_and_send_messages", methods=["POST"])
def check_and_send_messages():
    """
    その日に返信がないユーザーに3時間おきにメッセージを送信する
    """
    today = datetime.date.today()
    for user_id in USER_DICT.keys():
        last_reply = last_reply_date.get(user_id)
        if last_reply is None or last_reply != today:
            reply_message(user_id, "明日のご飯の予定を教えてね〜。1.朝 2.昼 3.夜 の数字をスペース区切りで送るんやで。送らんかったら3時間後にまた聞くからね。（例: 朝ごはんと昼ごはんがいらない場合: 1 2）。全部いる人は0を送ってや。")

# 3時間おきに実行するスケジュール設定
#schedule.every(15).seconds.do(check_and_send_messages)
#schedule.every().day.at("09:00").do(check_and_send_messages)
# 指定の時刻に実行するスケジュールを設定
#schedule.every().day.at("08:00").do(check_and_send_messages)
#schedule.every().day.at("11:00").do(check_and_send_messages)
#schedule.every().day.at("14:00").do(check_and_send_messages)
#schedule.every().day.at("17:00").do(check_and_send_messages)


def get_tomorrow_unwanted_meals(target_date: datetime.date) -> dict:
    """
    指定した日付に登録されている『ご飯不要』(朝/昼/夜)をユーザーごとに取得
    戻り値: {user_name: ["朝", "夜", ...], ...}
    """
    JST = datetime.timezone(datetime.timedelta(hours=9))  # 変更部分！！
    start_time = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=JST)  # 変更部分！！
    end_time = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=JST)    # 変更部分！！

    time_min = start_time.isoformat()  # 変更部分！！
    time_max = end_time.isoformat()    # 変更部分！！
    print(f"取得範囲: {time_min} 〜 {time_max}")

    calendar_id = "f59fe4057a49516a7712d5674722e0b12e5db99e78bb2a3099d9ef0787bd1494@group.calendar.google.com"
    events_result = (
        service.events()
        .list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max, singleEvents=True, orderBy="startTime").execute()
    )
    events = events_result.get("items", [])

    # {user_name: ["朝", "昼", ...]}という形式でまとめる
    result = {}
    for event in tqdm(events, desc="get_tomorrow_unwanted_meals"):  # 変更部分！！ tqdmで進捗表示
        summary = event.get("summary", "")
        # 例: "User1 の 朝ご飯不要"
        if "ご飯不要" in summary and " の " in summary:
            parts = summary.split(" の ")
            if len(parts) == 2:
                user_part = parts[0].strip()    # UserName
                meal_part = parts[1].replace("ご飯不要", "").strip()  # 朝/昼/夜 など
                if user_part not in result:
                    result[user_part] = []
                result[user_part].append(meal_part)
    return result

@app.route("/send_tommorow_info", methods=["POST"])
def send_tomorrow_info():
    """
    毎日18:00に、翌日に不要なご飯(朝/昼/夜)が登録されているユーザーをまとめてLINEに通知する
    """
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    unwanted_map = get_tomorrow_unwanted_meals(tomorrow)

    if not unwanted_map:
        msg = "明日はみんなご飯が必要みたいやで〜。ゴールデンカレーの辛口がおすすめやで〜。"
    else:
        lines = []
        for user_name, meals in unwanted_map.items():
            meal_str = "、".join(meals)
            lines.append(f"{user_name}: {meal_str}ご飯はいらんらしい")
        msg = "明日のご飯不要情報\n" + "\n".join(lines) + "\nゴールデンカレーの辛口がみんな食べたいんやって。後ここからも見れるわ。\nhttps://calendar.google.com/calendar/u/0/r"
    print(msg)
    reply_message(TARGET_USER_ID, msg)

# 18時に明日の不要ご飯を通知
#schedule.every().day.at("18:00").do(send_tomorrow_info)
#schedule.every(10).seconds.do(send_tomorrow_info)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    LINEのWebhookを受け取り、ご飯不要情報を解析してGoogleカレンダーに登録
    """
    body = request.json
    print("受信データ:", body)

    for event in body.get("events", []):
        if event.get("type") == "message":
            user_id = event["source"].get("userId")
            user_message = event["message"].get("text", "")
            #reply_token = event.get("replyToken")

            user_name = USER_DICT.get(user_id, "不明なユーザー")
            meal_types = [MEAL_MAP[n] for n in user_message.split() if n in MEAL_MAP]
            zeros = [n for n in user_message.split() if n == "0"]
            print(f"{user_name} が送信: {meal_types}")

            if meal_types:
                #today = datetime.date.today().isoformat()
                today = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
                add_meal_event(user_name, meal_types, today)
                last_reply_date[user_id] = datetime.date.today()
                reply_text = f"{user_name} の {'、'.join(meal_types)}ご飯不要に変えといたわ。どうも。予定変わったらもう一回番号で教えてな。ここから登録できてるか確認できるわ。\nhttps://calendar.google.com/calendar/u/0/r"
            elif zeros:
                calendar_id = "f59fe4057a49516a7712d5674722e0b12e5db99e78bb2a3099d9ef0787bd1494@group.calendar.google.com"
                user_colors = {
                     "遼": "1",  # 青
                     "伸": "2",  # 緑
                     "舞": "4",  # 赤
                     "潤": "6",  # オレンジ
                }
                
                # ユーザー名が辞書にない場合のデフォルト色
                default_color = "8"  # グレー
                # colorId を決定
                color_id = user_colors.get(user_name, default_color)
                date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
                # ===== 既存の同じ色のイベントを削除 =====
                delete_existing_events(calendar_id, color_id, date)
                last_reply_date[user_id] = datetime.date.today()
                reply_text = f"{user_name} は全部のご飯が必要なんやね。わかった。予定が変わったらまた番号で教えてな。"
            else:
                reply_text = "ご飯の登録しかできひんねん。だから、1.朝 2.昼 3.夜 の数字をスペース区切りで送ってや（例: 朝ごはんと昼ごはんだけいる場合: 「1 2」と送信）。全部いる人は0を送ってや。"

            reply_message(user_id, reply_text)
            print(f"返信: {user_name}, 内容: {reply_text}")
            #reply_message(reply_token, reply_text)

    return jsonify({"status": "ok"})

send_tomorrow_info()

# スケジュール実行ループ
#def run_schedule():
#    while True:
#        schedule.run_pending()
#        time.sleep(1800)

if __name__ == "__main__":
    schedule_thread = Thread(target=run_schedule)
    schedule_thread.start()
    app.run(port=8000)
