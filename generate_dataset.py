# 🔧 generate_dataset.py - 머신러닝 학습용 CSV 자동 생성기
import csv
import os
from pathlib import Path

# 예시용 변환 함수 (블럭 단어를 완성형으로 변환)
def normalize(value):
    if '좌3짝' in value: return '좌삼짝'
    if '우3홀' in value: return '우삼홀'
    if '좌4홀' in value: return '좌사홀'
    if '우4짝' in value: return '우사짝'
    return None  # 예외값 제외 처리

# 방향별 변환 함수들 (main.py와 동일하게 유지)
def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    return [('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀') for s, c, o in map(parse_block, block)]

def flip_start(block):
    return [s + ('4' if c == '3' else '3') + ('홀' if o == '짝' else '짝') for s, c, o in map(parse_block, block)]

def flip_odd_even(block):
    return [('우' if s == '좌' else '좌') + ('4' if c == '3' else '3') + o for s, c, o in map(parse_block, block)]

def rotate(block):
    return list(reversed(block))

DIRECTIONS = {
    "orig": lambda x: x,
    "flip_full": flip_full,
    "flip_start": flip_start,
    "flip_odd_even": flip_odd_even,
    "rotate": rotate
}

# 🔧 실제 생성 로직

def generate_dataset(input_sequence, save_path):
    rows = []
    for i in range(len(input_sequence) - 3):
        block = input_sequence[i:i+3]
        label_raw = input_sequence[i+3]
        label = normalize(label_raw)
        if not label:
            continue  # 예외값 제외

        for direction, func in DIRECTIONS.items():
            transformed = func(block)
            norm_block = [normalize(b) for b in transformed]
            if None in norm_block:
                continue  # 예외값 건너뜀

            rows.append({
                "block1": norm_block[0],
                "block2": norm_block[1],
                "block3": norm_block[2],
                "direction": direction,
                "label": label
            })

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["block1", "block2", "block3", "direction", "label"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ CSV 저장 완료: {save_path} ({len(rows)} rows)")

# 예시: 사용자가 보유한 전체 블럭 리스트 (최근순)
if __name__ == "__main__":
    # 예시 더미 데이터 - 실제로는 최신값부터 과거값 순서로 넣으세요
    dummy_data = [
        "좌3짝", "우3홀", "좌4홀", "우4짝", "좌3짝", "우3홀", "우4짝",
        "좌3짝", "우3홀", "좌4홀", "우4짝", "좌3짝"
    ]
    output_path = Path("data/ladder_dataset.csv")
    generate_dataset(dummy_data, output_path)
