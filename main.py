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

def flip(block):
    result = []
    for b in block:
        s = b[0]
        c = b[1:-1]
        o = b[-1]
        flipped = ('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀')
        result.append(flipped)
    return result

def find_prediction(block, all_blocks):
    for i in reversed(range(len(all_blocks) - len(block))):
        if all_blocks[i:i+len(block)] == block:
            if i - 1 >= 0:
                return all_blocks[i - 1]
            break
    return "❌ 없음"

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
        all_blocks = [convert(d) for d in data]

        results = {}
        for size in range(3, 7):
            recent_block = [convert(d) for d in data[:size]]
            flipped_block = flip(recent_block)

            original = find_prediction(recent_block, all_blocks)
            flipped = find_prediction(flipped_block, all_blocks)

            results[f"{size}줄"] = {
                "원본": original,
                "대칭": flipped
            }

        return jsonify({"예측회차": round_num, "예측결과": results})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
