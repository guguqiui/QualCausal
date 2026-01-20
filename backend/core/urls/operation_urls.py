from django.urls import path
from core.views import operation_views

urlpatterns = [
    path('operations/<str:user_id>/', operation_views.get_user_operations_view),
    path('operations/batch/', operation_views.add_operations_batch_view),
]