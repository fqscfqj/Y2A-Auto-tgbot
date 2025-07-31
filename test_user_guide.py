#!/usr/bin/env python3
"""
测试用户引导功能的脚本
"""
import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.managers.user_manager import UserManager
from src.database.models import User

def test_user_guide():
    """测试用户引导功能"""
    print("开始测试用户引导功能...")
    
    # 创建一个测试用户
    test_user_data = {
        'id': 1,
        'telegram_id': 123456789,
        'username': 'testuser',
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    # 注册用户
    user = UserManager.register_user(test_user_data)
    print(f"用户注册成功，ID: {user.id}")
    
    # 尝试获取用户引导信息
    try:
        guide = UserManager.get_user_guide(user.id)
        if guide:
            print(f"用户引导信息获取成功: {guide}")
        else:
            print("用户引导信息为空，这是正常的，因为用户还没有引导记录")
    except Exception as e:
        print(f"获取用户引导信息失败: {e}")
        return False
    
    # 确保用户有引导记录
    try:
        guide = UserManager.ensure_user_guide(user.id)
        print(f"用户引导记录创建/获取成功: {guide}")
    except Exception as e:
        print(f"创建/获取用户引导记录失败: {e}")
        return False
    
    # 再次获取用户引导信息
    try:
        guide = UserManager.get_user_guide(user.id)
        if guide:
            print(f"用户引导信息获取成功: {guide}")
        else:
            print("用户引导信息为空，不应该发生")
            return False
    except Exception as e:
        print(f"获取用户引导信息失败: {e}")
        return False
    
    print("用户引导功能测试完成")
    return True

if __name__ == "__main__":
    success = test_user_guide()
    sys.exit(0 if success else 1)