from flask import Flask, request, send_file, Response
from flask_cors import CORS
import pandas as pd
import os
import json

app = Flask(__name__)
CORS(app)

CSV_PATH = "ladder_results.csv"

def convert(row):
    # 좌우, 줄수, 홀짝 정보를 한 문자열로 결합
    side = '좌' if row['start_point'] == 'LEFT' else '우'
    count = str(row['line_count'])
    oe = '짝' if row['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    # 블럭 문자열을 (좌우, 줄수, 홀짝) 세 부분으로 분리
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    # 블럭 완전 대칭 변환 (좌우 반전 + 홀짝 반전)
    return [
        ('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀')
        for s, c, o in map(parse_block, block)
    ]

def flip_start(block):
    # 줄수와 홀짝을 반전시키는 변환 (시작점 고정)
    flipped = []
    for s, c, o in map(parse_block, block):
        c_flip = '4' if c == '3' else '3'
        o_flip = '홀' if o == '짝' else '짝'
        flipped.append(s + c_flip + o_flip)
    return flipped

def flip_odd_even(block):
    # 좌우 반전 + 줄수 변환 (홀짝 고정)
    flipped = []
    for s, c, o in map(parse_block, block):
        s_flip = '우' if s == '좌' else '좌'
        c_flip = '4' if c == '3' else '3'
        flipped.append(s_flip + c_flip + o)
    return flipped

def find_flow_match(block, full_data):
    # 최근 블럭과 과거 전체 데이터를 비교하여 가장 최근 일치하는 구간 찾기
    block_len = len(block)
    for i in reversed(range(len(full_data) - block_len)):
        candidate = full_data[i:i+block_len]
        if candidate == block:
            pred_index = i - 1
            # 일치 구간 바로 위줄을 예측값으로 사용
            pred = full_data[pred_index] if pred_index >= 0 else "❌ 없음"
            return pred, ">".join(block), i + 1
    return "❌ 없음", ">".join(block), -1

@app.route("/")
def home():
    # 메인 페이지 제공 (index.html)
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        if not os.path.exists(CSV_PATH):
            error_data = {"error": "CSV 파일 없음"}
            return Response(json.dumps(error_data, ensure_ascii=False), mimetype='application/json')

        df = pd.read_csv(CSV_PATH)
        if len(df) < 10:
            error_data = {"error": "CSV 데이터 부족"}
            return Response(json.dumps(error_data, ensure_ascii=False), mimetype='application/json')

        mode = request.args.get("mode", "3block_orig")
        size = int(mode[0])
        round_num = int(df.iloc[-1]["회차"]) + 1

        # 최근 288줄 데이터 역순으로 불러오기
        data = df.tail(288).iloc[::-1]
        flow_list = [convert(row) for _, row in data.iterrows()]
        recent_flow = flow_list[:size]

        # 모드에 따른 블럭 변형 적용
        if "flip_full" in mode:
            flow = flip_full(recent_flow)
        elif "flip_start" in mode:
            flow = flip_start(recent_flow)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_flow)
        else:
            flow = recent_flow

        # 매칭된 예측값, 블럭, 매칭 위치 반환
        result, blk, match_index = find_flow_match(flow, flow_list)

        response_data = {
            "예측회차": round_num,
            "예측값": result,
            "블럭": blk,
            "매칭순번": match_index if match_index > 0 else "❌ 없음"
        }

        # 한글 깨짐 방지 json 응답
        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')

    except Exception as e:
        error_data = {"error": str(e)}
        return Response(json.dumps(error_data, ensure_ascii=False), mimetype='application/json')

if __name__ == '__main__':
    # 기본 5000번 포트 사용
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
