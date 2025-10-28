import json
import requests
import boto3
from datetime import datetime

DEEPSEEK_API_KEY = "sk-fbcc127b9f384ba6b25442642a9cc485"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
table = dynamodb.Table('ds-chat-bot-history')

def lambda_handler(event, context):
    try:
        print(f"收到事件: {json.dumps(event)}")  # 打印完整事件
        
        # 解析请求体
        if 'body' in event:
            body = json.loads(event['body'])
            user_input = body.get("user_input", "")
            session_id = body.get("session_id", "default-session")
        else:
            user_input = event.get("user_input", "")
            session_id = event.get("session_id", "default-session")
        
        print(f"用户输入: {user_input}")
        print(f"会话ID: {session_id}")
        
        if not user_input:
            return error_response(400, "user_input 不能为空")
        
        # 调用 DeepSeek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": user_input}],
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": False
        }
        
        print("开始调用DeepSeek API...")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        
        # 详细调试信息
        print(f"API请求状态码: {response.status_code}")
        print(f"API响应头: {dict(response.headers)}")
        print(f"API原始响应: {response.text}")
        
        # 检查HTTP状态
        if response.status_code != 200:
            error_msg = f"DeepSeek API 请求失败: {response.status_code}"
            print(error_msg)
            return error_response(response.status_code, error_msg)
        
        # 尝试解析JSON
        try:
            response_data = response.json()
            print(f"解析后的响应数据: {json.dumps(response_data, ensure_ascii=False)}")
        except json.JSONDecodeError as e:
            error_msg = f"响应JSON解析失败: {str(e)}"
            print(error_msg)
            return error_response(500, error_msg)
        
        # 检查响应结构
        if "choices" in response_data and response_data["choices"]:
            bot_response = response_data["choices"][0]["message"]["content"]
            print(f"提取的回复内容: {bot_response}")
        else:
            error_info = response_data.get("error", {})
            error_msg = error_info.get("message", "API返回了未知的响应结构")
            print(f"API错误详情: {response_data}")
            return error_response(500, f"AI服务响应异常: {error_msg}")
        
        # 存储到DynamoDB
        store_chat_history(session_id, user_input, bot_response)
        
        # 返回成功响应
        return success_response(bot_response, session_id)
        
    except requests.exceptions.Timeout:
        error_msg = "DeepSeek API 请求超时"
        print(error_msg)
        return error_response(504, error_msg)
    except requests.exceptions.ConnectionError:
        error_msg = "无法连接到 DeepSeek API"
        print(error_msg)
        return error_response(503, error_msg)
    except Exception as e:
        error_msg = f"Lambda函数异常: {str(e)}"
        print(error_msg)
        return error_response(500, error_msg)

def success_response(bot_response, session_id):
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps({
            "response": bot_response,
            "session_id": session_id,
            "status": "success"
        })
    }

def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps({
            "error": message,
            "status": "error"
        })
    }

def store_chat_history(session_id, user_input, bot_response):
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        table.put_item(
            Item={
                "session_id": session_id,
                "timestamp": timestamp,
                "user_input": user_input,
                "bot_response": bot_response
            }
        )
        print("聊天记录存储成功")
    except Exception as e:
        print(f"存储聊天记录失败: {str(e)}")