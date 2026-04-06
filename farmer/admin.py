from django.contrib import admin
from .models import (
    SensorData,
    DiseaseResult,
    CropPredictionHistory,
    Livestock,
    OrganicLog,
    OrganicManureLog,
    OrganicAdvisory,
    ManureMarketplace,
)

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ("temperature", "humidity", "soil_moisture", "timestamp")
    list_filter = ("timestamp",)

@admin.register(DiseaseResult)
class DiseaseResultAdmin(admin.ModelAdmin):
    list_display = ("disease_name", "severity", "confidence", "created_at")
    list_filter = ("severity",)

@admin.register(CropPredictionHistory)
class CropPredictionHistoryAdmin(admin.ModelAdmin):
    list_display = ("crop_name", "ph", "rainfall", "created_at")
    list_filter = ("crop_name",)

from django.contrib import admin

from django.contrib import admin
from .models import SensorData, DiseaseResult, CropPredictionHistory

from .models import Livestock, OrganicManureLog

from .models import OrganicAdvisory

@admin.register(OrganicManureLog)
class OrganicManureLogAdmin(admin.ModelAdmin):
    list_display = ("source", "quantity_kg", "compost_started_on", "status")

from django.contrib import admin
from .models import (
    Livestock,
    OrganicLog,
    OrganicAdvisory,
    ManureMarketplace,
)


from django.contrib import admin
from .models import Livestock

@admin.register(Livestock)
class LivestockAdmin(admin.ModelAdmin):
    
    class Media:
        js = ("admin/js/livestock.js",)

    list_display = (
        "owner",
        "animal_type",
        "breed",
        "age_months",
        "weight_kg",
        "health_status",
        "milk_per_day_litre",
        "eggs_per_day",
        "daily_waste_kg",
    )

    list_filter = ("animal_type", "health_status")
    search_fields = ("breed", "owner__username")

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "owner",
                "animal_type",
                "breed",
                "age_months",
                "weight_kg",
            )
        }),
        ("Health", {
            "fields": (
                "health_status",
                "last_vaccination",
            )
        }),
        ("Yield Monitoring", {
            "fields": (
                "milk_per_day_litre",
                "eggs_per_day",
            )
        }),
        ("Organic Output", {
            "fields": ("daily_waste_kg",)
        }),
    )

    readonly_fields = ("daily_waste_kg",)




    
@admin.register(OrganicLog)
class OrganicLogAdmin(admin.ModelAdmin):
      list_display = (
          "owner",
          "waste_kg",
          "start_date",
          "status",
      )
  
      list_filter = ("status",)
      search_fields = ("owner__username",)

@admin.register(OrganicAdvisory)
class OrganicAdvisoryAdmin(admin.ModelAdmin):
    list_display = (
        "crop",
        "disease",
        "created_at",
    )

    list_filter = ("crop",)
    search_fields = ("crop", "disease")

@admin.register(ManureMarketplace)
class ManureMarketplaceAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "manure_type",
        "quantity_kg",
        "is_available",
        "created_at",
    )

    list_filter = ("is_available",)
    search_fields = ("manure_type", "owner__username")

from .models import LivestockHealthLog
    
@admin.register(LivestockHealthLog)
class LivestockHealthLogAdmin(admin.ModelAdmin):
        list_display = (
            "livestock",
            "vaccination",
            "weight_kg",
            "recorded_on",
        )
        list_display = ("livestock", "vaccination", "weight_kg", "recorded_on")
        list_filter = ("recorded_on",)


