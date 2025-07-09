import argparse
import os
import sys
import warnings

# 抑制 pkg_resources 相关的警告
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

from dependency_check import check_dependencies
from useragents import USER_AGENTS
from zhihu import ZhihuSummarizer
from xiaohongshu import XiaohongshuSummarizer
from weixin import WeixinSummarizer
from util.process_url import process_url
from elsepage import ElsepageSummarizer

def main():
    check_dependencies()
    parser = argparse.ArgumentParser(description='网页内容摘要生成工具（豆包大模型版）')
    parser.add_argument('url', help='要处理的网页URL')
    parser.add_argument('--force-login', action='store_true', help='强制重新登录')
    parser.add_argument('--no-login', action='store_true', help='跳过登录，直接以游客身份访问')
    parser.add_argument('--key', help='API密钥', default='7929a2db-9ee1-49ef-9246-1fd950f47dd9')
    parser.add_argument('--model', help='模型名称', default='doubao-seed-1-6-250615')
    parser.add_argument('--output', help='输出文件路径')
    args = parser.parse_args()
    
    url = args.url
    
    # 根据URL判断平台
    if "xiaohongshu.com" in url or "xhslink.com" in url:
        print("检测到小红书链接")
        summarizer = XiaohongshuSummarizer()
        if args.force_login:
            print("用户选择强制重新登录")
            summarizer.session_manager.manual_login()

    elif "zhihu.com" in url:
        print("检测到知乎链接")
        summarizer = ZhihuSummarizer()
        if args.force_login:
            print("用户选择强制重新登录")
            summarizer.session_manager.manual_login()

    elif "mp.weixin.qq.com" in url:
        print("检测到微信公众号链接")
        summarizer = WeixinSummarizer()
        if args.force_login:
            print("用户选择强制重新登录")
            summarizer.session_manager.manual_login()

    else:
        summarizer = ElsepageSummarizer()
    
    # 处理URL
    summary = process_url(summarizer, args.url, args.key, args.model, args.output)
    
    if summary:
        print("\n摘要预览:")
        print(summary[:500] + "..." if len(summary) > 500 else summary)
    else:
        print("处理失败")

if __name__ == "__main__":
    main() 