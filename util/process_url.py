import os
import re
import hashlib
from util.generate_summary import generate_summary
from util.save_to_markdown import save_to_markdown
from typing import Optional
from util.summary_xhs import summary_xhs

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

def process_url(summarizer, url: str, api_key: str, model_name: str, output_path: Optional[str] = None):
    print(f"开始处理: {url}")
    result = summarizer.fetch_web_content(url)
    if not result or not result[0]:
        print(f"[错误] 内容获取失败: 未能提取到网页正文")
        return None
    
    # 处理返回值，兼容不同Summarizer的返回格式
    if len(result) == 3:  # 小红书：返回 (content, save_dir, img_paths)
        raw_content, dir, img_paths = result
    else:  # 其他平台：返回 (content, save_dir)
        raw_content, dir = result
        img_paths = []
    
    print(f"获取内容成功, 长度: {len(raw_content)}字符")
    if "xiaohongshu.com" in url or "xhslink.com" in url:
        summary = summary_xhs(raw_content, img_paths, api_key, model_name)
    else:
        summary = generate_summary(raw_content, api_key, model_name)
    print(f"摘要生成完成, 长度: {len(summary)}字符")
    if not output_path:
        domain = re.sub(r'[^a-zA-Z0-9]', '_', url.split('//')[-1].split('/')[0])
        path_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        # 保留中文，去除emoji
        output_name = safe_filename(f"{domain}_{path_hash}_summary.md")
        output_path = os.path.join(dir, output_name)
    save_to_markdown(url, summary, output_path, model_name)
    return summary 