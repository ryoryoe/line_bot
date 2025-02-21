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


# Google Calendar API の設定
SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "linecalenderconnect-fea7489c120c.json"  # Google Cloudからダウンロードし>    たJSONキー
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("calendar", "v3", credentials=credentials)


# LINE API 設定
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"
push_url = "https://api.line.me/v2/bot/message/push"
LINE_ACCESS_TOKEN = "nZr8J+fYviQIbVZI8m/Q+5rMM8MREuiOlktU2oEDcHD2L5KMPz2CQ7rCOrlmL0CDcqaJpvbo
qoJYfm57Vv3QRH2nujvSbBNxAJziLCXVQQNCeRq9RHZXev7i0oW07RpGKpy1M63Lf9Sa45N+2rEdPgdB04t89/1O/w1cDnyil        FU="  # 発行したアクセストークンを記入

# LINEのユーザーIDと名前を対応づける辞書（手動で設定）
USER_DICT = {
    "U2cee263dd19d383fed6fc20e5158be79": "遼",
    #"Ubbf7780f762b4b1b4644543a77f32e72": "真弓",
    "U638fe389ce03b28ecce99d363857c8f8": "マイ",
}
TARGET_USER_ID = "Ubbf7780f762b4b1b4644543a77f32e72"
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
