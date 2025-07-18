#!/usr/bin/python3
# -*- coding:utf-8 -*-
from .fileupload import seve_file
import requests
import datetime
import hashlib
import base64
import hmac
import json
import os
import re
import time

path_pwd = os.path.split(os.path.realpath(__file__))[0]
os.chdir(path_pwd)


# 创建和查询
class get_result(object):
    def __init__(self, appid, apikey, apisecret):
        # 以下为POST请求
        self.Host = "ost-api.xfyun.cn"
        self.RequestUriCreate = "/v2/ost/pro_create"
        self.RequestUriQuery = "/v2/ost/query"
        # 设置url
        if re.match(r"^\d", self.Host):
            self.urlCreate = "http://" + self.Host + self.RequestUriCreate
            self.urlQuery = "http://" + self.Host + self.RequestUriQuery
        else:
            self.urlCreate = "https://" + self.Host + self.RequestUriCreate
            self.urlQuery = "https://" + self.Host + self.RequestUriQuery
        self.HttpMethod = "POST"
        self.APPID = appid
        self.Algorithm = "hmac-sha256"
        self.HttpProto = "HTTP/1.1"
        self.UserName = apikey
        self.Secret = apisecret

        # 设置当前时间
        cur_time_utc = datetime.datetime.utcnow()
        self.Date = self.httpdate(cur_time_utc)
        # 设置测试音频文件
        self.BusinessArgsCreate = {
            "language": "zh_cn",
            "accent": "mandarin",
            "domain": "pro_ost_ed",
            # "callback_url": "http://IP:端口号/xxx/"
        }

    def img_read(self, path):
        with open(path, 'rb') as fo:
            return fo.read()

    def hashlib_256(self, res):
        m = hashlib.sha256(bytes(res.encode(encoding='utf-8'))).digest()
        result = "SHA-256=" + base64.b64encode(m).decode(encoding='utf-8')
        return result

    def httpdate(self, dt):
        """
        Return a string representation of a date according to RFC 1123
        (HTTP/1.1).
        The supplied date must be in UTC.
        """
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                 "Oct", "Nov", "Dec"][dt.month - 1]
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
                                                        dt.year, dt.hour, dt.minute, dt.second)

    def generateSignature(self, digest, uri):
        signature_str = "host: " + self.Host + "\n"
        signature_str += "date: " + self.Date + "\n"
        signature_str += self.HttpMethod + " " + uri \
                         + " " + self.HttpProto + "\n"
        signature_str += "digest: " + digest
        signature = hmac.new(bytes(self.Secret.encode('utf-8')),
                             bytes(signature_str.encode('utf-8')),
                             digestmod=hashlib.sha256).digest()
        result = base64.b64encode(signature)
        return result.decode(encoding='utf-8')

    def init_header(self, data, uri):
        digest = self.hashlib_256(data)
        sign = self.generateSignature(digest, uri)
        auth_header = 'api_key="%s",algorithm="%s", ' \
                      'headers="host date request-line digest", ' \
                      'signature="%s"' \
                      % (self.UserName, self.Algorithm, sign)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Method": "POST",
            "Host": self.Host,
            "Date": self.Date,
            "Digest": digest,
            "Authorization": auth_header
        }
        return headers

    def get_create_body(self, fileurl):
        post_data = {
            "common": {"app_id": self.APPID},
            "business": self.BusinessArgsCreate,
            "data": {
                "audio_src": "http",
                "audio_url": fileurl,
                "encoding": "raw"
            }
        }
        body = json.dumps(post_data)
        return body

    def get_query_body(self, task_id):
        post_data = {
            "common": {"app_id": self.APPID},
            "business": {
                "task_id": task_id,
            },
        }
        body = json.dumps(post_data)
        return body

    def call(self, url, body, headers):
        print("[DEBUG] 实际请求url：", url)
        try:
            response = requests.post(url, data=body, headers=headers, timeout=8)
            status_code = response.status_code
            interval = response.elapsed.total_seconds()
            if status_code != 200:
                info = response.content
                return info
            else:
                resp_data = json.loads(response.text)
                return resp_data
        except Exception as e:
            print("Exception ：%s" % e)

    def get_fileurl(self):
        # 文件上传
        api = seve_file.SeveFile(app_id=appid, api_key=apikey, api_secret=apisecret, upload_file_path=file_path)
        file_total_size = os.path.getsize(file_path)
        if file_total_size < 31457280:
            print("-----不使用分块上传-----")
            resp = api.gene_params('/upload')
            print("[DEBUG] 上传返回：", resp)
            if resp and isinstance(resp, dict) and 'data' in resp and 'url' in resp['data']:
                fileurl = resp['data']['url']
            else:
                print("[ERROR] 文件上传失败，返回：", resp)
                return None
        else:
            print("-----使用分块上传-----")
            resp = api.gene_params('/mpupload/upload')
            print("[DEBUG] 分块上传返回：", resp)
            if resp and isinstance(resp, str) and resp.startswith("http"):
                fileurl = resp
            elif resp and isinstance(resp, dict) and 'data' in resp and 'url' in resp['data']:
                fileurl = resp['data']['url']
            else:
                print("[ERROR] 分块上传失败，返回：", resp)
                return None
        print("[DEBUG] 上传fileurl：", fileurl)
        self.fileurl = fileurl
        return fileurl

    def task_create(self):
        body = self.get_create_body(self.fileurl)
        headers_create = self.init_header(body, self.RequestUriCreate)
        task_id_resp = self.call(self.urlCreate, body, headers_create)
        print("[DEBUG] 创建任务返回：", task_id_resp)
        # 修复: 确保返回值为dict且包含'data'和'task_id'
        if isinstance(task_id_resp, dict) and 'data' in task_id_resp and 'task_id' in task_id_resp['data']:
            task_id = task_id_resp['data']['task_id']
            print("[DEBUG] 获取到的task_id：", task_id)
            return task_id
        else:
            print("[ERROR] 创建任务失败，返回：", task_id_resp)
            return None

    def task_query(self, task_id):
        if task_id:
            body = self.get_create_body(self.fileurl)
            query_body = self.get_query_body(task_id)
            headers_query = self.init_header(body, self.RequestUriQuery)
            result = self.call(self.urlQuery, query_body, headers_query)
            # 修复: 确保result为dict且包含'data'
            if isinstance(result, dict) and 'data' in result:
                return result
            else:
                print("[ERROR] 查询任务失败，返回：", result)
                return None

    def extract_text_from_result(self, data):
        texts = []
        try:
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == "json_1best" and isinstance(value, dict):
                        st = value.get("st", {})
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
                            texts.append("".join(para))
                    elif isinstance(value, (dict, list)):
                        sub_text = self.extract_text_from_result(value)
                        if sub_text:
                            texts.append(sub_text)
            elif isinstance(data, list):
                for item in data:
                    sub_text = self.extract_text_from_result(item)
                    if sub_text:
                        texts.append(sub_text)
        except Exception as e:
            print("[ERROR] 文本提取失败：", e)
        result = "\n".join([t for t in texts if t]).strip()
        return result

    def get_result(self):
        # 创建订单
        print("\n------ 创建任务 -------")
        task_id = self.task_create()
        if not task_id:
            print("[ERROR] 无法获取task_id，终止流程。")
            return None
        # 查询任务
        print("\n------ 查询任务 -------")
        print("任务转写中······")
        max_retry = 60  # 最多查60次（5分钟）
        retry = 0
        while retry < max_retry:
            result = self.task_query(task_id)
            if result is None:
                print("[ERROR] 查询任务返回None，终止。")
                break
            if isinstance(result, dict) and 'data' in result and 'task_status' in result['data']:
                status = result['data']['task_status']
                if status not in ['1', '2']:
                    desktop_path = r'C:/Users/ADMIN/Desktop/transcription_raw.json'
                    with open(desktop_path, 'w', encoding='utf-8') as f:
                        f.write(json.dumps(result, ensure_ascii=False, indent=2))
                    print(f"详细转写json已保存到 {desktop_path}")
                    content = result['data'].get('content', None)
                    if not content and 'st' in result['data']:
                        content = self.extract_text_from_result(result['data'])
                    print("[DEBUG] 最终转写内容：", content)
                    return content
                elif status in ['3', '4']:
                    print(f"[ERROR] 任务状态异常，task_status: {status}，无转写结果，终止。\n{json.dumps(result, ensure_ascii=False)}")
                    break
            elif isinstance(result, bytes):
                print("发生错误···\n", result)
                break
            time.sleep(5)
            retry += 1
        else:
            print("转写超时，请稍后在平台查询或重试。")
            return None


if __name__ == '__main__':
    # 输入讯飞开放平台的appid，secret、key和文件路径
    appid = "2f26cf64"
    apikey = "b68b98f065a4be4793449d3190d1baa3"
    apisecret = "M2M4M2FmYzBhMTMyOWU4ZWM1N2MzNzBj"
    import os
    file_path = os.path.join("audio", "audio_sample_little.wav")


    gClass = get_result(appid, apikey, apisecret)
    fileurl = gClass.get_fileurl()
    gClass.get_result()
