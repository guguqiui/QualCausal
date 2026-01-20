"""
 @file: user_view.py
 @Time    : 2025/6/11
 @Author  : Peinuan qin
 """
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from automaticExtractionBackend.models import SystemUser
#
# @csrf_exempt
# @require_GET
# def check_user_exists(request):
#     user_id = request.GET.get("user_id")
#     username = request.GET.get("username")
#     email = request.GET.get("email")
#
#     try:
#         if user_id:
#             user = SystemUser.objects.get(id=user_id)
#         elif username:
#             user = SystemUser.objects.get(username=username)
#         elif email:
#             user = SystemUser.objects.get(email=email)
#         else:
#             return JsonResponse({"error": "Provide one of user_id, username, or email."}, status=400)
#
#         return JsonResponse({
#             "exists": True,
#             "user": {
#                 "id": user.id,
#                 "username": user.username,
#                 "email": user.email
#             }
#         })
#
#     except SystemUser.DoesNotExist:
#         return JsonResponse({"exists": False})



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from automaticExtractionBackend.models import SystemUser

@require_GET
def check_user_exists(request):
    user_id = request.GET.get("user_id")

    if not user_id:
        return JsonResponse({"error": "user_id is required."}, status=400)

    try:
        user = SystemUser.objects.get(id=user_id)
        return JsonResponse({
            "exists": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        })
    except SystemUser.DoesNotExist:
        return JsonResponse({"exists": False})

@csrf_exempt
def create_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            email = data.get("email")

            if not username or not email:
                return JsonResponse({"error": "username and email are required"}, status=400)

            if SystemUser.objects.filter(username=username).exists():
                return JsonResponse({"error": "username already exists"}, status=400)
            if SystemUser.objects.filter(email=email).exists():
                return JsonResponse({"error": "email already exists"}, status=400)

            user = SystemUser.objects.create(username=username, email=email)
            return JsonResponse({"message": "User created", "user_id": user.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        return JsonResponse({"error": "Only POST allowed"}, status=405)
