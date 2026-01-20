"""
 @file: extract_entity.py
 @Time    : 2025/4/2
 @Author  : Peinuan qin
 """
# knowledge_graph/llm_utils.py

from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

def extract_entities(sentence: str) -> list[str]:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    system_prompt = """
Extract meaningful entities from the provided sentence, which is taken from a qualitative data interview transcript.

An entity is any distinct and meaningful phrase or component from the sentence that captures a complete thought, concept, 
action, feeling, belief, observation, or any other significant element of expression.

Return the extracted entities in JSON format as a simple list

[Example]
Input: "No, I would not feel angry, I would feel concerned and try to talk to them to calm them down. It is out of the ordinary behaviour for them, I do not like seeing people angry or arguments so I would try and defuse the situation."

[Output]:
{
  "entities": [
    "would not feel angry",
    "would feel concerned",
    "try to talk to them",
    "calm them down",
    "It is out of the ordinary behaviour for them",
    "I do not like seeing people angry",
    "I do not like arguments",
    "try and defuse the situation"
  ]
}

"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=sentence),
    ]

    response = llm(messages)
    try:
        response_dict = eval(response.content)  # assuming well-formatted output
        return response_dict.get("entities", [])
    except Exception:
        return []
