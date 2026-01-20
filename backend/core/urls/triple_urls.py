from django.urls import path
from core.views import triple_views

urlpatterns = [
    path('<int:user_id>/triples/', triple_views.get_triples),   # 获取某个 user 的全部 triples
    path('triple/<int:triple_id>/', triple_views.get_triple),   # 获取单个 triple
    path('<int:user_id>/triples/create/', triple_views.create_triple_view),     # 创建 triple
    path('triple/<int:triple_id>/update/', triple_views.update_triple_view),    # 更新 triple
    path('triple/<int:triple_id>/delete/', triple_views.delete_triple_view),    # 删除 triple
]