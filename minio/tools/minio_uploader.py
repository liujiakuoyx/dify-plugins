from collections.abc import Generator
from typing import Any
import os
import time
from minio import Minio
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class MinioUploaderTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # 从参数中获取本地文件路径和目标对象名称
        local_file_path = tool_parameters.get("local_file_path")
        object_name = tool_parameters.get("object_name")
        add_timestamp = tool_parameters.get("add_timestamp", False)
        
        if not local_file_path or not object_name:
            yield self.create_json_message({"message": "local_file_path and object_name are required"})
            return
        
        # 如果启用时间戳，在文件扩展名之前添加毫秒时间戳
        if add_timestamp:
            # 分离文件名和扩展名
            name_parts = object_name.rsplit('.', 1)
            if len(name_parts) == 2:
                # 有扩展名的情况
                timestamp = int(time.time() * 1000)
                object_name = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                # 没有扩展名的情况
                timestamp = int(time.time() * 1000)
                object_name = f"{object_name}_{timestamp}"
        
        # 检查本地文件是否存在
        if not os.path.exists(local_file_path):
            yield self.create_json_message({"message": f"File not found: {local_file_path}"})
            return
        
        if not os.path.isfile(local_file_path):
            yield self.create_json_message({"message": f"Path is not a file: {local_file_path}"})
            return
        
        # 从运行时凭据中获取MinIO配置
        access_key = tool_parameters.get("access_key")
        secret_key = tool_parameters.get("secret_key")
        endpoint = tool_parameters.get("endpoint")
        bucket_name = tool_parameters.get("bucket_name")

        try:
            # 初始化MinIO客户端
            minio_client = Minio(
                endpoint.replace("http://", "").replace("https://", ""),
                access_key=access_key,
                secret_key=secret_key,
                secure=endpoint.startswith("https://")
            )

            # 确保存储桶存在
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)

            # 上传本地文件
            minio_client.fput_object(
                bucket_name,
                object_name,
                local_file_path
            )

            # 获取文件大小
            file_size = os.path.getsize(local_file_path)
            
            # 返回成功消息
            yield self.create_text_message(
                f"File successfully uploaded to {bucket_name}/{object_name}\n"
                f"File size: {file_size} bytes"
            )
        except Exception as e:
            yield self.create_json_message({"message": f"Upload Failed: {str(e)}"})
            return
