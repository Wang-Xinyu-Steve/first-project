import os
import sys
import base64
import requests
import re
import unicodedata
from typing import List, Dict, Any
from openai import OpenAI
import json

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
    """使用火山引擎豆包大模型多模态API生成小红书内容摘要"""
    try:
        print(f"[DEBUG] 开始summary_xhs，文本长度: {len(text)}")
        print(f"[DEBUG] 图片路径数量: {len(img_paths)}")
        # 固定API Key和base_url
        api_key = "7929a2db-9ee1-49ef-9246-1fd950f47dd9"
        base_url = "https://ark.cn-beijing.volces.com/api/v3"
        model = "doubao-seed-1-6-250615"
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
        # 构造多模态消息内容
        content = []
        user_prompt = filter_non_bmp(
            """
            你是一个专业的新媒体内容分析师，请严格按此流程处理：

            （一）图片内容分析
            1. 图片1
            - 内容转录（原文用「」标注，保留换行）
                「第一段文字...」
                「第二段文字...」
            - 排版解析 
                布局：分栏/流程图/时间轴等
                重点标注：颜色/字号/下划线等
            - 数据关联 对应文字章节X段Y行

            2. 图片2
            ...

            （二）文本内容处理
            - 核心框架
            标题层级：H1「主标题」> H2「小标题」...
            - 关键信息
            论点1（支持数据：...）
            论点2（案例：...）
            - 图片锚点
            图1相关：第X段「引用句」
            图3相关：第Y段数据

            三、输出模板
            【图片内容分析】
            1. 图片1
            - 内容转录：
                「2023年用户增长数据」
                「Q1: 15% ↑ | Q2: 22% ↑」
            - 排版解析：
                双栏对比布局
                增长率使用绿色加粗
            - 数据关联：正文第三段

            2. 图片2
            ...

            【文本内容摘要】
            - 核心主张：...
            - 数据支撑：...（精确数值）
            - 图片呼应点：
            图1验证「...」观点
            图2例证「...」描述

            【评论区内容摘要】
            1. 核心信息：
            评论主要围绕...等展开。
            2. 关键评论：
            ...
            询问...，回答是...。
            ...

            四、执行要求
            1. 文字转录误差率<5%
            2. 每个图片关联点必须标注文字位置
            3. 禁用模糊表述如"相关"/"可能"
            4. 图片的所有文字内容必须全部展示出来，而不是只展示部分文字
            """
            f"内容如下：\n{text}"
        )
        content.append({"type": "text", "text": user_prompt})
        max_images = 20
        for i, base64_data in enumerate(image_contents[:max_images]):
            content.append({"type": "image_url", "image_url": {"url": base64_data}})
        print(f"[DEBUG] 实际传递图片数量: {len(content) - 1}")
        client = OpenAI(api_key=api_key, base_url=base_url)
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                temperature=0.3,
                max_tokens=20000,
                timeout=120
            )
            summary = completion.choices[0].message.content
            print("豆包大模型多模态摘要生成成功")
            return summary.strip() if summary else "摘要生成失败：API返回空内容"
        except Exception as e:
            print(f"[错误] 豆包大模型多模态API调用失败: {str(e)}")
            return fallback_text_summary(text)
    except Exception as e:
        print(f"[错误] 豆包大模型多模态API调用失败: {str(e)}")
        return fallback_text_summary(text)

def fallback_text_summary(text: str) -> str:
    """文本模式备用方案"""
    try:
        api_key = "7929a2db-9ee1-49ef-9246-1fd950f47dd9"
        base_url = "https://ark.cn-beijing.volces.com/api/v3"
        model = "doubao-seed-1-6-250615"
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的内容分析师。请生成结构化、详细、包含要点的Markdown格式摘要。使用中文输出结果。"},
                {"role": "user", "content": f"请为以下内容生成详细摘要：\n\n{text}"}
            ],
            temperature=0.3,
            max_tokens=2000,
            timeout=60
        )
        summary = completion.choices[0].message.content
        if summary:
            return summary.strip()
        else:
            return "摘要生成失败：API返回空内容"
    except Exception as e:
        print(f"[错误] 文本模式也失败: {str(e)}")
        return simple_text_summary(text)

def simple_text_summary(text: str) -> str:
    """简单的文本摘要，不依赖外部API"""
    try:
        lines = text.split('\n')
        content_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        if not content_lines:
            return "内容为空，无法生成摘要"
        summary_lines = content_lines[:3]
        summary = "\n\n".join(summary_lines)
        if len(summary) > 500:
            summary = summary[:500] + "..."
        return f"# 内容摘要\n\n{summary}\n\n*注：这是基于文本内容的简单摘要，如需更详细的多模态分析，请配置正确的API Key。*"
    except Exception as e:
        return f"摘要生成失败：{str(e)}" 