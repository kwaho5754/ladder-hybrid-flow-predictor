from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import defaultdict

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

def find_matches(block, all_data, used_indices):
    top_matches, bottom_matches = [], []
    matched_indices = set()
    L = len(block)

    for i in reversed(range(len(all_data) - L)):
        indices_range = set(range(i, i + L))
        if indices_range & used_indices:
            continue
        if all_data[i:i + L] == block:
            matched_indices.update(indices_range)

            top_val = all_data[i - 1] if i - 1 >= 0 else "❌ 없음"
            bottom_val = all_data[i + L] if i + L < len(all_data) else "❌ 없음"

            top_matches.append({"값": top_val, "블럭": ">".join(block), "순번": i + 1})
            bottom_matches.append({"값": bottom_val, "블럭": ">".join(block), "순번": i + 1})

    if not top_matches:
        top_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})
    if not bottom_matches:
        bottom_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})

    return top_matches[:12], bottom_matches[:12], matched_indices

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        response = supabase.table(SUPABASE_TABLE)\
            .select("*")\
            .order("reg_date", desc=True)\
            .order("date_round", desc=True)\
            .limit(3000)\
            .execute()

        raw = response.data
        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]

        used_6 = set()
        used_5 = set()
        used_4 = set()
        used_3 = set()

        result_top = []
        result_bottom = []

        def handle_block(size, transform_fn, used_above):
            base_block = all_data[:size]
            block = transform_fn(base_block)
            top, bottom, matched = find_matches(block, all_data, used_above)
            return top, bottom, matched

        block_defs = [
            (6, flip_full, used_6),
            (5, flip_start, used_5),
            (4, flip_odd_even, used_4),
            (3, lambda x: x, used_3),
        ]

        for size, fn, used in block_defs:
            if size == 6:
                used_above = set()
            elif size == 5:
                used_above = used_6
            elif size == 4:
                used_above = used_5
            elif size == 3:
                used_above = used_4

            top, bottom, matched = handle_block(size, fn, used_above)
            used.update(matched)
            result_top.extend(top)
            result_bottom.extend(bottom)

        return jsonify({
            "예측회차": round_num,
            "상단값들": result_top,
            "하단값들": result_bottom
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
