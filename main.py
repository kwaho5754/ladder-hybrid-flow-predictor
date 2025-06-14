# ✅ main.py - 3가지 예측 방식 기반 API
from flask import Flask, jsonify
from collections import defaultdict, Counter
import random
import supabase
import os
import math

app = Flask(__name__)

# Supabase 클라이언트 초기화
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supa = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

BLOCK_SIZE = 3
LIMIT = 7000

@app.route("/predict_analysis")
def predict_analysis():
    # 1. 데이터 로딩
    result = supa.table("raw_ladder").select("value").order("id", desc=True).limit(LIMIT).execute()
    all_values = [item['value'] for item in reversed(result.data)]

    predictions = {
        "강화학습 기반": predict_reinforcement(all_values),
        "상대 비교 기반": predict_relative(all_values),
        "부트스트랩 기반": predict_bootstrap(all_values)
    }

    return jsonify(predictions)

# 1️⃣ 강화학습 기반
reward_table = defaultdict(lambda: defaultdict(int))
def predict_reinforcement(data):
    history = defaultdict(list)
    for i in range(1, len(data) - BLOCK_SIZE):
        block = tuple(data[i:i + BLOCK_SIZE])
        top = data[i - 1]
        reward_table[block][top] += 1
        history[block].append(top)

    recent = tuple(data[-BLOCK_SIZE:])
    scores = reward_table.get(recent, {})
    ranked = Counter(scores).most_common(3)
    return format_result(ranked)

# 2️⃣ 상대 비교 기반
def predict_relative(data):
    comparison_table = defaultdict(Counter)
    for i in range(1, len(data) - BLOCK_SIZE):
        block = tuple(data[i:i + BLOCK_SIZE])
        top = data[i - 1]
        comparison_table[block][top] += 1

    recent = tuple(data[-BLOCK_SIZE:])
    counter = comparison_table.get(recent, Counter())
    candidates = list(counter.items())
    ranked = sorted(candidates, key=lambda x: (-x[1], random.random()))[:3]
    return format_result(ranked)

# 3️⃣ 부트스트랩 기반
def predict_bootstrap(data, samples=100):
    result_counter = Counter()
    for _ in range(samples):
        offset = random.randint(1, len(data) - BLOCK_SIZE - 1)
        block = tuple(data[offset:offset + BLOCK_SIZE])
        top = data[offset - 1]
        if block == tuple(data[-BLOCK_SIZE:]):
            result_counter[top] += 1
    ranked = result_counter.most_common(3)
    return format_result(ranked)

# 출력 포맷 통일
def format_result(pairs):
    total = sum([v for _, v in pairs]) or 1
    return [
        {"예측값": key, "점수": round(value / total, 3)}
        for key, value in pairs
    ]

if __name__ == "__main__":
    app.run(debug=True, port=5000)