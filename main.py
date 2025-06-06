# ✅ 사다리 예측 시스템 - 최종 구조 반영 main.py

from flask import Flask, jsonify, send_from_directory
from supabase import create_client
from collections import defaultdict
import os
from dotenv import load_dotenv

# ✅ 환경변수 로드
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# ✅ 블럭 이름 지정 함수
def get_block_name(block):
    return ''.join(block)

# ✅ 대칭, 시작점반전, 홀짝반전
def transform_block(block, mode):
    if mode == "original":
        return block
    elif mode == "mirror":
        return [b.replace("좌", "우") if "좌" in b else b.replace("우", "좌") for b in block]
    elif mode == "start_flip":
        return [block[0].replace("홀", "짝") if "홀" in block[0] else block[0].replace("짝", "홀")] + block[1:]
    elif mode == "even_odd_flip":
        return [b.replace("홀", "짝") if "홀" in b else b.replace("짝", "홀") for b in block]

# ✅ 블럭 분석 함수
def analyze_blocks(data):
    directions = ["original", "mirror", "start_flip", "even_odd_flip"]
    results = {size: {d: [] for d in directions} for size in [5, 4, 3]}
    used_ranges = set()
    recent_blocks = {}

    for size in [5, 4, 3]:
        for direction in directions:
            for i in range(len(data) - size):
                if any((i + k) in used_ranges for k in range(size)):
                    continue
                block = [data[i + k]["result"] for k in range(size)]
                transformed = transform_block(block, direction)
                name = get_block_name(transformed)
                prev_result = data[i - 1]["result"] if i > 0 else "없음"
                results[size][direction].append({
                    "index": i,
                    "block": transformed,
                    "name": name,
                    "predict": prev_result
                })
                for k in range(size):
                    used_ranges.add(i + k)
                break

    for size in [5, 4, 3]:
        recent_blocks[size] = [entry["result"] for entry in data[-size:]]

    return results, recent_blocks

@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    raw_data = supabase.table(SUPABASE_TABLE).select("*") \
        .order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute().data
    raw_data.reverse()

    result, recent = analyze_blocks(raw_data)
    return jsonify({"results": result, "recent_blocks": recent})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
