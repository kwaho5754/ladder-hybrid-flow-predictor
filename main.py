from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
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

# ✅ 블럭 겹침 방지: 앞 블럭 매칭되면, 이후 블럭이 그 일부 포함 시 건너뜀
def find_flow_matches(flow, max_block=6, min_block=3):
    results = []
    used_ranges = []

    for block_len in range(min_block, max_block + 1):
        found = False
        for i in reversed(range(len(flow) - block_len)):
            block_range = set(range(i, i + block_len))
            if any(block_range & used for used in used_ranges):
                continue

            block = flow[i:i + block_len]
            pred_index = i - 1
            pred = flow[pred_index] if pred_index >= 0 else "❌ 없음"

            results.append({
                "예측값": pred,
                "블럭": ">".join(block),
                "매칭순번": i + 1
            })

            used_ranges.append(set(range(i, i + block_len)))
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
        raw = requests.get(URL).json()
        data = raw[-288:]
        mode = request.args.get("mode", "3block_orig")
        round_num = int(data[0]['date_round']) + 1
        size = int(mode[0])
        recent_flow = [convert(d) for d in data[:size]]
        all_data = [convert(d) for d in data]

        if "flip_full" in mode:
            flow = flip_full(recent_flow)
        elif "flip_start" in mode:
            flow = flip_start(recent_flow)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_flow)
        else:
            flow = recent_flow

        matches = find_flow_matches(all_data)

        top_preds = [m["예측값"] for m in matches[:3]]
        while len(top_preds) < 3:
            top_preds.append("❌ 없음")

        response_data = {
            "예측회차": round_num,
            "예측값": top_preds,
            "블럭": matches[0]["블럭"] if matches else "❌ 없음",
            "매칭순번": matches[0]["매칭순번"] if matches else "❌ 없음"
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
