## Part 1：上传与抽取模块  
以下接口用于支持基于文本的知识图谱构建流程：  
### 1. /api/upload_entities/  
#### 功能：将用户上传的多行文本切分为句子，并从中抽取实体  
#### 请求方式：POST  
#### 请求体参数：
```json
{
  "user_id": 1,
  "text": "First sentence.\nSecond sentence."
}
```
#### 返回值：
```json
{
  "sentences": [
    {
      "sentence": "First sentence.",
      "entities": [
        {
          "id": 214,
          "name": "hope they see a doctor"
        },
        {
          "id": 213,
          "name": "would feel concern"
        }
      ],
      "error": null
    }
  ]
}
```

###  2. /api/upload_constructs/
#### 功能：上传用户自定义构念（constructs）信息
#### 请求方式：POST
#### 请求体参数：
```json
{
  "user_id": 1,
  "constructs": [
    {
      "name": "belief",
      "definition": "explanation...",
      "examples": ["example1", "example2"]
    }
  ]
}
```

###  3. /api/map_constructs/
#### 功能：将已有实体（entity）自动匹配到用户上传的构念（construct）
#### 请求方式：POST
#### 请求体参数：
```json
{
  "user_id": 1,
  "force": false  // 可选，默认为 false，表示是否强制重新匹配
}
```
###  4. /api/extract_causals/
#### 功能：基于实体关系提取因果对（triple），即“因”导致“果”的结构
#### 请求方式：POST
#### 请求体参数：
```json
{
  "user_id": 1
}
```

###  5. /api/auto_entity_resolution/
#### 功能：自动进行同义实体合并（entity resolution），将语义上等价或相近的实体进行聚合
#### 请求方式：POST
#### 请求体参数：
```json
{
  "user_id": 1,          
  "k": 5,                // 每个实体最多寻找 k 个近邻（默认值为 5）
  "max_workers": 20      // 最大并行处理线程数（默认值为 20）
}
```

## Part2: 数据导入模块
以下接口用于将数据导入本地数据库：  
###  6. /api/import-data/
#### 功能：从远端平台导入指定用户 ID 的构念（construct）、句子（sentence）、实体（entity）和因果关系（triple）数据，保存到本地数据库。
#### 请求方式：POST
#### 请求体参数：
```json
{
  "user_id": 1
}
```
#### 返回值（成功）：
```json
{
  "status": "success",
  "message": "已成功导入本地数据库"
}
```
#### 返回值（失败）：
```json
{
  "status": "error",
  "message": "Export 接口返回 404"
}
```

## Part3: 构念（construct）增删查改模块
### 7. /api/<user_id>/constructs/
#### 功能：获取某个用户的全部构念（construct）
#### 请求方式：GET
#### 请求参数：user_id：整数，用户 ID
#### 返回值示例：
```json
[
  {
    "id": 1,
    "name": "belief",
    "definition": "A belief about the person in the story",
    "examples": ["they are not dangerous"],
    "color": "#66C5CC"
  },
  {
    "id": 2,
    "name": "suggestion",
    "definition": "Suggestions for intervention",
    "examples": ["they should seek therapy"],
    "color": "#F89C74"
  }
]
```

### 8. /api/constructs/assign/
#### 功能：手动为实体指定构念
#### 请求方式：POST
#### 请求体参数：
```json
{
  "user_id": 1,
  "entity_id": 42,
  "construct_id": 2
}
```

### 9. /api/constructs/update/<construct_id>/
#### 功能：更新构念内容（如名称、定义、示例）
#### 请求方式：POST
#### 请求参数：id（路径参数）：要更新的构念 ID
#### 请求体示例：
```json
{
  "name": "suggestion",
  "definition": "A proposed intervention or recommendation",
  "examples": ["should talk to a counselor"],
  "color": "#F89C74"
}
```

### 10. /api/constructs/delete/<construct_id>>/
#### 功能：删除指定构念
#### 请求方式：POST
#### 请求参数：id（路径参数）：要删除的构念 ID

## Part4: 实体（entity）增删查改模块
### 11. /api/<user_id>/entities/
#### 功能：获取某个用户的全部实体（entity）
#### 请求方式：GET
#### 请求参数：user_id：整数，用户 ID
#### 返回值示例：
```json
[
  {
    "id": 10,
    "name": "feel embarrassed by Avery",
    "construct": "emotional response",
    "sentence_id": 5,
    "embeddings": { "bert": [...], "minilm": [...] },
    "canonical_entity_id": 7
  }
]
```

### 12. /api/<user_id>/entities/create/
#### 功能：创建新的实体（entity），并绑定到指定用户
#### 请求方式：POST
#### 请求参数：user_id（路径参数）：用户 ID
#### 请求体示例：
```json
{
  "name": "feel ashamed",
  "sentence_id": 12,
  "construct": "emotional response",
  "canonical_entity_id": 8
}
```
#### 返回值示例：
```json
{
  "id": 101,
  "message": "Entity created successfully"
}
```

### 13. /api/entity/<entity_id>/update/
#### 功能：更新指定实体的属性（如名称、绑定句子、构念）
#### 请求方式：PUT
#### 请求参数：entity_id（路径参数）：要更新的实体 ID
#### 请求体示例：
```json
{
  "name": "feel ashamed",
  "sentence_id": 12,
  "construct": "emotional response",
  "canonical_entity_id": 8
}
```
#### 返回值示例：
```json
{
  "id": 101,
  "message": "Entity updated successfully"
}
```

### 14. /api/entity/<entity_id>/delete/
#### 功能：删除指定实体（entity）
#### 请求方式：DELETE
#### 请求参数：entity_id（路径参数）：要更新的实体 ID
#### 返回值示例：
```json
{
  "message": "Entity deleted successfully"
}
```

## Part5: 句子（sentence）增删查改模块
### 15. /api/sentence/<sentence_id>/
#### 功能：获取指定句子的详细信息
#### 请求方式：GET
#### 请求参数：sentence_id（路径参数）：句子 ID
#### 返回值示例：
```json
{
  "id": 15,
  "text": "They feel ashamed about the situation.",
  "line_number": 3
}
```

### 16. /api/<user_id>/sentences/create/
#### 功能：为指定用户创建一个新的句子
#### 请求方式：POST
#### 请求参数：user_id（路径参数），用户 ID
#### 请求体示例：
```json
{
  "text": "They feel ashamed about the situation.",
  "line_number": 3
}
```
#### 返回值示例：
```json
{
  "id": 15,
  "line_number": 3,
  "message": "Sentence created"
}
```

## Part6: 三元组（triple）增删查改模块
### 17. /api/<user_id>/triples/
#### 功能：获取某个用户的全部因果三元组（triple）
#### 请求方式：GET
#### 请求参数：user_id（路径参数）：用户 ID
#### 返回值示例：
```json
[
  {
    "id": 21,
    "sentence_id": 3,
    "entity_cause_id": 5,
    "entity_effect_id": 6
  },
  {
    "id": 22,
    "sentence_id": 4,
    "entity_cause_id": 7,
    "entity_effect_id": 9
  }
]
```

### 18. /api/<user_id>/triples/create/
#### 功能：为指定用户创建一个新的因果三元组（triple）
#### 请求方式：POST
#### 请求参数：user_id（路径参数），用户 ID
#### 请求体示例：
```json
{
  "sentence_id": 3,
  "entity_cause_id": 5,
  "entity_effect_id": 6
}
```
#### 返回值示例：
```json
{
  "id": 23,
  "message": "Triple created successfully"
}
```