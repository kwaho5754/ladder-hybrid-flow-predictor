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
        df_new = pd.json_normalize(response.json())

        if 'date_round' in df_new.columns:
            df_new = df_new.rename(columns={'date_round': '회차'})

        df_new['회차'] = df_new['회차'].astype(int)

        if os.path.exists(CSV_PATH):
            df_existing = pd.read_csv(CSV_PATH)
            df_existing['회차'] = df_existing['회차'].astype(int)

            existing_rounds = set(df_existing['회차'])
            new_rows = df_new[~df_new['회차'].isin(existing_rounds)]

            if not new_rows.empty:
                df_updated = pd.concat([df_existing, new_rows])
                df_updated.to_csv(CSV_PATH, index=False)
        else:
            df_new.to_csv(CSV_PATH, index=False)

    except Exception as e:
        print(f"CSV 저장 실패: {e}")

    threading.Timer(60, fetch_and_save).start()

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

def find_flow_matches(flow, max_block=6, min_block=3):
    results = []
    used_blocks = []

    for block_len in range(min_block, max_block + 1):
        found = False
        for i in reversed(range(len(flow) - block_len)):
            block = flow[i:i + block_len]
            block_str = ">".join(block)

            # 중복 블럭 여부 판단
            is_overlapping = any(prev in block_str for prev in used_blocks)
            if is_overlapping:
                continue

            pred_index = i - 1
            pred = flow[pred_index] if pred_index >= 0 else "❌ 없음"
            results.append({
                "예측값": pred,
                "블럭": block_str,
                "매칭순번": i + 1
            })
            used_blocks.append(block_str)
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
            return Response(json.dumps({"error": "CSV 파일 없음"}, ensure_ascii=False), mimetype='application/json')

        df = pd.read_csv(CSV_PATH)
        if len(df) < 10:
            return Response(json.dumps({"error": "CSV 데이터 부족"}, ensure_ascii=False), mimetype='application/json')

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

        matches = find_flow_matches(flow)

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
        return Response(json.dumps({"error": str(e)}, ensure_ascii=False), mimetype='application/json')

@app.route("/check_csv")
def check_csv():
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
            rounds = df['회차'].tolist()[:5]
            return f"CSV 있음, 회차 일부: {rounds}"
        except Exception as e:
            return f"CSV 읽기 오류: {str(e)}"
    else:
        return "CSV 파일 없음"

if __name__ == '__main__':
    fetch_and_save()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
