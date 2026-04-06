import joblib
import os

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "yield_model.pkl"
)

model = joblib.load(MODEL_PATH)


def predict_yield(animal_type, weight_kg, health_status, total_feed, age_months):
    """
    Real ML-based yield prediction using trained regression model.
    """

    # Convert health to numeric
    health_map = {
        "Healthy": 0,
        "Mild": 1,
        "Moderate": 1,
        "Sick": 2
    }

    health_score = health_map.get(health_status, 1)

    prediction = model.predict([[
        weight_kg,
        age_months,
        health_score,
        total_feed
    ]])

    return round(float(prediction[0]), 2)