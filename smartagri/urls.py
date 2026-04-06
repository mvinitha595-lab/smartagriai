from django.contrib import admin
from django.urls import path, include
from farmer.views import (
    landing_page,
    farmer_login,
    farmer_dashboard,
    crop_predictor,
    admin_dashboard,
    disease_detection,
    live_farm_monitor,
    
)
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('admin/', admin.site.urls),
     path('i18n/', include('django.conf.urls.i18n')),
    path('', include('farmer.urls')),
    path('', landing_page, name='landing'),
    path('login/', farmer_login, name='farmer_login'),
    path('dashboard/', farmer_dashboard, name='farmer_dashboard'),
    
    path('predict/', crop_predictor, name='crop_predictor'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
      path('disease-detection/', disease_detection, name='disease_detection'),
      path('live-monitor/', live_farm_monitor, name='live_monitor'),
      
    

 
]

urlpatterns += i18n_patterns(
    path('', include('farmer.urls')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



