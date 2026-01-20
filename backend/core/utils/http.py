import requests

# 全局 session，整个项目都可以 import 用它发请求
session = requests.Session()
session.trust_env = False