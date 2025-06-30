from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import random
from useragents import USER_AGENTS

try:
    from seleniumwire.webdriver import Edge as WireEdge
except ImportError:
    WireEdge = None

class BaseSummarizer:
    def __init__(self):
        self.driver = None

    def _init_edge_driver(self):
        edge_options = EdgeOptions()
        # 基础反检测设置
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_argument("--start-maximized")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # 确保使用桌面版用户代理
        desktop_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        edge_options.add_argument(f'--user-agent={desktop_user_agent}')
        
        # 增强稳定性设置
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--disable-software-rasterizer")
        edge_options.add_argument("--disable-extensions")
        edge_options.add_argument("--disable-plugins")
        edge_options.add_argument("--disable-images")  # 可选：禁用图片加载提高速度
        edge_options.add_argument("--disable-javascript")  # 可选：禁用JS提高稳定性
        edge_options.add_argument("--disable-web-security")
        edge_options.add_argument("--allow-running-insecure-content")
        edge_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # 内存和性能优化
        edge_options.add_argument("--memory-pressure-off")
        edge_options.add_argument("--max_old_space_size=4096")
        
        # 禁用日志
        edge_options.add_argument("--log-level=3")
        edge_options.add_argument("--silent")
        
        try:
            self.driver = webdriver.Edge(
                service=Service(EdgeChromiumDriverManager().install()),
                options=edge_options
            )
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
            )
            # 设置窗口大小为桌面版
            self.driver.set_window_size(1920, 1080)
        except Exception as e:
            print(f"[错误] Edge浏览器初始化失败: {e}")
            raise

    def _close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _init_edge_wire_driver(self):
        edge_options = EdgeOptions()
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_argument('--start-maximized')
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--disable-dev-shm-usage')
        
        # 确保使用桌面版用户代理
        desktop_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        edge_options.add_argument(f'--user-agent={desktop_user_agent}')
        
        # 增强稳定性设置
        edge_options.add_argument("--disable-software-rasterizer")
        edge_options.add_argument("--disable-extensions")
        edge_options.add_argument("--disable-plugins")
        edge_options.add_argument("--disable-web-security")
        edge_options.add_argument("--allow-running-insecure-content")
        edge_options.add_argument("--disable-features=VizDisplayCompositor")
        edge_options.add_argument("--memory-pressure-off")
        edge_options.add_argument("--log-level=3")
        edge_options.add_argument("--silent")
        
        wire_options = {
            'disable_encoding': True,
        }
        if WireEdge is None:
            raise ImportError('请先安装selenium-wire: pip install selenium-wire')
        self.driver = WireEdge(options=edge_options, seleniumwire_options=wire_options)
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
        )
        # 设置窗口大小为桌面版
        self.driver.set_window_size(1920, 1080) 