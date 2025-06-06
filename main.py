from flask import Flask, jsonify
from flask_cors import CORS
from supabase import create_client, Client
import os

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

def reverse_name(name):
    name = name.replace('좌', '@').replace('우', '좌').replace('@', '우')
    name = name.replace('홀', '@').replace('짝', '홀').replace('@', '짝')
    return name

def flip_start(block):  # 시작점 반전
    return [reverse_name(b[:1]) + b[1:] for b in block]

def flip_odd_even(block):  # 홀짝 반전
    return [b[:-1] + ('짝' if '홀' in b else '홀') if b[-1] in ['홀', '짝'] else b for b in block]

def analyze_blocks(data, length):
    used = set()
    result = {'원본': [], '대칭': [], '시작반전': [], '홀짝반전': []}
    name_set = {"좌삼짝", "우삼홀", "좌사홀", "우사짝"}

    for i in range(len(data) - length):
        block = [convert(data[j]) for j in range(i, i+length)]
        top = convert(data[i-1]) if i > 0 else None
        if not top or any((i+j) in used for j in range(length)):
            continue

        key = tuple(block)
        if key not in used:
            used.update({i+j for j in range(length)})
            name = top if top in name_set else None
            if name: result['원본'].append((block, name))

        block_r = block[::-1]
        key = tuple(block_r)
        if key not in used:
            name = top if top in name_set else None
            if name: result['대칭'].append((block_r, name))

        flipped = flip_start(block)
        key = tuple(flipped)
        if key not in used:
            name = top if top in name_set else None
            if name: result['시작반전'].append((flipped, name))

        oddflip = flip_odd_even(block)
        key = tuple(oddflip)
        if key not in used:
            name = top if top in name_set else None
            if name: result['홀짝반전'].append((oddflip, name))

    return result

@app.route("/predict")
def predict():
    res = supabase.table(SUPABASE_TABLE).select("*").order("id", desc=True).limit(3000).execute()
    data = res.data[::-1]  # 최신순 정렬
    lengths = [5, 4, 3]
    results = {}

    for l in lengths:
        results[f"{l}줄"] = analyze_blocks(data, l)

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
