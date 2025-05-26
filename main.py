# ✅ main.py 전체
from flask import Flask, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

CSV_PATH = "ladder_results.csv"

def load_csv():
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        if len(df) >= 100:  # 최소 100줄 이상일 때만 분석
            return df
    return None

def predict_from_csv(df):
    # 예시 예측 로직 (가장 많이 나온 값 기준)
    last_500 = df.tail(500)
    predictions = last_500['결과'].value_counts().head(3).to_dict()
    return predictions

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/predict")
def predict():
    df = load_csv()
    if df is None:
        return jsonify({
            "회차": "CSV 없음",
            "예측": ["❌ 데이터 부족", "❌ 데이터 부족", "❌ 데이터 부족"]
        })
    predictions = predict_from_csv(df)
    predict_round = df.iloc[-1]["회차"] + 1
    top3 = list(predictions.keys()) + ["❌ 없음"] * (3 - len(predictions))
    return jsonify({
        "회차": int(predict_round),
        "예측": top3[:3]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
