def recommend_feed(animal_type, age_months, weight_kg, health_status, season):
    feed = {}
    health_note = ""

    # Base feed logic
    if animal_type == "cow":
        green = weight_kg * 0.03
        dry = weight_kg * 0.02
        protein = weight_kg * 0.005

        feed["Green Fodder (kg/day)"] = round(green, 1)
        feed["Dry Fodder (kg/day)"] = round(dry, 1)
        feed["Oil Cake (kg/day)"] = round(protein, 1)

    elif animal_type == "goat":
        green = weight_kg * 0.04
        dry = weight_kg * 0.01

        feed["Green Fodder (kg/day)"] = round(green, 1)
        feed["Dry Fodder (kg/day)"] = round(dry, 1)

    elif animal_type == "poultry":
        grain = weight_kg * 0.08
        feed["Grain Mix (g/day)"] = round(grain, 2)

    # 🌨️ Seasonal Adjustment
    if season == "Winter":
        if "Grain Mix (g/day)" in feed:
            feed["Grain Mix (g/day)"] *= 1.1
        elif "Oil Cake (kg/day)" in feed:
            feed["Oil Cake (kg/day)"] *= 1.1

        health_note = "Based on winter season, energy-rich feed increased by 10% for body heat maintenance."

    elif season == "Summer":
        health_note = "During summer, ensure adequate hydration and mineral supplementation."

    # 🏥 Health Adjustment
    if health_status.lower() == "sick":
        if "Oil Cake (kg/day)" in feed:
            feed["Oil Cake (kg/day)"] *= 1.15

        health_note += " Protein supplementation increased to support recovery."

    return feed, health_note

def predict_manure_output(animal_type, weight_kg, total_feed):
    """
    Rough biological estimation:
    Animals excrete 60–75% of total intake as manure.
    Larger ruminants produce more organic waste.
    """

    manure = 0

    if animal_type == "cow":
        manure = total_feed * 0.7 + (weight_kg * 0.01)

    elif animal_type == "goat":
        manure = total_feed * 0.6 + (weight_kg * 0.008)

    elif animal_type == "poultry":
        manure = total_feed * 0.65

    return round(manure, 2)

def predict_health_risk(weight_kg, age_months, health_status):
    """
    Simple regression-style health scoring system
    """

    base_score = 50

    age_factor = age_months * 0.3
    weight_factor = weight_kg * 0.05

    health_factor = {
        "Healthy": -10,
        "Mild": 5,
        "Sick": 15
    }.get(health_status, 0)

    risk_score = base_score + age_factor + weight_factor + health_factor

    if risk_score < 50:
        status = "Low Risk"
    elif risk_score < 80:
        status = "Moderate Risk"
    else:
        status = "High Risk"

    return round(risk_score, 2), status

