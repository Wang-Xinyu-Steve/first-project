from selenium import webdriver
from selenium.webdriver.edge.options import Options
import time
import os
import datetime

class XiaoyuzhouFMParser:
    def get_audio_info(self, url):
        edge_options = Options()
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        driver = webdriver.Edge(options=edge_options)
        driver.get(url)
        time.sleep(5)  # 等待页面加载
        try:
            audio_elem = driver.find_element("tag name", "audio")
            audio_url = audio_elem.get_attribute("src")
            title = driver.title
            driver.quit()
            if audio_url:
                return {
                    "audio_url": audio_url,
                    "title": title
                }
            else:
                raise Exception("未找到音频直链")
        except Exception as e:
            driver.quit()
            raise Exception(f"未找到音频直链: {e}")

def get_save_folder(title):
    safe_title = "".join([c for c in title if c.isalnum() or c in '_-（）()【】 ']).strip().replace(' ', '_')
    now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = os.path.join(os.path.expanduser('~'), 'Desktop', f'xiaoyuzhoufm_{safe_title}_{now_str}')
    os.makedirs(folder, exist_ok=True)
    return folder 