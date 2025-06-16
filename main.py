from flask import Flask, jsonify
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

def parse_block(s):
    return s[0], s[1:-1], s[-1]  # 좌/우, 줄수, 홀/짝

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def extract_direction(blocks):
    return [parse_block(b)[0] for b in blocks]

def extract_parity(blocks):
    return [parse_block(b)[2] for b in blocks]

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
                direction_matches.append(all_data[next_index])
            if extract_parity(block) == recent_parity:
                parity_matches.append(all_data[next_index])

        dir_top3 = [v[0] for v in Counter(direction_matches).most_common(3)]
        parity_top3 = [v[0] for v in Counter(parity_matches).most_common(3)]

        return jsonify({
            "예측회차": round_num,
            "최근방향흐름": recent_direction,
            "최근홀짝흐름": recent_parity,
            "방향예측값": dir_top3,
            "홀짝예측값": parity_top3
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)