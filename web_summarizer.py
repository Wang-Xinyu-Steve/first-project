import argparse
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from trafilatura.settings import use_config
import os
import re
import hashlib
import json
from datetime import datetime
import time
import random
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
from typing import Optional

USER_AGENTS = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0",
    
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # 移动端
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36"
]

# 依赖检查
REQUIRED_MODULES = [
    'argparse', 'urllib.parse', 'requests', 'bs4', 'trafilatura', 'os', 're', 'hashlib', 'json',
    'datetime', 'time', 'random', 'selenium', 'webdriver_manager',
]
missing = []
for mod in REQUIRED_MODULES:
    try:
        __import__(mod.split('.')[0])
    except ImportError:
        missing.append(mod)
if missing:
    print(f"[依赖缺失] 请先安装以下依赖: {', '.join(set(missing))}")
    print("推荐命令: pip install requests beautifulsoup4 trafilatura selenium webdriver-manager")
    sys.exit(1)

class DeepSeekSummarizer:
    save_dir = ""
    # 参数配置
    SCROLL_STEP = 800
    WAIT_TIME = (1.0, 2.0)
    MAX_CHARS = 10000
    def __init__(self, api_key: str, model_name: str = "deepseek-chat"):
        """
        初始化DeepSeek摘要生成器
        
        :param api_key: DeepSeek API密钥
        :param model_name: 使用的大模型名称
        """
        self.model_name = model_name
        self.api_key = api_key
        self.driver = None  # Edge 浏览器实例
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # 配置Trafilatura（高级内容提取库）
        self.trafilatura_config = use_config()
        self.trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")  # 禁用超时
    
    def _init_edge_driver(self):
        """初始化 Edge 浏览器（仅在需要时调用）"""
        edge_options = Options()
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_argument("--start-maximized")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # 隐藏自动化特征
        edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
        
        try:
            self.driver = webdriver.Edge(
                service=Service(EdgeChromiumDriverManager().install()),
                options=edge_options
            )
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
            )
        except Exception as e:
            print(f"[错误] Edge浏览器初始化失败: {e}")
            raise
    
    def _close_zhihu_popup(self):
        """精准关闭知乎所有弹窗（使用SVG路径定位）"""
        if self.driver is None:
            try:
                self._init_edge_driver()
            except Exception as e:
                print(f"Edge驱动初始化失败: {e}")
                return
        if self.driver is None:
            print("Edge驱动未初始化，无法关闭弹窗")
            return
        max_attempts = 3  # 最大尝试次数
        for _ in range(max_attempts):
            try:
                # 通过SVG路径定位关闭按钮
                close_buttons = self.driver.find_elements(
                    By.XPATH,
                    '//button[contains(@class, "Modal-closeButton")]//*[name()="svg"][contains(@class, "Modal-closeIcon")]'
                )
            # 修复：find_elements 应该是 WebDriver 的方法，确保 self.driver 已初始化且为 WebDriver 实例
                if close_buttons:
                    # 使用JavaScript直接点击（绕过元素拦截）
                    self.driver.execute_script("arguments[0].closest('button').click()", close_buttons[0])
                    print("使用SVG路径精准关闭弹窗")
                    time.sleep(1)  # 等待弹窗完全消失
                
                    # 二次确认弹窗已关闭
                    if not self.driver.find_elements(By.CLASS_NAME, "Modal-wrapper"):
                        break
            except Exception as e:
                print(f"关闭弹窗时出错: {str(e)}")
                break

    def _close_xiaohongshu_popup(self):
        """精准关闭小红书所有弹窗"""
        if self.driver is None:
            try:
                self._init_edge_driver()
            except Exception as e:
                print(f"Edge驱动初始化失败: {e}")
                return
        if self.driver is None:
            print("Edge驱动未初始化，无法关闭小红书弹窗")
            return
        max_attempts = 3  # 最大尝试次数
        for _ in range(max_attempts):
            try:
                # 通过class定位关闭按钮
                close_buttons = self.driver.find_elements(
                    By.XPATH,
                    '//div[contains(@class, "close") and contains(@class, "icon-btn-wrapper")]'
                )
        
                if close_buttons:
                    # 使用JavaScript直接点击（绕过元素拦截）
                    self.driver.execute_script("arguments[0].click()", close_buttons[0])
                    print("成功关闭小红书弹窗")
                    time.sleep(1)  # 等待弹窗完全消失
            
                    # 二次确认弹窗已关闭
                    if not self.driver.find_elements(By.XPATH, '//div[contains(@class, "close")]'):
                        break
            except Exception as e:
                print(f"关闭小红书弹窗时出错: {str(e)}")
                break

    def _save_raw_text(self, content: str, url: str, save_path):
        """将原始文本保存到桌面固定位置"""
        try:
            # 生成唯一文件名
            domain = re.sub(r'\W+', '_', url.split('//')[-1].split('/')[0])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"raw_{domain}_{timestamp}.txt"
            output_path = os.path.join(save_path, filename)

            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Saved at: {datetime.now()}\n\n")
                f.write(content if content else "NULL_CONTENT")
        
            print(f"原始文本已保存到桌面: {output_path}")
            print(f"保存路径: {os.path.abspath(output_path)}")  # 打印绝对路径便于查找
        except Exception as e:
            print(f"[警告] 原始文本保存失败: {str(e)}")

    def _close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def fetch_web_content(self, url: str) -> tuple[str, str] | None:
        """
        获取网页并提取主要内容（增强版）
        修改点：1. 增加完整请求头  2. 优化异常处理  3. 添加动态Cookie支持
        """
        print(f"[DEBUG] fetch_web_content: 开始处理 {url}")
        # ---------------------------- 新增部分 ----------------------------
        # 模拟浏览器的完整请求头
        headers = {
        'User-Agent': random.choice(USER_AGENTS),  # 关键修改点
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://www.google.com/',  # 伪装从Google跳转
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Connection': 'keep-alive',
        'DNT': '1'  # 禁止追踪
        }
        raw_content = None
        
        if "xhslink.com" in url:
            try:
                resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                url = resp.url  # 跳转后的真实小红书URL
                print(f"[DEBUG] 短链跳转后真实URL: {url}")
            except Exception as e:
                print(f"[错误] 小红书短链跳转失败: {e}")
                return None
        
        if "zhihu.com" in url:
            print(f"[DEBUG] 进入知乎分支: {url}")
            if self.driver is None:
                try:
                    self._init_edge_driver()
                except Exception as e:
                    print(f"Edge驱动初始化失败: {e}")
                    return None
            if self.driver is None:
                print("Edge驱动未初始化，无法打开网页")
                return None
            try:
                self.driver.get(url)
                print("[DEBUG] 已打开知乎页面")
                if "/question/" in url:
                    print("[DEBUG] 进入知乎问题页面分支")
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, '//h1[contains(@class, "QuestionHeader-title")]' ))
                    )

                    self._close_zhihu_popup()

                    # 1. 标题
                    title = self.driver.find_element(
                        By.XPATH, '//h1[contains(@class,"QuestionHeader-title")]'
                    ).text.strip()

                    # 新增：创建保存目录
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                    folder_name = f"zhihu_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    save_dir = os.path.join(desktop, folder_name)
                    img_dir = os.path.join(save_dir, "images")
                    os.makedirs(img_dir, exist_ok=True)

                    # 2. 问题描述
                    try:
                        description_elem = self.driver.find_element(
                            By.XPATH, '//div[contains(@class,"QuestionRichText")]//span[@itemprop="text"]'
                        )
                        description = description_elem.text.strip()
                    except Exception:
                        try:
                            description_elem = self.driver.find_element(
                                By.XPATH, '//div[contains(@class,"QuestionRichText")]'
                            )
                            description = description_elem.text.strip()
                        except Exception:
                            description = "无问题描述"

                    # 3. 回答内容
                    seen_texts = set()
                    extracted_content = []
                    img_records = []  # 用于存储图片记录
                    img_index = 1
                    seen_images = set()
                    inserted_images = set()
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    scroll_step = 800  # 增大滚动步长以提高效率
                    current_position = 0

                    while current_position < last_height:
                        print(f"[DEBUG] 滚动到: {current_position}/{last_height}")
                        # 滚动到当前位置
                        self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                        time.sleep(random.uniform(1.0, 2.0))  # 优化等待时间

                        # 在滚动前，先全局多次点击"展开阅读全文"
                        for _ in range(3):
                            expand_buttons = self.driver.find_elements(
                                By.XPATH, '//button[contains(text(), "展开阅读全文") or contains(@class, "ContentItem-expandButton")]'
                            )
                            if not expand_buttons:
                                break
                            for btn in expand_buttons:
                                try:
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    time.sleep(0.3)
                                except Exception:
                                    continue
                            time.sleep(1)

                        # 每次滚动后重新获取回答容器
                        try:
                            content_div = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((
                                    By.XPATH,
                                    '//div[contains(@class,"QuestionAnswers-answers") or contains(@class,"Question-main")]'
                                ))
                            )
                            print("[DEBUG] 找到知乎回答主容器")
                        except Exception as e:
                            print(f"[DEBUG] 未找到知乎回答主容器: {e}")
                            break

                        answer_divs = content_div.find_elements(By.XPATH, './/div[contains(@class, "AnswerItem") or contains(@class, "ContentItem")]')
                        print(f"[DEBUG] 找到回答容器数量: {len(answer_divs)}")
                        
                        for answer_div in answer_divs:
                            try:
                                # 每次都重新查找 RichContent-inner
                                rich_inners = answer_div.find_elements(By.CSS_SELECTOR, 'div.RichContent-inner')
                                for rich_inner in rich_inners:
                                    rich_texts = rich_inner.find_elements(By.CSS_SELECTOR, 'span.RichText')
                                    for rich_text in rich_texts:
                                        paragraphs = rich_text.find_elements(By.TAG_NAME, 'p')
                                        answer_text = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                                        if answer_text and answer_text not in seen_texts:
                                            seen_texts.add(answer_text)
                                            extracted_content.append(answer_text)
                                        # 新增：处理图片（插入占位符去重）
                                        img_elements = rich_text.find_elements(By.XPATH, './/img')
                                        for img in img_elements:
                                            try:
                                                img_url = (img.get_attribute("src") or 
                                                           img.get_attribute("data-src") or 
                                                           img.get_attribute("data-original") or
                                                           img.get_attribute("data-actualsrc"))
                                                if img_url and not img_url.startswith(("http://", "https://")):
                                                    img_url = urljoin(url, img_url)
                                                if img_url and img_url.startswith(("http://", "https://")):
                                                    if img_url in seen_images:
                                                        continue
                                                    seen_images.add(img_url)
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
                                                # 只在第一次遇到该图片时插入占位符
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
                            except Exception as e:
                                print(f"[DEBUG] 回答内容提取失败: {e}")
                                continue
                        # 更新滚动位置
                        current_position += scroll_step
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        if new_height > last_height:
                            last_height = new_height
                    
                    # 处理图片占位符，替换为Markdown图片语法
                    final_content = []
                    for item in extracted_content:
                        if isinstance(item, str) and item.startswith("[IMAGE_PLACEHOLDER:"):
                            try:
                                img_id = int(item.split(":")[1].rstrip("]"))
                                img_info = img_records[img_id]
                                path = img_info['path'].replace("\\", "/")
                                if not os.path.exists(img_info['path']):
                                    print(f"警告：文件不存在 - {img_info['path']}")
                                final_content.append(f"![{img_info['alt']}]({path})")
                            except Exception as e:
                                print(f"图片占位符处理失败: {e}")
                                continue
                        else:
                            final_content.append(item)
                    
                    # 生成最终内容
                    print(f"[DEBUG] extracted_content 长度: {len(extracted_content)}")
                    print(f"[DEBUG] extracted_content 内容: {extracted_content[:3]}")  # 只打印前3项
                    content = "\n".join([str(item) for item in final_content])
                    extracted_content = f"""# {title}\n\n## 问题描述\n{description}\n\n## 回答\n{content}"""
                    
                    # 保存原始文本
                    self._save_raw_text(extracted_content, url, save_dir)
                    
                    return extracted_content, save_dir
                    
                else:
                    print("[DEBUG] 进入知乎专栏页面分支")
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, '//h1[contains(@class,"Post-Title")]'))
                        )
                        self._close_zhihu_popup()
                    except Exception as e:
                        print(f"[DEBUG] 未找到知乎专栏标题: {e}")
                        return None

                    # 1. 标题提取（更宽松的定位）
                    title = self.driver.find_element(
                        By.XPATH, 
                        '//h1[contains(@class,"Post-Title")]'
                    ).text.strip()

                    # 2. 作者信息提取（多重定位策略）
                    author_info = {}
                    try:
                        # 尝试多种定位方式
                        author_elements = [
                            '//div[contains(@class,"AuthorInfo")]//meta[@itemprop="name"]',  # meta方式
                            '//div[contains(@class,"AuthorInfo-name")]//a',  # 直接链接方式
                            '//div[contains(@class,"AuthorInfo")]//span[contains(@class,"UserLink")]'  # 备用方式
                        ]
                
                        for xpath in author_elements:
                            try:
                                element = self.driver.find_element(By.XPATH, xpath)
                                author_info['name'] = element.get_attribute('content') or element.text
                                break
                            except:
                                continue

                        # 作者简介提取
                        bio_elements = [
                            '//div[contains(@class,"AuthorInfo-badgeText")]',
                            '//div[contains(@class,"AuthorInfo-head")]//span[contains(@class,"RichText")]'
                        ]
                
                        for xpath in bio_elements:
                            try:
                                author_info['bio'] = self.driver.find_element(By.XPATH, xpath).text
                                break
                            except:
                                continue

                    except Exception as auth_error:
                        print(f"作者信息提取失败: {str(auth_error)}")
                        author_info = {'name': '未知', 'bio': '未获取到简介'}

                    # 2. 创建保存目录
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                    folder_name = f"zhihu_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    save_dir = os.path.join(desktop, folder_name)
                    img_dir = os.path.join(save_dir, "images")
                    os.makedirs(img_dir, exist_ok=True)

                    # 3. 滚动加载所有内容
                    seen_texts = set()
                    seen_images = set()
                    inserted_images = set()
                    extracted_content = []
                    img_records = []  # 新增：用于存储图片记录
                    img_index = 1
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    scroll_step = 500
                    current_position = 0

                    while current_position < last_height:
                        self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                        time.sleep(random.uniform(1.5, 2.5))

                        # 获取正文容器
                        content_div = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((
                                By.XPATH,
                                '//div[contains(@class,"RichText") and contains(@class,"ztext") and contains(@class,"Post-RichText")]'
                            ))
                        )

                        # 获取所有子节点（保持原始顺序）
                        all_elements = content_div.find_elements(By.XPATH, "./*")
                        
                        for element in all_elements:
                            tag_name = element.tag_name.lower()
                            text = (element.get_attribute('textContent') or '').strip()  # 使用textContent获取完整文本    

                            img_elements = []
                            # 处理图片 - 修改为占位符模式
                            if tag_name in ["figure", "div"]:
                                img_elements = element.find_elements(By.XPATH, ".//img")
                                for img in img_elements:
                                    try:
                                        img_url = (img.get_attribute("src") or 
                                                img.get_attribute("data-src") or 
                                                img.get_attribute("data-original") or
                                                img.get_attribute("data-actualsrc"))
                                        if img_url and not img_url.startswith(("http://", "https://")):
                                            img_url = urljoin(url, img_url)

                                        if img_url and img_url.startswith(("http://", "https://")):
                                            if img_url in seen_images:
                                                continue
                                            seen_images.add(img_url)
                                            
                                            img_name = f"image_{img_index}.jpg"
                                            abs_img_path = os.path.join(img_dir, img_name)
                                            print(img_url)#
                                            if not os.path.exists(abs_img_path):
                                                try:
                                                    img_data = requests.get(img_url, headers=headers, timeout=10).content
                                                    with open(abs_img_path, 'wb') as f:
                                                        f.write(img_data)
                                                except Exception as download_error:
                                                    print(f"图片下载失败: {str(download_error)}")
                                                    continue
                                            
                                            alt_text = element.get_attribute("alt") or "图片"
                                            # 只在第一次遇到该图片时插入占位符
                                            if img_url not in inserted_images:
                                                img_records.append({
                                                    'path': os.path.join(img_dir, img_name),
                                                    'alt': alt_text
                                                })
                                                extracted_content.append(f"[IMAGE_PLACEHOLDER:{len(img_records)-1}]")
                                                img_index += 1
                                                inserted_images.add(img_url)
                                        else:
                                            print("未找到图片")#
                                            
                                    except Exception as e:
                                        print(f"图片处理失败: {str(e)}")
                                        continue  # 图片处理失败时跳过

                            # 处理列表
                            elif tag_name in ['ul', 'ol']:     
                                # 处理整个列表
                                list_items = []
                                for li in element.find_elements(By.XPATH, "./li"):
                                    li_text = (li.get_attribute('textContent') or '').strip()
                                    if li_text and li_text not in seen_texts:
                                        seen_texts.add(li_text)
                                        list_items.append(f"• {li_text}")
                                if list_items:
                                    extracted_content.append("\n".join(list_items))

                            elif tag_name == 'pre':
                                # 处理代码块
                                code_element = element.find_element(By.XPATH, ".//code")
                                if code_element:
                                    code_text = (code_element.get_attribute('textContent') or '').strip()
                                    if code_text and code_text not in seen_texts:
                                        seen_texts.add(code_text)
                                        extracted_content.append(f"\n```\n{code_text}\n```\n")
                                else:
                                    code_text = (element.get_attribute('textContent') or '').strip()
                                    if code_text and code_text not in seen_texts:
                                        seen_texts.add(code_text)
                                        extracted_content.append(f"\n```\n{code_text}\n```\n")
                    
                            elif tag_name == 'code':
                                # 处理行内代码
                                code_text = (element.get_attribute('textContent') or '').strip()
                                if code_text and code_text not in seen_texts:
                                    seen_texts.add(code_text)
                                    extracted_content.append(f"`{code_text}`")
                            
                             # 处理标题
                            elif tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                level = int(tag_name[1])
                                if text not in seen_texts:
                                    seen_texts.add(text)
                                    extracted_content.append(f"\n{'#' * level} {text}\n")

                            # 处理段落和其他文本
                            elif tag_name in ['p', 'div', 'span']:
                                # 处理特殊格式的文本（如带星标的）
                                cls = element.get_attribute("class") or ""
                                if "RichContent-EntityWord" in cls:
                                    text = text.replace("⍟", "").strip()
                                    
                                if text and text not in seen_texts:
                                    seen_texts.add(text)
                                    # 处理加粗文本
                                    if "bold" in cls.lower():
                                        extracted_content.append(f"**{text}**")
                                    else:
                                        extracted_content.append(text)
                        # 更新滚动位置
                        current_position += scroll_step
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        if new_height > last_height:
                            last_height = new_height
                    
                    # 生成最终内容前，替换占位符
                    final_content = []
                    
                    for item in extracted_content:
                        item_str = str(item)
                        if item_str.startswith("[IMAGE_PLACEHOLDER:"):
                            try:
                                img_id = int(item_str.split(":")[1].rstrip("]"))
                                img_info = img_records[img_id]
                                path = img_info['path'].replace("\\", "/")  # 处理路径分隔符
                                if not os.path.exists(img_info['path']):
                                    print(f"警告：文件不存在 - {img_info['path']}")
                                final_content.append(f"![{img_info['alt']}]({path})")
                            except Exception as e:
                                print(f"处理占位符失败：{item}，错误：{e}")
                        else:
                            final_content.append(item_str)

                    # 将结果写回原列表
                    extracted_content = final_content

                    # 4. 生成最终内容
                    print(f"[DEBUG] extracted_content 长度: {len(extracted_content)}")
                    print(f"[DEBUG] extracted_content 内容: {extracted_content[:3]}")  # 只打印前3项
                    content = "\n".join(extracted_content)
                    extracted_content = f"""# {title}

                ## 作者信息
                姓名：{author_info['name']}
                简介：{author_info['bio']}

                ## 正文内容
                {content}
                """
                    raw_content = extracted_content
                    self._save_raw_text(raw_content, url, save_dir)
                    
                    return raw_content, save_dir
                    
            except Exception as e:
                print(f"[DEBUG] Edge获取知乎内容失败: {str(e)}")
                return None
            
        elif "xiaohongshu.com" in url:
            print(f"[DEBUG] 进入小红书分支: {url}")
            if self.driver is None:
                try:
                    self._init_edge_driver()
                except Exception as e:
                    print(f"Edge驱动初始化失败: {e}")
                    return None
            if self.driver is None:
                print("Edge驱动未初始化，无法打开网页")
                return None
            try:
                self.driver.get(url)
                print("[DEBUG] 已打开小红书页面")
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="detail-title"]'))
                )
                self._close_xiaohongshu_popup()

                # 1. 标题提取
                title = self.driver.find_element(
                    By.XPATH, 
                    '//div[@id="detail-title"]'
                ).text.strip()

                # 2. 作者信息提取
                author = self.driver.find_element(
                    By.XPATH,
                    '//span[@class="username"]'
                ).text.strip()

                # 创建保存目录
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                folder_name = f"xiaohongshu_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                save_dir = os.path.join(desktop, folder_name)
                img_dir = os.path.join(save_dir, "images")
                os.makedirs(img_dir, exist_ok=True)

                # 3. 正文内容提取
                desc_element = self.driver.find_element(
                    By.XPATH,
                    '//div[@id="detail-desc"]'
                )
                # 获取正文文本
                content_text = desc_element.text.strip()

                # 滚动页面确保主图全部加载
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)

                # 精确提取主图
                main_imgs = self.driver.find_elements(By.XPATH, '//img[contains(@class,"note-slider-img")]')
                # 正文内嵌图片/表情
                desc_imgs = desc_element.find_elements(By.XPATH, './/img')
                # 合并去重
                all_imgs = main_imgs + desc_imgs
                img_url_set = set()
                img_records = []
                img_index = 1
                inserted_images = set()
                extracted_content = [content_text]
                for img in all_imgs:
                    try:
                        print(img.get_attribute("outerHTML"))  # 调试输出实际抓到的图片节点
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

                # 处理图片占位符，替换为Markdown图片语法
                final_content = []
                for item in extracted_content:
                    if isinstance(item, str) and item.startswith("[IMAGE_PLACEHOLDER:"):
                        try:
                            img_id = int(item.split(":")[1].rstrip("]"))
                            img_info = img_records[img_id]
                            path = img_info['path'].replace("\\", "/")
                            if not os.path.exists(img_info['path']):
                                print(f"警告：文件不存在 - {img_info['path']}")
                            final_content.append(f"![{img_info['alt']}]({path})")
                        except Exception as e:
                            print(f"图片占位符处理失败: {e}")
                            continue
                    else:
                        final_content.append(item)

                # 结构化输出
                extracted_content = f"""# {title}

## 作者信息
用户名：{author}

## 正文内容
{chr(10).join(final_content)}
"""
                raw_content = extracted_content
                self._save_raw_text(raw_content, url, save_dir)
                return raw_content, save_dir

            except Exception as e:
                print(f"[DEBUG] Edge获取小红书内容失败: {str(e)}")
                return None
        
        elif "weixin.qq.com" in url:  # 微信域名
            print(f"[DEBUG] 进入微信分支: {url}")
            if self.driver is None:
                try:
                    self._init_edge_driver()
                except Exception as e:
                    print(f"Edge驱动初始化失败: {e}")
                    return None
            if self.driver is None:
                print("Edge驱动未初始化，无法打开网页")
                return None
            try:
                self.driver.get(url)
                print("[DEBUG] 已打开微信页面")
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//h1[@id="activity-name"]'))
                )

                # 1. 标题提取
                title = self.driver.find_element(
                    By.XPATH, 
                    '//h1[@id="activity-name"]'
                ).text.strip()

                # 2. 作者信息提取
                author = self.driver.find_element(
                    By.XPATH,
                    '//div[@id="meta_content"]'
                ).text.strip()
                
                # 创建保存目录
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                folder_name = f"weixin_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                save_dir = os.path.join(desktop, folder_name)
                img_dir = os.path.join(save_dir, "images")
                os.makedirs(img_dir, exist_ok=True)

                # 3. 正文内容提取
                # 先滚动确保内容加载
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                # 提取所有段落
                paragraphs = self.driver.find_elements(
                    By.XPATH,
                    '//section[@data-role="paragraph"]//p[normalize-space()]'
                )
                content_text = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])

                # 新增：图片提取、去重、保存
                img_elements = self.driver.find_elements(By.XPATH, '//section[@data-role="paragraph"]//img')
                img_records = []
                img_index = 1
                seen_images = set()
                inserted_images = set()
                extracted_content = [content_text]
                for idx in range(len(img_elements)):
                    try:
                        img_elements_fresh = self.driver.find_elements(By.XPATH, '//section[@data-role="paragraph"]//img')
                        if idx >= len(img_elements_fresh):
                            continue
                        img = img_elements_fresh[idx]
                        img_url = (img.get_attribute("src") or 
                                img.get_attribute("data-src") or 
                                img.get_attribute("data-original") or
                                img.get_attribute("data-actualsrc"))
                        if img_url and not img_url.startswith(("http://", "https://", "data:image")):
                            img_url = urljoin(url, img_url)
                        img_name = f"image_{img_index}.jpg"
                        abs_img_path = os.path.join(img_dir, img_name)
                        if img_url and img_url.startswith("data:image"):
                            import base64
                            header, encoded = img_url.split(",", 1)
                            img_data = base64.b64decode(encoded)
                            with open(abs_img_path, 'wb') as f:
                                f.write(img_data)
                        elif img_url and img_url.startswith(("http://", "https://")):
                            if img_url in seen_images:
                                continue
                            seen_images.add(img_url)
                            try:
                                img_data = requests.get(img_url, headers=headers, timeout=10).content
                                with open(abs_img_path, 'wb') as f:
                                    f.write(img_data)
                            except Exception as download_error:
                                print(f"图片下载失败: {str(download_error)}")
                                continue
                        else:
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

                # 处理图片占位符，替换为Markdown图片语法
                final_content = []
                for item in extracted_content:
                    if isinstance(item, str) and item.startswith("[IMAGE_PLACEHOLDER:"):
                        try:
                            img_id = int(item.split(":")[1].rstrip("]"))
                            img_info = img_records[img_id]
                            path = img_info['path'].replace("\\", "/")
                            if not os.path.exists(img_info['path']):
                                print(f"警告：文件不存在 - {img_info['path']}")
                            final_content.append(f"![{img_info['alt']}]({path})")
                        except Exception as e:
                            print(f"图片占位符处理失败: {e}")
                            continue
                    else:
                        final_content.append(item)

                # 结构化输出
                extracted_content = f"""# {title}

## 作者信息
{author}

## 正文内容
{chr(10).join(final_content)}
"""
                raw_content = extracted_content
                self._save_raw_text(raw_content, url, save_dir)
                return raw_content, save_dir

            except Exception as e:
                print(f"[DEBUG] 微信内容提取失败: {str(e)}")
                if self.driver:
                    self.driver.save_screenshot('weixin_error.png')
                return None
                   
        else:
            print(f"[DEBUG] 进入通用网页分支: {url}")
            try:
                response = requests.get(url, headers=headers, timeout=15)
                print(f"[DEBUG] 通用网页状态码: {response.status_code}")
                print(f"[DEBUG] 最终请求URL: {response.url}")
                
                if "login" in response.url.lower():
                    print(f"[DEBUG] 被重定向到登录页: {response.url}")
                    raise RuntimeError(f"被重定向到登录页: {response.url}")
                
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                for element in soup(['header', 'footer', 'nav', 'aside', 'script', 'style']):
                    element.decompose()

                #创建保存目录
                domain = re.sub(r'[^a-zA-Z0-9]', '_', url.split('//')[-1].split('/')[0])
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                folder_name = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                save_dir = os.path.join(desktop, folder_name)
                os.makedirs(save_dir, exist_ok=True)
                
                main_content = (soup.find('main') or 
                            soup.find('article') or 
                            soup.find('div', class_=re.compile(r'content|main|post', re.I)))
            
                raw_content = main_content.get_text(separator='\n', strip=True) if main_content else soup.get_text(separator='\n', strip=True)

                self._save_raw_text(raw_content, url, save_dir)

            except Exception as e:
                error_msg = f"""
    [内容提取失败] URL: {url}
    错误类型: {type(e).__name__}
    详细信息: {str(e)}
    建议操作: {'请添加Cookie' if 'login' in str(e) else '检查反爬机制或重试'}
                """
                print(error_msg)
                return None
    
        if not raw_content or not save_dir:
            return None
        return raw_content, save_dir  # 最终统一返回


    def chunk_content(self, text: str, max_chars: Optional[int] = None) -> list:
        if max_chars is None:
            max_chars = self.MAX_CHARS
        paragraphs = text.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
                
            para_length = len(para)
            
            # 如果当前块长度+新段落长度超过限制，且当前块不为空，则保存当前块
            if current_length + para_length > max_chars and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
                
            current_chunk.append(para)
            current_length += para_length
            
        # 添加最后一个块
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        return chunks

    def generate_summary(self, text: str) -> str:
        """
        使用DeepSeek API生成文本摘要
        
        :param text: 输入文本
        :return: Markdown格式的摘要
        """
        chunks = self.chunk_content(text)
        summaries = []
        
        print(f"检测到 {len(chunks)} 个文本块需要处理")
        
        for i, chunk in enumerate(chunks):
            print(f"处理分块 {i+1}/{len(chunks)} (约 {len(chunk)} 字符)")
            
            # 构造DeepSeek API请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的摘要生成专家。请生成结构化、简洁、包含要点的Markdown格式摘要。保留关键数据和专业术语。使用中文输出结果。"
                    },
                    {
                        "role": "user",
                        "content": f"请为以下内容生成详细摘要,使用Markdown格式,包含主要观点、关键数据和结论，代码部分全部保留并高亮，图片链接全部保留引用：\n\n{chunk}"
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                
                if 'choices' in result and result['choices']:
                    summary = result['choices'][0]['message']['content'].strip()
                    summaries.append(summary)
                    print(f"分块 {i+1} 摘要生成成功")
                else:
                    print(f"[警告] 分块 {i+1} 摘要生成失败: 响应格式异常")
                    summaries.append(f"### 分块 {i+1} 摘要生成失败\n\n")
            
            except Exception as e:
                print(f"[错误] 分块 {i+1} API调用失败: {str(e)}")
                summaries.append(f"### 分块 {i+1} 摘要生成失败\n\n")
            
            # 避免API速率限制
            time.sleep(1)
        
        # 合并分块摘要
        if not summaries:
            return "摘要生成失败,请检查API密钥或网络连接"
            
        if len(summaries) == 1:
            return summaries[0]
        
        # 合并所有摘要
        combined_summary = "\n\n".join(summaries)
        
        # 请求DeepSeek整合摘要
        print("整合分段摘要...")
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业编辑,请将以下分段摘要整合成一份连贯的完整摘要,保持Markdown格式,确保逻辑流畅。"
                },
                {
                    "role": "user",
                    "content": f"请整合以下分段摘要，代码部分全部保留并高亮，图片链接全部保留引用：\n\n{combined_summary}"
                }
            ],
            "temperature": 0.2,
            "max_tokens": 2500
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and result['choices']:
                return result['choices'][0]['message']['content'].strip()
            else:
                print("[警告] 摘要整合失败，返回原始摘要")
                return combined_summary
                
        except Exception as e:
            print(f"[错误] 摘要整合失败: {str(e)}")
            return combined_summary

    def save_to_markdown(self, url: str, summary: str, output_path: str) -> None:
        """
        将摘要保存为Markdown文件
        
        :param url: 源URL
        :param summary: 生成的摘要
        :param output_path: 输出文件路径
        """
        # 添加元信息
        md_content = f"""# 网页内容摘要

**源URL**: [{url}]({url})

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**模型**: {self.model_name}

---

{summary}
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"摘要已保存至: {output_path}")

    def process_url(self, url: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        处理完整流程：抓取->清洗->摘要->保存
        
        :param url: 目标网页URL
        :param output_path: 输出文件路径（可选）
        :return: 生成的摘要内容
        """
        print(f"开始处理: {url}")
        
        # 获取网页内容
        try:
            result = self.fetch_web_content(url)
            if not result or not result[0]:
                print(f"[错误] 内容获取失败: 未能提取到网页正文")
                return None
            raw_content, dir = result
            print(f"获取内容成功, 长度: {len(raw_content)}字符")
        except Exception as e:
            print(f"[错误] 内容获取失败: {str(e)}")
            return None
        
        # 生成摘要
        summary = self.generate_summary(raw_content)
        print(f"摘要生成完成, 长度: {len(summary)}字符")
        
        # 确定输出路径
        if not output_path:
            # 从URL生成文件名
            domain = re.sub(r'[^a-zA-Z0-9]', '_', url.split('//')[-1].split('/')[0])
            path_hash = hashlib.md5(url.encode()).hexdigest()[:6]
            output_name = f"{domain}_{path_hash}_summary.md"
            output_path = os.path.join(dir, output_name)
        
        # 保存结果
        self.save_to_markdown(url, summary, output_path)
        
        return summary

def main():
    parser = argparse.ArgumentParser(description='网页内容摘要生成工具')
    parser.add_argument('url', type=str, help='要处理的网页URL')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径', default=None)
    parser.add_argument('--key', '-k', type=str, help='DeepSeek API密钥', default=None)
    parser.add_argument('--model', '-m', type=str, help='使用的模型名称', default="deepseek-chat")
    args = parser.parse_args()

    # 优先使用命令行参数，其次环境变量
    api_key = args.key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[错误] 未提供DeepSeek API密钥！")
        print("请通过以下方式之一提供密钥：")
        print("1. 使用 --key 参数")
        print("2. 设置环境变量 DEEPSEEK_API_KEY")
        print("   在命令提示符中使用: set DEEPSEEK_API_KEY=your_api_key")
        print("   或在系统属性中永久设置")
        return

    summarizer = DeepSeekSummarizer(api_key=api_key, model_name=args.model)
    try:
        summary = summarizer.process_url(
            url=args.url,
            output_path=args.output
        )
        if summary:
            print("\n摘要预览:")
            print(summary[:500] + "..." if len(summary) > 500 else summary)
    except Exception as e:
        print(f"[严重错误] 处理失败: {str(e)}")

if __name__ == "__main__":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass
    main()