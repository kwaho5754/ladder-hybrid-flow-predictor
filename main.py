from flask import Flask, jsonify, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

# 4가지 변형 방식
def flip_full(block):
    return [('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀') for s, c, o in map(parse_block, block)]

def flip_start(block):
    return [s + ('4' if c == '3' else '3') + ('홀' if o == '짝' else '짝') for s, c, o in map(parse_block, block)]

def flip_odd_even(block):
    return [('우' if s == '좌' else '좌') + ('4' if c == '3' else '3') + o for s, c, o in map(parse_block, block)]

def find_prediction(block, all_blocks):
    for i in reversed(range(len(all_blocks) - len(block))):
        if all_blocks[i:i+len(block)] == block:
            pred_index = i - 1
            pred = all_blocks[pred_index] if pred_index >= 0 else "❌ 없음"
            return pred, ">".join(block), i + 1
    return "❌ 없음", ">".join(block), -1

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        url = "https://ntry.com/data/json/games/power_ladder/recent_result.json"
        raw = requests.get(url).json()
        data = raw[-288:]
        round_num = int(data[0]['date_round']) + 1
        all_blocks = [convert(d) for d in data]

        results = {}
        transforms = {
            "orig": lambda x: x,
            "flip_start": flip_start,
            "flip_odd_even": flip_odd_even,
            "flip_full": flip_full
        }

        for size in range(3, 7):
            base_block = [convert(d) for d in data[:size]]
            for key, func in transforms.items():
                transformed = func(base_block)
                pred, blk, idx = find_prediction(transformed, all_blocks)
                results[f"{size}block_{key}"] = {
                    "예측값": pred,
                    "블럭": blk,
                    "매칭순번": idx
                }

        return jsonify({
            "예측회차": round_num,
            **results
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
