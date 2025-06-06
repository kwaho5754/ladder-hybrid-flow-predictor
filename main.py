from flask import Flask, jsonify, send_from_directory
from dotenv import load_dotenv
from supabase import create_client, Client
from collections import defaultdict
import os

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "ladder")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 블럭 변형 함수
def transform_block(block, mode):
    if mode == '대칭':
        return block[::-1]
    elif mode == '시작점반전':
        return ''.join(['짝' if c == '홀' else '홀' for c in block])
    elif mode == '홀짝반전':
        return ''.join([block[0]] + ['짝' if c == '홀' else '홀' for c in block[1:]])
    return block

# 블럭 분석 함수
def analyze_blocks(raw_data):
    results = defaultdict(list)
    used_ranges = set()
    directions = ['원본', '대칭', '시작점반전', '홀짝반전']
    max_len = 6

    for block_len in range(max_len, 2, -1):
        for i in range(len(raw_data) - block_len):
            block_range = tuple(range(i, i + block_len))
            if any(r in used_ranges for r in block_range):
                continue
            block = ''.join([raw_data[j]['result'] for j in block_range])
            for direction in directions:
                t_block = transform_block(block, direction)
                for j in range(i - 1, -1, -1):
                    if j + block_len > len(raw_data):
                        continue
                    cmp = ''.join([raw_data[k]['result'] for k in range(j, j + block_len)])
                    if t_block == transform_block(cmp, direction):
                        used_ranges.update(block_range)
                        results[f"{block_len}줄_{direction}"].append({
                            "블럭": t_block,
                            "순번": i,
                            "상단값": raw_data[j - 1]['result'] if j - 1 >= 0 else '없음',
                            "하단값": raw_data[j + block_len]['result'] if j + block_len < len(raw_data) else '없음'
                        })
                        break
                else:
                    continue
                break
    return results

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/predict_top3_summary')
def predict_top3_summary():
    response = supabase.table(SUPABASE_TABLE).select('*').order("reg_date", desc=True).limit(3000).execute()
    raw_data = response.data[::-1]
    result = analyze_blocks(raw_data)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
