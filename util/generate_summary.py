import os
from openai import OpenAI
from util.chunk_content import chunk_content

def generate_summary(text: str, api_key: str, model_name: str) -> str:
    """
    使用火山引擎豆包大模型生成摘要。
    """
    # 固定API Key和base_url
    api_key = "7929a2db-9ee1-49ef-9246-1fd950f47dd9"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model = "doubao-seed-1-6-250615"
    chunks = chunk_content(text)
    summaries = []
    print(f"检测到 {len(chunks)} 个文本块需要处理")
    client = OpenAI(api_key=api_key, base_url=base_url)
    for i, chunk in enumerate(chunks):
        print(f"处理分块 {i+1}/{len(chunks)} (约 {len(chunk)} 字符)")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的摘要生成专家。请生成结构化、简洁、包含要点的Markdown格式摘要。保留关键数据和专业术语。使用中文输出结果。"},
                    {"role": "user", "content": f"请为以下内容生成详细摘要,使用Markdown格式,包含主要观点、关键数据和结论，代码部分全部保留并高亮，图片链接全部保留引用：\n\n{chunk}"}
                ],
                temperature=0.3,
                max_tokens=20000,
                timeout=60
            )
            content = response.choices[0].message.content
            summary = content.strip() if content else ""
            summaries.append(summary)
            print(f"分块 {i+1} 摘要生成成功")
        except Exception as e:
            print(f"[错误] 分块 {i+1} API调用失败: {str(e)}")
            summaries.append(f"### 分块 {i+1} 摘要生成失败\n\n")
    if not summaries:
        return "摘要生成失败,请检查API密钥或网络连接"
    if len(summaries) == 1:
        return summaries[0]
    combined_summary = "\n\n".join(summaries)
    print("整合分段摘要...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业编辑,请将以下分段摘要整合成一份连贯的完整摘要,保持Markdown格式,确保逻辑流畅。"},
                {"role": "user", "content": f"请整合以下分段摘要，代码部分全部保留并高亮，注意：图片链接全部保留引用：\n\n{combined_summary}"}
            ],
            temperature=0.2,
            max_tokens=2500,
            timeout=90
        )
        content = response.choices[0].message.content
        return content.strip() if content else combined_summary
    except Exception as e:
        print(f"[错误] 摘要整合失败: {str(e)}")
        return combined_summary 