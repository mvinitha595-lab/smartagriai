from django import forms
from .models import Livestock

class LivestockHealthForm(forms.ModelForm):
    class Meta:
        model = Livestock
        fields = [
            "weight_kg",
            "health_status",
            "last_vaccination",
        ]

        widgets = {
            "last_vaccination": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "weight_kg": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1"}
            ),
            "health_status": forms.Select(
                attrs={"class": "form-control"}
            ),
        }