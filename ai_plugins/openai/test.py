from dotenv import load_dotenv
from openai import OpenAI
import os

# 加载项目根目录下的 .env 文件
load_dotenv()

# 现在可以通过 os.environ 获取变量
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

client = OpenAI()

completion = client.chat.completions.create(
  model="o3-mini",
  messages=[
    {"role": "developer", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
)

print(completion.choices[0].message)
