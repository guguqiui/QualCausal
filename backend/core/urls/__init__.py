from django.urls import path
from .user_urls import urlpatterns as user_urls
from .operation_urls import urlpatterns as operation_urls
from .import_urls import urlpatterns as import_urls
from .entity_urls import urlpatterns as entity_urls
from .triple_urls import urlpatterns as triple_urls
from .sentence_urls import urlpatterns as sentence_urls
from .construct_urls import urlpatterns as construct_urls
from .upload_urls import urlpatterns as upload_urls
from .search_urls import urlpatterns as search_urls

urlpatterns = user_urls + operation_urls + import_urls + entity_urls + triple_urls + sentence_urls + construct_urls + upload_urls + search_urls