import requests
import time
from util.chunk_content import chunk_content

def generate_summary(text: str, api_key: str, model_name: str) -> str:
    """
    使用百度智能云千帆平台ERNIE 4.5 Turbo大模型生成摘要。
    直接用API Key作为Bearer Token，无需access_token。
    """
    api_url = "https://qianfan.baidubce.com/v2/chat/completions"
    chunks = chunk_content(text)
    summaries = []
    print(f"检测到 {len(chunks)} 个文本块需要处理")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    for i, chunk in enumerate(chunks):
        print(f"处理分块 {i+1}/{len(chunks)} (约 {len(chunk)} 字符)")
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "你是一个专业的摘要生成专家。请生成结构化、简洁、包含要点的Markdown格式摘要。保留关键数据和专业术语。使用中文输出结果。"},
                {"role": "user", "content": f"请为以下内容生成详细摘要,使用Markdown格式,包含主要观点、关键数据和结论，代码部分全部保留并高亮，图片链接全部保留引用：\n\n{chunk}"}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            if 'choices' in result and result['choices']:
                summary = result['choices'][0]['message']['content'].strip()
                summaries.append(summary)
                print(f"分块 {i+1} 摘要生成成功")
            else:
                print(f"[警告] 分块 {i+1} 摘要生成失败: 响应格式异常")
                summaries.append(f"### 分块 {i+1} 摘要生成失败\n\n")
        except Exception as e:
            print(f"[错误] 分块 {i+1} API调用失败: {str(e)}")
            summaries.append(f"### 分块 {i+1} 摘要生成失败\n\n")
        time.sleep(1)
    if not summaries:
        return "摘要生成失败,请检查API密钥或网络连接"
    if len(summaries) == 1:
        return summaries[0]
    combined_summary = "\n\n".join(summaries)
    print("整合分段摘要...")
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "你是一个专业编辑,请将以下分段摘要整合成一份连贯的完整摘要,保持Markdown格式,确保逻辑流畅。"},
            {"role": "user", "content": f"请整合以下分段摘要，代码部分全部保留并高亮，注意：图片链接全部保留引用：\n\n{combined_summary}"}
        ],
        "temperature": 0.2,
        "max_tokens": 2500
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()
        if 'choices' in result and result['choices']:
            return result['choices'][0]['message']['content'].strip()
        else:
            print("[警告] 摘要整合失败，返回原始摘要")
            return combined_summary
    except Exception as e:
        print(f"[错误] 摘要整合失败: {str(e)}")
        return combined_summary 