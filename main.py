# ✅ 수정된 main.py - 3줄 블럭, 5방향, 연결제외, 상단값 10개 + top1
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

def find_matches_3_only(block, all_data):
    matches = []
    for i in range(len(all_data) - 3):
        candidate3 = all_data[i:i+3]
        candidate4 = all_data[i:i+4]
        if candidate3 == block and candidate4 != all_data[:4]:
            pred_index = i - 1
            pred = all_data[pred_index] if pred_index >= 0 else "❌ 없음"
            matches.append({
                "값": pred,
                "블럭": ">".join(block),
                "순번": i + 1
            })
    return sorted(matches, key=lambda x: int(x["순번"]))[:10]

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        mode = request.args.get("mode", "3block_orig")
        response = supabase.table(SUPABASE_TABLE).select("*").order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute()

        raw = response.data
        all_data = [convert(d) for d in raw]
        round_num = int(raw[0]["date_round"]) + 1
        recent_3 = all_data[:3]

        if "flip_full" in mode:
            flow = flip_full(recent_3)
        elif "flip_start" in mode:
            flow = flip_start(recent_3)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_3)
        elif "rotate" in mode:
            flow = list(reversed(recent_3))
        else:
            flow = recent_3

        matches = find_matches_3_only(flow, all_data)
        top1 = Counter([m["값"] for m in matches if m["값"] != "❌ 없음"]).most_common(1)

        return jsonify({
            "예측회차": round_num,
            "상단값들": matches,
            "top1": top1[0][0] if top1 else "❌ 없음"
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
