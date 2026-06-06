import os, csv, joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from essays.ai import _extract_features, _features_to_vector, ML_MODEL_PATH
DATA_CSV = os.path.join(os.path.dirname(__file__), "ml", "train_data.csv")
os.makedirs(os.path.dirname(ML_MODEL_PATH), exist_ok=True)

X, y = [], []
with open(DATA_CSV, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        text, score = row["essay"], float(row["score"])
        feat = _extract_features(text)
        X.append(_features_to_vector(feat))
        y.append(score)

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestRegressor(n_estimators=300, random_state=42)
model.fit(Xtr, ytr)
pred = model.predict(Xte)
mae = mean_absolute_error(yte, pred)
print(f"Validation MAE: {mae:.2f}")

joblib.dump(model, ML_MODEL_PATH)
print(f"Saved model to {ML_MODEL_PATH}")
