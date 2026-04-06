ORGANIC_NPK = {
    "Cow Manure": 0.5,
    "Goat Manure": 0.8,
    "Poultry Manure": 1.5,
    "Vermicompost": 1.2,
}

def calculate_organic_manure(required_n_kg):
    """
    Convert nitrogen requirement into organic manure quantities
    """
    recommendations = {}

    for source, n_percent in ORGANIC_NPK.items():
        manure_needed = (required_n_kg * 100) / n_percent
        recommendations[source] = round(manure_needed, 2)

    return recommendations
