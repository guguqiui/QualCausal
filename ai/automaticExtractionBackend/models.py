"""
 @file: models.py
 @Time    : 2025/3/29
 @Author  : Peinuan qin
 """
from datetime import timedelta
from django.db import models
from django.utils import timezone


class SystemUser(models.Model):
    username = models.CharField(max_length=32, unique=True)
    email = models.EmailField(unique=True)
    def __str__(self):
        return self.email

    # class Meta:
    #     # 添加这个确保异步支持
    #     base_manager_name = 'objects'

class Construct(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="constructs", blank=True, null=True)
    name = models.CharField(max_length=100)  # 构念名，如 Emotion
    definition = models.TextField()
    examples = models.JSONField(default=list)  # 用 JSONField 代替字符串（建议）
    color = models.CharField(max_length=20, default="#cccccc")  # 添加颜色字段

    def __str__(self):
        return f"{self.name}"

    # class Meta:
    #     # 添加这个确保异步支持
    #     base_manager_name = 'objects'



class Sentence(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="sentences", blank=True, null=True)
    text = models.TextField()
    # entities = models.ManyToManyField(Entity, related_name="sentences")  # e_id list 显式建关系
    line_number = models.PositiveIntegerField(default=1)  # 新增字段：所在行号

    def __str__(self):
        return self.text[:50]  # 简略显示句子

    # class Meta:
    #     # 添加这个确保异步支持
    #     base_manager_name = 'objects'

class Entity(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="entities", blank=True, null=True)
    name = models.TextField()  # 实体文本
    construct = models.ForeignKey(Construct, on_delete=models.CASCADE, null=True, blank=True)  # 实体类型，如 belief, action, emotion
    sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE, related_name="entities", null=True, blank=True)
    # 在 Entity 模型中新增字段(为了消除歧义使用）
    canonical_entity = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    embeddings = models.JSONField(default=dict, blank=True)  # {"bert": [...], "minilm": [...]} <-- ADDED
    color = models.CharField(max_length=20, default="#cccccc")  # 新增字段：颜色（HEX 代码或命名颜色）


    def __str__(self):
        return f"{self.name} ({self.construct})"

    # class Meta:
    #     # 添加这个确保异步支持
    #     base_manager_name = 'objects'

class Triple(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="triples", blank=True, null=True)
    sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE, related_name="triples")
    entity_cause = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="cause_triples")
    entity_effect = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="effect_triples")

    def __str__(self):
        return f"({self.entity_cause.name}) → ({self.entity_effect.name})"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'sentence', 'entity_cause', 'entity_effect'], name='unique_triple')
        ]
    # class Meta:
    #     # 添加这个确保异步支持
    #     base_manager_name = 'objects'
# class Triple(models.Model):
#     user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="triples", blank=True, null=True)
#     sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE, related_name="triples")
#     start_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="start_triples")
#     end_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="end_triples")
#
#     def __str__(self):
#         return f"({self.start_entity.name}) → ({self.end_entity.name})"



