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

def find_all_matches(block, full_data, used_indices):
    top_matches = []
    bottom_matches = []
    matched_indices = []
    block_len = len(block)

    for i in reversed(range(len(full_data) - block_len)):
        block_range = range(i, i + block_len)
        if any(idx in used_indices for idx in block_range):
            continue

        candidate = full_data[i:i + block_len]
        if candidate == block:
            matched_indices.extend(block_range)

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

    return top_matches, bottom_matches, matched_indices

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict_full_matches")
def predict_full_matches():
    try:
        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(3000) \
            .execute()

        raw = response.data
        all_data = [convert(d) for d in raw]

        result = defaultdict(dict)

        used_6 = set()
        used_5 = set()
        used_4 = set()

        block_defs = [
            (6, "6줄 블럭", set(), used_6),
            (5, "5줄 블럭", used_6, used_5),
            (4, "4줄 블럭", used_5, used_4),
            (3, "3줄 블럭", used_4, None),
        ]

        for size, label, exclude_set, update_set in block_defs:
            base_block = all_data[:size]
            transform_modes = {
                "원본": lambda x: x,
                "대칭": flip_full,
                "시작점변형": flip_start,
                "홀짝변형": flip_odd_even
            }

            for mode_name, fn in transform_modes.items():
                transformed = fn(base_block)
                top, bottom, matched = find_all_matches(transformed, all_data, exclude_set)

                if update_set is not None:
                    update_set.update(matched)

                result[label][mode_name] = {
                    "상단": top,
                    "하단": bottom
                }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
