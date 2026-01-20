import asyncio
import json
import random
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from openai import RateLimitError

from automaticExtractionBackend import settings
from automaticExtractionBackend.models import SystemUser, Sentence, Triple
import logging

import time

# 在各个阶段开始时记录时间
def log_time(stage_name):
    """记录每个阶段的时间"""
    start_time = time.time()
    # logger.info(f"Start {stage_name} at {start_time}")
    print(f"Start {stage_name} at {start_time}")
    return start_time

def log_duration(start_time, stage_name):
    """计算并记录每个阶段的持续时间"""
    end_time = time.time()
    duration = end_time - start_time
    # logger.info(f"{stage_name} took {duration:.2f} seconds")
    print(f"{stage_name} took {duration:.2f} seconds")
    return duration


# 全局配置
# from automaticExtractionBackend.settings import get_llm_instance

logger = logging.getLogger(__name__)
parser = JsonOutputParser()

# 全局线程池（根据服务器CPU核心数调整）
GLOBAL_THREAD_POOL = ThreadPoolExecutor(max_workers=100)  # 建议CPU核心数×2


def get_llm_instance():
    """每次调用时都返回一个新的 LLM 实例"""
    llm = ChatOpenAI(
        openai_api_key=random.choice(settings.OPENAI_KEYS),  # 可以从环境变量或者配置文件获取
        model="gpt-4o",
        temperature=0,
    )
    return llm

CAUSAL_PROMPT = """
[Instruction]
Analyze the given sentence and the two identified entities with their constructs. Determine if there is a meaningful causal relationship between these entities based on the text evidence. Determine if there is a causal relationship between these entities based on explicit causal markers (e.g., because, since, as, therefore) or implicit semantic relationships.

A causal relationship exists when one entity (cause) leads to, results in, or influences another entity (effect).

IMPORTANT:
1. Consider both explicit causal markers (like "because," "therefore," "since," "as a result") AND implicit causal relationships. While many causal relationships are explicitly indicated, others might be inferred from the meaning and context of the sentence. Both types are equally valid for this task.
2. The relationship field in the output must always be "lead to" - your task is to correctly identify which entity is the cause (comes before "lead to") and which is the effect (comes after "lead to").
3. Pay careful attention to the direction of causality - determine which entity leads to or influences the other, not the reverse.

[Input Format]
- Sentence: The complete sentence from a qualitative data interview transcript
- Entity 1: The first entity with its construct type in parentheses
- Entity 2: The second entity with its construct type in parentheses

[Output Format]
Return the results in JSON format:

If a causal relationship exists:
{
  "causal_relationship": {
    "cause": "entity that is the cause",
    "relationship": "lead to",
    "effect": "entity that is the effect"
  }
}

If no causal relationship exists:
{
  "causal_relationship": "none"
}

[Example 1]
Sentence: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
Entity 1: "would not feel angry" (emotional response)
Entity 2: "try to talk to them" (behavioral intention)

Output:
{
  "causal_relationship": {
    "cause": "would not feel angry",
    "relationship": "lead to",
    "effect": "try to talk to them"
  }
}

[Example 2]
Sentence: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."
Entity 1: "I do not like seeing people angry" (belief)
Entity 2: "I do not like arguments" (belief)

Output:
{
  "causal_relationship": "none"
}

[Input]
"""


# 批量异步分析句子中的所有实体对
async def analyze_sentence_async(sentence):
    # 获取句子中的所有实体
    entities = list(sentence.entities.all())
    if len(entities) < 2:
        return []  # 返回空列表，如果实体对不足

    # 生成实体对
    pairs = list(combinations(entities, 2))

    # 为所有实体对生成 prompt
    prompts = []
    for e1, e2 in pairs:
        construct1 = e1.construct.name if e1.construct else "unknown"
        construct2 = e2.construct.name if e2.construct else "unknown"

        prompt = f"""
        - Sentence: {sentence.text}
        - Entity 1: {e1.name} ({construct1})
        - Entity 2: {e2.name} ({construct2})
        """
        prompts.append(prompt)

    # 将所有的 prompts 作为批量请求传递给 llm.agenerates()
    llm = get_llm_instance()
    # messages = [
    #     SystemMessage(content=CAUSAL_PROMPT),
    #     # 为每个 prompt 创建一个单独的 HumanMessage
    #     *[HumanMessage(content=prompt) for prompt in prompts]
    # ]

    # messages_lst = []
    # for prompt in prompts:
    #     messages = [SystemMessage(content=CAUSAL_PROMPT),
    #     HumanMessage(content=prompt)]
    #     messages_lst.append(messages)

    # 使用列表生成每个单独的消息组
    messages_lst = [
        [SystemMessage(content=CAUSAL_PROMPT), HumanMessage(content=prompt)]
        for prompt in prompts
    ]

    try:
        # 批量处理所有的 prompts
        # response = await llm.agenerate([messages])  # 批量处理
        # response = await llm.agenerate(messages_lst)  # 批量处理
        # print("response:", response)
        # results = [parser.parse(r.generations[0][0].text) for r in response.generations]
        # print("results:", results)
        # return results  # 返回批量处理的结果

        results = []
        response = await llm.agenerate(messages_lst)  # 批量处理
        pprint(response)
        # print("response:", response)
        for generation_list in response.generations:  # Access 'generations' correctly
            for generation in generation_list:  # Now iterate over the inner list of ChatGeneration objects
                parsed_text = parser.parse(generation.text)
                print("parsed_text:", parsed_text)
                results.append(parsed_text)
            # parsed_text = parser.parse(generation.text)
            # print("parsed_text:", parsed_text)
            # results.append(parsed_text)

        # 修复：访问每个生成的对象并正确处理结果
        # results = []
        # for gen_response in response:  # Response should be a list of 'generations' lists
            # for generation in gen_response[0]['generations']:  # Accessing the 'generations' key
            #     parsed_text = parser.parse(generation.text)  # Now accessing 'text' from the 'generation' object
            #     print("parsed_text:", parsed_text)
            #     results.append(parsed_text)  # 处理生成的文本
            # print("gen_response:", gen_response)
            # print("gen_response_0:", gen_response[0])
            # print("gen_response_1:", gen_response[1])

        return results  # 返回批量处理的结果



        # 修复：迭代所有生成的 ChatGeneration，并从中提取生成的文本
        # response = await llm.agenerate(messages_lst)  # 批量处理
        # results = []
        # for gen_response in response[1]:
        #     print("gen_response:", gen_response)
        #     parsed_text = parser.parse(gen_response[0].text)
        #     print("parsed_text:", parsed_text)
        #     results.append(parsed_text)  # 处理生成的文本
        # for gen_response in response:
        #     if hasattr(gen_response, 'generations'):
        #         for generation in gen_response.generations:
        #             parsed_text = parser.parse(generation.text)
        #             print("parsed_text:", parsed_text)
        #             results.append(parsed_text)  # 处理生成的文本
        return results  # 返回批量处理的结果

    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        return {"error": "Rate limit exceeded. Try again later."}
    except Exception as e:
        logger.error(f"Error processing sentence: {str(e)}")
        return None


# 用于线程池处理多个句子的异步调用
def process_sentence_async(sentence):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(analyze_sentence_async(sentence))
        return result
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


# 汇总句子的所有分析结果
def process_sentences(sentences):
    futures = []
    for sentence in sentences:
        futures.append(GLOBAL_THREAD_POOL.submit(process_sentence_async, sentence))

    results = []
    for future in futures:
        try:
            result = future.result(timeout=300)
            if result:
                results.extend(result)
        except Exception as e:
            logger.error(f"Error processing sentence: {str(e)}")
    return results


@csrf_exempt
@require_http_methods(["POST"])
def extract_causal_relations(request):
    try:
        start_time = log_time("Request Parsing")
        data = json.loads(request.body)
        if not (user_id := data.get("user_id")):
            return JsonResponse({"error": "Missing user_id"}, status=400)
        log_duration(start_time, "Request Parsing")

        # 获取用户数据
        start_time = log_time("Fetching User Data")
        try:
            user = SystemUser.objects.get(pk=user_id)
            sentences = Sentence.objects.filter(user=user).prefetch_related(
                "entities",
                "entities__construct",
                "entities__canonical_entity"
            )
        except SystemUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        log_duration(start_time, "Fetching User Data")

        # 处理句子并汇总结果
        start_time = log_time("Processing Sentences")
        results = process_sentences(sentences)
        print("results:", results)
        log_duration(start_time, "Processing Sentences")

        # 存储结果
        start_time = log_time("Storing Results")
        created = []
        for r in results:
            if not (rel := r.get("causal_relationship")):
                continue
            if rel == "none" or not isinstance(rel, dict):
                continue

            e1 = r["e1"].canonical_entity or r["e1"]
            e2 = r["e2"].canonical_entity or r["e2"]

            if (cause := rel.get("cause")) == (effect := rel.get("effect")):
                continue

            if cause == r["e1"].name and effect == r["e2"].name:
                start, end = e1, e2
            elif cause == r["e2"].name and effect == r["e1"].name:
                start, end = e2, e1
            else:
                continue

            _, created_flag = Triple.objects.get_or_create(
                user=user,
                sentence=r["sentence"],
                entity_cause=start,
                entity_effect=end,
                defaults={"user": user}
            )

            if created_flag:
                created.append({
                    "sentence_id": r["sentence"].id,
                    "cause": start.name,
                    "effect": end.name
                })
        log_duration(start_time, "Storing Results")

        return JsonResponse({
            "status": "success",
            "created_triples": created,
            "count": len(created),
            "analyzed_pairs": len(results)
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("Unexpected error in extract_causal_relations")
        return JsonResponse({"error": str(e)}, status=500)

#
# async def analyze_pair_async(sentence, e1, e2):
#     """异步分析实体对"""
#     # llm = get_llm()
#
#     # 从 settings 的 LLM 池子中拿一个
#     llm = get_llm_instance()
#     construct1 = e1.construct.name if e1.construct else "unknown"
#     construct2 = e2.construct.name if e2.construct else "unknown"
#
#     prompt = f"""
# - Sentence: {sentence.text}
# - Entity 1: {e1.name} ({construct1})
# - Entity 2: {e2.name} ({construct2})
# """
#     messages = [
#         SystemMessage(content=CAUSAL_PROMPT),
#         HumanMessage(content=prompt),
#     ]
#
#     try:
#         response = await llm.agenerate([messages])
#         result = parser.parse(response.generations[0][0].text)
#         print("extracted causal:", result)
#         return {
#             "sentence": sentence,
#             "e1": e1,
#             "e2": e2,
#             "result": result
#         }
#     except RateLimitError as e:
#         # 捕获 RateLimitError 并返回相应的错误信息
#         logger.error(f"Rate limit exceeded while processing pair ({e1.name}, {e2.name}): {str(e)}", exc_info=True)
#         return {"error": "Rate limit exceeded. Please try again later."}
#     except Exception as e:
#         logger.error(f"Error analyzing pair ({e1.name}, {e2.name}): {str(e)}",
#                      exc_info=True)
#         return None
#
#
#
# def process_pair_sync(args):
#     """同步线程中处理异步任务"""
#     sentence, e1, e2 = args
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         result = loop.run_until_complete(analyze_pair_async(sentence, e1, e2))
#         return result
#     finally:
#         try:
#             loop.run_until_complete(loop.shutdown_asyncgens())
#             loop.close()
#         except:
#             pass
#
#
# def process_sentence(sentence):
#     """
#     处理单个句子中的所有实体对，使用全局线程池
#     返回格式: [{"sentence": sentence, "e1": e1, "e2": e2, "result": analysis_result}, ...]
#     """
#     # 获取句子中的所有实体
#     entities = list(sentence.entities.all())
#     if len(entities) < 2:
#         return []  # 不足两个实体，直接返回空列表
#
#     # 生成所有唯一的实体对组合
#     pairs = list(combinations(entities, 2))
#
#     # 使用全局线程池处理所有实体对
#     futures = []
#     for e1, e2 in pairs:
#         # 提交任务到全局线程池
#         future = GLOBAL_THREAD_POOL.submit(
#             process_pair_sync,
#             (sentence, e1, e2)
#         )
#         futures.append(future)
#
#     # 收集结果
#     results = []
#     for future in futures:
#         try:
#             result = future.result(timeout=300)  # 设置合理的超时时间
#             if result and "error" not in result:  # 过滤掉错误结果
#                 results.append(result)
#         except Exception as e:
#             logger.error(
#                 f"Error processing pair ({sentence.id}): {str(e)}",
#                 exc_info=True
#             )
#
#     return results
#
#
#
# @csrf_exempt
# @require_http_methods(["POST"])
# def extract_causal_relations(request):
#     try:
#         # 开始处理请求
#         start_time = log_time("Request Parsing")
#         data = json.loads(request.body)
#         if not (user_id := data.get("user_id")):
#             return JsonResponse({"error": "Missing user_id"}, status=400)
#         log_duration(start_time, "Request Parsing")
#
#         # 获取用户数据
#         start_time = log_time("Fetching User Data")
#         try:
#             user = SystemUser.objects.get(pk=user_id)
#             sentences = Sentence.objects.filter(user=user).prefetch_related(
#                 "entities",
#                 "entities__construct",
#                 "entities__canonical_entity"
#             )
#         except SystemUser.DoesNotExist:
#             return JsonResponse({"error": "User not found"}, status=404)
#         log_duration(start_time, "Fetching User Data")
#
#         # 处理所有句子
#         start_time = log_time("Processing Sentences")
#         futures = []
#         for sentence in sentences:
#             # 使用全局线程池提交任务
#             future = GLOBAL_THREAD_POOL.submit(process_sentence, sentence)
#             futures.append(future)
#
#         # 收集结果
#         results = []
#         for future in futures:
#             try:
#                 result = future.result(timeout=300)  # 设置超时时间
#                 if result:
#                     results.extend(result)
#             except Exception as e:
#                 logger.error(f"Error processing sentence: {str(e)}", exc_info=True)
#         log_duration(start_time, "Processing Sentences")
#
#         # 存储结果
#         start_time = log_time("Storing Results")
#         created = []
#         for r in results:
#             if not (rel := r["result"].get("causal_relationship")):
#                 continue
#             if rel == "none" or not isinstance(rel, dict):
#                 continue
#
#             e1 = r["e1"].canonical_entity or r["e1"]
#             e2 = r["e2"].canonical_entity or r["e2"]
#
#             if (cause := rel.get("cause")) == (effect := rel.get("effect")):
#                 continue
#
#             if cause == r["e1"].name and effect == r["e2"].name:
#                 start, end = e1, e2
#             elif cause == r["e2"].name and effect == r["e1"].name:
#                 start, end = e2, e1
#             else:
#                 continue
#
#             _, created_flag = Triple.objects.get_or_create(
#                 user=user,
#                 sentence=r["sentence"],
#                 entity_cause=start,
#                 entity_effect=end,
#                 defaults={"user": user}
#             )
#
#             if created_flag:
#                 created.append({
#                     "sentence_id": r["sentence"].id,
#                     "cause": start.name,
#                     "effect": end.name
#                 })
#         log_duration(start_time, "Storing Results")
#
#         return JsonResponse({
#             "status": "success",
#             "created_triples": created,
#             "count": len(created),
#             "analyzed_pairs": len(results)
#         }, status=200)
#
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         logger.exception("Unexpected error in extract_causal_relations")
#         return JsonResponse({"error": str(e)}, status=500)
