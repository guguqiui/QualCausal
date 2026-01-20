"""
 @file: views.py
 @Time    : 2025/6/24
 @Author  : Peinuan qin
 """
from django.shortcuts import render

def index(request):
    return render(request, "index.html")
