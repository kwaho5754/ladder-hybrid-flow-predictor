from flask import Flask, jsonify, send_from_directory
import csv

app = Flask(__name__)

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
        # ✅ CSV 파일에서 직접 데이터 불러오기
        with open("ladder_results.csv", "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        data = reader[1:]  # 헤더 제외
        data = data[-5000:]  # 최근 5000줄
        data.reverse()  # 최신이 위로 오도록

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
