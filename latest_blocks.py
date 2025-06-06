# 📦 latest_blocks.py - 최근 3줄 블럭 자동 추출기 (CSV 기반)
import csv
from pathlib import Path

CSV_PATH = Path("data/ladder_dataset.csv")  # 또는 별도 원본 CSV 경로 사용 가능

# 원본 블럭 형식에서 완성형이 아닌 원래 블럭으로 되돌리는 방법이 필요하면 별도 변환 사용
def get_recent_blocks(n=3):
    if not CSV_PATH.exists():
        return []

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if len(rows) < n:
        return []

    # 최근 가장 마지막 label이 나온 블럭 3줄 추출
    last_rows = rows[-n:]
    return [r["block1"] for r in last_rows]  # 또는 block2, block3 포함 가능

# 테스트 실행
if __name__ == "__main__":
    print("최근 3줄 블럭:", get_recent_blocks())
