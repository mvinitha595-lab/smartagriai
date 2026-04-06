import pandas as pd
import pickle

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# -----------------------------
# 1. LOAD DATASET
# -----------------------------
data = pd.read_csv('../dataset/crop_recommendation.csv')

# -----------------------------
# 2. DEFINE FEATURE ORDER (CRITICAL)
# -----------------------------
feature_columns = [
    'N',
    'P',
    'K',
    'temperature',
    'humidity',
    'ph',
    'rainfall'
]

X = data[feature_columns]
y = data['crop']

# -----------------------------
# 3. TRAIN-TEST SPLIT
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# -----------------------------
# 4. TRAIN MODEL
# -----------------------------
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

# -----------------------------
# 5. EVALUATE MODEL
# -----------------------------
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("✅ Model Accuracy:", round(accuracy * 100, 2), "%")

# -----------------------------
# 6. SAVE MODEL
# -----------------------------
with open('crop_model.pkl', 'wb') as file:
    pickle.dump(model, file)

print("✅ Model saved as crop_model.pkl")
