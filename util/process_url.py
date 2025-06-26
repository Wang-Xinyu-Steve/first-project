import os
import re
import hashlib
from util.generate_summary import generate_summary
from util.save_to_markdown import save_to_markdown
from typing import Optional

def process_url(summarizer, url: str, api_key: str, model_name: str, output_path: Optional[str] = None):
    print(f"开始处理: {url}")
    result = summarizer.fetch_web_content(url)
    if not result or not result[0]:
        print(f"[错误] 内容获取失败: 未能提取到网页正文")
        return None
    raw_content, dir = result if isinstance(result, tuple) else (result, os.getcwd())
    print(f"获取内容成功, 长度: {len(raw_content)}字符")
    summary = generate_summary(raw_content, api_key, model_name)
    print(f"摘要生成完成, 长度: {len(summary)}字符")
    if not output_path:
        domain = re.sub(r'[^a-zA-Z0-9]', '_', url.split('//')[-1].split('/')[0])
        path_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        output_name = f"{domain}_{path_hash}_summary.md"
        output_path = os.path.join(dir, output_name)
    save_to_markdown(url, summary, output_path, model_name)
    return summary 