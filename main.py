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

def rotate_block(block):
    return list(reversed([reverse_name(b) for b in block]))

def find_all_first_matches(data, block_sizes, rotate=False, transform=None):
    if transform:
        recent_blocks = {n: transform(data[0:n]) for n in block_sizes}
    elif rotate:
        recent_blocks = {n: rotate_block(data[0:n]) for n in block_sizes}
    else:
        recent_blocks = {n: data[0:n] for n in block_sizes}

    results = {}
    for size in sorted(block_sizes, reverse=True):
        recent = recent_blocks[size]
        for i in range(1, len(data) - size):
            candidate = data[i:i+size]
            # 🔍 매칭 기준에 맞게 변환 적용
            if rotate:
                candidate_transformed = rotate_block(candidate)
            elif transform:
                candidate_transformed = transform(candidate)
            else:
                candidate_transformed = candidate
            if candidate_transformed == recent:
                top = data[i - 1] if i > 0 else None
                bottom = data[i + size] if i + size < len(data) else None
                # 🔄 출력용 블럭은 다시 원래 방향으로 되돌림
                if rotate:
                    display_block = rotate_block(candidate)
                elif transform:
                    display_block = transform(candidate)
                else:
                    display_block = candidate
                results[size] = {
                    "블럭": display_block,
                    "상단": top,
                    "하단": bottom,
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
        first_matches = find_all_first_matches(all_data, [5, 4, 3])
        first_matches_r = find_all_first_matches(all_data, [5, 4, 3], rotate=True)
        first_matches_sym = find_all_first_matches(
            all_data, [5, 4, 3],
            transform=lambda b: [reverse_name(x) for x in b]
        )
        return jsonify({
            "예측회차": round_num,
            "처음매칭": first_matches,
            "처음매칭_180도": first_matches_r,
            "처음매칭_대칭": first_matches_sym
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
