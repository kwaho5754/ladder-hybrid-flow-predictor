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
    return [reverse_name(b) if i == 0 else b for i, b in enumerate(block)]

def flip_odd_even(block):
    return [reverse_name(b) if b[-1] in ['홀', '짝'] else b for b in block]

def find_all_first_matches(data, block_sizes, transform=None):
    results = {}
    for size in sorted(block_sizes, reverse=True):
        recent_block = transform(data[0:size]) if transform else data[0:size]
        for i in range(1, len(data) - size):
            candidate = data[i:i+size]
            candidate_transformed = transform(candidate) if transform else candidate
            if candidate_transformed == recent_block:
                results[size] = {
                    "블럭": candidate_transformed,  # 💡 변형된 블럭을 출력에도 사용
                    "상단": data[i - 1] if i > 0 else None,
                    "하단": data[i + size] if i + size < len(data) else None,
                    "순번": i + 1
                }
                break
    return {
        "3줄": results.get(3),
        "4줄": results.get(4),
        "5줄": results.get(5)
    }

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

        match_original = find_all_first_matches(all_data, [5, 4, 3])
        match_symmetric = find_all_first_matches(all_data, [5, 4, 3], transform=lambda b: [reverse_name(x) for x in b])
        match_start = find_all_first_matches(all_data, [5, 4, 3], transform=flip_start)
        match_odd = find_all_first_matches(all_data, [5, 4, 3], transform=flip_odd_even)

        return jsonify({
            "예측회차": round_num,
            "처음매칭": match_original,
            "처음매칭_대칭": match_symmetric,
            "처음매칭_시작반전": match_start,
            "처음매칭_홀짝반전": match_odd
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
