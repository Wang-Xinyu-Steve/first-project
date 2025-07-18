import requests
import os
import time
import hashlib
import hmac
import base64
import json
from pydub import AudioSegment
import math
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
from urllib.parse import urlparse
from urllib3 import encode_multipart_formdata

# 官方demo的SeveFile核心代码，直接集成
lfasr_host = 'https://upload-ost-api.xfyun.cn'
api_upload = '/upload'
api_cut = '/mpupload/upload'
file_piece_size = 5242880

class SeveFile:
    def __init__(self, app_id, api_key, api_secret, upload_file_path):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.request_id = '0'
        self.upload_file_path = upload_file_path
        self.cloud_id = '0'

    def get_request_id(self):
        return time.strftime("%Y%m%d%H%M")

    def hashlib_256(self, data):
        # data为bytes或str
        if isinstance(data, str):
            data = data.encode('utf-8')
        m = hashlib.sha256(data).digest()
        digest = "SHA-256=" + base64.b64encode(m).decode('utf-8')
        return digest

    def assemble_auth_header(self, requset_url, file_data_type, method="", api_key="", api_secret="", body=""):
        u = urlparse(requset_url)
        host = u.hostname
        path = u.path
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        digest = self.hashlib_256(body)  # 只保留SHA-256=...格式
        signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1\ndigest: {}".format(host, date, method, path, digest)
        print("[DEBUG] signature_origin:", signature_origin)
        signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'), digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
        authorization = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            api_key, "hmac-sha256", "host date request-line digest", signature_sha)
        print("[DEBUG] authorization:", authorization)
        headers = {
            "host": host,
            "date": date,
            "authorization": authorization,
            "digest": digest,
            'Content-Type': file_data_type,
        }
        return headers

    def call(self, url, file_data, file_data_type):
        api_key = self.api_key
        api_secret = self.api_secret
        headerss = self.assemble_auth_header(url, file_data_type, method="POST", api_key=api_key, api_secret=api_secret, body=file_data)
        try:
            print("[DEBUG] 实际上传url：", url)
            resp = requests.post(url, headers=headerss, data=file_data, timeout=30)
            return resp.json()
        except Exception as e:
            print("该片上传失败！Exception ：%s" % e)
            return False

    def gene_params(self, apiname):
        appid = self.app_id
        request_id = self.get_request_id()
        upload_file_path = self.upload_file_path
        # 上传文件api
        if apiname == api_upload:
            try:
                with open(upload_file_path, mode='rb') as f:
                    file = {
                        "data": (upload_file_path, f.read()),
                        "app_id": appid,
                        "request_id": request_id,
                    }
                    encode_data = encode_multipart_formdata(file)
                    file_data = encode_data[0]
                    file_data_type = encode_data[1]
                url = lfasr_host + api_upload
                fileurl = self.call(url, file_data, file_data_type)
                return fileurl
            except FileNotFoundError:
                print("Sorry!The file " + upload_file_path + " can't find.")
        elif apiname == api_cut:
            # 预处理和分片上传略，30M以下不需要
            pass

def get_xunfei_auth_headers(apikey, apisecret, url_path, method="POST"):
    from email.utils import formatdate
    cur_time = formatdate(timeval=None, localtime=False, usegmt=True)
    host = "upload-ost-api.xfyun.cn" if "upload" in url_path else "ost-api.xfyun.cn"
    signature_origin = f"host: {host}\ndate: {cur_time}\n{method} {url_path} HTTP/1.1"
    signature_sha = hmac.new(apisecret.encode('utf-8'), signature_origin.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(signature_sha).decode('utf-8')
    authorization = f'api_key="{apikey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    headers = {
        "Authorization": authorization,
        "Date": cur_time,
        "Host": host
    }
    return headers

def download_audio(audio_url, save_dir, filename=None):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    if not filename:
        filename = audio_url.split('/')[-1].split('?')[0]
    save_path = os.path.join(save_dir, filename)
    resp = requests.get(audio_url, stream=True)
    with open(save_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return save_path

def upload_audio(file_path, appid, apikey, apisecret):
    import requests
    url = "https://upload-ost-api.xfyun.cn/file/upload"
    with open(file_path, 'rb') as f:
        file_content = f.read()
    files = {'file': (os.path.basename(file_path), file_content)}
    data = {'app_id': appid}
    response = requests.post(url, files=files, data=data)
    resp_json = response.json()
    print("[DEBUG] 讯飞上传返回：", resp_json)
    if resp_json.get("code", 0) != 0 or "data" not in resp_json:
        raise Exception(f"音频上传失败: {resp_json.get('message', resp_json)}")
    return resp_json["data"]["url"]

def create_transcribe_task(fileurl, appid, apikey, apisecret):
    url = "https://ost-api.xfyun.cn/v2/ost/pro_create"
    host = "ost-api.xfyun.cn"
    request_uri = "/v2/ost/pro_create"
    http_method = "POST"
    http_proto = "HTTP/1.1"
    algorithm = "hmac-sha256"
    post_data = {
        "common": {"app_id": appid},
        "business": {"language": "zh_cn", "accent": "mandarin", "domain": "pro_ost_ed"},
        "data": {"audio_src": "http", "audio_url": fileurl, "encoding": "raw"}
    }
    body = json.dumps(post_data)
    m = hashlib.sha256(bytes(body.encode(encoding='utf-8'))).digest()
    digest = "SHA-256=" + base64.b64encode(m).decode(encoding='utf-8')
    
    import datetime
    cur_time_utc = datetime.datetime.now(datetime.timezone.utc)
    date = format_date_time(mktime(cur_time_utc.timetuple()))
    signature_str = f"host: {host}\ndate: {date}\n{http_method} {request_uri} {http_proto}\ndigest: {digest}"
    signature = hmac.new(apisecret.encode('utf-8'), signature_str.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(signature).decode('utf-8')
    auth_header = f'api_key="{apikey}",algorithm="{algorithm}", headers="host date request-line digest", signature="{signature}"'
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Method": "POST",
        "Host": host,
        "Date": date,
        "Digest": digest,
        "Authorization": auth_header
    }
    response = requests.post(url, data=body, headers=headers)
    resp_json = response.json()
    if resp_json.get("code", 0) != 0:
        raise Exception(f"创建转写任务失败: {resp_json}")
    return resp_json["data"]["task_id"]

def get_transcribe_result(task_id, appid, apikey, apisecret):
    url = "https://ost-api.xfyun.cn/v2/ost/query"
    host = "ost-api.xfyun.cn"
    request_uri = "/v2/ost/query"
    http_method = "POST"
    http_proto = "HTTP/1.1"
    algorithm = "hmac-sha256"
    post_data = {
        "common": {"app_id": appid},
        "business": {"task_id": task_id}
    }
    body = json.dumps(post_data)
    m = hashlib.sha256(bytes(body.encode(encoding='utf-8'))).digest()
    digest = "SHA-256=" + base64.b64encode(m).decode('utf-8')
    from email.utils import formatdate
    import datetime
    cur_time_utc = datetime.datetime.now(datetime.timezone.utc)
    date = format_date_time(mktime(cur_time_utc.timetuple()))
    signature_str = f"host: {host}\ndate: {date}\n{http_method} {request_uri} {http_proto}\ndigest: {digest}"
    signature = hmac.new(apisecret.encode('utf-8'), signature_str.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(signature).decode('utf-8')
    auth_header = f'api_key="{apikey}",algorithm="{algorithm}", headers="host date request-line digest", signature="{signature}"'
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Method": "POST",
        "Host": host,
        "Date": date,
        "Digest": digest,
        "Authorization": auth_header
    }
    while True:
        response = requests.post(url, data=body, headers=headers)
        resp_json = response.json()
        if resp_json.get("code", 0) != 0:
            raise Exception(f"查询转写任务失败: {resp_json}")
        status = resp_json["data"]["task"]["task_status"]
        if status == "9":  # 9=已完成
            return resp_json["data"]["task"]["result"]
        elif status in ("5", "6", "7"):  # 失败
            raise Exception(f"转写任务失败: {resp_json}")
        else:
            time.sleep(5)

def xunfei_asr(file_path, appid, apikey, apisecret):
    fileurl = upload_audio(file_path, appid, apikey, apisecret)
    task_id = create_transcribe_task(fileurl, appid, apikey, apisecret)
    result = get_transcribe_result(task_id, appid, apikey, apisecret)
    try:
        result_json = json.loads(result)
        text = ''.join([seg['onebest'] for seg in result_json['lattice']])
    except Exception:
        text = result
    return text

def summarize_text(text):
    try:
        from .generate_summary import generate_summary
        return generate_summary(text, api_key="", model_name="")
    except ImportError:
        return "摘要功能未实现或依赖缺失" 

def convert_to_wav(input_path, output_path):
    """
    将音频文件转换为采样率16kHz、16bit、单声道的wav文件
    """
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_sample_width(2).set_channels(1)
    audio.export(output_path, format="wav")
    return output_path 