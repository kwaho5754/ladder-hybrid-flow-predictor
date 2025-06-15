### main.py 전체 수정 버전 (reverse_block 추가)

import os
import json
from flask import Flask, jsonify
from collections import defaultdict
from supabase import create_client, Client

app = Flask(__name__)

# Supabase 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 블럭 변형 함수들
def flip_full(block):
    return [flip(b) for b in block[::-1]]

def flip_start(block):
    return [flip_side(b) if i == 0 else b for i, b in enumerate(block)]

def flip_odd_even(block):
    return [flip_odd_even_single(b) for b in block]

def reverse_block(block):
    return block[::-1]

def flip(b):
    return b.replace("좌", "tmp").replace("우", "좌").replace("tmp", "우")\
            .replace("홀", "tmp").replace("짝", "홀").replace("tmp", "짝")

def flip_side(b):
    return b.replace("좌", "tmp").replace("우", "좌").replace("tmp", "우")

def flip_odd_even_single(b):
    return b.replace("홀", "tmp").replace("짝", "홀").replace("tmp", "짝")

# 블럭 생성 함수
def make_blocks(data, size):
    return [data[i:i+size] for i in range(len(data)-size)]

# 예측 데이터 생성
def predict_from_blocks(blocks):
    result = defaultdict(list)
    for i in range(len(blocks)-1):
        key = tuple(blocks[i])
        result[key].append(blocks[i+1])
    return result

@app.route("/predict")
def predict():
    response = supabase.table("raw_result").select("*").order("date_round", desc=True).limit(7000).execute()
    data = [item['result'] for item in response.data if 'result' in item]

    results = {}
    directions = {
        "orig": lambda x: x,
        "flip_full": flip_full,
        "flip_start": flip_start,
        "flip_odd_even": flip_odd_even,
        "reverse_block": reverse_block
    }

    for dir_key, transform in directions.items():
        results[dir_key] = {}
        for block_size in range(3, 7):
            blocks = make_blocks(data, block_size)
            transformed = [transform(b) for b in blocks]
            predictions = predict_from_blocks(transformed)
            results[dir_key][f"{block_size}block"] = predictions

    return jsonify(results)

@app.route("/predict_top3_summary")
def predict_top3_summary():
    response = supabase.table("raw_result").select("*").order("date_round", desc=True).limit(7000).execute()
    data = [item['result'] for item in response.data if 'result' in item]
    latest_round = response.data[0]["date_round"] + 1 if response.data else 0

    summary = {}
    directions = {
        "orig": lambda x: x,
        "flip_full": flip_full,
        "flip_start": flip_start,
        "flip_odd_even": flip_odd_even,
        "reverse_block": reverse_block
    }

    for dir_key, transform in directions.items():
        summary[dir_key] = {}
        for block_size in [3, 4]:
            blocks = make_blocks(data, block_size)
            transformed = [transform(b) for b in blocks]
            predictions = predict_from_blocks(transformed)
            freq = defaultdict(int)
            for pred_list in predictions.values():
                for p in pred_list:
                    freq[tuple(p)] += 1
            top3 = sorted(freq.items(), key=lambda x: -x[1])[:3]
            summary[dir_key][f"{block_size}block"] = [{"value": list(k), "count": v} for k, v in top3]

    return jsonify({"summary": summary, "round": latest_round})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
