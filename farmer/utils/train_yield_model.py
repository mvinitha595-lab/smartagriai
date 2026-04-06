import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import joblib

# 🔹 Generate synthetic training dataset
np.random.seed(42)

data = []

for _ in range(500):
    weight = np.random.randint(200, 500)
    age = np.random.randint(12, 60)
    health = np.random.choice([0, 1, 2])  # 0=Healthy,1=Mild,2=Sick
    feed = weight * np.random.uniform(0.02, 0.04)

    # Realistic milk formula with noise
    milk = (
        0.035 * weight
        + 0.01 * age
        - 1.5 * health
        + 0.8 * feed
        + np.random.normal(0, 1)
    )

    data.append([weight, age, health, feed, milk])

df = pd.DataFrame(data, columns=[
    "weight", "age", "health", "feed", "milk"
])

X = df[["weight", "age", "health", "feed"]]
y = df["milk"]

model = LinearRegression()
model.fit(X, y)

joblib.dump(model, "yield_model.pkl")

print("✅ Yield ML Model Trained & Saved")