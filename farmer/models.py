from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class SensorData(models.Model):
    temperature = models.FloatField()
    humidity = models.FloatField()
    soil_moisture = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SensorData at {self.timestamp}"

class DiseaseResult(models.Model):
    disease_name = models.CharField(max_length=100)
    severity = models.CharField(max_length=20)
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.disease_name} ({self.severity})"
    
    from django.db import models

class CropPredictionHistory(models.Model):
    crop_name = models.CharField(max_length=100)
    nitrogen = models.FloatField()
    phosphorus = models.FloatField()
    potassium = models.FloatField()
    ph = models.FloatField()
    rainfall = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop_name} - {self.created_at.strftime('%d %b %Y')}"
from django.db import models
from django.contrib.auth.models import User

ANIMAL_CHOICES = [
    ("cow", "Cow"),
    ("goat", "Goat"),
    ("poultry", "Poultry"),
]

class Livestock(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    animal_type = models.CharField(
        max_length=20,
        choices=ANIMAL_CHOICES
    )

    breed = models.CharField(max_length=50)
    age_months = models.PositiveIntegerField()
    weight_kg = models.FloatField(null=True, blank=True)

    health_status = models.CharField(
        max_length=20,
        choices=[
            ("Healthy", "Healthy"),
            ("Sick", "Sick"),
            ("Under Obervation", "Under Obervation")
        ],
        default="Healthy"
    )

    last_vaccination = models.DateField(null=True, blank=True)

    milk_per_day_litre = models.FloatField(null=True, blank=True)
    eggs_per_day = models.PositiveIntegerField(null=True, blank=True)

    daily_waste_kg = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        if self.animal_type == "cow":
            self.daily_waste_kg = 15
        elif self.animal_type == "goat":
            self.daily_waste_kg = 3
        elif self.animal_type == "poultry":
            self.daily_waste_kg = 0.1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.animal_type} - {self.breed}"

class OrganicManureLog(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    source = models.CharField(max_length=50)  # Cow dung, Poultry waste etc
    quantity_kg = models.FloatField()
    compost_started_on = models.DateField()
    ready_after_days = models.IntegerField(default=45)
    status = models.CharField(max_length=20, default="Composting")

    
    def is_ready(self):
        from datetime import date, timedelta
        return date.today() >= self.compost_started_on + timedelta(days=self.ready_after_days)

    def __str__(self):
        return f"{self.source} - {self.quantity_kg}kg"

class OrganicAdvisory(models.Model):
    crop = models.CharField(max_length=50)
    disease = models.CharField(max_length=100)
    remedy = models.TextField()
    dosage = models.CharField(max_length=50)
    application = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop} - {self.disease}"


class OrganicLog(models.Model):
        owner = models.ForeignKey(User, on_delete=models.CASCADE)
        start_date = models.DateField()
        waste_kg = models.FloatField()
    
        status = models.CharField(
            max_length=20,
            choices=[("Composting", "Composting"), ("Ready", "Ready")],
            default="Composting",
        )
    
        def update_status(self):
            if (date.today() - self.start_date).days >= 45:
                self.status = "Ready"
    
        def save(self, *args, **kwargs):
            self.update_status()
            super().save(*args, **kwargs)
    
        def __str__(self):
            return f"Compost {self.status}"
        
class ManureMarketplace(models.Model):
      owner = models.ForeignKey(User, on_delete=models.CASCADE)
      manure_type = models.CharField(max_length=50)
      quantity_kg = models.FloatField()
      is_available = models.BooleanField(default=True)
      created_at = models.DateTimeField(auto_now_add=True)
  
      def __str__(self):
          return f"{self.manure_type} - {self.quantity_kg}kg"      

class LivestockHealthLog(models.Model):
     livestock = models.ForeignKey(Livestock, on_delete=models.CASCADE)
     vaccination = models.CharField(max_length=200, blank=True)
     weight_kg = models.FloatField(null=True, blank=True)
     health_status = models.CharField(max_length=50, default="Healthy")  # ✅ FIX
     notes = models.TextField(blank=True)
     recorded_on = models.DateTimeField(auto_now_add=True)

     def __str__(self):
        return f"Health log for {self.livestock}"
     
class LivestockYieldLog(models.Model):
    livestock = models.ForeignKey(
        Livestock,
        on_delete=models.CASCADE,
        related_name="yield_logs"
    )

    date = models.DateField(auto_now_add=True)

    milk_litre = models.FloatField(null=True, blank=True)
    eggs_count = models.IntegerField(null=True, blank=True)

    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.livestock.animal_type} | {self.date}"
    
class OrganicFertilizerCalculation(models.Model):
    crop = models.CharField(max_length=100)
    nitrogen_required_kg = models.FloatField(help_text="Nitrogen needed in kg")

    manure_type = models.CharField(max_length=50)
    manure_required_kg = models.FloatField(help_text="Equivalent manure in kg")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop} - {self.manure_type}"    
    
class CompostTracker(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    manure_type = models.CharField(max_length=50)
    start_date = models.DateField()
    duration_days = models.IntegerField(default=30)

    def days_left(self):
        from datetime import date
        return max(
            0,
            self.duration_days - (date.today() - self.start_date).days
        )

    def is_ready(self):
        return self.days_left() == 0
    
class OrganicMarketplaceListing(models.Model):
    farmer_name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=100)
    quantity_kg = models.FloatField()
    price_per_kg = models.FloatField()
    location = models.CharField(max_length=100)

    nitrogen = models.FloatField(default=0)
    phosphorus = models.FloatField(default=0)
    potassium = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.farmer_name} - {self.product_type}"
# models.py

class SoilTest(models.Model):
    nitrogen = models.FloatField()
    phosphorus = models.FloatField()
    potassium = models.FloatField()
    ph = models.FloatField()
    tested_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Soil Test - {self.tested_on}"
    

