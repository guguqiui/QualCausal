from django.urls import path
from core.views.upload_views import upload_entities
from core.views.upload_views import upload_constructs
from core.views.upload_views import map_constructs
from core.views.upload_views import extract_causals
from core.views.upload_views import auto_entity_resolution
from core.views.upload_views import create_user_view

urlpatterns = [
    # 第1步：上传 txt 并抽取 sentence 中的 entity
    path('upload_entities/',    upload_entities,    name='upload_entities'),
    # 第2步：上传 construct
    path('upload_constructs/',  upload_constructs,  name='upload_constructs'),
    # 第3步：把 entity map 到 construct
    path('map_constructs/',     map_constructs,     name='map_constructs'),
    # 第4步：获取triples
    path('extract_causals/',    extract_causals,    name='extract_causals'),
    # 第5步：合并
    path('auto_entity_resolution/',    auto_entity_resolution,    name='auto_entity_resolution'),
    path('user/create/',    create_user_view,    name='create_user_view'),
]