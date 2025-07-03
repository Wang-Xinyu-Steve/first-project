from base import BaseSummarizer
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
import random
from typing import Optional, Dict, Any
from useragents import USER_AGENTS
from util._save_raw_text import _save_raw_text
from util.summary_xhs import safe_filename
from PIL import Image
from typing import Optional
import pickle

class XiaohongshuSessionManager:
    """小红书专用的会话管理器"""
    
    def __init__(self):
        pass

    def manual_login(self) -> None:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        print("[XiaohongshuSessionManager] 正在打开小红书登录页面...")
        edge_options = Options()
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        browser_profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_profile_xiaohongshu")
        edge_options.add_argument(f"--user-data-dir={browser_profile_dir}")
        print(f"[DEBUG] 使用浏览器用户数据目录: {browser_profile_dir}")
        driver = webdriver.Edge(options=edge_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get("https://www.xiaohongshu.com/login")
        print("[XiaohongshuSessionManager] 请在浏览器中完成登录操作...")
        input("登录完成后请按回车继续...")
        driver.quit()

class XiaohongshuSummarizer(BaseSummarizer):
    def __init__(self):
        super().__init__()
        self.session_manager = XiaohongshuSessionManager()
        self.driver = None

    def _init_edge_driver(self):
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        edge_options = Options()
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        browser_profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_profile_xiaohongshu")
        edge_options.add_argument(f"--user-data-dir={browser_profile_dir}")
        self.driver = webdriver.Edge(options=edge_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

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
        max_retries = 3
        for attempt in range(max_retries):
            try:
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
                time.sleep(3)  # 增加等待时间
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="detail-title"]'))
                )
                self._close_xiaohongshu_popup()
                title = self.driver.find_element(By.XPATH, '//div[@id="detail-title"]').text.strip()
                author = self.driver.find_element(By.XPATH, '//span[@class="username"]').text.strip()
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                folder_name = safe_filename(f"xiaohongshu_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
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
                extracted_content: list[str] = [content_text]
                for img in all_imgs:  # type: ignore
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
                            img_name = safe_filename(f"image_{img_index}.jpg")
                            abs_img_path = os.path.join(img_dir, img_name)
                            if not os.path.exists(abs_img_path):
                                try:
                                    img_data = requests.get(img_url, headers=headers, timeout=10).content
                                    # 先保存原始图片到临时文件
                                    tmp_path = abs_img_path + ".tmp"
                                    with open(tmp_path, 'wb') as f:
                                        f.write(img_data)
                                    # 用Pillow转换为jpg
                                    try:
                                        with Image.open(tmp_path) as img_pil:
                                            rgb_img = img_pil.convert('RGB')
                                            rgb_img.save(abs_img_path, format='JPEG')
                                        os.remove(tmp_path)
                                    except Exception as e:
                                        print(f"图片格式转换失败: {e}")
                                        os.rename(tmp_path, abs_img_path)  # 保底直接重命名
                                except Exception as download_error:
                                    print(f"图片下载失败: {str(download_error)}")
                                    continue
                            # 只有下载和保存成功后，才获取alt_text
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
                extracted_content_str = f"""# {title}\n\n## 作者信息\n用户名：{author}\n\n## 正文内容\n{chr(10).join(final_content)}\n"""
                _save_raw_text(extracted_content_str, url, save_dir)
                # 收集图片路径列表，供多模态API使用
                img_paths = [img_info['path'] for img_info in img_records]
                return extracted_content_str, save_dir, img_paths
                
            except Exception as e:
                print(f"[尝试 {attempt + 1}/{max_retries}] 处理失败: {str(e)}")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                if attempt < max_retries - 1:
                    print("等待5秒后重试...")
                    time.sleep(5)
                else:
                    print("所有重试都失败了")
                    return None 