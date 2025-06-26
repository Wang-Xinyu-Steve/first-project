from base import BaseSummarizer
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime
from urllib.parse import urljoin
import requests
import random
from useragents import USER_AGENTS
from util._save_raw_text import _save_raw_text

class XiaohongshuSummarizer(BaseSummarizer):
    def _close_xiaohongshu_popup(self):
        assert self.driver is not None
        max_attempts = 3
        for _ in range(max_attempts):
            try:
                close_buttons = self.driver.find_elements(
                    By.XPATH,
                    '//div[contains(@class, "close") and contains(@class, "icon-btn-wrapper")]'
                )
                if close_buttons:
                    self.driver.execute_script("arguments[0].click()", close_buttons[0])
                    time.sleep(1)
                    if not self.driver.find_elements(By.XPATH, '//div[contains(@class, "close")]'):
                        break
            except Exception as e:
                print(f"关闭小红书弹窗时出错: {str(e)}")
                break

    def fetch_web_content(self, url: str):
        if self.driver is None:
            self._init_edge_driver()
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        if "xhslink.com" in url:
            try:
                resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                url = resp.url
            except Exception as e:
                print(f"[错误] 小红书短链跳转失败: {e}")
                return None
        assert self.driver is not None
        self.driver.get(url)
        time.sleep(2)
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@id="detail-title"]'))
        )
        self._close_xiaohongshu_popup()
        title = self.driver.find_element(By.XPATH, '//div[@id="detail-title"]').text.strip()
        author = self.driver.find_element(By.XPATH, '//span[@class="username"]').text.strip()
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        folder_name = f"xiaohongshu_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_dir = os.path.join(desktop, folder_name)
        img_dir = os.path.join(save_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        desc_element = self.driver.find_element(By.XPATH, '//div[@id="detail-desc"]')
        content_text = desc_element.text.strip()
        for _ in range(3):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        main_imgs = self.driver.find_elements(By.XPATH, '//img[contains(@class,"note-slider-img")]')
        desc_imgs = desc_element.find_elements(By.XPATH, './/img')
        all_imgs = main_imgs + desc_imgs
        img_url_set = set()
        img_records = []
        img_index = 1
        inserted_images = set()
        extracted_content = [content_text]
        for img in all_imgs:
            try:
                img_url = (img.get_attribute("src") or 
                        img.get_attribute("data-src") or 
                        img.get_attribute("data-original") or
                        img.get_attribute("data-actualsrc"))
                if img_url and not img_url.startswith(("http://", "https://")):
                    img_url = urljoin(url, img_url)
                if img_url and img_url.startswith(("http://", "https://")):
                    if img_url in img_url_set:
                        continue
                    img_url_set.add(img_url)
                    img_name = f"image_{img_index}.jpg"
                    abs_img_path = os.path.join(img_dir, img_name)
                    if not os.path.exists(abs_img_path):
                        try:
                            img_data = requests.get(img_url, headers=headers, timeout=10).content
                            with open(abs_img_path, 'wb') as f:
                                f.write(img_data)
                        except Exception as download_error:
                            print(f"图片下载失败: {str(download_error)}")
                            continue
                    alt_text = img.get_attribute("alt") or "图片"
                    if img_url not in inserted_images:
                        img_records.append({
                            'path': os.path.join(img_dir, img_name),
                            'alt': alt_text
                        })
                        extracted_content.append(f"[IMAGE_PLACEHOLDER:{len(img_records)-1}]")
                        img_index += 1
                        inserted_images.add(img_url)
            except Exception as e:
                print(f"图片处理失败: {str(e)}")
                continue
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
        extracted_content = f"""# {title}\n\n## 作者信息\n用户名：{author}\n\n## 正文内容\n{chr(10).join(final_content)}\n"""
        _save_raw_text(extracted_content, url, save_dir)
        return extracted_content, save_dir 