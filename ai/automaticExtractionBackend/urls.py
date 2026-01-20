"""automaticExtractionBackend URL Configuration

The `urlpatterns` list routes URLs to all_views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function all_views
    1. Add an import:  from my_app import all_views
    2. Add a URL to urlpatterns:  path('', all_views.home, name='home')
Class-based all_views
    1. Add an import:  from other_app.all_views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from automaticExtractionBackend.all_views.canonical_view import get_canonical_group, entity_cluster_graph
from automaticExtractionBackend.all_views.export_view import export_user_data
# from automaticExtractionBackend.all_views.extract_causal_view import extract_causal_relations
# from automaticExtractionBackend.all_views.extract_causal_patch_view import extract_causal_relations
from automaticExtractionBackend.all_views.extract_entity_view import extract_entity, update_entity_construct, \
    update_entity_name, delete_entity


from automaticExtractionBackend.all_views.construct_view import (
    get_constructs,
    add_construct,
    update_construct,
    delete_construct, upload_constructs_from_json, map_construct, map_all_constructs_for_user,
    assign_construct_to_entity, get_all_constructs_for_user,
)
# from automaticExtractionBackend.all_views.simple_resolution_view import auto_entity_resolution
from automaticExtractionBackend.all_views.resolution_patch_view import auto_entity_resolution
from automaticExtractionBackend.all_views.user_view import create_user, check_user_exists




# async 三个接口
from automaticExtractionBackend.async_views.extract_entity_view import extract_entity
from automaticExtractionBackend.async_views.extract_entity_from_batch_sentences import extract_entities_batch
from automaticExtractionBackend.async_views.resolution_patch_view import auto_entity_resolution
from automaticExtractionBackend.async_views.extract_causal_patch_view import extract_causal_relations
from automaticExtractionBackend.async_views.map_construct_view import map_all_constructs_for_user
from automaticExtractionBackend.async_views.test import async_llm_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('extract_entity/', extract_entity),  # async_extract
    path('extract_entity_batch/', extract_entities_batch),  # async_extract
    path("update_entity_construct/", update_entity_construct),
    path("update_entity_name/", update_entity_name),
    path("delete_entity/", delete_entity),


    path("constructs/", get_constructs),
    path("constructs/add/", add_construct),
    path("constructs/upload/", upload_constructs_from_json),
    path("constructs/update/<int:id>/", update_construct),
    path("constructs/delete/<int:id>/", delete_construct),
    path("constructs/map_construct/", map_construct),
    path("constructs/map_all_constructs_for_user/", map_all_constructs_for_user),
    path("constructs/assign/", assign_construct_to_entity),        # 手动分配 construct 给 entity
    # path("constructs/all/", get_all_constructs_for_user),          # 获取所有 constructs（供前端选择）
    path("constructs/all/<int:user_id>/", get_all_constructs_for_user),



    path("extract_causals/", extract_causal_relations),
    path("auto_entity_resolution/", auto_entity_resolution),
    path("canonical_group/<int:entity_id>/", get_canonical_group),
    path("entity_cluster_graph/<int:user_id>/", entity_cluster_graph),


    path("user/create/", create_user),
    path("user/check/", check_user_exists),


    path('export/<int:user_id>/', export_user_data, name='export_user_data'),
    # path('test/', send_llm_requests),
    path('test/', async_llm_view),
]
