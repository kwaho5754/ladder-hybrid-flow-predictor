from flask import Flask, jsonify, send_from_directory
import csv
import requests
import os
import threading
import time
from waitress import serve

app = Flask(__name__)
CSV_FILE = "ladder_results.csv"
FETCH_URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"
CHECK_INTERVAL = 60  # 60초 간격으로 새 회차 확인

# ✅ 자동 저장 루프
def auto_fetch_loop():
    while True:
        try:
            res = requests.get(FETCH_URL, timeout=5)
            data = res.json()[0]
            new_row = [
                data["reg_date"],
                str(data["date_round"]),
                data["start_point"],
                data["line_count"],
                data["odd_even"]
            ]

            file_exists = os.path.exists(CSV_FILE)
            existing = set()
            if file_exists:
                with open(CSV_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    existing = set(row[1] for row in reader if len(row) > 1)

            if new_row[1] not in existing:
                with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["날짜", "회차", "좌우", "줄수", "홀짝"])
                    writer.writerow(new_row)
                print(f"✅ 새 회차 저장됨: {new_row[1]}")
            else:
                print(f"⏳ 이미 저장된 회차: {new_row[1]}")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")

        time.sleep(CHECK_INTERVAL)

# ✅ 예측 블럭 변환 및 비교 함수들
def convert_row(row):
    return {
        "start": row[2],
        "line": row[3],
        "odd_even": row[4]
    }

def flip_start(block):
    return [{"start": "RIGHT" if x["start"] == "LEFT" else "LEFT", "line": x["line"], "odd_even": x["odd_even"]} for x in block]

def flip_odd_even(block):
    return [{"start": x["start"], "line": x["line"], "odd_even": "EVEN" if x["odd_even"] == "ODD" else "ODD"} for x in block]

def flip_full(block):
    return [{"start": "RIGHT" if x["start"] == "LEFT" else "LEFT", "line": x["line"], "odd_even": "EVEN" if x["odd_even"] == "ODD" else "ODD"} for x in block]

def find_prediction(base_block, all_blocks):
    for k in range(len(all_blocks) - len(base_block)):
        if all_blocks[k:k+len(base_block)] == base_block:
            return all_blocks[k + len(base_block)]["odd_even"], all_blocks[k:k+len(base_block)], k
    return "❌ 없음", [], -1

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/predict")
def predict():
    try:
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        data = reader[1:]  # 헤더 제외
        data = data[-5000:]
        data.reverse()

        round_num = int(data[0][1]) + 1
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

if __name__ == "__main__":
    threading.Thread(target=auto_fetch_loop, daemon=True).start()
    serve(app, host="0.0.0.0", port=5000)
