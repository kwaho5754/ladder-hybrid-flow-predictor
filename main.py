# ⬇️ main.py — 하이브리드 예측 시스템
# 정방향 + 역방향 점수제 통합 + 흐름 분석 포함

from flask import Flask, jsonify, send_file
from flask_cors import CORS
import requests
import os
from collections import defaultdict

app = Flask(__name__)
CORS(app)

def parse_block(block):
    return block[0], block[1], block[2]

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def flip_start(s): return '우' if s == '좌' else '좌'
def flip_oe(o): return '짝' if o == '홀' else '홀'

def generate_variants_for_block(block):
    variants = {"원본": block, "대칭시작": [], "대칭홀짝": [], "대칭둘다": []}
    for b in block:
        s, c, o = parse_block(b)
        variants["대칭시작"].append(f"{flip_start(s)}{c}{o}")
        variants["대칭홀짝"].append(f"{s}{c}{flip_oe(o)}")
        variants["대칭둘다"].append(f"{flip_start(s)}{c}{flip_oe(o)}")
    return variants

def score_blocks(data, size, reverse=False):
    if reverse:
        data = list(reversed(data))
    recent = [convert(d) for d in data[:size]]
    variants = generate_variants_for_block(recent)
    all_data = [convert(d) for d in data]

    scores = defaultdict(lambda: {"score": 0, "detail": defaultdict(int)})
    for i in range(len(all_data) - size):
        past = all_data[i:i+size]
        target_idx = i + size if reverse else i - 1
        if target_idx < 0 or target_idx >= len(data): continue
        target = convert(data[target_idx])

        for key, variant in variants.items():
            if past == variant:
                weight = {"원본": 3, "대칭시작": 2, "대칭홀짝": 2, "대칭둘다": 1}[key]
                scores[target]["score"] += weight
                scores[target]["detail"][key] += 1
    return scores

def analyze_flow(data):
    flow = {"시작방향": [], "줄수": [], "홀짝": []}
    for d in data[-5:]:
        s, c, o = parse_block(convert(d))
        flow["시작방향"].append(s)
        flow["줄수"].append(int(c))
        flow["홀짝"].append(o)
    불안정도 = sum(1 for i in range(4) if flow["줄수"][i] != flow["줄수"][i+1]) / 4
    return {**flow, "불안정도": round(불안정도, 2)}

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        url = "https://ntry.com/data/json/games/power_ladder/recent_result.json"
        raw = requests.get(url).json()
        data = raw[-288:]
        round_num = int(raw[-1]['date_round']) + 1

        scores = defaultdict(lambda: {"score": 0, "detail": defaultdict(int)})
        for size in range(3, 8):
            for reverse in [False, True]:
                result = score_blocks(data, size, reverse)
                for k, v in result.items():
                    scores[k]["score"] += v["score"]
                    for dkey, dval in v["detail"].items():
                        scores[k]["detail"][dkey] += dval

        sorted_result = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
        top3 = []
        for i in range(3):
            if i < len(sorted_result):
                name, info = sorted_result[i]
                top3.append({"값": name, "점수": info["score"], "근거": dict(info["detail"])})
            else:
                top3.append({"값": "❌ 없음", "점수": 0, "근거": {}})
        flow_info = analyze_flow(data)

        return jsonify({"예측회차": round_num, "Top3": top3, "흐름해석": flow_info})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
