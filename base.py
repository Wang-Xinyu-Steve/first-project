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
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_argument("--start-maximized")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
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
        edge_options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
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