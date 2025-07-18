import sys
import os
from xiaoyuzhoufm import XiaoyuzhouFMParser, get_save_folder
from util.audio_utils import download_audio, summarize_text
from speed_transcription_python_demo.ost_fast import get_result
import json
import datetime

appid = None
apikey = None
apisecret = None
file_path = None


def main():
    url = input("请输入音频链接：")
    save_dir = "C:/Users/ADMIN/Desktop/音频转写"
    # 讯飞星火认证信息（请替换为你的实际信息）
    global appid, apikey, apisecret, file_path  # 声明为全局变量
    appid = "2f26cf64"
    apikey = "b68b98f065a4be4793449d3190d1baa3"
    apisecret = "M2M4M2FmYzBhMTMyOWU4ZWM1N2MzNzBj"
    # 判断平台
    if "xiaoyuzhoufm.com" in url:
        parser = XiaoyuzhouFMParser()
    else:
        print("暂不支持该平台")
        return
    info = parser.get_audio_info(url)
    print("音频信息：", info)
    audio_path = download_audio(info['audio_url'], save_dir)
    print("已下载到：", audio_path)

    import os
    from util.audio_utils import convert_to_wav
    wav_path = os.path.splitext(audio_path)[0] + "_16k.wav"
    convert_to_wav(audio_path, wav_path)
    print("已转换为wav：", wav_path)
    try:
        os.remove(audio_path)
        print(f"已删除原始音频文件：{audio_path}")
    except Exception as e:
        print(f"删除原始音频文件失败：{e}")

    file_path = wav_path

    # 调用官方demo的上传和转写流程
    import speed_transcription_python_demo.ost_fast as ost_fast
    ost_fast.appid = appid
    ost_fast.apikey = apikey
    ost_fast.apisecret = apisecret
    ost_fast.file_path = file_path
    gClass = get_result(appid, apikey, apisecret)
    fileurl = gClass.get_fileurl()
    print("[DEBUG] 上传后fileurl:", fileurl)
    text = gClass.get_result()
    summary = summarize_text(text)
    print("摘要：", summary)


def extract_text_from_json_file(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    paragraphs = []
    def extract_from_json_1best(obj):
        if not isinstance(obj, dict):
            return
        if "json_1best" in obj and isinstance(obj["json_1best"], dict):
            st = obj["json_1best"].get("st", {})
            rt_list = st.get("rt", [])
            para = []
            for rt in rt_list:
                ws_list = rt.get("ws", [])
                for ws in ws_list:
                    cw_list = ws.get("cw", [])
                    for cw in cw_list:
                        w = cw.get("w", "")
                        para.append(w)
            if para:
                paragraphs.append("".join(para))
        # 递归遍历所有子dict和list
        for v in obj.values():
            if isinstance(v, dict):
                extract_from_json_1best(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        extract_from_json_1best(item)
    extract_from_json_1best(data)
    return "\n".join(paragraphs)


if __name__ == "__main__":
    url = input("请输入音频链接：")
    # 网页标题作为文件夹名
    parser = XiaoyuzhouFMParser() if "xiaoyuzhoufm.com" in url else None
    if not parser:
        print("暂不支持该平台")
        exit()
    info = parser.get_audio_info(url)
    folder = get_save_folder(info.get('title'))
    # 文件名前缀
    folder_name = os.path.basename(folder)
    prefix = folder_name  # 直接用文件夹名做前缀，保证唯一
    # 下载音频到专属文件夹
    audio_filename = info['audio_url'].split('/')[-1].split('?')[0]
    audio_path = os.path.join(folder, audio_filename)
    download_audio(info['audio_url'], folder, filename=audio_filename)
    print("已下载到：", audio_path)
    from util.audio_utils import convert_to_wav
    wav_path = os.path.splitext(audio_path)[0] + "_16k.wav"
    convert_to_wav(audio_path, wav_path)
    print("已转换为wav：", wav_path)
    try:
        os.remove(audio_path)
        print(f"已删除原始音频文件：{audio_path}")
    except Exception as e:
        print(f"删除原始音频文件失败：{e}")
    file_path = wav_path
    appid = "2f26cf64"
    apikey = "b68b98f065a4be4793449d3190d1baa3"
    apisecret = "M2M4M2FmYzBhMTMyOWU4ZWM1N2MzNzBj"
    import speed_transcription_python_demo.ost_fast as ost_fast
    ost_fast.appid = appid
    ost_fast.apikey = apikey
    ost_fast.apisecret = apisecret
    ost_fast.file_path = file_path
    gClass = get_result(appid, apikey, apisecret)
    fileurl = gClass.get_fileurl()
    print("[DEBUG] 上传后fileurl:", fileurl)
    text = gClass.get_result()
    # 保存json
    json_path = os.path.join(folder, f'{prefix}_raw.json')
    if os.path.exists(r'C:/Users/ADMIN/Desktop/transcription_raw.json'):
        os.replace(r'C:/Users/ADMIN/Desktop/transcription_raw.json', json_path)
    # 提取文本
    text_path = os.path.join(folder, f'{prefix}_text.txt')
    text = extract_text_from_json_file(json_path)
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"已提取文本内容到 {text_path}")
    # 生成摘要
    summary_path = os.path.join(folder, f'{prefix}_summary.md')
    if text and text.strip():
        summary = summarize_text(text)
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"摘要已保存到 {summary_path}")
    else:
        print("未获取到有效转写文本，无法生成摘要。") 