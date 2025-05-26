from flask import Flask, jsonify, send_file
from flask_cors import CORS
import requests
import csv

app = Flask(__name__)
CORS(app)

# ✅ 시트 CSV 주소
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1j72Y36aXDYTxsJId92DCnQLouwRgHL2BBOqI9UUDQzE/export?format=csv&gid=0"

# ✅ 시트 한 줄을 분석용 문자열로 변환
def convert_row(row):
    side = '좌' if row[2].strip() == 'LEFT' else '우'
    line = row[3].strip()
    odd = '짝' if row[4].strip() == 'EVEN' else '홀'
    return f"{side}{line}{odd}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    return [('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀') for s, c, o in map(parse_block, block)]

def flip_start(block):
    return [s + ('4' if c == '3' else '3') + ('홀' if o == '짝' else '짝') for s, c, o in map(parse_block, block)]

def flip_odd_even(block):
    return [('우' if s == '좌' else '좌') + ('4' if c == '3' else '3') + o for s, c, o in map(parse_block, block)]

def find_prediction(block, all_blocks):
    for i in reversed(range(len(all_blocks) - len(block))):
        if all_blocks[i:i+len(block)] == block:
            pred_index = i - 1
            pred = all_blocks[pred_index] if pred_index >= 0 else "❌ 없음"
            return pred, ">".join(block), i + 1
    return "❌ 없음", ">".join(block), -1

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        # ✅ 시트에서 CSV 데이터 불러오기
        csv_text = requests.get(SHEET_CSV_URL).text
        reader = list(csv.reader(csv_text.splitlines()))
        data = reader[1:]  # 헤더 제외
        data = data[-5000:]  # ✅ 최근 5000줄만 분석
        data.reverse()  # ✅ 사람이 보는 흐름과 일치 (최신이 위)

        round_num = int(data[0][1]) + 1  # 최신 회차 + 1

        all_blocks = [convert_row(r) for r in data]

        results = {}
        transforms = {
            "orig": lambda x: x,
            "flip_start": flip_start,
            "flip_odd_even": flip_odd_even,
            "flip_full": flip_full
        }

        for size in range(3, 7):
            base_block = [convert_row(r) for r in data[:size]]
            for key, func in transforms.items():
                transformed = func(base_block)
                pred, blk, idx = find_prediction(transformed, all_blocks)
                results[f"{size}block_{key}"] = {
                    "예측값": pred,
                    "블럭": blk,
                    "매칭순번": idx
                }

        return jsonify({
            "예측회차": round_num,
            **results
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
