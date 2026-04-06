from django.urls import path
from . import views
from .views import health_tracker, feed_management, yield_monitoring, organic_fertilizer_calculator, download_feed_pdf
urlpatterns = [
    path("login/", views.farmer_login, name="login"),
    path("register/", views.register, name="register"),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('predict/', views.crop_predictor, name='crop_predictor'),
    path('disease-detection/', views.disease_detection, name='disease_detection'),
    path('live-farm-monitor/', views.live_farm_monitor, name='live_farm_monitor'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('crop-advisory-pdf/', views.crop_advisory_pdf, name='crop_advisory_pdf'),
   path("disease-report-pdf/", views.disease_report_pdf, name="disease_report_pdf"),
    path("logout/", views.farmer_logout, name="farmer_logout"),
    path("", views.landing_page, name="landing_page"),
    path("history/", views.field_history, name="field_history"),
    path("history/pdf/", views.history_pdf, name="history_pdf"),
    path("disease-history-pdf/",views.disease_history_pdf,name="disease_history_pdf"),
    path("organic-livestock/", views.organic_livestock, name="organic_livestock"),
    path("organic-advisor/", views.organic_advisor, name="organic_advisor"),
    path("livestock/<int:pk>/health/",views.livestock_health_tracker,name="livestock_health_tracker"),
    path("health-tracker/", views.health_tracker, name="health_tracker"),
    path("feed-management/", views.feed_management, name="feed_management"),
    path("yield-monitoring/", views.yield_monitoring, name="yield_monitoring"),
    path("organic-fertilizer/", views.organic_fertilizer_calculator, name="organic_fertilizer"),
    path("organic-advisor-ai/", views.organic_advisor_ai, name="organic_advisor_ai"),
    path("organic-marketplace/",views.organic_marketplace,name="organic_marketplace"),
    path("download-feed-pdf/", download_feed_pdf, name="download_feed_pdf"),
    path("download-health-report/", views.download_health_report, name="download_health_report"),
    path("download-yield-analytics/", views.download_yield_analytics, name="download_yield_analytics"),
    path("download-fertilizer-report/", views.download_fertilizer_report, name="download_fertilizer_report"),
    
    path(
    "export-advisory-pdf/",
    views.export_advisory_pdf,
    name="export_advisory_pdf"
),
path("ai-chatbot/", views.agri_chatbot, name="agri_chatbot"),


]



