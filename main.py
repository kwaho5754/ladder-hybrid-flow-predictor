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

@app.route("/predict_split")
def predict_split():
    try:
        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(3000) \
            .execute()

        raw = response.data
        round_num = int(raw[0]["date_round"]) + 1

        all_data = [convert(d) for d in raw]
        recent = all_data[:5]  # 최근 5개 사용

        pred = Counter(recent).most_common(1)[0][0] if recent else "❌"

        if len(pred) == 3:
            요소별 = {
                "시작점": pred[0],
                "사다리": pred[1],
                "끝자리": pred[2]
            }
        else:
            요소별 = {
                "시작점": "❌",
                "사다리": "❌",
                "끝자리": "❌"
            }

        # 점수 계산 함수
        def get_score(seq, value):
            return round(Counter(seq)[value] / len(seq) * 100) if value in seq else 0

        # 요소별 시퀀스 생성
        start_seq = [x[0] for x in all_data if len(x) == 3][:20]
        shape_seq = [x[1] for x in all_data if len(x) == 3][:20]
        oe_seq = [x[2] for x in all_data if len(x) == 3][:20]

        요소점수 = {
            "시작점": get_score(start_seq, 요소별["시작점"]),
            "사다리": get_score(shape_seq, 요소별["사다리"]),
            "끝자리": get_score(oe_seq, 요소별["끝자리"])
        }

        return jsonify({
            "예측회차": round_num,
            "최근값들": recent,
            "가장많이나온값": pred,
            "요소별예측": 요소별,
            "요소별점수": 요소점수,
            "전체개수": len(all_data)
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)