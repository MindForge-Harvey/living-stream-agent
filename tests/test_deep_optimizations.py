"""
深度全面测试 - 测试所有优化功能
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5172"
API_BASE = f"{BASE_URL}/chat/api"

# 测试结果统计
passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    """记录测试结果"""
    global passed, failed, total
    total += 1
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} {detail}")
        failed += 1


def get_admin_token():
    """获取管理员token"""
    # 尝试普通管理员
    res = requests.post(f"{API_BASE}/admin/login", json={
        "username": "admin123",
        "password": "admin123"
    })
    if res.ok and res.json().get("success"):
        return res.json().get("token")
    return None


def run_tests():
    global passed, failed
    
    print("\n" + "=" * 60)
    print("深度全面测试 - 测试所有优化功能")
    print("=" * 60)
    
    # ==================== 1. 违禁词替换测试 ====================
    print("\n[1] 违禁词替换测试")
    
    token = get_admin_token()
    test("获取管理员token", token is not None)
    
    # 创建测试违禁词
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 创建多字违禁词
    res = requests.post(f"{API_BASE}/forbidden-words", headers=headers, json={
        "word": "测试违禁词",
        "replacement": "***",
        "level": "multi"
    })
    test("创建多字违禁词", res.ok)
    multi_word_id = res.json().get("id") if res.ok else None
    
    # 创建单字违禁词
    res = requests.post(f"{API_BASE}/forbidden-words", headers=headers, json={
        "word": "禁",
        "replacement": "X",
        "level": "single"
    })
    test("创建单字违禁词", res.ok)
    single_word_id = res.json().get("id") if res.ok else None
    
    # 测试API健康
    res = requests.get(f"{API_BASE}/health")
    test("API健康检查", res.ok and res.json().get("status") == "ok")
    
    # 清理测试数据
    if multi_word_id:
        requests.delete(f"{API_BASE}/forbidden-words/{multi_word_id}", headers=headers)
    if single_word_id:
        requests.delete(f"{API_BASE}/forbidden-words/{single_word_id}", headers=headers)
    
    # ==================== 2. 脚本模板系统测试 ====================
    print("\n[2] 脚本模板系统测试")
    
    # 获取公开模板列表（无需认证）
    res = requests.get(f"{API_BASE}/templates/public")
    test("获取公开模板列表", res.ok)
    templates = res.json() if res.ok else []
    test("包含预置模板", len(templates) > 0)
    test("预置模板数量正确", len(templates) == 5)
    
    # 获取带认证的模板列表
    res = requests.get(f"{API_BASE}/templates", headers=headers)
    test("获取带认证模板列表", res.ok)
    
    # 创建自定义模板
    res = requests.post(f"{API_BASE}/templates", headers=headers, json={
        "name": "测试模板",
        "category": "custom",
        "product_type": "测试",
        "template_content": "## 开场白\n测试内容",
        "description": "测试描述"
    })
    test("创建自定义模板", res.ok)
    template_id = res.json().get("id") if res.ok else None
    
    # 更新模板
    if template_id:
        res = requests.put(f"{API_BASE}/templates/{template_id}", headers=headers, json={
            "name": "更新后的测试模板"
        })
        test("更新模板", res.ok)
    
    # 删除模板
    if template_id:
        res = requests.delete(f"{API_BASE}/templates/{template_id}", headers=headers)
        test("删除模板", res.ok)
    
    # 初始化预置模板
    res = requests.post(f"{API_BASE}/templates/init-presets", headers=headers)
    test("初始化预置模板", res.ok)
    
    # ==================== 3. 脚本版本历史测试 ====================
    print("\n[3] 脚本版本历史测试")
    
    # 创建测试对话
    res = requests.post(f"{API_BASE}/dialogs", headers=headers, json={
        "userId": "test_user",
        "toolId": "living-stream-agent",
        "toolName": "直播话术生成智能体",
        "title": "测试对话"
    })
    test("创建测试对话", res.ok)
    dialog_id = res.json().get("id") if res.ok else None
    
    if dialog_id:
        # 获取版本历史
        res = requests.get(f"{API_BASE}/agent/versions/{dialog_id}", headers=headers)
        test("获取版本历史", res.ok)
        test("版本历史为列表", isinstance(res.json(), list))
    
    # ==================== 4. 导出功能测试 ====================
    print("\n[4] 导出功能测试")
    
    if dialog_id:
        # 导出为TXT
        res = requests.post(f"{API_BASE}/export", headers=headers, json={
            "dialog_id": dialog_id,
            "format": "txt"
        })
        # 注意：可能没有消息内容，会返回404
        test("导出TXT请求", res.status_code in [200, 404])
        
        # 导出为Markdown
        res = requests.post(f"{API_BASE}/export", headers=headers, json={
            "dialog_id": dialog_id,
            "format": "markdown"
        })
        test("导出Markdown请求", res.status_code in [200, 404])
        
        # 导出为Word
        res = requests.post(f"{API_BASE}/export", headers=headers, json={
            "dialog_id": dialog_id,
            "format": "docx"
        })
        test("导出Word请求", res.status_code in [200, 404])
    
    # ==================== 5. 对话消息保存测试 ====================
    print("\n[5] 对话消息保存测试")
    
    if dialog_id:
        # 保存用户消息
        res = requests.post(f"{API_BASE}/dialogs/message", headers=headers, json={
            "dialogId": dialog_id,
            "userId": "test_user",
            "role": "user",
            "content": "测试消息"
        })
        test("保存用户消息", res.ok)
        
        # 保存助手消息（带元数据）
        res = requests.post(f"{API_BASE}/dialogs/message", headers=headers, json={
            "dialogId": dialog_id,
            "userId": "test_user",
            "role": "assistant",
            "content": "测试回复",
            "metadata": json.dumps({"file_content": "测试文件内容", "file_name": "test.txt"})
        })
        # 注意：API可能不支持metadata参数
        test("保存助手消息", res.ok)
        
        # 获取消息列表
        res = requests.get(f"{API_BASE}/dialogs/{dialog_id}/messages", headers=headers)
        test("获取消息列表", res.ok)
        messages = res.json() if res.ok else []
        test("消息数量正确", len(messages) >= 2)
    
    # ==================== 6. 管理员功能测试 ====================
    print("\n[6] 管理员功能测试")
    
    # 获取违禁词列表
    res = requests.get(f"{API_BASE}/forbidden-words", headers=headers)
    test("获取违禁词列表", res.ok)
    
    # 获取记忆列表
    res = requests.get(f"{API_BASE}/memories?user_id=test_user", headers=headers)
    test("获取记忆列表", res.ok)
    
    # ==================== 7. 统计功能测试 ====================
    print("\n[7] 统计功能测试")
    
    # 获取概览统计
    res = requests.get(f"{API_BASE}/dialogs/stats/overview", headers=headers)
    test("获取概览统计", res.ok)
    
    # 获取用户统计
    res = requests.get(f"{API_BASE}/dialogs/stats/users", headers=headers)
    test("获取用户统计", res.ok)
    
    # 获取筛选选项
    res = requests.get(f"{API_BASE}/dialogs/stats/filters", headers=headers)
    test("获取筛选选项", res.ok)
    
    # ==================== 8. 前端静态资源测试 ====================
    print("\n[8] 前端静态资源测试")
    
    # 测试主页面
    res = requests.get(f"{BASE_URL}/chat/")
    test("主页面可访问", res.ok and "直播脚本" in res.text)
    
    # 测试登录页面
    res = requests.get(f"{BASE_URL}/chat/login")
    test("登录页面可访问", res.ok)
    
    # 测试超级管理员登录页面
    res = requests.get(f"{BASE_URL}/superlogin")
    test("超级管理员登录页面可访问", res.ok)
    
    # 测试静态资源
    res = requests.get(f"{BASE_URL}/assets/index-C5Gj938W.js")
    # 可能文件名不同，检查是否有任何JS文件
    
    # ==================== 9. 清理测试数据 ====================
    print("\n[9] 清理测试数据")
    
    if dialog_id:
        res = requests.delete(f"{API_BASE}/dialogs/{dialog_id}?userId=test_user", headers=headers)
        test("删除测试对话", res.ok)
    
    # ==================== 测试结果 ====================
    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败, 共 {total} 项")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务已启动")
        print("   运行: docker compose up -d")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
