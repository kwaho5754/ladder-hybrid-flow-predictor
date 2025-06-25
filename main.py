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

def is_overlapping(i, block_len, used_ranges):
    for start, length in used_ranges:
        if max(i, start) < min(i + block_len, start + length):
            return True
    return False

def find_all_matches_exclusive(flow, full_data, block_len, used_ranges, transform_fn):
    top_values = []
    bottom_values = []

    for i in reversed(range(len(full_data) - block_len)):
        if is_overlapping(i, block_len, used_ranges):
            continue

        candidate = full_data[i:i + block_len]
        transformed = transform_fn(candidate)

        if transformed == flow:
            top_idx = i - 1
            bottom_idx = i + block_len

            if top_idx >= 0:
                top_values.append(full_data[top_idx])
            if bottom_idx < len(full_data):
                bottom_values.append(full_data[bottom_idx])

            used_ranges.append((i, block_len))

    return top_values, bottom_values

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict_top3_summary")
def predict_top3_summary():
    try:
        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(3000) \
            .execute()

        raw = response.data
        all_data = [convert(d) for d in raw]

        result = {}
        used_ranges = []

        transform_fns = [
            ("원본", lambda x: x),
            ("대칭", flip_full),
            ("시작점", flip_start),
            ("홀짝", flip_odd_even)
        ]

        for size in [6, 5, 4, 3]:
            recent_block = all_data[:size]
            all_top = []
            all_bottom = []

            for label, fn in transform_fns:
                flow = fn(recent_block)
                top_vals, bottom_vals = find_all_matches_exclusive(flow, all_data, size, used_ranges, fn)
                all_top += top_vals
                all_bottom += bottom_vals

            result[f"{size}줄 블럭 Top3 요약"] = {
                "Top3상단": [v[0] for v in Counter(all_top).most_common(3)],
                "Top3하단": [v[0] for v in Counter(all_bottom).most_common(3)]
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)