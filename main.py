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
    parser = argparse.ArgumentParser(description='网页内容摘要生成工具')
    parser.add_argument('url', help='要处理的网页URL')
    parser.add_argument('--key', help='API密钥', default='bce-v3/ALTAK-Of56tLQhJtuDtnjlsohkj/a38fd6231c7332083163522f6c8fc534b1c87a64')
    parser.add_argument('--model', help='模型名称', default='ernie-4.5-turbo-vl-preview')
    parser.add_argument('--output', help='输出文件路径')
    args = parser.parse_args()
    
    # 根据URL选择对应的处理器
    if "zhihu.com" in args.url:
        summarizer = ZhihuSummarizer()
    elif "xiaohongshu.com" in args.url or "xhslink.com" in args.url:
        summarizer = XiaohongshuSummarizer()
    elif "mp.weixin.qq.com" in args.url:
        summarizer = WeixinSummarizer()
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
    # try:
    #     import io
    #     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    # except Exception:
    #     pass
    main() 