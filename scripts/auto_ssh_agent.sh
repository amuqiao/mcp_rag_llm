#!/bin/bash

# 自动启动SSH代理并通过公钥关联加载私钥的脚本
# 使用方法: source ./auto_ssh_agent.sh

# 检查SSH代理是否已经在运行
agent_pid=$(pgrep -u $USER ssh-agent | head -n 1)  # 只取第一个PID

if [ -z "$agent_pid" ]; then
  echo "🔄 SSH代理未运行，正在启动..."
  # 启动SSH代理并导出环境变量
  eval "$(ssh-agent -s)"
else
  echo "✅ SSH代理已在运行 (PID: $agent_pid)"
  # 检查环境变量是否已设置
  if [ -z "$SSH_AUTH_SOCK" ]; then
    echo "🔄 设置SSH环境变量..."
    # 查找并设置SSH代理环境变量
    agent_sock=$(find /tmp -type s -name "agent.*" 2>/dev/null | grep "ssh-" | head -n 1)
    if [ -n "$agent_sock" ]; then
      export SSH_AUTH_SOCK=$agent_sock
      export SSH_AGENT_PID=$(echo $agent_sock | cut -d. -f2)
      echo "✅ SSH环境变量已设置"
    else
      echo "⚠️ 无法找到SSH代理套接字文件，将启动新的代理..."
      eval "$(ssh-agent -s)"
    fi
  fi
fi

# 检查密钥是否已添加到代理
added_keys=$(ssh-add -l)

# 先查找所有公钥文件(.pub结尾)，再关联对应的私钥
echo -e "\n🔍 正在通过公钥查找关联的私钥..."
ssh_dir="$HOME/.ssh"

if [ -d "$ssh_dir" ]; then
  # 查找所有公钥文件（.pub结尾且是文件）
  pub_keys=$(find "$ssh_dir" -maxdepth 1 -type f -name "*.pub")
  
  if [ -z "$pub_keys" ]; then
    echo "⚠️ 在~/.ssh目录中未找到公钥文件(*.pub)"
  else
    # 遍历所有公钥，找到对应的私钥
    while IFS= read -r pub_key; do
      # 从公钥文件名中移除.pub后缀，得到私钥文件名
      private_key="${pub_key%.pub}"
      key_name=$(basename "$private_key")
      
      # 检查私钥文件是否存在
      if [ -f "$private_key" ]; then
        # 检查密钥是否已加载
        if ! echo "$added_keys" | grep -qF "$key_name"; then
          echo -n "🔑 尝试添加密钥: $key_name..."
          if ssh-add "$private_key" 2>/dev/null; then
            echo " ✅"
            added_keys=$(ssh-add -l)  # 更新已加载密钥列表
          else
            echo " ⚠️ 失败（可能需要密码或不是有效的私钥）"
            # 提示用户手动添加（如果需要密码）
            read -p "   是否手动添加此密钥（可能需要输入密码）? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
              ssh-add "$private_key"
              added_keys=$(ssh-add -l)
            fi
          fi
        else
          echo "✅ 密钥 $key_name 已加载"
        fi
      else
        echo "⚠️ 未找到公钥 $pub_key 对应的私钥 $private_key"
      fi
    done <<< "$pub_keys"
  fi
else
  echo "⚠️ ~/.ssh目录不存在，无法加载密钥"
fi

# 显示当前加载的所有密钥
echo -e "\n🔍 当前加载的SSH密钥:"
ssh-add -l

# 提供测试连接命令
cat << EOF

📋 测试连接命令:
1. 测试连接GitHub (22端口):
   ssh -v -T git@github.com
   ssh -T git@github.com

2. 测试连接GitHub (22端口):
   ssh -v -T git@github-com-original
   ssh -T git@github-com-original

3. 临时使用HTTPS协议（如果SSH完全不可用）:
   git config --global url."https://github.com/".insteadOf git@github.com:
   # 恢复SSH协议:
   # git config --global --unset url."https://github.com/".insteadOf
4. 清除密钥
  # 清除所有已加载的密钥
  ssh-add -D
  # 通过密钥路径删除（最常用）
  ssh-add -d ~/.ssh/你的密钥文件名
  # 示例：删除名为 wq_linux_215_to_git 的密钥
  ssh-add -d ~/.ssh/wq_linux_215_to_git
EOF
