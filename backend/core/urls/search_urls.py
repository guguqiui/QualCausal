from django.urls import path
from core.views import search_views

urlpatterns = [
    path('<int:user_id>/search/search-with-nodes/', search_views.search_with_nodes, name='search_with_nodes'),
]