import os
from datetime import datetime
import re

def _save_raw_text(content: str, url: str, save_path):
    try:
        domain = re.sub(r'\W+', '_', url.split('//')[-1].split('/')[0])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_{domain}_{timestamp}.txt"
        output_path = os.path.join(save_path, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n")
            f.write(f"Saved at: {datetime.now()}\n\n")
            f.write(content if content else "NULL_CONTENT")
        print(f"原始文本已保存到桌面: {output_path}")
        print(f"保存路径: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"[警告] 原始文本保存失败: {str(e)}") 