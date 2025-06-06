from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "ladder")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    return [('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀') for s, c, o in map(parse_block, block)]

def flip_start(block):
    return [s + ('4' if c == '3' else '3') + ('홀' if o == '짝' else '짝') for s, c, o in map(parse_block, block)]

def flip_odd_even(block):
    return [('우' if s == '좌' else '좌') + ('4' if c == '3' else '3') + o for s, c, o in map(parse_block, block)]

def find_all_matches(block, full_data):
    top_matches = []
    bottom_matches = []
    block_len = len(block)

    for i in reversed(range(len(full_data) - block_len)):
        candidate = full_data[i:i + block_len]
        if candidate == block:
            top_index = i - 1
            top_pred = full_data[top_index] if top_index >= 0 else "❌ 없음"
            top_matches.append({
                "값": top_pred,
                "블럭": ">".join(block),
                "순번": i + 1
            })

            bottom_index = i + block_len
            bottom_pred = full_data[bottom_index] if bottom_index < len(full_data) else "❌ 없음"
            bottom_matches.append({
                "값": bottom_pred,
                "블럭": ">".join(block),
                "순번": i + 1
            })

    if not top_matches:
        top_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})
    if not bottom_matches:
        bottom_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})

    top_matches = sorted(top_matches, key=lambda x: int(x["순번"]) if str(x["순번"]).isdigit() else 99999)[:12]
    bottom_matches = sorted(bottom_matches, key=lambda x: int(x["순번"]) if str(x["순번"]).isdigit() else 99999)[:12]

    return top_matches, bottom_matches

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        mode = request.args.get("mode", "3block_orig")
        size = int(mode[0])
        transform = mode.split("_")[1] if "_" in mode else "orig"

        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(3000) \
            .execute()

        raw = response.data
        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]

        # 최근 흐름에서 블럭 길이만큼 슬라이딩하면서 동일한 블럭만 허용
        recent_block = []
        for i in range(len(all_data) - size + 1):
            block_candidate = all_data[i:i+size]
            valid = True
            for j in range(1, size):
                if all_data[i+j-1][-1] == all_data[i+j][-1]:  # 예시로 홀짝이 동일하면 불연속
                    valid = False
                    break
            if valid:
                recent_block = block_candidate
                break

        if not recent_block:
            return jsonify({
                "예측회차": round_num,
                "상단값들": [{"값": "❌ 없음", "블럭": "없음", "순번": "❌"}],
                "하단값들": [{"값": "❌ 없음", "블럭": "없음", "순번": "❌"}]
            })

        if transform == "flip_full":
            recent_block = flip_full(recent_block)
        elif transform == "flip_start":
            recent_block = flip_start(recent_block)
        elif transform == "flip_odd_even":
            recent_block = flip_odd_even(recent_block)

        top, bottom = find_all_matches(recent_block, all_data)

        return jsonify({
            "예측회차": round_num,
            "상단값들": top,
            "하단값들": bottom
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)