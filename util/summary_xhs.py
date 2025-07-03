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
        print(f"[DEBUG] base64前500位: {base64_data[:500]}")
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
                    print(f"[DEBUG] 图片大小: {os.path.getsize(img_path)} 字节")
                    base64_data = image_to_base64(img_path)
                    if base64_data:
                        print(f"[DEBUG] base64前500位: {base64_data[:500]}")
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

            四、执行要求
            1. 文字转录误差率<5%
            2. 每个图片关联点必须标注文字位置
            3. 禁用模糊表述如"相关"/"可能"
            4. 图片的所有文字内容必须全部展示出来，而不是只展示部分文字
            """
            f"内容如下：\n{text}"
        )
        
        content.append({"type": "text", "text": user_prompt})
        
        # 添加图片Base64数据
        # 限制图片数量，避免API参数错误
        max_images = 10  # 改回6张图片，测试API是否能正常处理
        print(f"[提示] 为避免API限制，将处理前{max_images}张图片进行分析")
        for i, base64_data in enumerate(image_contents[:max_images]):
            content.append({"type": "image_url", "image_url": {"url": base64_data}})
            print(f"[DEBUG] 添加图片 {i+1}/{min(len(image_contents), max_images)}")
        
        print(f"[DEBUG] 实际传递图片数量: {len(content) - 1}")  # 减去文本内容
        
        # 使用 requests 直接调用千帆平台API
        api_url = "https://qianfan.baidubce.com/v2/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": content}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
            "stream": False
        }
        print(f"[DEBUG] API请求体前500字符: {json.dumps(payload, ensure_ascii=False)[:500]}")
        
        # 重试机制
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                print(f"[DEBUG] 多模态API请求尝试 {attempt + 1}/{max_retries + 1}")
                # 增加超时时间，多模态请求通常需要更长时间
                response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=120)
                result = response.json()
                if 'choices' in result:
                    summary = result['choices'][0]['message']['content'].strip()
                    print("百度智能云千帆平台多模态摘要生成成功")
                    return summary
                else:
                    summary = "摘要生成失败：API返回空内容"
                    print("完整API响应：", json.dumps(result, ensure_ascii=False, indent=2))
                    return summary
            except requests.exceptions.ReadTimeout:
                if attempt < max_retries:
                    print(f"[警告] 多模态API请求超时，尝试重试 ({attempt + 1}/{max_retries})")
                    continue
                else:
                    print(f"[错误] 多模态API请求最终超时，回退到文本模式")
                    raise
            except requests.exceptions.RequestException as e:
                print(f"[错误] 多模态API请求失败: {str(e)}")
                # 打印完整的错误响应
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_detail = e.response.json()
                        print(f"[DEBUG] 完整错误响应: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
                    except:
                        print(f"[DEBUG] 错误响应状态码: {e.response.status_code}")
                        print(f"[DEBUG] 错误响应内容: {e.response.text}")
                raise
            except Exception as e:
                print(f"[错误] 其他异常: {str(e)}")
                raise
        
        # 如果所有重试都失败，抛出异常让外层处理
        raise Exception("多模态API请求失败")
        
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
            max_tokens=2000,
            timeout=60  # 文本模式设置60秒超时
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