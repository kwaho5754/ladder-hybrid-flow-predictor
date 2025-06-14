from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter, defaultdict

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

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict_top_by_blocksize")
def predict_top_by_blocksize():
    try:
        response = supabase.table(SUPABASE_TABLE).select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(7000) \
            .execute()

        raw = response.data
        all_data = [convert(d) for d in raw]  # 최신 → 과거 방향 유지
        round_num = int(raw[0]["date_round"]) + 1 if raw else "❓"

        result = {"예측회차": round_num}

        for size in [3, 4, 5]:
            if len(all_data) <= size:
                result[f"{size}줄 블럭"] = {"예측값": "❌ 데이터 부족", "출현": 0}
                continue

            block_to_top = defaultdict(Counter)

            # 슬라이딩 블럭: block → 상단값 매핑 저장
            for i in range(1, len(all_data) - size + 1):
                block = tuple(all_data[i : i + size])
                top_value = all_data[i - 1]  # 블럭보다 앞에 있었던 상단값
                block_to_top[block][top_value] += 1

            # 블럭별 예측값: 각 블럭이 가장 자주 예측한 상단값을 모아 통계 집계
            prediction_counter = Counter()
            for block, tops in block_to_top.items():
                most_common_top = tops.most_common(1)[0]  # top1
                prediction_counter[most_common_top[0]] += 1

            top = prediction_counter.most_common(1)
            if top:
                result[f"{size}줄 블럭"] = {"예측값": top[0][0], "출현": top[0][1]}
            else:
                result[f"{size}줄 블럭"] = {"예측값": "❌ 없음", "출현": 0}

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)