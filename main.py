from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

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

        if start not in ['LEFT', 'RIGHT']:
            raise ValueError(f"start_point 이상: {start}")
        if line not in [3, 4]:
            raise ValueError(f"line_count 이상: {line}")
        if oe not in ['EVEN', 'ODD']:
            raise ValueError(f"odd_even 이상: {oe}")

        side = '좌' if start == 'LEFT' else '우'
        count = str(line)
        parity = '짝' if oe == 'EVEN' else '홀'
        return f"{side}{count}{parity}"

    except Exception as e:
        print(f"⚠️ 변환 실패: {e} → entry: {entry}")
        return '❌ 없음'

def normalize(value):
    if '좌3짝' in value: return '좌삼짝'
    if '우3홀' in value: return '우삼홀'
    if '좌4홀' in value: return '좌사홀'
    if '우4짝' in value: return '우사짝'
    return '❌ 없음'

# 기존 10개 예측 모델들
def meta_flow_predict(data):
    counter = Counter(data[:100])
    total = sum(counter.values())
    score_map = {k: 1 - (v/total)**1.2 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

def periodic_pattern_predict(data):
    score = defaultdict(int)
    for offset in [5, 13]:
        for i in range(offset, len(data)):
            if data[i] == data[i - offset]:
                score[data[i]] += 1
    return max(score, key=score.get) if score else '❌ 없음'

def even_line_predict(data):
    even_lines = [data[i] for i in range(0, min(len(data), 100), 2)]
    counter = Counter(even_lines)
    total = sum(counter.values())
    score_map = {k: 1 - (v / total)**1.1 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

def low_frequency_predict(data):
    recent = data[:50]
    counter = Counter(recent)
    total = sum(counter.values())
    score_map = {k: (1 - (v / total))**1.5 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

def reverse_bias_predict(data):
    recent = data[:30]
    bias = {'좌': 0, '우': 0, '홀': 0, '짝': 0, '3': 0, '4': 0}
    for d in recent:
        if d.startswith('좌'): bias['좌'] += 1
        if d.startswith('우'): bias['우'] += 1
        if '홀' in d: bias['홀'] += 1
        if '짝' in d: bias['짝'] += 1
        if '3' in d: bias['3'] += 1
        if '4' in d: bias['4'] += 1
    result = ''
    result += '우' if bias['좌'] > 21 else '좌' if bias['우'] > 21 else '좌'
    result += '4' if bias['3'] > 21 else '3' if bias['4'] > 21 else '3'
    result += '짝' if bias['홀'] > 21 else '홀' if bias['짝'] > 21 else '홀'
    return result

def volatility_predict(data):
    recent = data[:30]
    diffs = [1 if recent[i] != recent[i + 1] else 0 for i in range(len(recent) - 1)]
    rate = sum(diffs) / len(diffs)
    counter = Counter(recent)
    if rate < 0.3:
        score_map = {k: 1 - (v / sum(counter.values())) for k, v in counter.items()}
        return max(score_map, key=score_map.get)
    return counter.most_common(1)[0][0]

def trend_bias_predict(data):
    recent = data[:30]
    counter = Counter(recent)
    for key, val in counter.items():
        if val > 18:
            return key
    return '❌ 없음'

def start_position_predict(data):
    recent = data[:40]
    left = sum(1 for d in recent if d.startswith('좌'))
    right = len(recent) - left
    return '좌3홀' if left > right else '우4짝'

def odd_even_flow_predict(data):
    recent = data[:30]
    flow = ''.join(['1' if '홀' in x else '0' for x in recent])
    if flow.endswith('1010'): return '좌3홀'
    if flow.endswith('0101'): return '우4짝'
    return '좌4홀'

def block_tail_predict(data):
    tail = data[5:35]
    counter = Counter(tail)
    return counter.most_common(1)[0][0] if counter else '❌ 없음'

# 추가된 1, 3, 5번 기능들
def detect_anomaly(data, window=20, threshold=0.3):
    try:
        values = np.array([hash(d) % 100 for d in data])
        if len(values) < window:
            return False
        rolling_std = np.std(values[-window:])
        return rolling_std > threshold
    except Exception as e:
        print(f"Error in detect_anomaly: {e}")
        return False

def anomaly_focused_predict(data):
    if detect_anomaly(data):
        counter = Counter(data[-50:])
        rare = [k for k, v in counter.items() if v < 3]
        return rare if rare else ['❌ 없음']
    return ['❌ 없음']

def decompose_timeseries(data):
    try:
        values = [hash(d) % 100 for d in data]
        series = pd.Series(values)
        if len(series) < 13:
            return []
        result = seasonal_decompose(series, model='additive', period=12, extrapolate_trend='freq')
        return result.resid.dropna().tolist()
    except Exception as e:
        print(f"Error in decompose_timeseries: {e}")
        return []

PRIORITY = {'좌삼짝': 0, '우삼홀': 1, '좌사홀': 2, '우사짝': 3, '❌ 없음': 99}

def fixed_top3(predictions):
    norm = [normalize(p) for p in predictions if isinstance(p, str) and p != '❌ 없음']
    count = Counter(norm)
    sorted_items = sorted(count.items(), key=lambda x: (-x[1], PRIORITY.get(x[0], 99)))
    return [item[0] for item in sorted_items[:3]]

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

        anomaly_flag = detect_anomaly(all_data)
        anomaly_preds = anomaly_focused_predict(all_data)
        residuals = decompose_timeseries(all_data)

        base_preds = [
            meta_flow_predict(all_data),
            periodic_pattern_predict(all_data),
            even_line_predict(all_data),
            low_frequency_predict(all_data),
            reverse_bias_predict(all_data),
            volatility_predict(all_data),
            trend_bias_predict(all_data),
            start_position_predict(all_data),
            odd_even_flow_predict(all_data),
            block_tail_predict(all_data),
        ]

        if anomaly_preds != ['❌ 없음']:
            base_preds.extend(p for p in anomaly_preds if isinstance(p, str))

        top3_final = fixed_top3(base_preds)

        return jsonify({
            "예측회차": int(raw[0]["date_round"]) + 1 if "date_round" in raw[0] else 9999,
            "Top3최종예측": top3_final,
            "변화감지": anomaly_flag,
            "잔차분석": residuals[:10]
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
