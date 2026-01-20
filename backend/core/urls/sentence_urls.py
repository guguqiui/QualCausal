from django.urls import path
from core.views import sentence_views

urlpatterns = [
    path('<int:user_id>/sentences/', sentence_views.get_sentences),
    path('sentence/<int:sentence_id>/', sentence_views.get_sentence),
    path('<int:user_id>/sentences/create/', sentence_views.create_sentence_view),
    path('sentence/<int:sentence_id>/update/', sentence_views.update_sentence_view),
    path('sentence/<int:sentence_id>/delete/', sentence_views.delete_sentence_view),
]