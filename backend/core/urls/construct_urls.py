from django.urls import path
from core.views import construct_views

urlpatterns = [
    path('<int:user_id>/constructs/', construct_views.get_constructs),
    path('construct/<int:construct_id>/', construct_views.get_construct),
    path('<int:user_id>/constructs/create/', construct_views.create_construct_view),
    path('construct/<int:construct_id>/update/', construct_views.update_construct_view),
    path('construct/<int:construct_id>/delete/', construct_views.delete_construct_view),
    path('constructs/assign/',          construct_views.assign_construct),
    path('constructs/all/<int:user_id>/', construct_views.list_constructs),
    path('constructs/update/<int:id>/',   construct_views.update_construct),
    path('constructs/delete/<int:id>/',   construct_views.delete_construct),
]