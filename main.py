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

def is_overlapping(i, block_len, existing_matches):
    for existing_start, existing_len in existing_matches:
        if max(i, existing_start) < min(i + block_len, existing_start + existing_len):
            return True
    return False

def find_all_matches(block, full_data, block_len, existing_matches):
    top_matches = []
    bottom_matches = []

    for i in reversed(range(len(full_data) - block_len)):
        if is_overlapping(i, block_len, existing_matches):
            continue

        candidate = full_data[i:i + block_len]
        if candidate == block:
            top_index = i - 1
            bottom_index = i + block_len

            top_value = full_data[top_index] if top_index >= 0 else "❌ 없음"
            bottom_value = full_data[bottom_index] if bottom_index < len(full_data) else "❌ 없음"

            top_matches.append({"값": top_value, "블럭": ">".join(block), "순번": i + 1})
            bottom_matches.append({"값": bottom_value, "블럭": ">".join(block), "순번": i + 1})

            existing_matches.append((i, block_len))

    if not top_matches:
        top_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})
    if not bottom_matches:
        bottom_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})

    top_matches = sorted(top_matches, key=lambda x: int(x["순번"]) if str(x["순번"]).isdigit() else 99999)[:20]
    bottom_matches = sorted(bottom_matches, key=lambda x: int(x["순번"]) if str(x["순번"]).isdigit() else 99999)[:20]

    return top_matches, bottom_matches

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        mode = request.args.get("mode", "3block_orig")
        size = int(mode[0])

        response = supabase.table(SUPABASE_TABLE).select("*").order("reg_date", desc=True).order("date_round", desc=True).limit(7000).execute()
        raw = response.data
        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]
        recent_flow = all_data[:size]

        if "flip_full" in mode:
            flow = flip_full(recent_flow)
        elif "flip_start" in mode:
            flow = flip_start(recent_flow)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_flow)
        else:
            flow = recent_flow

        existing_matches = []
        top, bottom = find_all_matches(flow, all_data, size, existing_matches)

        return jsonify({"예측회차": round_num, "상단값들": top, "하단값들": bottom})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/predict_top3_summary")
def predict_top3_summary():
    try:
        response = supabase.table(SUPABASE_TABLE).select("*").order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute()
        raw = response.data
        all_data = [convert(d) for d in raw]

        result = {}
        for size in [3, 4, 5, 6]:
            recent_block = all_data[:size]
            transform_modes = {
                "orig": lambda x: x,
                "flip_full": flip_full,
                "flip_start": flip_start,
                "flip_odd_even": flip_odd_even
            }

            top_values = []
            bottom_values = []
            existing_matches = []

            for fn in transform_modes.values():
                flow = fn(recent_block)
                top, bottom = find_all_matches(flow, all_data, size, existing_matches)
                top_values += [t["값"] for t in top if t["값"] != "❌ 없음"]
                bottom_values += [b["값"] for b in bottom if b["값"] != "❌ 없음"]

            result[f"{size}줄 블럭 Top3 요약"] = {
                "Top3상단": [v[0] for v in Counter(top_values).most_common(3)],
                "Top3하단": [v[0] for v in Counter(bottom_values).most_common(3)]
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
