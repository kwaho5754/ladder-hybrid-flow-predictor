from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os

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

def reverse_name(name):
    name = name.replace('좌', '@').replace('우', '좌').replace('@', '우')
    name = name.replace('홀', '@').replace('짝', '홀').replace('@', '짝')
    return name

def flip_start(block):
    return [reverse_name(block[0])] + block[1:] if block else []

def flip_odd_even(block):
    return [reverse_name(b) if b[-1] in ['홀', '짝'] else b for b in block]

def find_matches_by_size(data, size, transform, used_indices):
    recent_block = data[0:size]
    if transform:
        recent_block = transform(recent_block)

    for i in range(1, len(data) - size):
        if any(j in used_indices for j in range(i, i + size)):
            continue
        candidate = data[i:i+size]
        candidate_transformed = transform(candidate) if transform else candidate
        if candidate_transformed == recent_block:
            used_indices.update(range(i, i + size))
            return {
                "블럭": candidate_transformed,
                "상단": data[i - 1] if i > 0 else None,
                "하단": data[i + size] if i + size < len(data) else None,
                "순번": i + 1
            }
    return None

def find_all_directions(data):
    directions = {
        "원본": None,
        "대칭": lambda b: [reverse_name(x) for x in b],
        "시작반전": flip_start,
        "홀짝반전": flip_odd_even
    }
    results = {}
    for label, transform in directions.items():
        used_indices = set()
        results[label] = {}
        for size in [5, 4, 3]:
            match = find_matches_by_size(data, size, transform, used_indices)
            if match:
                results[label][f"{size}줄"] = match
    return results

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        raw = supabase.table(SUPABASE_TABLE).select("*") \
            .order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute().data

        if not raw:
            return jsonify({"error": "데이터 없음"}), 500

        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]
        results = find_all_directions(all_data)
        results["예측회차"] = round_num

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
