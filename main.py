from flask import Flask, request, send_file, Response
from flask_cors import CORS
import pandas as pd
import os
import json
import threading
import requests

app = Flask(__name__)
CORS(app)

CSV_PATH = "ladder_results.csv"

def fetch_and_save():
    try:
        url = "https://ntry.com/data/json/games/power_ladder/recent_result.json"
        response = requests.get(url)
        data = response.json()

        df_new = pd.json_normalize(data)

        if os.path.exists(CSV_PATH):
            df_existing = pd.read_csv(CSV_PATH)
            df = pd.concat([df_existing, df_new]).drop_duplicates(subset=['회차'], keep='last')
        else:
            df = df_new

        df.to_csv(CSV_PATH, index=False)
        print(f"CSV 저장 완료: {len(df)}개 행")
    except Exception as e:
        print(f"CSV 저장 실패: {e}")

    threading.Timer(60, fetch_and_save).start()  # 60초 후 다시 실행

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

def find_flow_matches(full_data, max_block=6, min_block=3):
    results = []
    used_indices = set()

    for block_len in range(min_block, max_block + 1):
        found = False
        for i in reversed(range(len(full_data) - block_len)):
            if any(idx in used_indices for idx in range(i, i + block_len)):
                continue
            block = full_data[i:i+block_len]
            pred_index = i - 1
            pred = full_data[pred_index] if pred_index >= 0 else "❌ 없음"
            results.append({
                "예측값": pred,
                "블럭": ">".join(block),
                "매칭순번": i + 1
            })
            for idx in range(i, i + block_len):
                used_indices.add(idx)
            found = True
            break
        if found:
            continue
    return results

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

        data = df.tail(5000).iloc[::-1]
        flow_list = [convert(row) for _, row in data.iterrows()]

        size = int(mode[0])
        recent_flow = flow_list[:size]

        if "flip_full" in mode:
            flow = flip_full(recent_flow)
        elif "flip_start" in mode:
            flow = flip_start(recent_flow)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_flow)
        else:
            flow = recent_flow

        matches = find_flow_matches(flow_list)

        round_num = int(df.iloc[-1]["회차"]) + 1

        top_preds = [m["예측값"] for m in matches[:3]]
        while len(top_preds) < 3:
            top_preds.append("❌ 없음")

        response_data = {
            "예측회차": round_num,
            "예측값": top_preds,
            "블럭": matches[0]["블럭"] if matches else "❌ 없음",
            "매칭순번": matches[0]["매칭순번"] if matches else "❌ 없음"
        }

        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')

    except Exception as e:
        error_data = {"error": str(e)}
        return Response(json.dumps(error_data, ensure_ascii=False), mimetype='application/json')

if __name__ == '__main__':
    fetch_and_save()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
