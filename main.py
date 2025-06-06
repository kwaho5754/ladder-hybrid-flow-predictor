from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter
import numpy as np

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "ladder")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def convert(entry):
    try:
        start = entry.get('start_point', '')
        line = entry.get('line_count', '')
        oe = entry.get('odd_even', '')

        if start not in ['LEFT', 'RIGHT'] or line not in [3, 4] or oe not in ['EVEN', 'ODD']:
            raise ValueError("Invalid entry")

        side = '좌' if start == 'LEFT' else '우'
        count = str(line)
        parity = '짝' if oe == 'EVEN' else '홀'
        return f"{side}{count}{parity}"
    except:
        return '❌ 없음'

def meta_flow_predict(data):
    recent = data[:100]
    counter = Counter(recent)
    total = sum(counter.values())
    score_map = {k: 1 - (v/total)**1.2 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

def low_frequency_predict(data):
    mid_range = data[50:200]
    counter = Counter(mid_range)
    total = sum(counter.values())
    score_map = {k: (1 - (v / total))**1.8 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

def reverse_bias_predict(data):
    long_range = data[:1000]
    bias = {'좌': 0, '우': 0, '홀': 0, '짝': 0, '3': 0, '4': 0}
    for d in long_range:
        if d.startswith('좌'): bias['좌'] += 1
        if d.startswith('우'): bias['우'] += 1
        if '홀' in d: bias['홀'] += 1
        if '짝' in d: bias['짝'] += 1
        if '3' in d: bias['3'] += 1
        if '4' in d: bias['4'] += 1
    result = ''
    result += '우' if bias['좌'] > bias['우'] else '좌'
    result += '4' if bias['3'] > bias['4'] else '3'
    result += '짝' if bias['홀'] > bias['짝'] else '홀'
    return result

def start_position_predict(data):
    window = data[100:300]
    left = sum(1 for d in window if d.startswith('좌'))
    right = len(window) - left
    return '좌3홀' if left > right else '우4짝'

def periodic_pattern_predict(data):
    pattern_range = data[200:1000]
    score = Counter()
    for offset in [5, 13, 21]:
        for i in range(offset, len(pattern_range)):
            if pattern_range[i] == pattern_range[i - offset]:
                score[pattern_range[i]] += 1
    return max(score, key=score.get) if score else '❌ 없음'

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/meta_predict")
def meta_predict():
    try:
        response = supabase.table(SUPABASE_TABLE).select("*")\
            .order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute()
        raw = response.data
        all_data = [convert(d) for d in raw][::-1]

        diverse_preds = {
            "시작 위치": start_position_predict(all_data),
            "주기 반복": periodic_pattern_predict(all_data),
            "편향 반전": reverse_bias_predict(all_data),
            "흐름 기반": meta_flow_predict(all_data),
            "희귀 기반": low_frequency_predict(all_data)
        }

        return jsonify({
            "예측회차": int(raw[0]["date_round"]) + 1 if "date_round" in raw[0] else 9999,
            "다양한예측값": diverse_preds
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/latest_blocks")
def latest_blocks():
    try:
        response = supabase.table(SUPABASE_TABLE).select("*")\
            .order("reg_date", desc=True).order("date_round", desc=True).limit(5).execute()
        raw = response.data
        blocks = [convert(d) for d in raw][::-1]
        return jsonify({"blocks": blocks})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)