from django.urls import path
from core.views import import_views

urlpatterns = [
    path('import-data/', import_views.import_data),
]