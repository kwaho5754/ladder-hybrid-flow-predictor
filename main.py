from flask import Flask, jsonify, send_from_directory
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

def find_all_matches(block, full_data, exclude_indices=None):
    if exclude_indices is None:
        exclude_indices = set()

    top_matches = []
    bottom_matches = []
    block_len = len(block)

    for i in reversed(range(len(full_data) - block_len)):
        if i in exclude_indices:
            continue

        candidate = full_data[i:i + block_len]
        if candidate == block:
            top_index = i - 1
            top_pred = full_data[top_index] if top_index >= 0 else "❌ 없음"
            bottom_index = i + block_len
            bottom_pred = full_data[bottom_index] if bottom_index < len(full_data) else "❌ 없음"

            top_matches.append({"값": top_pred, "블럭": ">".join(block), "순번": i + 1})
            bottom_matches.append({"값": bottom_pred, "블럭": ">".join(block), "순번": i + 1})
            exclude_indices.add(i)

    if not top_matches:
        top_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})
    if not bottom_matches:
        bottom_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})

    return top_matches[:20], bottom_matches[:20], exclude_indices

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict_all")
def predict_all():
    try:
        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(7000) \
            .execute()

        raw = response.data
        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]
        recent_base = all_data[:6]  # a0~a5 기준 블럭 생성은 동일

        result = {}
        used_indices_by_size = {6: set(), 5: set(), 4: set(), 3: set()}

        block_sizes = [6, 5, 4, 3]  # 긴 줄 먼저 매칭
        transforms = {
            "orig": lambda x: x,
            "flip_full": flip_full,
            "flip_start": flip_start,
            "flip_odd_even": flip_odd_even
        }

        for size in block_sizes:
            base_block = recent_base[:size]  # 동일한 블럭 생성 기준 사용
            for transform_name, fn in transforms.items():
                key = f"{size}block_{transform_name}"
                flow = fn(base_block)
                top, bottom, used = find_all_matches(flow, all_data, used_indices_by_size[size])
                used_indices_by_size[size].update(used)  # 같은 줄수끼리만 겹침 방지
                result[key] = {
                    "예측회차": round_num,
                    "상단값들": top,
                    "하단값들": bottom
                }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
