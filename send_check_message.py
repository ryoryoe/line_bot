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
def reply_message(user_id, text):
    """
    指定したユーザーにLINEメッセージを送信する
    """
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    response = requests.post(push_url, headers=headers, json=data)
    print(f"送信: {user_id}, ステータス: {response.status_code}, 内容: {response.text}")

def check_and_send_messages():
    """
    その日に返信がないユーザーに3時間おきにメッセージを送信する
    """
    today = datetime.date.today()
    for user_id in USER_DICT.keys():
        last_reply = last_reply_date.get(user_id)
        if last_reply is None or last_reply != today:
            reply_message(user_id, "明日のご飯の予定を教えてね〜。1.朝 2.昼 3.夜 の数字をスペース区切りで送るんやで。送らんかったら3時間後にまた聞くからね。（例: 朝ごはんと昼ごはんがいらない場合: 1 2）。全部いる人は0を送ってや。")


check_and_send_messages()  # 一度実行しておく
