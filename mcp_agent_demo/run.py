#!/usr/bin/env python3
# coding=utf-8

import subprocess
import sys
import os

def main():
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建client.py和server.py的绝对路径
    client_path = os.path.join(script_dir, "client.py")
    server_path = os.path.join(script_dir, "server.py")
    
    # 检查文件是否存在
    if not os.path.exists(client_path):
        print(f"错误: 找不到client.py文件在 {script_dir}")
        sys.exit(1)
    
    if not os.path.exists(server_path):
        print(f"错误: 找不到server.py文件在 {script_dir}")
        sys.exit(1)
    
    # 执行命令: python client.py server.py
    command = [sys.executable, client_path, server_path]
    
    print("正在启动客户端并连接到服务器...")
    print(f"执行命令: {' '.join(command)}")
    
    try:
        # 执行命令并等待完成
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)

if __name__ == "__main__":
    main()