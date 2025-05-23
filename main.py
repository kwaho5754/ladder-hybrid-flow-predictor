# main.py (복사 버튼 지원 HTML 박스 포함 출력용)
# ✅ 흐름 일치 + 흐름 반전 + 블럭 기반 통합 예측 구조

from flask import Flask, jsonify, send_file
from flask_cors import CORS
import requests
import os
from collections import defaultdict, Counter

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

def analyze_flow(data):
    flow = {"시작방향": [], "줄수": [], "홀짝": []}
    for d in data[-5:]:
        s, c, o = parse_block(convert(d))
        flow["시작방향"].append(s)
        flow["줄수"].append(int(c))
        flow["홀짝"].append(o)
    불안정도 = sum(1 for i in range(4) if flow["줄수"][i] != flow["줄수"][i+1]) / 4
    return {**flow, "불안정도": round(불안정도, 2)}

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

def detect_recent_flow(data, n=20):
    return [convert(d) for d in data[-n:]]

def detect_reverse_pattern_match(data, recent_flow):
    all_data = [convert(d) for d in data]
    reverse_scores = defaultdict(int)
    length = len(recent_flow)
    for i in range(len(all_data) - length - 1):
        if all_data[i:i+length] == recent_flow:
            next_value = all_data[i+length]
            reverse_scores[next_value] += 1
    return reverse_scores

def get_most_common_flow_item(data):
    last = convert(data[-1])
    return parse_block(last)

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        url = "https://ntry.com/data/json/games/power_ladder/recent_result.json"
        raw = requests.get(url).json()
        data = raw[-288:]
        round_num = int(raw[0]['date_round']) + 1

        flow_info = analyze_flow(data)
        instability = flow_info["불안정도"]

        scores = defaultdict(lambda: {"score": 0, "detail": defaultdict(int)})
        for size in range(3, 8):
            for reverse in [False, True]:
                result = score_blocks(data, size, reverse)
                for k, v in result.items():
                    scores[k]["score"] += v["score"]
                    for dkey, dval in v["detail"].items():
                        scores[k]["detail"][dkey] += dval

        recent_flow = detect_recent_flow(data, 20)
        reverse_boost = detect_reverse_pattern_match(data, recent_flow)
        flow_start, flow_line, flow_oe = get_most_common_flow_item(data)

        scored_items = []
        for name, info in scores.items():
            s, c, o = parse_block(name)
            match_score = 0
            if s == flow_start: match_score += 1
            if int(c) == int(flow_line): match_score += 1
            if o == flow_oe: match_score += 1
            flow_match_bonus = match_score * 1.0
            reverse_bonus = reverse_boost.get(name, 0) * 2
            adjusted_score = round((info["score"] + reverse_bonus + flow_match_bonus) * (1 - instability * 0.5), 2)
            scored_items.append((name, adjusted_score, info["detail"]))

        seen = set()
        top5 = []
        for name, adj_score, details in sorted(scored_items, key=lambda x: x[1], reverse=True):
            if name not in seen and adj_score > 0:
                top5.append({"값": name, "점수": adj_score, "근거": dict(details)})
                seen.add(name)
            if len(top5) == 5:
                break

        if not top5:
            top5 = [{"값": "❌ 예측 불가 (불안정도 최대)", "점수": 0, "근거": {}}]

        return jsonify({"예측회차": round_num, "Top5": top5, "흐름해석": flow_info})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
