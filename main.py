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

def main():
    check_dependencies()
    parser = argparse.ArgumentParser(description='网页内容摘要生成工具')
    parser.add_argument('url', type=str, help='要处理的网页URL')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径', default=None)
    parser.add_argument('--key', '-k', type=str, help='DeepSeek API密钥', default=None)
    parser.add_argument('--model', '-m', type=str, help='使用的模型名称', default="deepseek-chat")
    args = parser.parse_args()
    api_key = args.key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[错误] 未提供DeepSeek API密钥！")
        print("请通过 --key 参数或设置环境变量 DEEPSEEK_API_KEY 提供密钥")
        return
    url = args.url
    if "zhihu.com" in url:
        summarizer = ZhihuSummarizer()
    elif "xiaohongshu.com" in url or "xhslink.com" in url:
        summarizer = XiaohongshuSummarizer()
    elif "weixin.qq.com" in url:
        summarizer = WeixinSummarizer()
    else:
        print("暂不支持该类型网页！")
        return
    try:
        summary = process_url(
            summarizer=summarizer,
            url=url,
            api_key=api_key,
            model_name=args.model,
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