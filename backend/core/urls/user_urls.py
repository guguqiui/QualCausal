from django.urls import path
from core.views import user_views

urlpatterns = [
    path('users/validate/<str:user_id>/', user_views.validate_user_view),
]