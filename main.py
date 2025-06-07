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

def find_all_matches(block, full_data, used_index=set()):
    top_matches = []
    bottom_matches = []
    matched_indices = set()
    block_len = len(block)

    for i in reversed(range(len(full_data) - block_len)):
        block_range = set(range(i, i + block_len))
        if block_range & used_index:
            continue

        candidate = full_data[i:i + block_len]
        if candidate == block:
            used_index.update(block_range)
            matched_indices.update(block_range)

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

    return top_matches, bottom_matches, matched_indices

def get_non_overlapping_block(size, all_data, used_index):
    for i in range(len(all_data) - size):
        block_range = set(range(i, i + size))
        if not block_range & used_index:
            return all_data[i:i+size], block_range
    return [], set()

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
        used_index_total = set()

        # **1️⃣ 4줄 블럭 먼저 선택 및 매칭**
        size = 4
        transform_modes = {
            "flip_full": flip_full,
            "flip_start": flip_start,
            "flip_odd_even": flip_odd_even
        }

        for fn in transform_modes.values():
            block, block_range = get_non_overlapping_block(size, all_data, used_index_total)
            if not block:
                continue

            flow = fn(block)
            top, bottom, matched = find_all_matches(flow, all_data, used_index_total)

            used_index_total.update(block_range)  # **4줄 블럭에서 사용된 인덱스 저장**
            used_index_total.update(matched)

        # **2️⃣ 3줄 블럭 선택 시 4줄 사용된 인덱스를 철저히 제외**
        size = 3
        top_values = []
        bottom_values = []

        for fn in transform_modes.values():
            block, block_range = get_non_overlapping_block(size, all_data, used_index_total)  # 🚀 4줄과 중복 방지
            if not block:
                continue

            flow = fn(block)
            top, bottom, matched = find_all_matches(flow, all_data, used_index_total)

            used_index_total.update(block_range)
            used_index_total.update(matched)

            top_values += [t["값"] for t in top if t["값"] != "❌ 없음"]
            bottom_values += [b["값"] for b in bottom if b["값"] != "❌ 없음"]

        top_counter = Counter(top_values)
        bottom_counter = Counter(bottom_values)

        result[f"4줄 블럭 Top3 요약"] = {
            "Top3상단": [v[0] for v in top_counter.most_common(3)],
            "Top3하단": [v[0] for v in bottom_counter.most_common(3)]
        }

        result[f"3줄 블럭 Top3 요약"] = {
            "Top3상단": [v[0] for v in top_counter.most_common(3)],
            "Top3하단": [v[0] for v in bottom_counter.most_common(3)]
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)