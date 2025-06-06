# 🤖 train_model.py – 학습용 모델 생성 및 저장
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os

# ✅ 경로
DATA_PATH = "data/ladder_dataset.csv"
MODEL_PATH = "model/model.pkl"

# 🔧 인코딩 함수 (범주형 문자열 → 숫자)
def encode(df):
    for col in ["block1", "block2", "block3", "direction"]:
        df[col] = df[col].astype("category").cat.codes
    return df

# 📚 데이터 로딩 및 전처리
df = pd.read_csv(DATA_PATH)
df = encode(df)

X = df[["block1", "block2", "block3", "direction"]]
y = df["label"].astype("category").cat.codes
label_map = dict(enumerate(df["label"].astype("category").cat.categories))

# 📊 모델 학습
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# 🎯 정확도 평가
preds = clf.predict(X_test)
acc = accuracy_score(y_test, preds)
print(f"✅ 모델 학습 완료 - 정확도: {acc:.2%}")

# 💾 모델 저장
os.makedirs("model", exist_ok=True)  # ✅ 정답
joblib.dump({"model": clf, "label_map": label_map}, MODEL_PATH)
print(f"📦 모델 저장 완료: {MODEL_PATH}")
