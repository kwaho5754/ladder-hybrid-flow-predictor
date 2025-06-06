# 📈 evaluate_accuracy.py – 예측 로그 기반 정확도 계산 (회차 유효성 검사 추가)
import pandas as pd
from pathlib import Path

LOG_PATH = Path("logs/predict_log.csv")
TRUE_LABEL_PATH = Path("data/ladder_dataset.csv")

def evaluate_accuracy():
    if not LOG_PATH.exists() or not TRUE_LABEL_PATH.exists():
        print("❌ 로그 파일 또는 실제값 CSV가 없습니다.")
        return

    log_df = pd.read_csv(LOG_PATH)
    true_df = pd.read_csv(TRUE_LABEL_PATH)

    if "회차" not in log_df.columns:
        print("❌ 로그에 회차 정보가 없습니다.")
        return

    matches = 0
    total = 0
    max_index = len(true_df)

    for _, row in log_df.iterrows():
        try:
            round_num = int(row["회차"])
            if round_num - 1 >= max_index:
                continue  # 회차가 실제 라벨 범위를 초과하면 skip

            top1 = row["Top3_ML"].split(",")[0]
            actual = true_df.iloc[round_num - 1]["label"]

            if actual == top1:
                matches += 1
            total += 1
        except:
            continue

    if total == 0:
        print("❌ 비교 가능한 데이터가 없습니다.")
        return

    accuracy = matches / total
    print(f"🎯 Top1 정확도: {accuracy:.2%} ({matches}/{total})")

if __name__ == "__main__":
    evaluate_accuracy()
