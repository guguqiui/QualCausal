"""
 @file: test.py
 @Time    : 2025/7/6
 @Author  : Peinuan qin
 """

import asyncio
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import sync_and_async_middleware
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# 初始化 LLM（OpenAI 也可以替换为其它异步支持的模型）
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, streaming=False)

async def async_llm_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_input = data.get("input", "")

        if not user_input:
            return JsonResponse({"error": "No input provided"}, status=400)

        # 构造消息列表
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=user_input),
        ]

        # 异步调用 LLM
        result = await llm.ainvoke(messages)

        return JsonResponse({"response": result.content})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
