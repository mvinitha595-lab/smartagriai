from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

from tensorflow.keras.models import load_model

from tensorflow.keras.preprocessing import image

from farmer.models import (
    SensorData,
    DiseaseResult,
    CropPredictionHistory
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, black, grey,red,yellow

import tensorflow as tf

from reportlab.lib.units import cm
    
from organic.utils import calculate_organic_manure

from .models import Livestock, OrganicManureLog
from django.contrib.auth.decorators import login_required

from .models import OrganicAdvisory



# -----------------------------
# BASIC PAGES
# -----------------------------
def landing_page(request):
    return render(request, "landing.html")


def farmer_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # ✅ Remember Me logic
            if not request.POST.get('remember'):
                request.session.set_expiry(0)

            messages.success(request, "Login successful ✅")

            # 🔥 ROLE BASED REDIRECT (FIX)
            if user.is_superuser:
                return redirect("/admin-dashboard/")
            else:
                return redirect("/dashboard/")

        else:
            messages.error(request, "Invalid username or password ❌")

    return render(request, "login.html")

from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists ❌")
        else:
            User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            messages.success(request, "Account created successfully ✅")
            return redirect("/login/")

    return render(request, "register.html")

from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import render

def password_reset(request):
    if request.method == "POST":
        email = request.POST.get("email")

        user = User.objects.filter(email=email).first()

        if user:
            reset_link = f"http://127.0.0.1:8000/reset/{user.id}/"

            send_mail(
                "SmartAgri Password Reset",
                f"Hello Farmer,\n\nClick below link to reset password:\n{reset_link}",
                "your_email@gmail.com",
                [email],
                fail_silently=False,
            )

            messages.success(request, "Reset link sent successfully ✅")
        else:
            messages.error(request, "Email not registered ❌")

    return render(request, "password_reset.html")
# -----------------------------
# FARMER DASHBOARD
# -----------------------------
@login_required(login_url="farmer_login")
@login_required(login_url="/login/")
def farmer_dashboard(request):
    sensor_data = SensorData.objects.order_by("-timestamp")[:10]
    last_disease = DiseaseResult.objects.order_by("-created_at").first()

    def r(x):
        return round(x, 2) if x is not None else None

    context = {
        "temperatures": [r(d.temperature) for d in sensor_data][::-1],
        "humidities": [r(d.humidity) for d in sensor_data][::-1],
        "moisture": [r(d.soil_moisture) for d in sensor_data][::-1],
        "timestamps": [d.timestamp.strftime("%H:%M") for d in sensor_data][::-1],

        "disease_name": last_disease.disease_name if last_disease else "Healthy",
        "disease_severity": last_disease.severity if last_disease else "Low",
    }

    return render(request, "farmer_dashboard.html", context)




def farmer_logout(request):
    logout(request)
    return redirect("landing_page")

# -----------------------------
# CROP & FERTILIZER PREDICTION
# -----------------------------
def crop_predictor(request):
    prediction = None
    fertilizer_advice = []
    organic_recommendation = None
    error = None

    if request.method == "POST":
        try:
            N = float(request.POST["N"])
            P = float(request.POST["P"])
            K = float(request.POST["K"])
            ph = float(request.POST["ph"])
            rainfall = float(request.POST["rainfall"])

            temperature = 25.0
            humidity = 60.0

            organic_recommendation = calculate_organic_manure(N)

            model_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "ml_models",
                "crop_model.pkl"
            )

            with open(model_path, "rb") as f:
                model = pickle.load(f)

            features = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
            prediction = model.predict(features)[0]

            if N < 50:
                fertilizer_advice.append("Apply Nitrogen-rich fertilizer (Urea)")
            if P < 40:
                fertilizer_advice.append("Apply Phosphorus-rich fertilizer (DAP / SSP)")
            if K < 40:
                fertilizer_advice.append("Apply Potassium-rich fertilizer (MOP)")

            if not fertilizer_advice:
                fertilizer_advice.append("Soil nutrients are balanced. No major fertilizer required.")

# ✅ SAVE TO HISTORY
            CropPredictionHistory.objects.create(
                crop_name=prediction,
                nitrogen=N,
                phosphorus=P,
                potassium=K,
                ph=ph,
                rainfall=rainfall
            )

            # Save for PDF
            request.session["crop_advisory"] = {
                "Crop": prediction,
                "Nitrogen": N,
                "Phosphorus": P,
                "Potassium": K,
                "pH": ph,
                "Rainfall": rainfall
            }

        except Exception as e:
            error = str(e)

    return render(request, "predictor.html", {
        "prediction": prediction,
        "fertilizer_advice": fertilizer_advice,
        "organic_recommendation" : organic_recommendation,
        "error": error
    })



# -----------------------------
# LIVE FARM MONITOR
# -----------------------------
def live_farm_monitor(request):
    data = SensorData.objects.order_by('-timestamp')[:10]

    context = {
        "temperatures": [d.temperature for d in data][::-1],
        "humidities": [d.humidity for d in data][::-1],
        "moisture": [d.soil_moisture for d in data][::-1],
        "timestamps": [d.timestamp.strftime("%H:%M") for d in data][::-1],
    }

    return render(request, "live_farm_monitor.html", context)


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
import os
import pandas as pd
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from django.contrib.auth.decorators import user_passes_test

from farmer.models import CropPredictionHistory, DiseaseResult


# ✅ Admin check
def is_admin(user):
    return user.is_staff


@user_passes_test(is_admin, login_url='/login/')
def admin_dashboard(request):

    # 📊 Dataset
    data_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "dataset",
        "crop_recommendation.csv"
    )

    df = pd.read_csv(data_path)

    # 👨‍🌾 Farmers
    total_farmers = User.objects.count()

    # 💰 Savings
    total_savings = total_farmers * 330

    # 🌾 Crop data (SAFE)
    crop_qs = CropPredictionHistory.objects.values("crop_name").annotate(count=Count("id"))
    crop_labels = [c["crop_name"] for c in crop_qs] if crop_qs else ["No Data"]
    crop_values = [c["count"] for c in crop_qs] if crop_qs else [0]

    # 🦠 Disease data (SAFE)
    disease_qs = DiseaseResult.objects.values("disease_name").annotate(count=Count("id"))
    disease_labels = [d["disease_name"] for d in disease_qs] if disease_qs else ["No Data"]
    disease_counts = [d["count"] for d in disease_qs] if disease_qs else [0]

    # ⚠️ High risk
    high_risk_count = DiseaseResult.objects.filter(severity="High").count()

    # 🕒 Recent activity
    recent_crops = CropPredictionHistory.objects.order_by('-id')[:5]
    recent_diseases = DiseaseResult.objects.order_by('-id')[:5]

    context = {
        "accuracy": 98,
        "total_records": len(df),

        "total_farmers": total_farmers,
        "total_savings": total_savings,
        "high_risk_count": high_risk_count,

        "crop_labels": crop_labels,
        "crop_values": crop_values,

        "disease_labels": disease_labels,
        "disease_counts": disease_counts,

        "recent_crops": recent_crops,
        "recent_diseases": recent_diseases,
    }

    return render(request, "admin_dashboard.html", context)

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect('/login/')

# -----------------------------
# LOAD CNN MODEL (GLOBAL)
# -----------------------------
CNN_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "ml_models",
    "disease_cnn_multiclass.h5"
)

cnn_model = load_model(CNN_MODEL_PATH)

CLASS_NAMES = ["Healthy", "Leaf_Blight", "Leaf_Spot"]

DISEASE_DETAILS = {
    "Leaf_Blight": {
        "info": "Leaf blight is a fungal disease caused by prolonged moisture and poor air circulation. It spreads rapidly during humid conditions.",
        "organic": [
            "Neem oil spray every 7 days",
            "Remove infected leaves",
            "Use compost-based bio-fungicides"
        ],
        "chemical": [
            "Mancozeb fungicide",
            "Chlorothalonil spray (as per label instructions)"
        ],
        "prevention": [
            "Avoid overhead irrigation",
            "Ensure proper plant spacing",
            "Practice crop rotation"
        ]
    },

    "Leaf_Spot": {
        "info": "Leaf spot is caused by fungi or bacteria and appears as dark circular spots on leaves.",
        "organic": [
            "Neem oil spray",
            "Baking soda + soap solution"
        ],
        "chemical": [
            "Copper-based fungicides"
        ],
        "prevention": [
            "Remove plant debris",
            "Avoid wet foliage"
        ]
    },

    "Healthy": {
        "info": "The plant leaf appears healthy with no visible disease symptoms.",
        "organic": ["No treatment required"],
        "chemical": ["No treatment required"],
        "prevention": [
            "Regular monitoring",
            "Balanced fertilization"
        ]
    }
}

# -----------------------------
# DISEASE DETECTION
# -----------------------------
def disease_detection(request):
    # -------------------------------
    # DEFAULTS (VERY IMPORTANT)
    # -------------------------------
    prediction = None
    confidence = None
    severity = None

    disease_info = ""
    organic_treatment = []
    chemical_treatment = []
    prevention_tips = []
   

    # MUST match training folders
    CLASS_NAMES = ["Healthy", "Leaf_Blight", "Leaf_Spot"]

    # -------------------------------
    # KNOWLEDGE BASE (STATIC, SAFE)
    # -------------------------------
    DISEASE_DETAILS = {
        "Leaf_Blight": {
            "info": "Leaf blight is a fungal disease caused by prolonged moisture and poor air circulation. It spreads rapidly in humid conditions.",
            "organic": [
                "Apply neem oil spray weekly",
                "Remove infected leaves immediately",
                "Improve air circulation"
            ],
            "chemical": [
                "Use Mancozeb fungicide",
                "Apply Copper-based fungicide"
            ],
            "prevention": [
                "Avoid overhead irrigation",
                "Maintain proper plant spacing",
                "Practice crop rotation"
            ],
          
        },

        "Leaf_Spot": {
            "info": "Leaf spot is commonly caused by bacteria or fungi and appears as dark circular spots on leaves.",
            "organic": [
                "Neem oil spray",
                "Remove affected leaves"
            ],
            "chemical": [
                "Apply Chlorothalonil fungicide"
            ],
            "prevention": [
                "Avoid excess moisture",
                "Use disease-free seeds"
            ],
           
        },

        "Healthy": {
            "info": "The plant leaf appears healthy with no visible disease symptoms.",
            "organic": [],
            "chemical": [],
            "prevention": [
                "Maintain proper irrigation",
                "Monitor plants regularly"
            ],
            
            
        }
    }

    # -------------------------------
    # IMAGE UPLOAD & PREDICTION
    # -------------------------------
    if request.method == "POST" and request.FILES.get("leaf_image"):
        img_file = request.FILES["leaf_image"]

        img_path = os.path.join(settings.MEDIA_ROOT, "uploaded_leaf.jpg")
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        with open(img_path, "wb+") as f:
            for chunk in img_file.chunks():
                f.write(chunk)

        # Preprocess
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # Predict
        preds = cnn_model.predict(img_array)
        class_index = int(np.argmax(preds[0]))

        prediction = CLASS_NAMES[class_index]
        confidence = round(float(preds[0][class_index]) * 100, 2)

        # Severity
        if confidence >= 80:
            severity = "High"
        elif confidence >= 50:
            severity = "Medium"
        else:
            severity = "Low"


        # Load disease content
        disease_data = DISEASE_DETAILS.get(prediction, {})

        disease_info = disease_data.get("info", "")
        organic_treatment = disease_data.get("organic", [])
        chemical_treatment = disease_data.get("chemical", [])
        prevention_tips = disease_data.get("prevention", [])
       
        
        
        # Save history
        DiseaseResult.objects.create(
            disease_name=prediction,
            severity=severity,
            confidence=confidence,
           
        )

    # -------------------------------
    # RENDER (ALL VARIABLES SAFE)
    # -------------------------------
    return render(request, "disease_detection.html", {
        "prediction": prediction,
        "confidence": confidence,
        "severity": severity,
        "disease_info": disease_info,
        "organic_treatment": organic_treatment,
        "chemical_treatment": chemical_treatment,
        "prevention_tips": prevention_tips,
        
    })


# -----------------------------
# PDF EXPORTS
# -----------------------------
from reportlab.lib.colors import green, black, grey
from datetime import datetime





def crop_advisory_pdf(request):
    data = request.session.get("crop_advisory")
    if not data:
        return HttpResponse("No advisory data available")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=SmartAgri_Crop_Advisory_Report.pdf"

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # ======================
    # HEADER
    # ======================
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 50, "SmartAgri AI – Crop Advisory Report")

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(
        width / 2,
        height - 70,
        "AI-powered decision support system for smart agriculture"
    )

    # Divider
    pdf.line(50, height - 85, width - 50, height - 85)

    # ======================
    # BASIC DETAILS
    # ======================
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 120, "Recommended Crop:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(200, height - 120, data["Crop"].title())

    # ======================
    # SOIL PARAMETERS TABLE
    # ======================
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, height - 160, "Soil Parameter Summary")

    pdf.setFont("Helvetica", 11)
    y = height - 190
    line_gap = 20

    soil_data = [
        ("Nitrogen (mg/kg)", data["Nitrogen"]),
        ("Phosphorus (mg/kg)", data["Phosphorus"]),
        ("Potassium (mg/kg)", data["Potassium"]),
        ("Soil pH", data["pH"]),
        ("Rainfall (mm)", data["Rainfall"]),
    ]

    for label, value in soil_data:
        pdf.drawString(60, y, f"{label}:")
        pdf.drawString(220, y, str(value))
        y -= line_gap

    # ======================
    # INTERPRETATION SECTION
    # ======================
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y - 10, "AI Interpretation & Advisory")

    pdf.setFont("Helvetica", 11)
    y -= 40

    advisory_lines = []

    # pH interpretation
    if data["pH"] < 5.5:
        advisory_lines.append(
            "• Soil pH is acidic. Consider applying lime to improve nutrient availability."
        )
    elif data["pH"] > 7.5:
        advisory_lines.append(
            "• Soil pH is alkaline. Organic matter can help balance soil chemistry."
        )
    else:
        advisory_lines.append(
            "• Soil pH is within the optimal range for most crops."
        )

    # Nutrient interpretation
    if data["Nitrogen"] < 50:
        advisory_lines.append(
            "• Nitrogen level is low. Nitrogen-rich fertilizers (e.g., Urea) are recommended."
        )
    else:
        advisory_lines.append(
            "• Nitrogen level is sufficient to support healthy vegetative growth."
        )

    if data["Potassium"] < 40:
        advisory_lines.append(
            "• Potassium is low. Apply Potassium-based fertilizer (MOP) to strengthen roots."
        )
    else:
        advisory_lines.append(
            "• Potassium level is adequate for crop resilience and yield."
        )

    for line in advisory_lines:
        pdf.drawString(60, y, line)
        y -= 18


    # ======================
    # CONCLUSION
    # ======================
    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Conclusion:")

    pdf.setFont("Helvetica", 11)
    y -= 20
    pdf.drawString(
        60,
        y,
        f"Based on the provided soil parameters, {data['Crop'].title()} is a suitable crop choice."
    )

    # ======================
    # FOOTER
    # ======================
    pdf.setFont("Helvetica", 9)
    pdf.line(50, 70, width - 50, 70)

    pdf.drawString(
        50,
        55,
        f"Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p')}"
    )
    pdf.drawRightString(
        width - 50,
        55,
        "SmartAgri AI | Final Year Project"
    )

    pdf.showPage()
    pdf.save()

    return response

from django.shortcuts import get_object_or_404
from farmer.models import CropPredictionHistory

def history_pdf(request, pk):
    record = get_object_or_404(CropPredictionHistory, pk=pk)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f"attachment; filename=Crop_Report_{record.created_at.date()}.pdf"
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # HEADER
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 50, "SmartAgri AI – Crop Advisory Report")

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(
        width / 2,
        height - 70,
        "Generated from Field Prediction History"
    )

    pdf.line(50, height - 90, width - 50, height - 90)

    # CONTENT
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, height - 130, f"Recommended Crop: {record.crop_name.title()}")

    pdf.setFont("Helvetica", 11)
    y = height - 170

    details = [
        ("Nitrogen", record.nitrogen),
        ("Phosphorus", record.phosphorus),
        ("Potassium", record.potassium),
        ("Soil pH", record.ph),
        ("Rainfall (mm)", record.rainfall),
    ]

    for label, value in details:
        pdf.drawString(60, y, f"{label}:")
        pdf.drawString(200, y, str(value))
        y -= 20

    # FOOTER
    pdf.setFont("Helvetica", 9)
    pdf.line(50, 70, width - 50, 70)

    pdf.drawString(
        50,
        55,
        f"Generated on {record.created_at.strftime('%d %b %Y %I:%M %p')}"
    )

    pdf.drawRightString(
        width - 50,
        55,
        "SmartAgri AI | Final Year Project"
    )

    pdf.showPage()
    pdf.save()

    return response


def disease_report_pdf(request):
    last = DiseaseResult.objects.order_by("-created_at").first()

    if not last:
        return HttpResponse("No disease report available")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=SmartAgri_Disease_Report.pdf"

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # =========================
    # HEADER (Branding)
    # =========================
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
    if os.path.exists(logo_path):
        pdf.drawImage(logo_path, 2 * cm, height - 3 * cm, width=2 * cm, height=2 * cm)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 2.2 * cm, "SmartAgri AI – Disease Detection Report")

    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(grey)
    pdf.drawCentredString(
        width / 2,
        height - 3 * cm,
        "AI-powered Plant Health Diagnostic System"
    )

    pdf.setFillColor(black)
    pdf.line(2 * cm, height - 3.4 * cm, width - 2 * cm, height - 3.4 * cm)

    # =========================
    # REPORT DETAILS
    # =========================
    y = height - 4.5 * cm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "Report Details")

    pdf.setFont("Helvetica", 11)
    y -= 18
    pdf.drawString(2 * cm, y, f"Farmer Name: {request.user.username if request.user.is_authenticated else 'N/A'}")

    y -= 16
    pdf.drawString(2 * cm, y, f"Date & Time: {last.created_at.strftime('%d %b %Y, %I:%M %p')}")

    # =========================
    # DIAGNOSIS SUMMARY
    # =========================
    y -= 30
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(2 * cm, y, "Diagnosis Summary")

    pdf.setFont("Helvetica", 12)
    y -= 20
    pdf.drawString(2 * cm, y, f"Disease Identified: {last.disease_name}")

    y -= 18
    pdf.drawString(2 * cm, y, f"Confidence Level: {last.confidence}%")

    # Severity with color
    y -= 18
    pdf.setFont("Helvetica-Bold", 12)

    if last.severity == "High":
        pdf.setFillColor(red)
    elif last.severity == "Medium":
        pdf.setFillColor(yellow)
    else:
        pdf.setFillColor(green)

    pdf.drawString(2 * cm, y, f"Severity Level: {last.severity}")
    pdf.setFillColor(black)

    # =========================
    # DISEASE INFORMATION
    # =========================
    y -= 30
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(2 * cm, y, "Disease Information")

    pdf.setFont("Helvetica", 11)
    y -= 18

    disease_info = {
        "Leaf_Blight": "Leaf blight is a fungal disease caused by prolonged moisture and poor air circulation.",
        "Leaf_Spot": "Leaf spot is caused by bacteria or fungi and appears as dark circular spots on leaves.",
        "Healthy": "The plant leaf appears healthy with no visible disease symptoms."
    }

    pdf.drawString(
        2 * cm,
        y,
        disease_info.get(last.disease_name, "No additional information available.")
    )

    # =========================
    # TREATMENT & PREVENTION
    # =========================
    y -= 30
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(2 * cm, y, "Recommended Actions")

    pdf.setFont("Helvetica", 11)
    y -= 18

    recommendations = {
        "Leaf_Blight": [
            "Apply neem oil spray every 7 days",
            "Remove infected leaves immediately",
            "Improve air circulation",
            "Avoid overhead irrigation"
        ],
        "Leaf_Spot": [
            "Remove affected leaves",
            "Use copper-based fungicide",
            "Avoid wet foliage"
        ],
        "Healthy": [
            "Continue regular monitoring",
            "Maintain balanced fertilization"
        ]
    }

    for step in recommendations.get(last.disease_name, []):
        pdf.drawString(2.2 * cm, y, f"• {step}")
        y -= 14

    # =========================
    # DISCLAIMER & FOOTER
    # =========================
    y -= 20
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(grey)
    pdf.drawString(
        2 * cm,
        y,
        "Disclaimer: This report is AI-generated. Consult an agricultural expert for severe cases."
    )

    pdf.setFillColor(black)
    pdf.line(2 * cm, 2 * cm, width - 2 * cm, 2 * cm)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        2 * cm,
        1.5 * cm,
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )

    pdf.drawRightString(
        width - 2 * cm,
        1.5 * cm,
        "SmartAgri AI | Final Year Project"
    )

    pdf.showPage()
    pdf.save()

    return response


from django.db.models import Count
from farmer.models import CropPredictionHistory

from collections import Counter
import json


from django.db.models import Count
from django.shortcuts import render
from farmer.models import CropPredictionHistory, DiseaseResult
import json

def field_history(request):
    # -------------------------
    # CROP HISTORY (UNCHANGED)
    # -------------------------
    history = CropPredictionHistory.objects.order_by("created_at")

    dates = [h.created_at.strftime("%d %b") for h in history]
    ph_values = [float(h.ph) for h in history]

    crop_counts = (
        CropPredictionHistory.objects
        .values("crop_name")
        .annotate(total=Count("id"))
    )

    crop_labels = [c["crop_name"].title() for c in crop_counts]
    crop_values = [c["total"] for c in crop_counts]

    # -------------------------
    # DISEASE HISTORY (NEW ADD)
    # -------------------------
    disease_history = DiseaseResult.objects.order_by("created_at")

    disease_dates = [
        d.created_at.strftime("%d %b")
        for d in disease_history
    ]

    severity_map = {
        "Low": 1,
        "Medium": 2,
        "High": 3
    }

    disease_severity_values = [
        severity_map.get(d.severity, 1)
        for d in disease_history
    ]

    # -------------------------
    # CONTEXT (MERGED SAFELY)
    # -------------------------
    context = {
        # crop history
        "history": history,
        "dates": json.dumps(dates),
        "ph_values": json.dumps(ph_values),
        "crop_labels": json.dumps(crop_labels),
        "crop_values": json.dumps(crop_values),

        # disease history
        "disease_history": disease_history,
        "disease_dates": json.dumps(disease_dates),
        "disease_severity_values": json.dumps(disease_severity_values),
    }

    return render(request, "field_history.html", context)


def disease_history_pdf(request, pk):
    record = get_object_or_404(DiseaseResult, pk=pk)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f"attachment; filename=Disease_Report_{record.created_at.date()}.pdf"
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # HEADER
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 50, "SmartAgri AI – Disease Detection Report")

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(
        width / 2,
        height - 70,
        "AI-powered plant disease analysis"
    )

    pdf.line(50, height - 90, width - 50, height - 90)

    # CONTENT
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, height - 130, f"Disease Name:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(200, height - 130, record.disease_name)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, height - 160, f"Severity:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(200, height - 160, record.severity)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, height - 190, f"Confidence:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(200, height - 190, f"{record.confidence}%")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, height - 220, f"Date:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(
        200,
        height - 220,
        record.created_at.strftime("%d %b %Y")
    )

    # FOOTER
    pdf.setFont("Helvetica", 9)
    pdf.line(50, 70, width - 50, 70)

    pdf.drawString(
        50,
        55,
        f"Generated on {datetime.now().strftime('%d %b %Y %I:%M %p')}"
    )

    pdf.drawRightString(
        width - 50,
        55,
        "SmartAgri AI | Final Year Project"
    )

    pdf.showPage()
    pdf.save()

    return response



def crop_history_pdf(request, pk):
    h = CropPredictionHistory.objects.get(id=pk)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=Crop_Report.pdf"

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width/2, height-50, "SmartAgri AI – Crop Advisory Report")

    pdf.setFont("Helvetica", 11)
    y = height - 100

    pdf.drawString(60, y, f"Crop: {h.crop_name}")
    y -= 20
    pdf.drawString(60, y, f"Soil pH: {h.ph}")
    y -= 20
    pdf.drawString(60, y, f"Rainfall: {h.rainfall} mm")
    y -= 20
    pdf.drawString(60, y, f"Date: {h.created_at.strftime('%d %b %Y')}")

    pdf.showPage()
    pdf.save()
    return response

def organic_livestock(request):
    livestock = Livestock.objects.all()

    total_livestock = livestock.count()

    total_daily_waste = sum(
        l.daily_waste_kg or 0 for l in livestock
    )

    health_alerts = livestock.exclude(
        health_status="Healthy"
    ).count()

    fertilizer_potential = round(
        (total_daily_waste * 30) / 700, 2
    )
    # 700 kg manure ≈ 1 acre/month

    context = {
        "livestock": livestock,                 # ✅ single source
        "total_livestock": total_livestock,
        "total_waste": total_daily_waste,       # ✅ matches HTML
        "alerts": health_alerts,                # ✅ matches HTML
        "total_land_coverage": fertilizer_potential,
    }

    return render(request, "organic_livestock.html", context)

def organic_advisor(request):
    advisories = OrganicAdvisory.objects.all()
    
    return render(request, "organic_advisor.html", {
        "advisories": advisories
    })

def organic_equivalent(n_required_kg):
    cow_manure = n_required_kg * 20      # avg conversion
    vermicompost = n_required_kg * 10
    poultry_manure = n_required_kg * 5

    return {
        "cow_manure": cow_manure,
        "vermicompost": vermicompost,
        "poultry_manure": poultry_manure,
    }

from .forms import LivestockHealthForm

@login_required
def livestock_health_tracker(request, pk):
    livestock = get_object_or_404(Livestock, pk=pk, owner=request.user)

    if request.method == "POST":
        form = LivestockHealthForm(request.POST, instance=livestock)
        if form.is_valid():
            form.save()
            return redirect("organic_livestock")
    else:
        form = LivestockHealthForm(instance=livestock)

    return render(request, "livestock_health_tracker.html", {
        "livestock": livestock,
        "form": form,
    })

from django.shortcuts import render, get_object_or_404
from .models import Livestock, LivestockHealthLog
from farmer.utils.feed_ai import predict_health_risk, predict_manure_output
from farmer.utils.soil_ai import predict_manure_nutrients

from django.utils import timezone   # ✅ FIX
from datetime import timedelta


def health_tracker(request):
    livestock = Livestock.objects.all()

    risk_score = None
    risk_status = None
    insight_message = None
    vaccination_alert = None
    next_vaccination_date = None
    days_remaining = None
    nutrient_output = None
    previous_logs = None
    animal = None

    organic_cost = 0
    market_cost = 0
    cost_savings = 0
    cost_note = None

    manure_output = None
    compost_ready = None
    circular_message = None

    if request.method == "POST":

        animal_id = request.POST.get("animal")
        health_status = request.POST.get("health_status")
        vaccination = request.POST.get("vaccination")

        # ✅ SAFE WEIGHT
        weight_input = request.POST.get("weight_kg")
        weight_kg = float(weight_input) if weight_input else 0

        if animal_id:
            animal = get_object_or_404(Livestock, id=animal_id)

            feed_result = request.session.get("last_feed_result")

            # 🔹 Save Health Log
            LivestockHealthLog.objects.create(
                livestock=animal,
                weight_kg=weight_kg,
                health_status=health_status,
                vaccination=vaccination
            )

            # 🔹 AI Risk
            risk_score, risk_status = predict_health_risk(
                weight_kg,
                animal.age_months,
                health_status
            )

            # ================= ECONOMIC =================

            market_feed_price_per_kg = 28
            estimated_feed_kg = weight_kg * 0.03

            organic_cost = estimated_feed_kg * 12
            market_cost = estimated_feed_kg * market_feed_price_per_kg
            cost_savings = round(market_cost - organic_cost, 2)

            if cost_savings > 0:
                cost_note = f"Using organic feed saves ₹{cost_savings} per day."
            else:
                cost_note = f"Organic feed costs ₹{abs(cost_savings)} more per day."

            # ================= NUTRIENTS =================

            if feed_result:
                nutrient_output = predict_manure_nutrients(
                    feed_result,
                    health_status
                )
                total_feed = sum(feed_result.values())
            else:
                total_feed = estimated_feed_kg

            # ================= CIRCULAR =================

            manure_output = predict_manure_output(
                animal.animal_type.lower(),
                weight_kg,
                total_feed
            )

            compost_ready = round(manure_output * 0.8, 2)

            nitrogen = round(compost_ready * 0.005, 2)
            phosphorus = round(compost_ready * 0.003, 2)
            potassium = round(compost_ready * 0.004, 2)

            circular_message = (
                f"Daily Organic Manure Output: {manure_output} kg — "
                f"{compost_ready} kg compost-ready. "
                f"N={nitrogen}kg, P={phosphorus}kg, K={potassium}kg."
            )

            # ================= VACCINATION (FIXED) =================

            if animal.last_vaccination:
                next_vaccination_date = animal.last_vaccination + timedelta(days=180)
                today = timezone.now().date()   # ✅ FIX

                if today >= next_vaccination_date:
                    vaccination_alert = "🚨 Vaccination overdue! Immediate vet visit required."
                else:
                    days_remaining = (next_vaccination_date - today).days
                    vaccination_alert = f"🩺 Next vaccination in {days_remaining} days."
            else:
                vaccination_alert = "⚠ No vaccination record found."

            # ================= HISTORY =================

            previous_logs = LivestockHealthLog.objects.filter(
                livestock=animal
            ).order_by('-recorded_on')

            if previous_logs.count() >= 2:
                latest = previous_logs[0]
                earlier = previous_logs[1]

                if earlier.weight_kg and earlier.weight_kg > 0:
                    percent_drop = ((earlier.weight_kg - latest.weight_kg) / earlier.weight_kg) * 100

                    if percent_drop > 5:
                        insight_message = (
                            f"⚠ Weight dropped by {round(percent_drop, 2)}%. "
                            "Possible stress or feed imbalance."
                        )

            recent_sick = previous_logs.filter(health_status="Sick").count() if previous_logs else 0

            if recent_sick >= 3:
                insight_message = "🚨 Multiple sickness records. Recommend vet inspection."

    return render(request, "health_tracker.html", {
        "livestock": livestock,
        "risk_score": risk_score,
        "risk_status": risk_status,
        "insight_message": insight_message,
        "vaccination_alert": vaccination_alert,
        "next_vaccination_date": next_vaccination_date,
        "days_remaining": days_remaining,
        "nutrient_output": nutrient_output,
        "organic_cost": round(organic_cost, 2),
        "market_cost": round(market_cost, 2),
        "cost_savings": cost_savings,
        "cost_note": cost_note,
        "manure_output": manure_output,
        "compost_ready": compost_ready,
        "circular_message": circular_message,
    })

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import styles
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from django.http import HttpResponse
from django.utils import timezone

def download_health_report(request):

    # Fetch latest health log
    latest_log = LivestockHealthLog.objects.order_by("-recorded_on").first()

    if not latest_log:
        return HttpResponse("No health records available.")

    animal = latest_log.livestock

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Livestock_Health_Report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles_sheet = styles.getSampleStyleSheet()

    title_style = styles_sheet["Heading1"]
    normal_style = styles_sheet["Normal"]

    # 🔹 Title
    elements.append(Paragraph("SmartAgri AI - Livestock Health Intelligence Report", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # 🔹 Animal Profile Section
    elements.append(Paragraph("<b>Animal Profile</b>", styles_sheet["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    profile_data = [
        ["Animal Type", animal.animal_type.title()],
        ["Age (months)", str(animal.age_months)],
        ["Weight (kg)", str(latest_log.weight_kg)],
        ["Health Status", latest_log.health_status],
        ["Vaccination", latest_log.vaccination or "N/A"],
        ["Report Date", timezone.now().strftime("%d %B %Y")]
    ]

    table = Table(profile_data, colWidths=[2.5 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.4 * inch))

    # 🔹 AI Risk Section
    risk_score, risk_status = predict_health_risk(
        latest_log.weight_kg,
        animal.age_months,
        latest_log.health_status
    )

    elements.append(Paragraph("<b>AI Health Risk Analysis</b>", styles_sheet["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(f"Risk Score: {risk_score}%", normal_style))
    elements.append(Paragraph(f"Risk Category: {risk_status}", normal_style))
    elements.append(Spacer(1, 0.4 * inch))

    # 🔹 Advisory Section
    elements.append(Paragraph("<b>Advisory Recommendation</b>", styles_sheet["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    if risk_status == "High Risk":
        advisory_text = "Immediate veterinary consultation recommended. Monitor feed and hydration closely."
    elif risk_status == "Moderate Risk":
        advisory_text = "Monitor animal for behavioral or appetite changes. Preventive check advised."
    else:
        advisory_text = "Animal appears stable. Continue routine monitoring and balanced nutrition."

    elements.append(Paragraph(advisory_text, normal_style))
    elements.append(Spacer(1, 0.4 * inch))

    # 🔹 Footer
    elements.append(Paragraph(
        "Disclaimer: This AI-generated report is advisory in nature. "
        "Consult a licensed veterinary professional for severe conditions.",
        styles_sheet["Italic"]
    ))

    doc.build(elements)

    return response

from django.shortcuts import render, get_object_or_404
from .models import Livestock
from farmer.utils.feed_ai import recommend_feed, predict_manure_output
import json

from django.utils import timezone   # ✅ FIXED (Django safe)
from datetime import timedelta


def feed_management(request):
    livestock = Livestock.objects.all()

    feed_result = None
    health_note = None
    season = None

    feed_chart_labels = None
    feed_chart_data = None

    animal_profile = None

    manure_output = None
    circular_note = None

    vet_alert = None
    next_vaccination_date = None

    organic_cost = 0
    market_cost = 0
    cost_savings = 0
    cost_note = None

    if request.method == "POST":
        animal_id = request.POST.get("animal")
        season = request.POST.get("season")

        if animal_id:
            animal = get_object_or_404(Livestock, id=animal_id)

            # 🐄 AI Feed Recommendation
            feed_result, health_note = recommend_feed(
                animal.animal_type.lower(),
                animal.age_months,
                animal.weight_kg,
                animal.health_status,
                season
            )

            total_feed = round(sum(feed_result.values()), 2) if feed_result else 0

            # 🐾 Animal Profile
            animal_profile = {
                "type": animal.animal_type.title(),
                "weight": animal.weight_kg,
                "age": animal.age_months,
                "last_vaccination": animal.last_vaccination,
                "total_feed": total_feed
            }

            # 💉 Vaccination Logic (FIXED)
            if animal.last_vaccination:
                next_vaccination_date = animal.last_vaccination + timedelta(days=180)
                today = timezone.now().date()   # ✅ FIX HERE

                if today >= next_vaccination_date:
                    vet_alert = "⚠ Vaccination overdue! Schedule vet visit immediately."
                else:
                    days_remaining = (next_vaccination_date - today).days
                    vet_alert = f"Next vaccination due in {days_remaining} days."
            else:
                vet_alert = "⚠ No vaccination record found."

            # 📊 Chart Data
            if feed_result:
                total = sum(feed_result.values())
                labels = []
                percentages = []

                for key, value in feed_result.items():
                    labels.append(key)
                    percent = round((value / total) * 100, 2)
                    percentages.append(percent)

                feed_chart_labels = json.dumps(labels)
                feed_chart_data = json.dumps(percentages)

            # Save session
            request.session["last_feed_result"] = feed_result

            # 💰 Cost Calculation
            organic_price = {
                "Green Fodder": 5,
                "Dry Fodder": 8,
                "Oil Cake": 25,
                "Grain Mix": 30
            }

            market_feed_price_per_kg = 28

            if feed_result:
                for item, quantity in feed_result.items():
                    price = organic_price.get(item, 20)
                    organic_cost += quantity * price

                total_feed_weight = sum(feed_result.values())
                market_cost = total_feed_weight * market_feed_price_per_kg

                cost_savings = round(market_cost - organic_cost, 2)

                if cost_savings > 0:
                    cost_note = f"Using organic feed saves ₹{cost_savings} per day."
                else:
                    cost_note = f"Organic feed costs ₹{abs(cost_savings)} more per day."

            # 🌿 Circular Economy
            manure_output = predict_manure_output(
                animal.animal_type.lower(),
                animal.weight_kg,
                total_feed
            )

            circular_note = (
                f"Daily Organic Manure Output: {manure_output} kg — "
                "Ready for composting and soil enrichment."
            )

    return render(request, "feed_management.html", {
        "livestock": livestock,
        "feed_result": feed_result,
        "health_note": health_note,
        "feed_chart_labels": feed_chart_labels,
        "feed_chart_data": feed_chart_data,
        "animal_profile": animal_profile,
        "manure_output": manure_output,
        "circular_note": circular_note,
        "vet_alert": vet_alert,
        "next_vaccination_date": next_vaccination_date,
        "organic_cost": round(organic_cost, 2),
        "market_cost": round(market_cost, 2),
        "cost_savings": cost_savings,
        "cost_note": cost_note,
        "season": season
    })

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table
from reportlab.platypus import TableStyle
from django.utils import timezone


def download_feed_pdf(request):
    if request.method != "POST":
        return HttpResponse("Invalid request")

    animal_type = request.POST.get("animal_type")
    feed_result = eval(request.POST.get("feed_result"))
    health_note = request.POST.get("health_note")
    manure_output = request.POST.get("manure_output")
    organic_cost = request.POST.get("organic_cost")
    market_cost = request.POST.get("market_cost")
    cost_note = request.POST.get("cost_note")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=feed_plan.pdf"

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]

    elements.append(Paragraph("SmartAgri AI - Feed Recommendation Report", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Animal Type: {animal_type}", styles["Normal"]))
    elements.append(Paragraph(f"Generated On: {timezone.now().strftime('%d %b %Y')}", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    data = [["Feed Component", "Quantity"]]

    for key, value in feed_result.items():
        data.append([key, str(value)])

    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.green),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Health Insight: {health_note}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(f"Daily Manure Output: {manure_output} kg", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(f"Organic Feed Cost: ₹{organic_cost}", styles["Normal"]))
    elements.append(Paragraph(f"Market Feed Cost: ₹{market_cost}", styles["Normal"]))
    elements.append(Paragraph(cost_note, styles["Normal"]))

    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(
        "Disclaimer: This feed plan is AI-generated. Consult local veterinary experts for critical conditions.",
        styles["Italic"]
    ))

    doc.build(elements)

    return response

from django.db.models import Sum, Avg
from django.shortcuts import render, get_object_or_404
from .models import Livestock, LivestockYieldLog
from farmer.utils.yield_ai import predict_yield
from django.utils import timezone
from datetime import timedelta
import json


def yield_monitoring(request):
    livestock_list = Livestock.objects.all()

    predicted_yield = None
    selected_animal = None
    correlation_alert = None

    chart_labels = []
    chart_values = []

    feed_efficiency = None
    efficiency_status = None

    # ================= FORM =================
    if request.method == "POST":

        livestock_id = request.POST.get("livestock_id")

        if livestock_id:
            selected_animal = get_object_or_404(Livestock, id=livestock_id)

            # ✅ SAFE VALUE CONVERSION
            milk = request.POST.get("milk_litre")
            eggs = request.POST.get("eggs_count")

            milk = float(milk) if milk else None
            eggs = int(eggs) if eggs else None

            # 📝 Save log
            LivestockYieldLog.objects.create(
                livestock=selected_animal,
                milk_litre=milk,
                eggs_count=eggs,
                notes=request.POST.get("notes", "")
            )

            # 🔮 AI Prediction
            estimated_feed = selected_animal.weight_kg * 0.03

            predicted_yield = predict_yield(
                selected_animal.animal_type.lower(),
                selected_animal.weight_kg,
                selected_animal.health_status,
                estimated_feed,
                selected_animal.age_months
            )

            # ================= CORRELATION =================
            previous_logs = LivestockYieldLog.objects.filter(
                livestock=selected_animal
            ).order_by('-id')

            if previous_logs.count() >= 2:
                latest = previous_logs[0]
                earlier = previous_logs[1]

                latest_value = latest.milk_litre or latest.eggs_count
                earlier_value = earlier.milk_litre or earlier.eggs_count

                if earlier_value and latest_value:
                    percent_drop = ((earlier_value - latest_value) / earlier_value) * 100

                    if percent_drop > 10 and selected_animal.health_status in ["Moderate", "Sick"]:
                        correlation_alert = (
                            f"⚠ Yield decreased by {round(percent_drop,1)}%; "
                            f"health issue '{selected_animal.health_status}' detected."
                        )

    # ================= STATS =================

    total_milk = LivestockYieldLog.objects.aggregate(
        total=Sum("milk_litre")
    )["total"] or 0

    total_eggs = LivestockYieldLog.objects.aggregate(
        total=Sum("eggs_count")
    )["total"] or 0

    avg_milk = LivestockYieldLog.objects.aggregate(
        avg=Avg("milk_litre")
    )["avg"] or 0

    # ================= ECONOMICS =================

    milk_price = 60
    egg_price = 5

    milk_revenue = round(total_milk * milk_price, 2)
    egg_revenue = round(total_eggs * egg_price, 2)
    total_revenue = round(milk_revenue + egg_revenue, 2)

    revenue_note = f"₹{milk_revenue} (Milk) + ₹{egg_revenue} (Eggs)"

    # ================= 7 DAYS TREND =================

    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)

    logs = LivestockYieldLog.objects.filter(
        date__gte=seven_days_ago
    )

    daily_data = (
        logs.values("date")
        .annotate(total_milk=Sum("milk_litre"))
        .order_by("date")
    )

    for entry in daily_data:
        if entry["date"]:
            chart_labels.append(entry["date"].strftime("%b %d"))
            chart_values.append(float(entry["total_milk"] or 0))

    chart_labels = json.dumps(chart_labels)
    chart_values = json.dumps(chart_values)

    # ================= FEED EFFICIENCY =================

    if selected_animal and predicted_yield:
        estimated_feed = selected_animal.weight_kg * 0.03

        if estimated_feed > 0:
            feed_efficiency = round(predicted_yield / estimated_feed, 2)

            if feed_efficiency >= 1.2:
                efficiency_status = "Excellent Conversion"
            elif feed_efficiency >= 0.8:
                efficiency_status = "Optimal Efficiency"
            else:
                efficiency_status = "Low Efficiency – Check Feed or Health"

    return render(request, "yield_monitoring.html", {
        "livestock": livestock_list,
        "total_milk": round(total_milk, 2),
        "total_eggs": total_eggs,
        "avg_milk": round(avg_milk, 2),
        "predicted_yield": predicted_yield,
        "selected_animal": selected_animal,
        "correlation_alert": correlation_alert,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "milk_revenue": milk_revenue,
        "egg_revenue": egg_revenue,
        "total_revenue": total_revenue,
        "revenue_note": revenue_note,
        "feed_efficiency": feed_efficiency,
        "efficiency_status": efficiency_status,
    })

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Paragraph
from reportlab.platypus import Spacer
from reportlab.platypus import ListFlowable
from reportlab.platypus import ListItem
from reportlab.lib.units import inch
from io import BytesIO
from django.utils import timezone


def download_yield_analytics(request):

    total_milk = LivestockYieldLog.objects.aggregate(
        total=Sum("milk_litre")
    )["total"] or 0

    total_eggs = LivestockYieldLog.objects.aggregate(
        total=Sum("eggs_count")
    )["total"] or 0

    avg_milk = LivestockYieldLog.objects.aggregate(
        avg=Avg("milk_litre")
    )["avg"] or 0

    # Simple revenue estimate
    milk_price = 40
    egg_price = 5

    revenue = (total_milk * milk_price) + (total_eggs * egg_price)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>SmartAgriAI - Yield Analytics Report</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Report Generated: {timezone.now().strftime('%d %B %Y')}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph("<b>Production Summary</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    data_points = [
        f"Total Milk Production: {round(total_milk,2)} Litres",
        f"Total Eggs Production: {total_eggs}",
        f"Average Milk per Entry: {round(avg_milk,2)} Litres",
        f"Estimated Daily Revenue: ₹{round(revenue,2)}"
    ]

    elements.append(ListFlowable(
        [ListItem(Paragraph(point, styles["Normal"])) for point in data_points],
        bulletType='bullet'
    ))

    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("<b>AI Advisory Notes</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    advisory = [
        "• Monitor yield fluctuations weekly.",
        "• Maintain optimal feed-to-yield efficiency.",
        "• Investigate sudden production drops immediately.",
        "• Regular health checks improve long-term revenue."
    ]

    elements.append(ListFlowable(
        [ListItem(Paragraph(point, styles["Normal"])) for point in advisory],
        bulletType='bullet'
    ))

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="yield_analytics_report.pdf"'
    response.write(pdf)

    return response

from django.shortcuts import render
from farmer.utils.soil_ai import predict_weekly_manure
from farmer.models import Livestock, SoilTest
import json


def organic_fertilizer_calculator(request):

    result = None
    warning = None
    weekly_manure_available = None
    availability_message = None
    nutrient_chart_labels = None
    nutrient_chart_values = None
    savings = None
    savings_message = None
    market_cost = None
    organic_cost = None
    application_tip = None   # ✅ FIX: define at top

    # 🔍 Auto Load Latest Soil Test
    latest_soil = SoilTest.objects.order_by('-tested_on').first()

    auto_n = latest_soil.nitrogen if latest_soil else None
    auto_p = latest_soil.phosphorus if latest_soil else None
    auto_k = latest_soil.potassium if latest_soil else None
    auto_ph = latest_soil.ph if latest_soil else None

    # 🔄 Import From Livestock Module
    if request.GET.get("import_manure"):
        livestock = Livestock.objects.all()
        weekly_manure_available = predict_weekly_manure(livestock)
        availability_message = (
            f"Predicted weekly manure available: {weekly_manure_available} kg."
        )

    if request.method == "POST":

        crop = request.POST.get("crop")
        selected_manure = request.POST.get("manure_type")

        if not crop:
            return render(request, "organic_fertilizer.html", {
                "error": "Please select a crop",
                "auto_n": auto_n,
                "auto_p": auto_p,
                "auto_k": auto_k,
                "auto_ph": auto_ph
            })

        try:
            nitrogen_needed = float(request.POST.get("nitrogen"))
            phosphorus_needed = float(request.POST.get("phosphorus"))
            potassium_needed = float(request.POST.get("potassium"))
            soil_ph = float(request.POST.get("soil_ph"))
        except (TypeError, ValueError):
            return render(request, "organic_fertilizer.html", {
                "error": "Please enter valid NPK and pH values",
                "auto_n": auto_n,
                "auto_p": auto_p,
                "auto_k": auto_k,
                "auto_ph": auto_ph
            })

        manure_data = {
            "Cow Manure": {"N": 0.005, "P": 0.003, "K": 0.004},
            "Poultry Manure": {"N": 0.02, "P": 0.015, "K": 0.01},
            "Vermicompost": {"N": 0.015, "P": 0.01, "K": 0.008},
        }

        optimized_mix = {}

        for manure_type, nutrients in manure_data.items():
            n_weight = nitrogen_needed / nutrients["N"]
            p_weight = phosphorus_needed / nutrients["P"]
            k_weight = potassium_needed / nutrients["K"]

            required_weight = max(n_weight, p_weight, k_weight)
            optimized_mix[manure_type] = round(required_weight, 2)

        best_manure = (
            selected_manure if selected_manure in optimized_mix
            else min(optimized_mix, key=optimized_mix.get)
        )

        result = {
            "crop": crop,
            "nitrogen": nitrogen_needed,
            "phosphorus": phosphorus_needed,
            "potassium": potassium_needed,
            "best_manure": best_manure,
            "required_weight": optimized_mix[best_manure],
        }

        # 📊 Nutrient Chart
        selected_nutrients = manure_data[best_manure]

        nutrient_chart_labels = json.dumps(
            ["Nitrogen", "Phosphorus", "Potassium"]
        )

        nutrient_chart_values = json.dumps([
            selected_nutrients["N"] * 100,
            selected_nutrients["P"] * 100,
            selected_nutrients["K"] * 100
        ])

        # 🌿 Manure Prediction
        livestock = Livestock.objects.all()
        weekly_manure_available = predict_weekly_manure(livestock)

        required = result["required_weight"]

        if weekly_manure_available >= required:
            availability_message = (
                f"Farm will produce approx {weekly_manure_available} kg manure next week."
            )
        else:
            deficit = round(required - weekly_manure_available, 2)
            availability_message = (
                f"Only {weekly_manure_available} kg predicted. "
                f"Shortage of {deficit} kg."
            )

        # 💰 Economic Benefit
        market_price = 35
        home_cost = 5

        market_cost = required * market_price
        organic_cost = required * home_cost
        savings = round(market_cost - organic_cost, 2)

        savings_message = (
            f"Saves ₹{savings} per application."
            if savings > 0
            else "No cost benefit."
        )

        # 🧠 Soil Advice
        if soil_ph < 5.5:
            warning = "Soil is acidic. Poultry manure recommended."
        elif soil_ph > 7.5:
            warning = "Soil is alkaline. Vermicompost recommended."
        else:
            warning = "Soil pH is optimal."

        # 🌱 Application Roadmap
        if best_manure == "Cow Manure":
            application_tip = "Apply 2–3 weeks before sowing."
        elif best_manure == "Poultry Manure":
            application_tip = "Apply 1–2 weeks before sowing."
        elif best_manure == "Vermicompost":
            application_tip = "Apply 1 week before sowing."

        # ✅ Store for PDF
        request.session["fertilizer_result"] = result
        request.session["fertilizer_savings"] = savings_message
        request.session["fertilizer_availability"] = availability_message
        request.session["fertilizer_warning"] = warning
        request.session["fertilizer_application_tip"] = application_tip

    return render(request, "organic_fertilizer.html", {
        "result": result,
        "warning": warning,
        "weekly_manure_available": weekly_manure_available,
        "availability_message": availability_message,
        "auto_n": auto_n,
        "auto_p": auto_p,
        "auto_k": auto_k,
        "auto_ph": auto_ph,
        "nutrient_chart_labels": nutrient_chart_labels,
        "nutrient_chart_values": nutrient_chart_values,
        "market_cost": market_cost,
        "organic_cost": organic_cost,
        "savings": savings,
        "savings_message": savings_message,
        "application_tip": application_tip,
    })

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import TableStyle
from reportlab.lib import colors


def download_fertilizer_report(request):
    result = request.session.get("fertilizer_result")

    if not result:
        return HttpResponse("No report data available.")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Organic_Application_Plan.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("SmartAgri AI", styles["Heading1"]))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Organic Fertilizer Advisory Report", styles["Heading2"]))
    elements.append(Spacer(1, 0.4 * inch))

    data = [
        ["Crop", result["crop"]],
        ["Nitrogen Required", f'{result["nitrogen"]} kg'],
        ["Phosphorus Required", f'{result["phosphorus"]} kg'],
        ["Potassium Required", f'{result["potassium"]} kg'],
        ["Recommended Manure", result["best_manure"]],
        ["Required Quantity", f'{result["required_weight"]} kg'],
    ]

    table = Table(data, colWidths=[2.5 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elements.append(table)

    doc.build(elements)

    return response



from django.shortcuts import render

CROP_DISEASE_DB = {
    "Maize": {
        "Leaf Blight": {
            "pesticide": "Neem oil + garlic extract spray",
            "fertilizer": "Apply 5 kg poultry manure per 10 sq ft"
        },
        "Stem Borer": {
            "pesticide": "Neem seed kernel extract (NSKE)",
            "fertilizer": "Apply 10 kg vermicompost per acre"
        }
    },
    "Cotton": {
        "Bollworm": {
            "pesticide": "Neem seed extract",
            "fertilizer": "Apply 12 kg FYM per acre"
        },
        "Whitefly": {
            "pesticide": "Soap + neem oil spray",
            "fertilizer": "Apply compost tea spray"
        }
    },
    "Tomato": {
        "Leaf Curl": {
            "pesticide": "Neem oil spray",
            "fertilizer": "Apply 5 kg vermicompost per plant row"
        },
        "Early Blight": {
            "pesticide": "Garlic–chilli extract",
            "fertilizer": "Apply cow dung slurry"
        }
    },
    "Paddy": {
        "Blast": {
            "pesticide": "Cow urine + neem extract",
            "fertilizer": "Apply green manure (Dhaincha)"
        },
        "Brown Spot": {
            "pesticide": "Neem oil spray",
            "fertilizer": "Apply Azolla compost"
        }
    }
}


from django.shortcuts import render
from farmer.models import SoilTest, CropPredictionHistory
import random

# Use lowercase keys for robust matching with your CSV data
CROP_DISEASE_DB = {
    "rice": {
        "Blast": {"pesticide": "Pseudomonas fluorescens (10ml/L)", "fertilizer": "Azospirillum", "practice": "Water management"},
        "Brown Spot": {"pesticide": "Organic Mancozeb mix", "fertilizer": "Potash enrichment", "practice": "Soil solarization"}
    },
    "maize": {
        "Rust": {"pesticide": "Baking Soda Spray", "fertilizer": "Vermicompost", "practice": "Crop rotation"},
        "Blight": {"pesticide": "Neem Oil 5%", "fertilizer": "Organic NPK", "practice": "Clean cultivation"}
    },
    "chickpea": {
        "Wilt": {"pesticide": "Trichoderma viride", "fertilizer": "Phosphobacteria", "practice": "Seed treatment"},
        "Root Rot": {"pesticide": "Neem cake application", "fertilizer": "FYM enrichment", "practice": "Deep summer ploughing"}
    },
    "kidneybeans": {
        "Leaf Spot": {"pesticide": "Cow Urine extract", "fertilizer": "Bio-NPK mix", "practice": "Clean cultivation"},
        "Anthracnose": {"pesticide": "Garlic-Chili extract", "fertilizer": "Liquid Seaweed", "practice": "Avoid overhead watering"}
    },
    "pigeonpeas": {
        "Sterility Mosaic": {"pesticide": "Organic Acaricide", "fertilizer": "Micronutrient mix", "practice": "Crop sanitation"},
        "Wilt": {"pesticide": "Bio-control agents", "fertilizer": "VAM fungi", "practice": "Intercropping with Sorghum"}
    },
    "mothbeans": {
        "Mosaic Virus": {"pesticide": "Yellow Sticky Traps", "fertilizer": "Organic Potash", "practice": "Vector control"},
        "Root Rot": {"pesticide": "Trichoderma powder", "fertilizer": "Bio-compost", "practice": "Proper drainage"}
    },
    "mungbean": {
        "Powdery Mildew": {"pesticide": "Wettable Sulphur (organic)", "fertilizer": "Bio-compost", "practice": "Early sowing"},
        "Leaf Spot": {"pesticide": "Neem Gold spray", "fertilizer": "Vermiwash", "practice": "Seed solarization"}
    },
    "blackgram": {
        "Root Rot": {"pesticide": "Bio-control agents", "fertilizer": "Vermicompost", "practice": "Proper drainage"},
        "Leaf Crinkle": {"pesticide": "NSKE 5% spray", "fertilizer": "Bio-fertilizer mix", "practice": "Remove host weeds"}
    },
    "lentil": {
        "Rust": {"pesticide": "Copper based organic spray", "fertilizer": "Bio-fertilizer", "practice": "Avoid waterlogging"},
        "Wilt": {"pesticide": "Trichoderma viride", "fertilizer": "Rhizobium culture", "practice": "Crop rotation"}
    },
    "pomegranate": {
        "Bacterial Blight": {"pesticide": "Streptocycline organic", "fertilizer": "Boron spray", "practice": "Pruning"},
        "Fruit Spot": {"pesticide": "Bordeaux Mixture 1%", "fertilizer": "Zinc sulphate", "practice": "Orchard sanitation"}
    },
    "banana": {
        "Sigatoka": {"pesticide": "Mineral oil spray", "fertilizer": "Stem compost", "practice": "De-leafing"},
        "Wilt": {"pesticide": "Bio-fumigation", "fertilizer": "Potash enrichment", "practice": "Use healthy suckers"}
    },
    "mango": {
        "Anthracnose": {"pesticide": "Copper oxychloride (org)", "fertilizer": "Organic mulch", "practice": "Post-harvest care"},
        "Powdery Mildew": {"pesticide": "Sulphur dust (organic)", "fertilizer": "Bio-NPK", "practice": "Pruning crowded branches"}
    },
    "grapes": {
        "Downy Mildew": {"pesticide": "Bordeaux Mixture 1%", "fertilizer": "Seaweed extract", "practice": "Canopy management"},
        "Powdery Mildew": {"pesticide": "Organic Sulphur", "fertilizer": "Liquid seaweed", "practice": "Leaf thinning"}
    },
    "watermelon": {
        "Bud Necrosis": {"pesticide": "Bio-pesticide T1", "fertilizer": "Organic fertigation", "practice": "Mulching"},
        "Downy Mildew": {"pesticide": "Ginger extract", "fertilizer": "Compost Tea", "practice": "Wider spacing"}
    },
    "muskmelon": {
        "Fruit Fly": {"pesticide": "Pheromone traps", "fertilizer": "Soil drench", "practice": "Sanitation"},
        "Wilt": {"pesticide": "Bio-agents", "fertilizer": "Organic mulch", "practice": "Grafting on resistant rootstock"}
    },
    "apple": {
        "Scab": {"pesticide": "Lime Sulphur spray", "fertilizer": "Organic Nitrogen", "practice": "Remove fallen leaves"},
        "Fire Blight": {"pesticide": "Copper organic formulation", "fertilizer": "Balanced bio-mix", "practice": "Pruning infected twigs"}
    },
    "orange": {
        "Canker": {"pesticide": "Bordeaux paste", "fertilizer": "Citrus organic mix", "practice": "Windbreaks"},
        "Gummosis": {"pesticide": "Trichoderma paste", "fertilizer": "Zinc & Iron spray", "practice": "Avoid trunk contact with water"}
    },
    "papaya": {
        "Ring Spot": {"pesticide": "Aphid control (organic)", "fertilizer": "Organic Manure", "practice": "Net cultivation"},
        "Foot Rot": {"pesticide": "Bordeaux Mixture", "fertilizer": "Bio-Potash", "practice": "Raised bed planting"}
    },
    "coconut": {
        "Bud Rot": {"pesticide": "Bordeaux paste", "fertilizer": "Coir pith compost", "practice": "Crown cleaning"},
        "Leaf Rot": {"pesticide": "Contaf organic alt", "fertilizer": "Salt application", "practice": "Avoid excess shade"}
    },
    "cotton": {
        "Bollworm": {"pesticide": "BT formulation", "fertilizer": "Neem cake", "practice": "Trap crops"},
        "Leaf Spot": {"pesticide": "Copper organic spray", "fertilizer": "Bio-NPK", "practice": "Clean seeds"}
    },
    "jute": {
        "Stem Rot": {"pesticide": "Copper Oxychloride (organic) 3g/L", "fertilizer": "Bio-potash", "practice": "Field drainage"},
        "Yellow Mite": {"pesticide": "Lime Sulphur spray", "fertilizer": "Compost enrichment", "practice": "Early sowing"}
    },
    "coffee": {
        "Leaf Rust": {"pesticide": "Systemic organic fungicide", "fertilizer": "Coffee pulp compost", "practice": "Shade management"},
        "Berry Borer": {"pesticide": "Beauveria bassiana", "fertilizer": "Bio-Potash", "practice": "Timely picking"}
    }
}

CATEGORIES = ["Organic Pesticides", "Bio-Fertilizers", "Sustainable Practices"]

def organic_advisor_ai(request):
    selected_crop = request.POST.get("crop")
    selected_disease = request.POST.get("disease")
    selected_category = request.POST.get("category")

    diseases = []
    recommendation = None
    treatment_plan = []
    savings_data = None

    # Load unique crops from history
    db_crops = list(CropPredictionHistory.objects.values_list("crop_name", flat=True).distinct())
    
    # Load crops defined in the AI Dictionary to ensure all 22 show up
    ai_crops = list(CROP_DISEASE_DB.keys())
    
    # Combine lists and clean up naming for the dropdown
    all_crops = sorted(list(set([c.lower().strip() for c in db_crops] + ai_crops)))

    # 🔥 FIX: Load diseases immediately if crop is selected
    if selected_crop:
        crop_key = selected_crop.lower().strip()
        if crop_key in CROP_DISEASE_DB:
            diseases = CROP_DISEASE_DB[crop_key].keys()

    # Process AI recommendation only if all selections are made
    if request.method == "POST" and selected_crop and selected_disease and selected_category:
        crop_key = selected_crop.lower().strip()
        try:
            base_data = CROP_DISEASE_DB[crop_key][selected_disease]
            
            if selected_category == "Organic Pesticides":
                recommendation = base_data.get("pesticide")
            elif selected_category == "Bio-Fertilizers":
                recommendation = base_data.get("fertilizer")
            else:
                recommendation = base_data.get("practice")

            treatment_plan = [
                {"step": "STEP 1", "title": "Prepare Solution", "action": f"Mix {recommendation} thoroughly."},
                {"step": "STEP 2", "title": "Precision Spray", "action": "Apply to foliage in the late evening for max absorption."},
                {"step": "STEP 3", "title": "Cultural Management", "action": f"Eco-Tip: {base_data.get('practice')}"}
            ]

            savings_data = {
                "organic_cost": 150, 
                "chemical_cost": 480, 
                "savings": 330, 
                "message": "Sustainable methods reduce input costs by 68%."
            }
        except KeyError:
            recommendation = "AI data for this specific crop/disease is being updated."

    return render(request, "organic_advisor_ai.html", {
        "crops": all_crops,
        "diseases": diseases,
        "categories": CATEGORIES,
        "selected_crop": selected_crop,
        "selected_disease": selected_disease,
        "selected_category": selected_category,
        "recommendation": recommendation,
        "treatment_plan": treatment_plan,
        "savings_data": savings_data,
        "soil_profile": SoilTest.objects.order_by('-tested_on').first(),
    })
import os
from django.http import HttpResponse
from django.conf import settings
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch


def export_advisory_pdf(request):

    # Get stored session data
    recommendation = request.session.get("organic_recommendation")
    contextual_advice = request.session.get("contextual_advice")
    preventive_alert = request.session.get("preventive_alert")
    treatment_plan = request.session.get("treatment_plan")
    savings_data = request.session.get("savings_data")
    soil_profile = request.session.get("soil_profile")

    if not recommendation:
        return HttpResponse("No advisory data available.")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Organic_Advisory_Report.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []

    styles = getSampleStyleSheet()

    # ================= LOGO =================
    logo_path = os.path.join(settings.BASE_DIR, "static", "imagees", "logo.png")

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5 * inch, height=1.5 * inch)
        elements.append(logo)
        elements.append(Spacer(1, 0.2 * inch))

    # ================= TITLE =================
    elements.append(Paragraph("SmartAgri AI", styles["Heading1"]))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph("Organic Advisory Report", styles["Heading2"]))
    elements.append(Spacer(1, 0.4 * inch))

    # ================= RECOMMENDATION =================
    elements.append(Paragraph("<b>AI Recommendation:</b>", styles["Heading3"]))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(str(recommendation), styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    # ================= CONTEXTUAL ADVICE =================
    if contextual_advice:
        elements.append(Paragraph("<b>Contextual Application:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.1 * inch))

        data = [
            ["Dosage", contextual_advice.get("dosage", "")],
            ["Timing", contextual_advice.get("timing", "")],
            ["Weather", contextual_advice.get("weather", "")],
            ["Soil pH", str(contextual_advice.get("soil_ph", ""))]
        ]

        table = Table(data, colWidths=[2.5 * inch, 3 * inch])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen)
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.4 * inch))

    # ================= TREATMENT PLAN =================
    if treatment_plan:
        elements.append(Paragraph("<b>Organic Treatment Roadmap:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.2 * inch))

        for step in treatment_plan:
            elements.append(
                Paragraph(
                    f"{step['step']} - {step['title']}: {step['action']}",
                    styles["Normal"]
                )
            )
            elements.append(Spacer(1, 0.15 * inch))

        elements.append(Spacer(1, 0.3 * inch))

    # ================= PREVENTIVE ALERT =================
    if preventive_alert:
        elements.append(Paragraph("<b>Predictive Prevention:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(preventive_alert.get("message", ""), styles["Normal"]))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(preventive_alert.get("prevention", ""), styles["Normal"]))
        elements.append(Spacer(1, 0.4 * inch))

    # ================= SOIL PROFILE =================
    if soil_profile:
        elements.append(Paragraph("<b>Soil Profile Analysis:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.1 * inch))

        soil_data = [
            ["Nitrogen", f"{soil_profile.nitrogen} kg/ha"],
            ["Phosphorus", f"{soil_profile.phosphorus} kg/ha"],
            ["Potassium", f"{soil_profile.potassium} kg/ha"],
            ["pH", f"{soil_profile.ph}"]
        ]

        soil_table = Table(soil_data, colWidths=[2.5 * inch, 3 * inch])
        soil_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)
        ]))

        elements.append(soil_table)
        elements.append(Spacer(1, 0.4 * inch))

    # ================= ECONOMIC IMPACT =================
    if savings_data:
        elements.append(Paragraph("<b>Economic Impact:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.1 * inch))

        eco_data = [
            ["Organic Cost", f"₹{savings_data['organic_cost']}"],
            ["Chemical Cost", f"₹{savings_data['chemical_cost']}"],
            ["Savings", f"₹{savings_data['savings']}"]
        ]

        eco_table = Table(eco_data, colWidths=[2.5 * inch, 3 * inch])
        eco_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 2), (-1, 2), colors.lightgreen)
        ]))

        elements.append(eco_table)
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph(savings_data["message"], styles["Normal"]))
        elements.append(Spacer(1, 0.4 * inch))

    # ================= FOOTER =================
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph(
            "Generated by SmartAgri AI – Sustainable Farming Intelligence System",
            styles["Italic"]
        )
    )

    doc.build(elements)

    return response



def organic_advisory_pdf(request):
    crop = request.GET.get("crop")
    disease = request.GET.get("disease")

    data = CROP_DISEASE_DB.get(crop, {}).get(disease)

    if not data:
        return HttpResponse("Invalid crop or disease")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=Organic_Advisory_Report.pdf"

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "Organic Farming Advisory Report")

    # Meta info
    p.setFont("Helvetica", 11)
    p.drawString(50, height - 90, f"Crop: {crop}")
    p.drawString(50, height - 110, f"Disease: {disease}")
    p.drawString(50, height - 130, f"Generated on: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

    # Organic section
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 180, "🌿 Organic Alternatives")

    p.setFont("Helvetica", 12)
    p.drawString(50, height - 210, "Natural Pesticide:")
    p.drawString(70, height - 230, f"- {data['pesticide']}")

    p.drawString(50, height - 270, "Organic Fertilizer:")
    p.drawString(70, height - 290, f"- {data['fertilizer']}")

    # Footer
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(
        50, 40,
        "SmartAgri AI | Supporting Sustainable & Organic Farming"
    )

    p.showPage()
    p.save()

    return response

from django.shortcuts import render, redirect
from farmer.models import OrganicMarketplaceListing, CropPredictionHistory
from django.contrib import messages
from django.db.models import Avg
import random


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def organic_marketplace(request):

    ai_price_suggestion = None
    demand_forecast = None
    logistics_estimate = None

    average_price = None
    weekly_change = None
    trending_product = None

    delivery_cost = None

    # ================= FETCH EXISTING LISTINGS =================
    listings = OrganicMarketplaceListing.objects.order_by("-created_at")

# Add badge to each listing
    for item in listings:
        item.badge = nutrient_quality_badge(
        item.nitrogen,
        item.phosphorus,
        item.potassium
    )
    # ================= MARKET ANALYSIS (ONLY IF DATA EXISTS) =================
    if listings.exists():

        avg_price = listings.aggregate(
            Avg("price_per_kg")
        )["price_per_kg__avg"]

        if avg_price:
            average_price = round(avg_price, 2)
            weekly_change = round(random.uniform(-3, 5), 2)

        # Trending product
        product_count = {}
        for item in listings:
            product_count[item.product_type] = (
                product_count.get(item.product_type, 0) + 1
            )

        trending_product = max(product_count, key=product_count.get)

    # ================= FORM SUBMISSION =================
    if request.method == "POST":

        farmer_name = request.POST.get("farmer_name")
        product_type = request.POST.get("product_type")
        location = request.POST.get("location")

        quantity = safe_float(request.POST.get("quantity_kg"))
        price = safe_float(request.POST.get("price_per_kg"))

        nitrogen = safe_float(request.POST.get("nitrogen")) or 0
        phosphorus = safe_float(request.POST.get("phosphorus")) or 0
        potassium = safe_float(request.POST.get("potassium")) or 0

        distance_input = request.POST.get("distance")

        if distance_input:
            try:
                distance_value = float(distance_input)
                delivery_cost = predict_delivery_cost(distance_value)
            except:
                delivery_cost = None
        # 🚫 STRICT VALIDATION
        if not farmer_name or not product_type or not quantity or not price:
            messages.error(request, "Please fill all required fields correctly.")
            return redirect("organic_marketplace")

        # ================= SMART PRICE =================
        nutrient_score = (nitrogen + phosphorus + potassium) / 3
        base_market_price = 6
        quality_multiplier = 1 + (nutrient_score / 100)
        regional_demand_factor = random.uniform(0.9, 1.3)

        ai_price_suggestion = round(
            base_market_price * quality_multiplier * regional_demand_factor,
            2
        )

        # ================= DEMAND FORECAST =================
        active_crops = CropPredictionHistory.objects.values_list(
            "crop_name", flat=True
        )

        crop_frequency = {}
        for crop in active_crops:
            crop_frequency[crop] = crop_frequency.get(crop, 0) + 1

        if crop_frequency:
            most_common_crop = max(crop_frequency, key=crop_frequency.get)
            demand_forecast = f"High fertilizer demand expected for {most_common_crop}."
        else:
            demand_forecast = "Stable fertilizer demand in your region."

        # ================= LOGISTICS =================
        estimated_distance = random.randint(5, 50)
        transport_cost = round(estimated_distance * 2.5, 2)

        logistics_estimate = {
            "distance": estimated_distance,
            "transport_cost": transport_cost
        }

        # ================= SAVE =================
        OrganicMarketplaceListing.objects.create(
            farmer_name=farmer_name,
            product_type=product_type,
            quantity_kg=quantity,
            price_per_kg=price,
            location=location,
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium,
            
        )

        messages.success(request, "Listing added successfully.")

        return render(request, "organic_marketplace.html", {
            "listings": listings,
            "ai_price_suggestion": ai_price_suggestion,
            "demand_forecast": demand_forecast,
            "logistics_estimate": logistics_estimate,
            "average_price": average_price,
            "weekly_change": weekly_change,
            "trending_product": trending_product,
            "delivery_cost": delivery_cost
        })

    # ================= DEFAULT RENDER =================
    return render(request, "organic_marketplace.html", {
        "listings": listings,
        "average_price": average_price,
        "weekly_change": weekly_change,
        "trending_product": trending_product,
    })

def nutrient_quality_badge(n, p, k):
    score = (n or 0) + (p or 0) + (k or 0)

    if score >= 120:
        return "Certified Organic"
    elif score >= 70:
        return "High Quality"
    else:
        return "Standard"

from sklearn.linear_model import LinearRegression
import numpy as np   
def predict_delivery_cost(distance):

    # Training data (distance km → cost ₹)
    X = np.array([[5], [10], [20], [30], [40], [50]])
    y = np.array([40, 70, 130, 190, 250, 310])

    model = LinearRegression()
    model.fit(X, y)

    predicted_cost = model.predict([[distance]])

    return round(predicted_cost[0], 2)

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from farmer.models import SoilTest, CropPredictionHistory


@csrf_exempt
def agri_chatbot(request):

    if request.method != "POST":
        return JsonResponse({"reply": "SmartAgri AI is ready."})

    try:
        data = json.loads(request.body)
        message = data.get("message", "").lower().strip()
    except:
        return JsonResponse({"reply": "Invalid request format."})

    reply = "I can help you with SmartAgri modules like crop prediction, soil analysis, livestock, organic fertilizer, advisory, and marketplace."

    # ---------------- Greeting ----------------
    if any(word in message for word in ["hi", "hello", "hey"]):
        reply = (
            "Hello! I am SmartAgri AI 🌱\n"
            "You can ask about crops, soil health, livestock, fertilizer, disease detection, or marketplace."
        )

    # ---------------- Crop Prediction ----------------
    elif "crop" in message or "which crop" in message:
        reply = (
            "Use the Crop & Fertilizer module to predict the best crop "
            "based on soil nutrients and climate conditions."
        )

    # ---------------- Soil Data ----------------
    elif "soil" in message or "soil health" in message:

        soil = SoilTest.objects.order_by("-tested_on").first()

        if soil:
            reply = (
                f"Latest soil test results:\n"
                f"Nitrogen: {soil.nitrogen}\n"
                f"Phosphorus: {soil.phosphorus}\n"
                f"Potassium: {soil.potassium}\n"
                f"Soil pH: {soil.ph}"
            )
        else:
            reply = "No soil test data available yet. Please upload a soil test."

    # ---------------- Crop History ----------------
    elif "history" in message or "previous crop" in message:

        crop = CropPredictionHistory.objects.order_by("-predicted_on").first()

        if crop:
            reply = f"Your last predicted crop was {crop.crop_name}."
        else:
            reply = "No crop prediction history found."

    # ---------------- Disease Detection ----------------
    elif "disease" in message or "plant disease" in message:
        reply = (
            "Use the Disease Detection module to upload a crop leaf image.\n"
            "The AI model will detect plant diseases and suggest treatment."
        )

    # ---------------- Livestock ----------------
    elif "livestock" in message or "animal" in message:
        reply = (
            "The Livestock module helps track animal health, feeding schedules, "
            "and productivity monitoring."
        )

    # ---------------- Organic Fertilizer ----------------
    elif "fertilizer" in message or "manure" in message:
        reply = (
            "Use the Organic Fertilizer calculator to determine the correct manure "
            "quantity based on soil nutrient deficiency."
        )

    # ---------------- Organic Advisory ----------------
    elif "organic advisory" in message or "organic farming" in message:
        reply = (
            "The Organic Advisor AI recommends organic pesticides, "
            "bio-fertilizers, and sustainable farming practices."
        )

    # ---------------- Marketplace ----------------
    elif "market" in message or "sell manure" in message or "sell compost" in message:
        reply = (
            "You can sell compost, manure, or organic products "
            "in the Organic Marketplace module."
        )

    # ---------------- Weather / IoT ----------------
    elif "weather" in message or "temperature" in message or "humidity" in message:
        reply = (
            "Your SmartAgri dashboard displays real-time IoT farm data "
            "including temperature, humidity, and soil moisture."
        )

    # ---------------- Help ----------------
    elif "help" in message:
        reply = (
            "I can assist you with:\n"
            "- Crop Prediction\n"
            "- Soil Health Analysis\n"
            "- Disease Detection\n"
            "- Livestock Monitoring\n"
            "- Organic Fertilizer Calculator\n"
            "- Organic Advisory AI\n"
            "- Organic Marketplace"
        )

    # ---------------- Unknown Question ----------------
    else:
        reply = (
            "Sorry, I didn't understand that.\n"
            "You can ask about crops, soil health, livestock, fertilizer, "
            "disease detection, or marketplace."
        )

    return JsonResponse({"reply": reply})

