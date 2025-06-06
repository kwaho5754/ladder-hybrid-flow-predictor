from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import requests
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BLOCK_SIZES = [6, 5, 4, 3]
DIRECTIONS = ["original", "symmetric", "start_flip", "parity_flip"]
MAX_MATCHES = 12

# 블럭 변형 함수들
def get_symmetric(block):
    return [line[::-1] for line in block]

def get_start_flip(block):
    return [
        ('짝' if line[0] == '홀' else '홀') + line[1:] for line in block
    ]

def get_parity_flip(block):
    return [
        line[0] + ('짝' if line[1] == '홀' else '홀') for line in block
    ]

def transform_block(block, mode):
    if mode == "original":
        return block
    elif mode == "symmetric":
        return get_symmetric(block)
    elif mode == "start_flip":
        return get_start_flip(block)
    elif mode == "parity_flip":
        return get_parity_flip(block)
    return block

def block_name(block):
    return ">".join(block)

def check_overlap(used, start, end):
    return any(i in used for i in range(start, end))

@app.get("/predict")
def predict():
    url = os.getenv("SUPABASE_URL") + "/rest/v1/ladder?select=odd_even&order=id.desc&limit=3000"
    headers = {"apikey": os.getenv("SUPABASE_KEY")}
    response = requests.get(url, headers=headers)
    data = response.json()
    lines = [d['odd_even'] for d in data if 'odd_even' in d and len(d['odd_even']) == 2]

    results = defaultdict(lambda: defaultdict(list))
    used_indexes = set()

    for size in BLOCK_SIZES:
        for mode in DIRECTIONS:
            transformed_blocks = {}

            for i in range(len(lines) - size):
                if i in used_indexes:
                    continue
                block = lines[i:i+size]
                transformed = transform_block(block, mode)
                key = block_name(transformed)

                if key not in transformed_blocks:
                    transformed_blocks[key] = []
                transformed_blocks[key].append(i)

            latest_block_raw = lines[0:size]
            latest_block = transform_block(latest_block_raw, mode)
            latest_key = block_name(latest_block)

            matches = []
            for idx in transformed_blocks.get(latest_key, []):
                if idx == 0 or check_overlap(used_indexes, idx, idx+size):
                    continue

                upper = lines[idx - 1] if idx - 1 >= 0 else "❌ 없음"
                lower = lines[idx + size] if idx + size < len(lines) else "❌ 없음"

                results[size][mode].append({
                    "index": idx,
                    "block": latest_block,
                    "name": latest_key,
                    "upper": upper,
                    "lower": lower
                })

                for j in range(idx, idx + size):
                    used_indexes.add(j)

                if len(results[size][mode]) >= MAX_MATCHES:
                    break

    output = {"상단값들": [], "하단값들": []}
    for size in BLOCK_SIZES:
        for mode in DIRECTIONS:
            for match in results[size][mode]:
                output["상단값들"].append({
                    "값": match['upper'],
                    "블럭": match['name'],
                    "순번": match['index']
                })
                output["하단값들"].append({
                    "값": match['lower'],
                    "블럭": match['name'],
                    "순번": match['index']
                })

    while len(output["상단값들"]) < MAX_MATCHES:
        output["상단값들"].append({"값": "❌ 없음", "블럭": "❌ 없음", "순번": "❌"})
    while len(output["하단값들"]) < MAX_MATCHES:
        output["하단값들"].append({"값": "❌ 없음", "블럭": "❌ 없음", "순번": "❌"})

    return JSONResponse(content=output)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
