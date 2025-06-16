from flask import Flask, jsonify
from supabase import create_client
from collections import Counter
import os

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "ladders")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def convert(d):
    return d["result"]

def extract_direction(block):
    result = []
    for i in range(len(block)-1):
        result.append("좌" if block[i] == block[i+1] else "우")
    return result

def extract_parity(block):
    return ["짝" if b in ["짝", "우삼짝", "좌사짝"] else "홀" for b in block]

@app.route("/predict_flow")
def predict_flow():
    try:
        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(5000) \
            .execute()

        raw = response.data
        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]

        recent_block = all_data[:4]
        recent_direction = extract_direction(recent_block)
        recent_parity = extract_parity(recent_block)

        direction_matches = []
        parity_matches = []

        for i in range(len(all_data) - 4):
            block = all_data[i:i+4]
            next_index = i + 4
            if next_index >= len(all_data):
                continue

            if extract_direction(block) == recent_direction:
                direction_matches.append({"예측값": all_data[next_index], "순번": i + 1})
            if extract_parity(block) == recent_parity:
                parity_matches.append({"예측값": all_data[next_index], "순번": i + 1})

        dir_counter = Counter([m["예측값"] for m in direction_matches])
        parity_counter = Counter([m["예측값"] for m in parity_matches])

        dir_top3 = [{"값": val, "빈도": count} for val, count in dir_counter.most_common(3)]
        parity_top3 = [{"값": val, "빈도": count} for val, count in parity_counter.most_common(3)]

        return jsonify({
            "예측회차": round_num,
            "최근방향흐름": recent_direction,
            "최근홀짝흐름": recent_parity,
            "방향예측값": dir_top3,
            "홀짝예측값": parity_top3,
            "방향매칭": direction_matches[:20],
            "홀짝매칭": parity_matches[:20]
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
