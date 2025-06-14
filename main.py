from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter, defaultdict
import math

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

@app.route("/predict_analysis")
def predict_analysis():
    try:
        response = supabase.table(SUPABASE_TABLE).select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(7000) \
            .execute()

        raw = response.data
        all_data = [convert(d) for d in raw]
        round_num = int(raw[0]["date_round"]) + 1 if raw else "❓"

        results = {"예측회차": round_num}
        size = 3  # 3줄 블럭으로 고정

        block_to_tops = defaultdict(list)
        for i in range(1, len(all_data) - size + 1):
            block = tuple(all_data[i:i + size])
            top = all_data[i - 1]
            block_to_tops[block].append((i, top))  # (등장위치, 상단값)

        freshness_score = Counter()
        diversity_score = Counter()

        for block, matches in block_to_tops.items():
            total = len(matches)
            tops = [t for _, t in matches]
            dist = Counter(tops)
            most_common = dist.most_common(1)[0][0]

            # 신선도 점수 = 최신 등장 위치가 높을수록 점수 높음 (위치 역순 → 0이 최신)
            last_index = matches[-1][0]  # 가장 마지막 등장 위치
            freshness = 1 - (last_index / len(all_data))  # 0~1 사이 값
            freshness_score[most_common] += freshness

            # 다양도 점수 = 엔트로피 기반 (1 - normalized entropy)
            probs = [c / total for c in dist.values()]
            entropy = -sum(p * math.log2(p) for p in probs if p > 0)
            max_entropy = math.log2(len(dist)) if len(dist) > 1 else 1
            diversity = 1 - (entropy / max_entropy if max_entropy > 0 else 0)
            diversity_score[most_common] += diversity

        results["신선도 기반 예측"] = [
            {"예측값": v, "점수": round(s, 4)}
            for v, s in freshness_score.most_common(3)
        ]
        results["다양도 기반 예측"] = [
            {"예측값": v, "점수": round(s, 4)}
            for v, s in diversity_score.most_common(3)
        ]

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)