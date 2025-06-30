import os
import sys
import base64
import requests
import re
import unicodedata
from typing import List, Dict, Any
from openai import OpenAI
import json

# 百度智能云千帆平台配置
# 根据百度官方SDK示例，使用OpenAI兼容接口
QIANFAN_API_KEY = "bce-v3/ALTAK-Of56tLQhJtuDtnjlsohkj/a38fd6231c7332083163522f6c8fc534b1c87a64"  # 千帆bearer token
QIANFAN_BASE_URL = "https://qianfan.baidubce.com/v2"  # 千帆域名
QIANFAN_MODEL = "ernie-4.5-turbo-vl-preview"  # ERNIE 4.5 Turbo VL Preview 多模态大模型

def safe_filename(s):
    """保留中文，去除emoji和特殊符号"""
    def is_valid_char(c):
        # 保留中文
        if '\u4e00' <= c <= '\u9fff':
            return True
        # 保留英文、数字、下划线、点、横线
        if re.match(r'[A-Za-z0-9._-]', c):
            return True
        # 去除emoji和其他特殊符号
        return False
    return ''.join(c for c in s if is_valid_char(c))

def image_to_base64(image_path):
    """将图片转换为Base64编码，仅支持JPG/JPEG/PNG/BMP"""
    try:
        ext = os.path.splitext(image_path)[-1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.bmp']:
            print(f"[警告] 不支持的图片格式: {ext}，仅支持JPG/JPEG/PNG/BMP")
            return None
        with open(image_path, 'rb') as f:
            image_data = f.read()
        if ext == '.jpg' or ext == '.jpeg':
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.bmp':
            mime_type = 'image/bmp'
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
    except Exception as e:
        print(f"[DEBUG] 图片转Base64失败: {str(e)}")
        return None

def filter_non_bmp(text):
    """只保留基本多文种平面（BMP）字符，去除emoji和特殊符号"""
    return ''.join(c for c in text if ord(c) <= 0xFFFF)

def deep_filter_non_bmp(obj):
    """递归过滤所有内容中的emoji和特殊符号"""
    if isinstance(obj, str):
        return filter_non_bmp(obj)
    elif isinstance(obj, list):
        return [deep_filter_non_bmp(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: deep_filter_non_bmp(v) for k, v in obj.items()}
    else:
        return obj

def summary_xhs(text: str, img_paths: list, api_key: str, model_name: str) -> str:
    """使用百度智能云千帆平台多模态API生成小红书内容摘要"""
    try:
        print(f"[DEBUG] 开始summary_xhs，文本长度: {len(text)}")
        print(f"[DEBUG] 图片路径数量: {len(img_paths)}")
        
        # 检查百度智能云配置
        if not api_key:
            print("[警告] 百度智能云API Key未配置，跳过图片分析，直接使用文本模式")
            print("[提示] 请在 util/summary_xhs.py 中配置正确的 QIANFAN_API_KEY")
            return fallback_text_summary(text)
        
        # 处理图片，转换为Base64编码
        image_contents = []
        if img_paths:
            print(f"开始处理 {len(img_paths)} 张图片...")
            for i, img_path in enumerate(img_paths):
                if os.path.exists(img_path):
                    print(f"处理图片 {i+1}/{len(img_paths)}: {os.path.basename(img_path)}")
                    base64_data = image_to_base64(img_path)
                    if base64_data:
                        image_contents.append(base64_data)
                        print(f"图片处理成功: {os.path.basename(img_path)}")
                    else:
                        print(f"图片处理失败: {os.path.basename(img_path)}")
                else:
                    print(f"图片文件不存在: {img_path}")
        
        print(f"[DEBUG] 开始构造AI请求，图片数量: {len(image_contents)}")
        
        # 如果没有成功处理图片，回退到文本模式
        if not image_contents:
            print("[提示] 没有成功处理图片，回退到文本模式")
            return fallback_text_summary(text)
        
        # 构造多模态消息内容
        content = []
        
        # 添加文本内容
        user_prompt = filter_non_bmp(
            "你是一个专业的新媒体内容分析师。请严格按照如下要求总结：\n"
            "1. 对每一张图片，逐张、详细、具体描述图片内容，不能泛泛而谈，不要归纳、想象、增删图片信息。\n"
            "2. 图片总结请用编号列表，格式为：\n"
            "   1. 图片1：<详细内容>\n"
            "   2. 图片2：<详细内容>\n"
            "3. 文字内容请单独总结。\n"
            "4. 图片和文字内容请分开输出。\n"
            "5. 输出格式示例：\n"
            "【图片总结】\n1. 图片1：...\n2. 图片2：...\n【文字总结】\n...\n"
            f"内容如下：\n{text}"
        )
        
        content.append({"type": "text", "text": user_prompt})
        
        # 添加图片Base64数据
        for base64_data in image_contents:
            content.append({"type": "image_url", "image_url": {"url": base64_data}})
        
        # 使用 requests 直接调用千帆平台API
        api_url = "https://qianfan.baidubce.com/v2/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "请生成结构化、简洁、包含要点的Markdown格式摘要。保留关键数据和专业术语。使用中文输出结果。注意：图片链接全部保留引用"},
                {"role": "user", "content": content}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        print("已经构造了payload")
        response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=60)
        print("已经发送了请求")
        result = response.json()
        print("已经收到了响应")
        if 'id' in result:
            print(f"请求ID: {result['id']}")
        if 'object' in result:
            print(f"对象类型: {result['object']}")
        if 'created' in result:
            print(f"创建时间: {result['created']}")
        if 'model' in result:
            print(f"模型: {result['model']}")
        if 'usage' in result:
            print(f"使用情况: {result['usage']}")
        if 'choices' in result:
            summary = result['choices'][0]['message']['content'].strip()
        else:
            summary = "摘要生成失败：API返回空内容"
        print("完整API响应：", json.dumps(result, ensure_ascii=False, indent=2))
        print("百度智能云千帆平台多模态摘要生成成功")
        return summary
        
    except Exception as e:
        print(f"[错误] 百度智能云千帆平台多模态API调用失败: {str(e)}")
        print(f"[DEBUG] 错误类型: {type(e)}")
        # 如果多模态API失败，回退到文本模式
        print("回退到文本模式...")
        return fallback_text_summary(text)

def fallback_text_summary(text: str) -> str:
    """文本模式备用方案"""
    try:
        # 检查API Key是否已配置
        if not QIANFAN_API_KEY:
            print("[提示] API Key未配置，使用简单文本摘要模式")
            return simple_text_summary(text)
        
        print(f"[DEBUG] 文本模式 - 使用base_url: {QIANFAN_BASE_URL}")
        print(f"[DEBUG] 文本模式 - 使用模型: {QIANFAN_MODEL}")
        print(f"[DEBUG] 文本模式 - 使用API Key: {QIANFAN_API_KEY[:30]}...")
        
        client = OpenAI(
            api_key=QIANFAN_API_KEY,
            base_url=QIANFAN_BASE_URL
        )
        
        completion = client.chat.completions.create(
            model=QIANFAN_MODEL,
            messages=[
                {"role": "system", "content": "你是一个专业的内容分析师。请生成结构化、详细、包含要点的Markdown格式摘要。使用中文输出结果。"},
                {"role": "user", "content": f"请为以下内容生成详细摘要：\n\n{text}"}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        summary = completion.choices[0].message.content
        
        if summary:
            return summary.strip()
        else:
            return "摘要生成失败：API返回空内容"
        
    except Exception as e:
        print(f"[错误] 文本模式也失败: {str(e)}")
        print(f"[DEBUG] 文本模式错误类型: {type(e)}")
        print("[提示] 使用简单文本摘要模式")
        return simple_text_summary(text)

def simple_text_summary(text: str) -> str:
    """简单的文本摘要，不依赖外部API"""
    try:
        # 简单的文本处理
        lines = text.split('\n')
        # 过滤空行和过短的行
        content_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        
        if not content_lines:
            return "内容为空，无法生成摘要"
        
        # 取前几行作为摘要
        summary_lines = content_lines[:3]
        summary = "\n\n".join(summary_lines)
        
        # 如果摘要太长，截取前500字符
        if len(summary) > 500:
            summary = summary[:500] + "..."
        
        return f"# 内容摘要\n\n{summary}\n\n*注：这是基于文本内容的简单摘要，如需更详细的多模态分析，请配置正确的百度智能云API Key。*"
        
    except Exception as e:
        return f"摘要生成失败：{str(e)}" 