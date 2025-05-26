from flask import Flask, request, send_file, Response
from flask_cors import CORS
import pandas as pd
import requests
import os
import threading
import time
import json

app = Flask(__name__)
CORS(app)

CSV_PATH = "ladder_results.csv"
URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"

def fetch_and_save():
    try:
        raw = requests.get(URL).json()
        if not raw:
            print("❌ 실시간 데이터 없음")
            return

        latest = raw[0]
        latest_round = int(latest["date_round"])

        new_row = {
            "회차": latest_round,
            "start_point": latest["start_point"],
            "line_count": latest["line_count"],
            "odd_even": latest["odd_even"]
        }

        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            if latest_round in df["회차"].values:
                print(f"✅ 이미 저장됨: {latest_round}회차")
                return
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df = pd.DataFrame([new_row])

        df.to_csv(CSV_PATH, index=False)
        print(f"✅ 저장 완료: {latest_round}회차")

    except Exception as e:
        print("❌ 저장 중 오류:", e)

def run_collector_loop():
    while True:
        fetch_and_save()
        time.sleep(300)

def convert(row):
    side = '좌' if row['start_point'] == 'LEFT' else '우'
    count = str(row['line_count'])
    oe = '짝' if row['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    return [
        ('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀')
        for s, c, o in map(parse_block, block)
    ]

def flip_start(block):
    flipped = []
    for s, c, o in map(parse_block, block):
        c_flip = '4' if c == '3' else '3'
        o_flip = '홀' if o == '짝' else '짝'
        flipped.append(s + c_flip + o_flip)
    return flipped

def flip_odd_even(block):
    flipped = []
    for s, c, o in map(parse_block, block):
        s_flip = '우' if s == '좌' else '좌'
        c_flip = '4' if c == '3' else '3'
        flipped.append(s_flip + c_flip + o)
    return flipped

def find_flow_match(block, full_data):
    block_len = len(block)
    for i in reversed(range(len(full_data) - block_len)):
        candidate = full_data[i:i+block_len]
        if candidate == block:
            pred_index = i - 1
            pred = full_data[pred_index] if pred_index >= 0 else "❌ 없음"
            return pred, ">".join(block), i + 1
    return "❌ 없음", ">".join(block), -1

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        if not os.path.exists(CSV_PATH):
            error_data = {"error": "CSV 파일 없음"}
            return Response(json.dumps(error_data, ensure_ascii=False), mimetype='application/json')

        df = pd.read_csv(CSV_PATH)
        if len(df) < 10:
            error_data = {"error": "CSV 데이터 부족"}
            return Response(json.dumps(error_data, ensure_ascii=False), mimetype='application/json')

        mode = request.args.get("mode", "3block_orig")
        size = int(mode[0])
        round_num = int(df.iloc[-1]["회차"]) + 1

        data = df.tail(288).iloc[::-1]
        flow_list = [convert(row) for _, row in data.iterrows()]
        recent_flow = flow_list[:size]

        if "flip_full" in mode:
            flow = flip_full(recent_flow)
        elif "flip_start" in mode:
            flow = flip_start(recent_flow)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_flow)
        else:
            flow = recent_flow

        result, blk, match_index = find_flow_match(flow, flow_list)

        response_data = {
            "예측회차": round_num,
            "예측값": result,
            "블럭": blk,
            "매칭순번": match_index if match_index > 0 else "❌ 없음"
        }

        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')

    except Exception as e:
        error_data = {"error": str(e)}
        return Response(json.dumps(error_data, ensure_ascii=False), mimetype='application/json')

if __name__ == '__main__':
    threading.Thread(target=run_collector_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
