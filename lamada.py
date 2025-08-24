import json
import boto3
from datetime import datetime

# 初始化DynamoDB客户端（指定你的AWS区域，如ap-southeast-2）
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
# 关联到创建的表
table = dynamodb.Table('ds-chat-bot-history')

def lambda_handler(event, context):
    # 从event中获取用户输入（后续通过API Gateway传递）
    user_input = event.get("user_input", "")
    session_id = event.get("session_id", "default-session")  # 建议前端生成唯一ID传入

    # 调用回复生成函数
    response = generate_response(user_input)

    store_chat_history(session_id, user_input, bot_response)

    history = get_chat_history(session_id)
    
    # 返回JSON格式响应
    result = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",  # 生产环境替换为具体前端域名
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Credentials": "false"
        },
        # "body": json.dumps({"response": response}, ensure_ascii=False)
        "body": {"response": response}  
    }
    # 可以在这里打印一下，方便控制台看
    print("实际返回内容：", result)  
    return result

def generate_response(user_input):
    # 这里放入你的回复逻辑（可替换为调用OpenAI等API）
    if "你好" in user_input:
        return "你好呀！有什么可以帮你的？"
    elif "再见" in user_input:
        return "再见~ 欢迎下次再来！"
    else:
        return "我不太明白你的意思，可以换个说法吗？"

# 存储聊天记录到DynamoDB
def store_chat_history(session_id, user_input, bot_response):
    # 生成UTC时间戳（确保排序一致）
    timestamp = datetime.utcnow().isoformat() + "Z"  # 格式：2024-08-24T12:34:56.789Z
    
    # 写入表中
    table.put_item(
        Item={
            "session_id": session_id,  # 分区键
            "timestamp": timestamp,    # 排序键（按时间排序）
            "user_input": user_input,  # 用户输入
            "bot_response": bot_response  # 机器人回复
        }
    )

# （可选）查询会话历史记录
def get_chat_history(session_id):
    # 查询指定session_id的所有记录，并按时间戳升序排列
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
        ScanIndexForward=True  # True=升序（旧→新），False=降序（新→旧）
    )
    # 返回查询到的记录（去掉DynamoDB内部字段）
    return response.get('Items', [])
