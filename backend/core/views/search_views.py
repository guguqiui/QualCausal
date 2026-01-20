import json
import re
import math
from collections import Counter

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def tokenize(text):
    """
    简单分词：提取所有字母/数字序列，统一小写
    """
    return re.findall(r'\w+', text.lower())


def get_term_frequencies(text):
    """
    计算词频 Counter
    """
    tokens = tokenize(text)
    return Counter(tokens)


def compute_cosine_similarity(text1, text2):
    """
    余弦相似度计算
    """
    freq1 = get_term_frequencies(text1)
    freq2 = get_term_frequencies(text2)

    # 所有出现过的词
    all_terms = set(freq1) | set(freq2)

    dot_product = sum(freq1[t] * freq2[t] for t in all_terms)
    norm1 = math.sqrt(sum(v * v for v in freq1.values()))
    norm2 = math.sqrt(sum(v * v for v in freq2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


@csrf_exempt
@require_http_methods(["POST"])
def search_with_nodes(request, user_id):
    """
    接收 POST /api/<user_id>/search/search-with-nodes/
    Body JSON:
    {
      "nodes": ["node1", "node2", ...],
      "query": "你的检索文本"
    }
    返回：[{ "name": "...", "score": 0.123 }, ...]
    """
    try:
        payload = json.loads(request.body.decode())
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload.")

    node_names = payload.get("nodes")
    query = payload.get("query")

    if not isinstance(node_names, list) or not isinstance(query, str):
        return HttpResponseBadRequest("需要 'nodes' (数组) 和 'query' (字符串)。")

    results = []
    for name in node_names:
        score = compute_cosine_similarity(name, query)
        results.append({"name": name, "score": score})

    # 按分数降序，并取前 10
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:10]

    return JsonResponse(results, safe=False)