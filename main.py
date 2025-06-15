# ✅ main.py - Supabase 연동 + 3가지 분석기 기반 예측 시스템
from flask import Flask, jsonify, send_from_directory
from collections import defaultdict, Counter
import random
import supabase
import os

app = Flask(__name__)

# Supabase 클라이언트 초기화
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "ladder")
supa = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

BLOCK_SIZE = 3
LIMIT = 7000

# 🔁 좌우/홀짝 블럭 문자열 변환
def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict_analysis")
def predict_analysis():
    # 1. Supabase에서 데이터 로딩
    result = supa.table(SUPABASE_TABLE).select("*").order("reg_date", desc=True).order("date_round", desc=True).limit(LIMIT).execute()
    all_data = [convert(row) for row in reversed(result.data)]

    predictions = {
        "강화학습 기반": predict_reinforcement(all_data),
        "상대 비교 기반": predict_relative(all_data),
        "부트스트랩 기반": predict_bootstrap(all_data)
    }
    return jsonify(predictions)

# 1️⃣ 강화학습 기반 분석기
reward_table = defaultdict(lambda: defaultdict(int))
def predict_reinforcement(data):
    for i in range(1, len(data) - BLOCK_SIZE):
        block = tuple(data[i:i + BLOCK_SIZE])
        top = data[i - 1]
        reward_table[block][top] += 1

    recent = tuple(data[-BLOCK_SIZE:])
    scores = reward_table.get(recent, {})
    ranked = Counter(scores).most_common(3)
    return format_result(ranked)

# 2️⃣ 상대 비교 기반 분석기
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

# 3️⃣ 부트스트랩 기반 분석기
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

# 출력 포맷 통일 함수
def format_result(pairs):
    total = sum([v for _, v in pairs]) or 1
    return [
        {"예측값": key, "점수": round(value / total, 3)}
        for key, value in pairs
    ]

if __name__ == "__main__":
    app.run(debug=True, port=5000)
