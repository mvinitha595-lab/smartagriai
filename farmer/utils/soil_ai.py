def predict_manure_nutrients(feed_result, health_status):
    """
    Estimate NPK output based on feed composition and animal health.
    Working model (rule-based approximation).
    """

    if not feed_result:
        return None

    total_feed = sum(feed_result.values())

    # Digestion efficiency (working assumption)
    if health_status.lower() == "healthy":
        absorption_rate = 0.85
    elif health_status.lower() == "sick":
        absorption_rate = 0.70
    else:
        absorption_rate = 0.78  # average

    # Undigested portion becomes manure
    manure_mass = total_feed * (1 - absorption_rate)

    # Nutrient factors (approximate agricultural model)
    protein_factor = 0.16  # Nitrogen link
    mineral_factor = 0.05
    fiber_factor = 0.12

    nitrogen = round(manure_mass * protein_factor, 2)
    phosphorus = round(manure_mass * mineral_factor, 2)
    potassium = round(manure_mass * fiber_factor, 2)

    fertilizer_note = (
        f"Estimated nutrient return after composting: "
        f"{nitrogen} kg N, {phosphorus} kg P, {potassium} kg K."
    )

    return {
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,
        "note": fertilizer_note
    }

def predict_weekly_manure(livestock_list):
    """
    Predict total manure production for next 7 days
    based on weight and health condition.
    """

    total_daily_manure = 0

    for animal in livestock_list:
        if not animal.weight_kg:
            continue

        # Base feed estimation
        estimated_feed = animal.weight_kg * 0.03

        # Health multiplier
        if animal.health_status == "Healthy":
            multiplier = 1.0
        elif animal.health_status == "Mild":
            multiplier = 0.9
        else:
            multiplier = 0.75

        if animal.animal_type.lower() == "cow":
            manure = estimated_feed * 0.7
        elif animal.animal_type.lower() == "goat":
            manure = estimated_feed * 0.6
        else:
            manure = estimated_feed * 0.65

        total_daily_manure += manure * multiplier

    weekly_manure = round(total_daily_manure * 7, 2)

    return weekly_manure
