import os
from datetime import datetime
import re

def safe_filename(s, allow_chinese=True):
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

def _save_raw_text(content: str, url: str, save_path):
    try:
        domain = re.sub(r'\W+', '_', url.split('//')[-1].split('/')[0])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 保留中文，去除emoji
        filename = safe_filename(f"raw_{domain}_{timestamp}.txt", allow_chinese=True)
        output_path = os.path.join(save_path, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n")
            f.write(f"Saved at: {datetime.now()}\n\n")
            f.write(content if content else "NULL_CONTENT")
        print(f"原始文本已保存到桌面: {output_path}")
        print(f"保存路径: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"[警告] 原始文本保存失败: {str(e)}") 