import os
import requests
import json
import logging
from collections import deque
import time
import base64
import hashlib
import struct
from typing import Tuple
import xml.etree.ElementTree as ET

try:
    # 需要 pycryptodome
    from Crypto.Cipher import AES
except Exception:
    AES = None
from flask import Flask, request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeishuService:
    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.verification_token = os.getenv("FEISHU_VERIFICATION_TOKEN")
        self.tenant_access_token = ""
        
        if not self.app_id or not self.app_secret:
            logger.critical("【严重错误】飞书配置缺失！请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量。")
            logger.critical("例如: export FEISHU_APP_ID='cli_xxx'")
            # 这里不直接退出，以免影响调试，但在实际运行时必须设置
        else:
            logger.info(f"飞书配置已加载: AppID={self.app_id[:4]}***")

    def get_tenant_access_token(self):
        """获取 tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                self.tenant_access_token = data.get("tenant_access_token")
                return self.tenant_access_token
            else:
                logger.error(f"获取 tenant_access_token 失败: {data}")
                return None
        except Exception as e:
            logger.error(f"请求 tenant_access_token 异常: {e}")
            return None

    def send_message(self, receive_id, msg_type, content):
        """发送消息到飞书"""
        if not self.tenant_access_token:
            self.get_tenant_access_token()
            
        # 根据 ID 格式自动判断接收者类型
        if str(receive_id).startswith("oc_"):
            receive_id_type = "chat_id"
        elif str(receive_id).startswith("ou_"):
            receive_id_type = "open_id"
        elif str(receive_id).startswith("on_"):
            receive_id_type = "union_id"
        elif "@" in str(receive_id):
            receive_id_type = "email"
        else:
            # 默认为 open_id
            receive_id_type = "open_id"
            
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content)
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            # 如果 token 过期，重试一次
            if response.status_code == 400 and response.json().get("code") == 99991663:
                self.get_tenant_access_token()
                headers["Authorization"] = f"Bearer {self.tenant_access_token}"
                response = requests.post(url, headers=headers, json=payload)
                
            return response.json()
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return None

    def upload_image(self, image_path):
        """上传图片到飞书"""
        if not self.tenant_access_token:
            self.get_tenant_access_token()
            
        url = "https://open.feishu.cn/open-apis/im/v1/images"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}"
        }
        
        try:
            logger.info(f"正在上传图片: {image_path}")
            if not os.path.exists(image_path):
                logger.error(f"文件不存在: {image_path}")
                return None

            with open(image_path, "rb") as f:
                image_data = f.read()
                
            # 必须指定文件名和类型，否则某些版本 requests/server 可能无法识别
            filename = os.path.basename(image_path)
            files = {
                "image": (filename, image_data, "image/png")
            }
            data = {
                "image_type": "message"
            }
            
            response = requests.post(url, headers=headers, files=files, data=data)
            result = response.json()
            
            if result.get("code") == 0:
                image_key = result.get("data", {}).get("image_key")
                logger.info(f"图片上传成功，key: {image_key}")
                return image_key
            else:
                logger.error(f"上传图片失败: {result}")
                return None
        except Exception as e:
            logger.error(f"上传图片异常: {e}")
            return None

    def upload_file(self, file_path, file_type="pdf"):
        if not self.tenant_access_token:
            self.get_tenant_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/files"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}"}
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            filename = os.path.basename(file_path)
            files = {"file": (filename, open(file_path, "rb"), "application/pdf")}
            data = {"file_type": file_type}
            resp = requests.post(url, headers=headers, files=files, data=data).json()
            if resp.get("code") == 0:
                return resp.get("data", {}).get("file_key")
            else:
                logger.error(f"上传文件失败: {resp}")
                return None
        except Exception as e:
            logger.error(f"上传文件异常: {e}")
            return None

    def send_interactive_card(self, chat_id, title, content_list):
        """发送通用富文本卡片"""
        if not self.tenant_access_token:
            self.get_tenant_access_token()
            
        elements = []
        for item in content_list:
            if item['type'] == 'text':
                elements.append({
                    "tag": "div",
                    "text": {
                        "content": item['content'],
                        "tag": "lark_md"
                    }
                })
            elif item['type'] == 'image':
                elements.append({
                    "tag": "img",
                    "img_key": item['key'],
                    "alt": {
                        "tag": "plain_text",
                        "content": "image"
                    }
                })
            elif item['type'] == 'json':
                # 用代码块展示 JSON
                json_str = json.dumps(item['content'], ensure_ascii=False, indent=2)
                elements.append({
                    "tag": "div",
                    "text": {
                        "content": f"```json\n{json_str}\n```",
                        "tag": "lark_md"
                    }
                })

        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"content": title, "tag": "plain_text"}
            },
            "elements": elements
        }
        
        # 根据 ID 类型发送
        if str(chat_id).startswith("oc_"):
            receive_id_type = "chat_id"
        elif str(chat_id).startswith("ou_"):
            receive_id_type = "open_id"
        else:
            receive_id_type = "open_id"
            
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        body = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        
        try:
            resp = requests.post(url, headers=headers, json=body).json()
            if resp.get("code") != 0:
                logger.error(f"发送卡片失败: {resp}")
            return resp
        except Exception as e:
            logger.error(f"发送卡片异常: {e}")
            return None

feishu_service = FeishuService()
app = Flask(__name__)

import threading

# 简单的消息去重缓存，避免飞书重试导致重复回复
_processed_msg_ids = deque()
_processed_msg_ids_set = set()
_processed_max = 300
_cache_lock = threading.Lock()

# 基于 chat_id + 文本内容 的二级去重，避免不同 message_id 的重复推送
_recent_text_cache = {}
_recent_text_ttl = int(os.getenv("FEISHU_DEDUP_SECONDS", "45"))

# in-flight 并发去重：相同 chat_id+text 仅允许一个处理线程运行
_inflight = set()

def _already_processed(message_id: str) -> bool:
    if not message_id:
        return False
    with _cache_lock:
        if message_id in _processed_msg_ids_set:
            return True
        # 维护定长窗口
        if len(_processed_msg_ids) >= _processed_max:
            old = _processed_msg_ids.popleft()
            _processed_msg_ids_set.discard(old)
        _processed_msg_ids.append(message_id)
        _processed_msg_ids_set.add(message_id)
        return False

def _is_duplicate_content(chat_id: str, text: str) -> bool:
    if not chat_id or not text:
        return False
    key = f"{chat_id}:{text.strip()}"
    now = time.time()
    with _cache_lock:
        ts = _recent_text_cache.get(key)
        # 清理过期项（惰性）
        if ts and now - ts < _recent_text_ttl:
            return True
        _recent_text_cache[key] = now
        # 轻量清理，防止无限增长
        if len(_recent_text_cache) > 2000:
            cutoff = now - _recent_text_ttl
            for k, v in list(_recent_text_cache.items()):
                if v < cutoff:
                    _recent_text_cache.pop(k, None)
    return False

def handle_user_message(chat_id, text):
    """处理用户消息的核心逻辑 (运行在子线程中)"""
    logger.info(f"开始处理消息: {text}")
    inflight_key = f"{chat_id}:{text.strip()}"
    with _cache_lock:
        if inflight_key in _inflight:
            logger.info(f"并发重复已忽略: {inflight_key}")
            return
        _inflight.add(inflight_key)
    try:
        from agents import main_agent
        
        # 调用 MainAgent 获取结果
        result = main_agent.run_and_return(text)
        
        if result:
            profile_data = result.get("profile")
            blessing_text = result.get("blessing", "")
            image_path = result.get("image_path")
            pdf_path = result.get("pdf_path")
            
            # 1. 发送客户画像 (如果有)
            if profile_data:
                feishu_service.send_interactive_card(
                    chat_id, 
                    "👤 客户画像数据", 
                    [{"type": "json", "content": profile_data}]
                )
            
            # 2. 如果没有画像，但有文本，先发文本 (作为兜底)
            # 或者把祝福语作为文本发送
            if blessing_text and not image_path:
                 feishu_service.send_message(chat_id, "text", {"text": blessing_text})

            # 3. 发送贺卡 (带图片)
            if image_path:
                image_key = feishu_service.upload_image(image_path)
                if image_key:
                    # 仅发送图片卡片，不再重复发送文字
                    feishu_service.send_interactive_card(
                        chat_id,
                        "🎂 祝福贺卡",
                        [{"type": "image", "key": image_key}]
                    )
                else:
                    feishu_service.send_message(chat_id, "text", {"text": "[图片生成失败]"})
            
            # 4. 如有 PDF，发送文件
            if pdf_path and os.path.exists(pdf_path):
                file_key = feishu_service.upload_file(pdf_path, "pdf")
                if file_key:
                    feishu_service.send_message(chat_id, "file", {"file_key": file_key})
        else:
            feishu_service.send_message(chat_id, "text", {"text": "抱歉，我没有理解您的指令。"})
            
    except Exception as e:
        logger.error(f"处理消息异常: {e}")
        feishu_service.send_message(chat_id, "text", {"text": f"系统发生错误: {str(e)}"})
    finally:
        with _cache_lock:
            _inflight.discard(inflight_key)

@app.route("/webhook/event", methods=["POST"])
def feishu_event_handler():
    # 校验请求签名 (可选，建议生产环境开启)
    # ...

    data = request.json
    
    # 1. URL 校验 (首次配置时需要)
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    
    # 2. 处理消息事件
    if data.get("header", {}).get("event_type") == "im.message.receive_v1":
        event = data.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})
        
        # 忽略由机器人自身发送的消息，避免回环
        if sender.get("sender_type") != "user":
            return jsonify({"code": 0})
        
        # 去重：同一 message_id 不重复处理
        message_id = message.get("message_id")
        if _already_processed(message_id):
            logger.info(f"重复事件已忽略: message_id={message_id}")
            return jsonify({"code": 0})
        
        chat_id = message.get("chat_id")
        content_json = message.get("content", "{}")
        try:
            content_dict = json.loads(content_json)
            text = content_dict.get("text", "")
        except:
            text = ""
            
        # 过滤掉空消息或非文本消息
        if not text:
            return jsonify({"code": 0})
        
        # 二级去重：相同 chat_id + 文本在窗口内不重复处理
        if _is_duplicate_content(chat_id, text):
            logger.info(f"重复内容已忽略: chat_id={chat_id}")
            return jsonify({"code": 0})
            
        # 启动异步线程处理，主线程立即返回 200，避免飞书重试
        threading.Thread(target=handle_user_message, args=(chat_id, text)).start()
            
    return jsonify({"code": 0, "msg": "success"})

import subprocess
import time
import argparse

class WeComService:
    def __init__(self):
        self.corp_id = os.getenv("WECOM_CORP_ID") or ""
        self.corp_secret = os.getenv("WECOM_CORP_SECRET") or ""
        self.agent_id = os.getenv("WECOM_AGENT_ID") or ""
        self.access_token = ""
        self.token_ts = 0
        if self.corp_id and self.corp_secret:
            logger.info("企业微信配置已加载")

    def get_access_token(self):
        # 每次尝试前动态补全环境变量，避免运行中修改环境后实例未刷新
        if not self.corp_id:
            self.corp_id = os.getenv("WECOM_CORP_ID") or ""
        if not self.corp_secret:
            self.corp_secret = os.getenv("WECOM_CORP_SECRET") or ""
        if not self.agent_id:
            self.agent_id = os.getenv("WECOM_AGENT_ID") or ""
        if not self.corp_id or not self.corp_secret:
            missing = []
            if not self.corp_id:
                missing.append("WECOM_CORP_ID")
            if not self.corp_secret:
                missing.append("WECOM_CORP_SECRET")
            logger.error(f"获取企业微信 access_token 失败：缺少环境变量 {', '.join(missing)}")
            return None
        try:
            logger.info(f"WeCom gettoken corp_id={self.corp_id[:3]}*** agent_id={self.agent_id} secret_len={len(self.corp_secret)}")
        except Exception:
            pass
        if self.access_token and time.time() - self.token_ts < 7000:
            return self.access_token
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        try:
            r = requests.get(url, params={"corpid": self.corp_id, "corpsecret": self.corp_secret})
            data = r.json()
            if data.get("errcode") == 0:
                self.access_token = data.get("access_token")
                self.token_ts = time.time()
                return self.access_token
            else:
                logger.error(f"获取企业微信 access_token 失败: {data}")
        except Exception as e:
            logger.error(f"获取企业微信 access_token 异常: {e}")
        return None

    def send_text(self, to_user, content):
        if not self.get_access_token():
            return None
        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
        payload = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": int(self.agent_id) if self.agent_id.isdigit() else self.agent_id,
            "text": {"content": content},
            "duplicate_check_interval": 1800
        }
        try:
            resp = requests.post(url, params={"access_token": self.access_token}, json=payload).json()
            if resp.get("errcode") != 0:
                logger.error(f"企业微信发送文本失败: {resp}")
            return resp
        except Exception as e:
            logger.error(f"企业微信发送文本异常: {e}")
            return None

    def send_textcard(self, to_user, title, description, url_link=""):
        if not self.get_access_token():
            return None
        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
        payload = {
            "touser": to_user,
            "msgtype": "textcard",
            "agentid": int(self.agent_id) if self.agent_id.isdigit() else self.agent_id,
            "textcard": {
                "title": title,
                "description": description,
                "url": url_link or "https://work.weixin.qq.com/",
                "btntxt": "查看"
            },
            "duplicate_check_interval": 1800
        }
        try:
            resp = requests.post(url, params={"access_token": self.access_token}, json=payload).json()
            if resp.get("errcode") != 0:
                logger.error(f"企业微信发送文本卡片失败: {resp}")
            return resp
        except Exception as e:
            logger.error(f"企业微信发送文本卡片异常: {e}")
            return None

    def upload_image(self, image_path):
        if not self.get_access_token():
            return None
        url = "https://qyapi.weixin.qq.com/cgi-bin/media/upload"
        try:
            if not os.path.exists(image_path):
                logger.error(f"文件不存在: {image_path}")
                return None
            files = {"media": (os.path.basename(image_path), open(image_path, "rb"), "image/png")}
            resp = requests.post(url, params={"access_token": self.access_token, "type": "image"}, files=files).json()
            if resp.get("errcode") == 0:
                return resp.get("media_id")
            else:
                logger.error(f"企业微信上传图片失败: {resp}")
                return None
        except Exception as e:
            logger.error(f"企业微信上传图片异常: {e}")
            return None

    def send_image(self, to_user, media_id):
        if not self.get_access_token():
            return None
        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
        payload = {
            "touser": to_user,
            "msgtype": "image",
            "agentid": int(self.agent_id) if self.agent_id.isdigit() else self.agent_id,
            "image": {"media_id": media_id},
            "duplicate_check_interval": 1800
        }
        try:
            resp = requests.post(url, params={"access_token": self.access_token}, json=payload).json()
            if resp.get("errcode") != 0:
                logger.error(f"企业微信发送图片失败: {resp}")
            return resp
        except Exception as e:
            logger.error(f"企业微信发送图片异常: {e}")
            return None

wecom_service = WeComService()

def handle_user_message_wecom(user_id, text):
    logger.info(f"开始处理企业微信消息: {text}")
    try:
        from agents import main_agent
        result = main_agent.run_and_return(text)
        if result:
            profile_data = result.get("profile")
            blessing_text = result.get("blessing", "")
            image_path = result.get("image_path")
            if profile_data:
                # 优先用文本卡片展示关键摘要，提升可读性与兼容性
                summary = []
                name = profile_data.get("name")
                gender = profile_data.get("gender")
                level = profile_data.get("level") or profile_data.get("membership_level")
                assets = profile_data.get("assets") or profile_data.get("assets_level")
                risk = profile_data.get("risk_preference")
                hobbies = profile_data.get("hobbies") or profile_data.get("interests") or []
                if name: summary.append(f"姓名：{name}")
                if gender: summary.append(f"性别：{gender}")
                if level: summary.append(f"等级：{level}")
                if assets: summary.append(f"资产：{assets}")
                if risk: summary.append(f"偏好：{risk}")
                if hobbies: summary.append(f"爱好：{','.join(hobbies)}")
                desc = "<br/>".join(summary) if summary else "暂无画像信息"
                wecom_service.send_textcard(user_id, "客户画像", desc)
                # 再按需发送完整 JSON（分片避免超长导致丢弃）
                full_json = json.dumps(profile_data, ensure_ascii=False, indent=2)
                max_len = 2048
                for i in range(0, len(full_json), max_len):
                    chunk = full_json[i:i+max_len]
                    wecom_service.send_text(user_id, chunk)
            if blessing_text and not image_path:
                wecom_service.send_text(user_id, blessing_text)
            if image_path:
                media_id = wecom_service.upload_image(image_path)
                if media_id:
                    wecom_service.send_image(user_id, media_id)
                else:
                    wecom_service.send_text(user_id, "图片发送失败")
        else:
            wecom_service.send_text(user_id, "抱歉，我没有理解您的指令。")
    except Exception as e:
        logger.error(f"处理企业微信消息异常: {e}")
        wecom_service.send_text(user_id, f"系统发生错误: {str(e)}")

@app.route("/wecom/event", methods=["POST", "GET"])
def wecom_event_handler():
    if request.method == "GET":
        # 企业微信 URL 验证（安全模式）
        echostr = request.args.get("echostr", "")
        msg_signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        if echostr and msg_signature and timestamp and nonce:
            token = os.getenv("WECOM_TOKEN", "")
            encoding_aes_key = os.getenv("WECOM_ENCODING_AES_KEY", "")
            corp_id = os.getenv("WECOM_CORP_ID", "")
            # 验证签名
            sig = hashlib.sha1("".join(sorted([token, timestamp, nonce, echostr])).encode("utf-8")).hexdigest()
            if sig != msg_signature:
                logger.error("企业微信 URL 验证签名失败")
                return "signature error", 403
            # 解密 echostr
            if AES and encoding_aes_key:
                try:
                    plain, recv_id = _wecom_decrypt(encoding_aes_key, echostr)
                    if corp_id and recv_id and corp_id != recv_id:
                        logger.error("企业微信 URL 验证 corp_id 不匹配")
                        return "corp id mismatch", 403
                    return plain
                except Exception as e:
                    logger.error(f"企业微信 URL 验证解密失败: {e}")
                    return "decrypt error", 500
            else:
                # 无加解密能力或未配置 encoding_aes_key，直接回显（仅明文模式可用）
                return echostr
        # 明文模式或健康检查
        return "ok"
    ctype = request.headers.get("Content-Type", "")
    if "xml" in ctype or request.data.strip().startswith(b"<xml"):
        try:
            root = ET.fromstring(request.data)
            enc = root.findtext("Encrypt")
            token = os.getenv("WECOM_TOKEN", "")
            encoding_aes_key = os.getenv("WECOM_ENCODING_AES_KEY", "")
            msg_signature = request.args.get("msg_signature", "")
            timestamp = request.args.get("timestamp", "")
            nonce = request.args.get("nonce", "")
            if enc:
                sig = hashlib.sha1("".join(sorted([token, timestamp, nonce, enc])).encode("utf-8")).hexdigest()
                if sig != msg_signature:
                    return "signature error", 403
                plain_xml, _ = _wecom_decrypt(encoding_aes_key, enc) if AES and encoding_aes_key else (None, None)
                if not plain_xml:
                    return "decrypt error", 500
                xr = ET.fromstring(plain_xml)
            else:
                xr = root
            user_id = xr.findtext("FromUserName") or ""
            text = xr.findtext("Content") or ""
            if user_id and text:
                threading.Thread(target=handle_user_message_wecom, args=(user_id, text)).start()
            return "success"
        except Exception as e:
            logger.error(f"企业微信 XML 解析失败: {e}")
            return "parse error", 400
    else:
        data = request.get_json(silent=True) or {}
        user_id = data.get("FromUserId") or data.get("from_user") or ""
        text = data.get("Text") or data.get("text") or ""
        if not user_id or not text:
            return jsonify({"errcode": 0})
        threading.Thread(target=handle_user_message_wecom, args=(user_id, text)).start()
        return jsonify({"errcode": 0})

@app.route("/wecom/diagnose", methods=["GET"])
def wecom_diagnose():
    ok = bool(wecom_service.get_access_token())
    return jsonify({"ok": ok})


def _pkcs7_unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 32:
        raise ValueError("invalid padding")
    return data[:-pad_len]


def _wecom_decrypt(encoding_aes_key: str, encrypt: str) -> Tuple[str, str]:
    """
    解密企业微信加密消息/echostr
    返回: (明文字符串, receive_id)
    """
    aes_key = base64.b64decode(encoding_aes_key + "=")
    iv = aes_key[:16]
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    cipher_text = base64.b64decode(encrypt)
    plain_padded = cipher.decrypt(cipher_text)
    plain = _pkcs7_unpad(plain_padded)
    # 结构: 16字节随机 + 4字节网络序长度 + 内容 + receive_id
    content = plain[16:]
    msg_len = struct.unpack(">I", content[:4])[0]
    msg = content[4:4 + msg_len]
    receive_id = content[4 + msg_len:].decode("utf-8", errors="ignore")
    return msg.decode("utf-8"), receive_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-backend", choices=["deepseek", "ollama", "glm"], default=os.getenv("LLM_BACKEND", "deepseek"))
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"))
    parser.add_argument("--ollama-base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--glm-model", default=os.getenv("GLM_MODEL", "glm-4-flash"))
    parser.add_argument("--glm-api-key", default=os.getenv("GLM_API_KEY", ""))

    args, _ = parser.parse_known_args()
    os.environ["LLM_BACKEND"] = args.llm_backend
    
    if args.llm_backend == "ollama":
        os.environ["OLLAMA_MODEL"] = args.ollama_model
        os.environ["OLLAMA_BASE_URL"] = args.ollama_base_url
    elif args.llm_backend == "glm":
        os.environ["GLM_MODEL"] = args.glm_model
        if args.glm_api_key:
            os.environ["GLM_API_KEY"] = args.glm_api_key
    # macOS 上 5000 端口常被 AirPlay 占用，改用 8080 端口更安全
    port = int(os.environ.get("PORT", 8080))
    
    # 自动启动 localtunnel
    # 注意：localtunnel 需要通过 npm 安装 (npm install -g localtunnel)
    # 如果未安装，这里会失败，我们将提示用户
    try:
        # 在后台启动 lt
        logger.info(f" * 正在尝试启动 localtunnel (端口 {port})...")
        lt_process = subprocess.Popen(
            ["lt", "--port", str(port)], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 简单等待一下获取 URL (更健壮的方式是解析输出)
        # 这里为了简单，我们直接提示用户在终端看输出或者手动运行
        logger.info(" * Localtunnel 正在启动...")
        logger.info(" * 如果您已安装 localtunnel (npm i -g localtunnel)，")
        logger.info(f" * 请在另一个终端运行: lt --port {port}")
        logger.info(" * 然后将生成的 URL 填入飞书。")
        
    except FileNotFoundError:
        logger.warning("未找到 'lt' 命令。请先安装: npm install -g localtunnel")
        logger.warning(f"或者手动使用其他工具将端口 {port} 暴露到公网。")
    except Exception as e:
        logger.error(f"启动 localtunnel 失败: {e}")

    app.run(host="0.0.0.0", port=port)
