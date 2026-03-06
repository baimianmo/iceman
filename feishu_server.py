import os
import requests
import json
import logging
from collections import deque
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

def handle_user_message(chat_id, text):
    """处理用户消息的核心逻辑 (运行在子线程中)"""
    logger.info(f"开始处理消息: {text}")
    try:
        from agents import main_agent
        
        # 调用 MainAgent 获取结果
        result = main_agent.run_and_return(text)
        
        if result:
            profile_data = result.get("profile")
            blessing_text = result.get("blessing", "")
            image_path = result.get("image_path")
            
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
        else:
            feishu_service.send_message(chat_id, "text", {"text": "抱歉，我没有理解您的指令。"})
            
    except Exception as e:
        logger.error(f"处理消息异常: {e}")
        feishu_service.send_message(chat_id, "text", {"text": f"系统发生错误: {str(e)}"})

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
            
        # 启动异步线程处理，主线程立即返回 200，避免飞书重试
        threading.Thread(target=handle_user_message, args=(chat_id, text)).start()
            
    return jsonify({"code": 0, "msg": "success"})

import subprocess
import time

if __name__ == "__main__":
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
