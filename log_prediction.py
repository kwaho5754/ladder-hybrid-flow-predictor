# 🗂️ log_prediction.py – 예측 결과 로그 저장 모듈
import csv
import os
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("logs/predict_log.csv")
os.makedirs(LOG_PATH.parent, exist_ok=True)

HEADER = ["timestamp", "회차", "recent_block", "Top3_ML", "예측값들"]

def log_prediction(round_num: int, recent: list, top3: list, all_preds: list):
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "회차": round_num,
        "recent_block": ",".join(recent),
        "Top3_ML": ",".join(top3),
        "예측값들": ",".join(all_preds)
    }

    write_header = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    print(f"✅ 예측 결과 로그 저장 완료 (회차 {round_num})")

# 예시
if __name__ == "__main__":
    log_prediction(215, ["좌3홀", "우4짝", "좌4홀"], ["좌삼짝", "우사짝", "좌사홀"], ["좌삼짝", "좌삼짝", "우사짝", "좌사홀", "우사짝"])
