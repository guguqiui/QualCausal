from core.models import Sentence, SystemUser
from django.db.models import Max

def get_all_sentences(user_id):
    return Sentence.objects.filter(user__id=user_id)

def get_sentence_by_id(sentence_id):
    return Sentence.objects.get(id=sentence_id)


def create_sentence(data, user_id):
    # 1. 获取 user 对象（如果不存在，会抛出异常）
    user = SystemUser.objects.get(id=user_id)

    text = data.get("text", "").strip()
    if not text:
        raise ValueError("A non-empty text field needs to be provided")

    existing = Sentence.objects.filter(user=user, text=text).first()
    if existing:
        # 如果找到了同文本的句子，就直接返回已有那条记录
        return existing

    # 2. 查询该用户现有句子的最大 line_number
    max_ln = (
        Sentence.objects
        .filter(user=user)
        .aggregate(max_ln=Max("line_number"))
        .get("max_ln")
    )
    if max_ln is None:
        max_ln = 0
    next_ln = max_ln + 1

    # 3. 创建新句子，并把 computed line_number 传给它
    return Sentence.objects.create(
        user=user,
        text=data['text'],
        line_number=next_ln
    )

def update_sentence(sentence_id, data):
    sentence = Sentence.objects.get(id=sentence_id)
    sentence.text = data.get('text', sentence.text)
    sentence.line_number = data.get('line_number', sentence.line_number)
    sentence.save()
    return sentence

def delete_sentence(sentence_id):
    Sentence.objects.get(id=sentence_id).delete()
