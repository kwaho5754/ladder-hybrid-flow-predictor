from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()  # ✅ .env 환경변수 로드

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
    valid = {"좌삼짝", "우삼홀", "좌사홀", "우사짝"}

    for i in range(len(data) - length):
        block = [convert(data[j]) for j in range(i, i+length)]
        top = convert(data[i-1]) if i > 0 else None
        if not top or any((i+j) in used for j in range(length)):
            continue

        def store(name, transformed, key):
            if key not in used and name in valid:
                used.update({i+j for j in range(length)})
                result[key].append((transformed, name))

        store(top, block, '원본')
        store(top, block[::-1], '대칭')
        store(top, flip_start(block), '시작반전')
        store(top, flip_odd_even(block), '홀짝반전')

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

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
