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

@app.route("/predict_pure_3block")
def predict_pure_3block():
    try:
        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(3000) \
            .execute()

        raw = response.data
        all_data = [convert(d) for d in raw]

        # 3줄 블럭만 필터링
        three_only_data = [x for x in all_data if '3' in x]
        if len(three_only_data) < 3:
            return jsonify({"error": "3줄 블럭 데이터가 부족합니다."})

        base_block = three_only_data[:3]
        transform_modes = {
            "원본": lambda x: x,
            "대칭": flip_full,
            "시작점반전": flip_start,
            "홀짝반전": flip_odd_even
        }

        all_predictions = []
        per_mode = {}

        for name, fn in transform_modes.items():
            transformed = fn(base_block)
            top_matches, bottom_matches = find_all_matches(transformed, three_only_data)
            preds = [m['값'] for m in bottom_matches if m['값'] != '❌ 없음']
            per_mode[name] = preds
            all_predictions.extend(preds)

        balance = Counter(all_predictions)

        return jsonify({
            "예측회차": int(raw[0]["date_round"]) + 1 if "date_round" in raw[0] else 9999,
            "기준블럭": base_block,
            "방향별예측": per_mode,
            "예측발란스": dict(balance.most_common())
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
