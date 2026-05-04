"""
测试脚本：确认 Gemini API 能调通
跑一次成功就说明环境完全配好了
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# 从 .env 读 API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("错误：没找到 GEMINI_API_KEY，检查 .env 文件")
    exit(1)

# 配置 Gemini
genai.configure(api_key=api_key)

# 用 gemini-2.5-pro：精度高，适合本研究的政策文本分类
# 后续正式编码也用这个模型
model = genai.GenerativeModel("gemini-2.5-pro")

# 发一个最简单的请求
response = model.generate_content("用一句话介绍 TikTok。")

print("Gemini 2.5 Pro 回复：")
print(response.text)
print("\n环境配置成功，可以进入下一步。")