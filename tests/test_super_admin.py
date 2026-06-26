"""
超级管理员控制台自动化测试
"""

import requests
import sys

BASE_URL = "http://localhost:5172"
SUPER_ADMIN_API = f"{BASE_URL}/api/super-admin"

# 测试结果统计
passed = 0
failed = 0


def test(name, condition, detail=""):
    """记录测试结果"""
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} {detail}")
        failed += 1


def run_tests():
    global passed, failed
    token = None
    created_admin_id = None

    print("\n" + "=" * 50)
    print("超级管理员控制台自动化测试")
    print("=" * 50)

    # ==================== 1. 登录测试 ====================
    print("\n[1] 登录功能测试")

    # 1.1 错误密码登录
    print("\n  测试错误密码登录:")
    res = requests.post(f"{SUPER_ADMIN_API}/login", json={
        "username": "admin",
        "password": "wrong_password"
    })
    data = res.json()
    test("错误密码应返回失败", not data.get("success"))
    test("应返回错误信息", data.get("error") == "用户名或密码错误")

    # 1.2 普通管理员尝试超级管理员登录
    print("\n  测试普通管理员登录超级管理员:")
    res = requests.post(f"{SUPER_ADMIN_API}/login", json={
        "username": "admin123",
        "password": "admin123"
    })
    data = res.json()
    test("普通管理员应被拒绝", not data.get("success"))
    test("应返回错误信息", data.get("error") is not None)

    # 1.3 正确的超级管理员登录
    print("\n  测试超级管理员登录:")
    res = requests.post(f"{SUPER_ADMIN_API}/login", json={
        "username": "admin",
        "password": "admin"
    })
    data = res.json()
    test("登录应成功", data.get("success"))
    test("应返回 token", data.get("token") is not None)
    token = data.get("token")

    # ==================== 2. 访问控制测试 ====================
    print("\n[2] 访问控制测试")

    # 2.1 无 token 访问
    print("\n  测试无 token 访问:")
    res = requests.get(f"{SUPER_ADMIN_API}/admins")
    test("无 token 应返回 403", res.status_code == 403)

    # 2.2 使用普通管理员 token 访问
    print("\n  测试使用普通管理员 token:")
    # 先获取普通管理员 token
    res = requests.post(f"{BASE_URL}/chat/api/admin/login", json={
        "username": "admin123",
        "password": "admin123"
    })
    admin_token = res.json().get("token")
    res = requests.get(f"{SUPER_ADMIN_API}/admins", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    test("普通管理员 token 应返回 401", res.status_code == 401)

    # 2.3 使用正确的超级管理员 token
    print("\n  测试使用超级管理员 token:")
    res = requests.get(f"{SUPER_ADMIN_API}/admins", headers={
        "Authorization": f"Bearer {token}"
    })
    test("超级管理员 token 应返回 200", res.status_code == 200)

    # ==================== 3. 获取管理员列表 ====================
    print("\n[3] 获取管理员列表测试")

    res = requests.get(f"{SUPER_ADMIN_API}/admins", headers={
        "Authorization": f"Bearer {token}"
    })
    data = res.json()
    test("应返回列表", isinstance(data, list))
    test("应包含超级管理员", any(a.get("is_superadmin") for a in data))
    test("应包含普通管理员", any(not a.get("is_superadmin") for a in data))
    test("每个管理员应有 id 字段", all("id" in a for a in data))
    test("每个管理员应有 username 字段", all("username" in a for a in data))
    test("每个管理员应有 is_active 字段", all("is_active" in a for a in data))
    test("每个管理员应有 is_superadmin 字段", all("is_superadmin" in a for a in data))

    # ==================== 4. 创建管理员 ====================
    print("\n[4] 创建管理员测试")

    # 4.1 创建新管理员
    print("\n  测试创建新管理员:")
    res = requests.post(f"{SUPER_ADMIN_API}/admins", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "username": "test_admin",
        "password": "test123"
    })
    data = res.json()
    test("创建应返回 200", res.status_code == 200)
    test("应返回管理员信息", "id" in data)
    test("用户名应正确", data.get("username") == "test_admin")
    test("应为普通管理员", not data.get("is_superadmin"))
    test("应为启用状态", data.get("is_active"))
    created_admin_id = data.get("id")

    # 4.2 创建重复用户名
    print("\n  测试创建重复用户名:")
    res = requests.post(f"{SUPER_ADMIN_API}/admins", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "username": "test_admin",
        "password": "test456"
    })
    test("重复用户名应返回 400", res.status_code == 400)
    test("应返回用户名已存在", "已存在" in res.json().get("detail", ""))

    # 4.3 创建重复用户名（已存在的普通管理员）
    print("\n  测试创建已存在的普通管理员用户名:")
    res = requests.post(f"{SUPER_ADMIN_API}/admins", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "username": "admin123",
        "password": "test789"
    })
    test("已存在用户名应返回 400", res.status_code == 400)

    # ==================== 5. 更新管理员 ====================
    print("\n[5] 更新管理员测试")

    if created_admin_id:
        # 5.1 禁用管理员
        print("\n  测试禁用管理员:")
        res = requests.put(f"{SUPER_ADMIN_API}/admins/{created_admin_id}", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "is_active": False
        })
        test("禁用应返回 200", res.status_code == 200)
        test("状态应为禁用", not res.json().get("is_active"))

        # 5.2 启用管理员
        print("\n  测试启用管理员:")
        res = requests.put(f"{SUPER_ADMIN_API}/admins/{created_admin_id}", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "is_active": True
        })
        test("启用应返回 200", res.status_code == 200)
        test("状态应为启用", res.json().get("is_active"))

        # 5.3 修改用户名
        print("\n  测试修改用户名:")
        res = requests.put(f"{SUPER_ADMIN_API}/admins/{created_admin_id}", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "username": "test_admin_renamed"
        })
        test("修改用户名应返回 200", res.status_code == 200)
        test("用户名应已更新", res.json().get("username") == "test_admin_renamed")

        # 5.4 修改为重复用户名
        print("\n  测试修改为重复用户名:")
        res = requests.put(f"{SUPER_ADMIN_API}/admins/{created_admin_id}", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "username": "admin123"
        })
        test("修改为重复用户名应返回 400", res.status_code == 400)

    # 5.5 尝试修改超级管理员
    print("\n  测试修改超级管理员:")
    super_admin = next(a for a in requests.get(f"{SUPER_ADMIN_API}/admins", headers={
        "Authorization": f"Bearer {token}"
    }).json() if a.get("is_superadmin"))
    res = requests.put(f"{SUPER_ADMIN_API}/admins/{super_admin['id']}", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "is_active": False
    })
    test("修改超级管理员应返回 400", res.status_code == 400)
    test("应返回不能修改提示", "不能修改" in res.json().get("detail", ""))

    # 5.6 更新不存在的管理员
    print("\n  测试更新不存在的管理员:")
    res = requests.put(f"{SUPER_ADMIN_API}/admins/99999", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "is_active": False
    })
    test("更新不存在的管理员应返回 404", res.status_code == 404)

    # ==================== 6. 重置密码 ====================
    print("\n[6] 重置密码测试")

    if created_admin_id:
        # 6.1 重置密码
        print("\n  测试重置密码:")
        res = requests.post(f"{SUPER_ADMIN_API}/admins/{created_admin_id}/reset-password", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "new_password": "new_password123"
        })
        test("重置密码应返回 200", res.status_code == 200)

        # 6.2 使用新密码登录
        print("\n  测试使用新密码登录:")
        res = requests.post(f"{BASE_URL}/chat/api/admin/login", json={
            "username": "test_admin_renamed",
            "password": "new_password123"
        })
        data = res.json()
        test("新密码登录应成功", data.get("success"))

        # 6.3 使用旧密码登录
        print("\n  测试使用旧密码登录:")
        res = requests.post(f"{BASE_URL}/chat/api/admin/login", json={
            "username": "test_admin_renamed",
            "password": "test123"
        })
        data = res.json()
        test("旧密码登录应失败", not data.get("success"))

    # 6.4 尝试重置超级管理员密码
    print("\n  测试重置超级管理员密码:")
    res = requests.post(f"{SUPER_ADMIN_API}/admins/{super_admin['id']}/reset-password", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "new_password": "hack_password"
    })
    test("重置超级管理员密码应返回 400", res.status_code == 400)
    test("应返回不能重置提示", "不能重置" in res.json().get("detail", ""))

    # 6.5 重置不存在的管理员密码
    print("\n  测试重置不存在的管理员密码:")
    res = requests.post(f"{SUPER_ADMIN_API}/admins/99999/reset-password", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "new_password": "test"
    })
    test("重置不存在的管理员应返回 404", res.status_code == 404)

    # ==================== 7. 删除管理员 ====================
    print("\n[7] 删除管理员测试")

    # 7.1 尝试删除超级管理员
    print("\n  测试删除超级管理员:")
    res = requests.delete(f"{SUPER_ADMIN_API}/admins/{super_admin['id']}", headers={
        "Authorization": f"Bearer {token}"
    })
    test("删除超级管理员应返回 400", res.status_code == 400)
    test("应返回不能删除提示", "不能删除" in res.json().get("detail", ""))

    # 7.2 删除不存在的管理员
    print("\n  测试删除不存在的管理员:")
    res = requests.delete(f"{SUPER_ADMIN_API}/admins/99999", headers={
        "Authorization": f"Bearer {token}"
    })
    test("删除不存在的管理员应返回 404", res.status_code == 404)

    # 7.3 删除创建的测试管理员
    if created_admin_id:
        print("\n  测试删除测试管理员:")
        res = requests.delete(f"{SUPER_ADMIN_API}/admins/{created_admin_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        test("删除应返回 200", res.status_code == 200)

        # 验证已删除
        res = requests.get(f"{SUPER_ADMIN_API}/admins", headers={
            "Authorization": f"Bearer {token}"
        })
        admin_ids = [a["id"] for a in res.json()]
        test("管理员列表中应已删除", created_admin_id not in admin_ids)

    # ==================== 测试结果 ====================
    print("\n" + "=" * 50)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 50)

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
        sys.exit(1)
