from django.db import models
import datetime

# Create your models here.
class SystemUser(models.Model):
    username = models.CharField(max_length=32, unique=True)
    email = models.EmailField(unique=True)
    def __str__(self):
        return self.email

class Operation(models.Model):
    operation_type = models.CharField(max_length=100)
    operation_data = models.TextField()
    timestamp = models.DateTimeField(default=datetime.datetime.now)
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name='operations')

    def __str__(self):
        return f"Operation(user_id={self.user_id}, type={self.operation_type})"

class Construct(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="constructs", blank=True, null=True)
    name = models.CharField(max_length=100)  # 构念名，如 Emotion
    definition = models.TextField()
    examples = models.JSONField(default=list)  # 用 JSONField 代替字符串（建议
    color = models.CharField(max_length=20, default="#cccccc")  # 新增字段：颜色（HEX 代码或命名颜色）

    def __str__(self):
        return f"{self.name}"

class Sentence(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="sentences", blank=True, null=True)
    text = models.TextField()
    line_number = models.PositiveIntegerField(default=1)  # 新增字段：所在行号

    def __str__(self):
        return self.text[:50]  # 简略显示句子



class Entity(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="entities", blank=True, null=True)
    name = models.TextField()  # 实体文本
    construct = models.ForeignKey(Construct, on_delete=models.CASCADE, null=True, blank=True)  # 实体类型，如 belief, action, emotion
    sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE, related_name="entities", null=True, blank=True)
    canonical_entity = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    embeddings = models.JSONField(default=dict, blank=True)  # {"bert": [...], "minilm": [...]} <-- ADDED

    def __str__(self):
        return f"{self.name} ({self.construct})"


class Triple(models.Model):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name="triples", blank=True, null=True)
    sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE, related_name="triples")
    entity_cause = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="cause_triples")
    entity_effect = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="effect_triples")