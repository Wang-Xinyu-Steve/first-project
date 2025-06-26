from datetime import datetime

def save_to_markdown(url: str, summary: str, output_path: str, model_name: str):
    md_content = f"""# 网页内容摘要

**源URL**: [{url}]({url})

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**模型**: {model_name}

---

{summary}
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"摘要已保存至: {output_path}") 