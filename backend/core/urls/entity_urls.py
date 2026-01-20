from django.urls import path
from core.views import entity_views

urlpatterns = [
    path('<int:user_id>/entities/', entity_views.get_entities),
    path('<int:user_id>/entities/name/<path:node_name>/', entity_views.get_entities_by_name, name='get_entities_by_name'),
    path('entity/<int:entity_id>/', entity_views.get_entity),
    path('<int:user_id>/entities/create/', entity_views.create_entity_view),
    path('entity/<int:entity_id>/update/', entity_views.update_entity_view),
    path('entity/<int:entity_id>/delete/', entity_views.delete_entity_view),
    path('entity/update_entity_name/',entity_views.update_entity_name_view),
    path('entity/delete_entity/', entity_views.delete_entity),
]