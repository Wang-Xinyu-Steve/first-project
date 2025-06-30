from base import BaseSummarizer
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime
from urllib.parse import urljoin
import re
from util._save_raw_text import _save_raw_text
from util.summary_xhs import safe_filename
from PIL import Image

class WeixinSummarizer(BaseSummarizer):
    def fetch_web_content(self, url: str):
        if self.driver is None or not hasattr(self.driver, 'requests'):
            self._init_edge_wire_driver()
        assert self.driver is not None
        self.driver.get(url)
        time.sleep(2)
        assert self.driver is not None
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//h1[@id="activity-name"]'))
        )
        title = self.driver.find_element(By.XPATH, '//h1[@id="activity-name"]').text.strip()
        author = self.driver.find_element(By.XPATH, '//div[@id="meta_content"]').text.strip()
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        folder_name = safe_filename(f"weixin_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        save_dir = os.path.join(desktop, folder_name)
        img_dir = os.path.join(save_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        print("[DEBUG] 页面加载后等待5秒...")
        time.sleep(5)
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_step = 300
        current_position = 0
        while current_position < last_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(0.5)
            current_position += scroll_step
            last_height = self.driver.execute_script("return document.body.scrollHeight")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        content_div = self.driver.find_element(By.XPATH, '//div[@id="js_content"]')
        img_records = []
        img_index = [1]
        inserted_images = set()
        seen_texts = set()
        def extract_content(element):
            content = []
            tag_name = element.tag_name.lower()
            if tag_name == 'img':
                img_url = (
                    element.get_attribute("src") or 
                    element.get_attribute("data-src") or 
                    element.get_attribute("data-original") or
                    element.get_attribute("data-actualsrc")
                )
                if img_url:
                    img_url = urljoin(url, img_url.split('?')[0])
                if img_url and img_url not in inserted_images:
                    img_name = safe_filename(f"image_{img_index[0]}.jpg")
                    abs_img_path = os.path.join(img_dir, img_name)
                    for req in self.driver.requests:  # type: ignore
                        if req.response and req.url.split('?')[0] == img_url:
                            if not os.path.exists(abs_img_path):
                                # 先保存原始图片到临时文件
                                tmp_path = abs_img_path + ".tmp"
                                with open(tmp_path, 'wb') as f:
                                    f.write(req.response.body)
                                # 用Pillow转换为jpg
                                try:
                                    with Image.open(tmp_path) as img:
                                        rgb_img = img.convert('RGB')
                                        rgb_img.save(abs_img_path, format='JPEG')
                                    os.remove(tmp_path)
                                except Exception as e:
                                    print(f"图片格式转换失败: {e}")
                                    os.rename(tmp_path, abs_img_path)  # 保底直接重命名
                            break
                    img_records.append({
                        'path': os.path.join(img_dir, img_name),
                        'alt': element.get_attribute("alt") or "图片"
                    })
                    content.append(f"[IMAGE_PLACEHOLDER:{len(img_records)-1}]")
                    img_index[0] += 1
                    inserted_images.add(img_url)
            else:
                children = element.find_elements(By.XPATH, './*')
                if not children:
                    text = (element.get_attribute('textContent') or '').strip()
                    norm_text = re.sub(r'\s+', '', text)
                    if norm_text and norm_text not in seen_texts:
                        content.append(text)
                        seen_texts.add(norm_text)
                for child in children:
                    content.extend(extract_content(child))
            return content
        extracted_content = extract_content(content_div)
        final_content = []
        for item in extracted_content:
            if isinstance(item, str) and item.startswith("[IMAGE_PLACEHOLDER:"):
                try:
                    img_id = int(item.split(":")[1].rstrip("]"))
                    img_info = img_records[img_id]
                    path = img_info['path'].replace("\\", "/")
                    final_content.append(f"![{img_info['alt']}]({path})")
                except Exception as e:
                    print(f"图片占位符处理失败: {e}")
                    continue
            else:
                final_content.append(item)
        extracted_content = f"""# {title}\n\n## 作者信息\n{author}\n\n## 正文内容\n{chr(10).join(final_content)}\n"""
        _save_raw_text(extracted_content, url, save_dir)
        return extracted_content, save_dir 