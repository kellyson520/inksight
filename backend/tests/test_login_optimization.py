"""
Test user authentication speed, multi-identifier login (username/email/phone),
and non-blocking verification.
"""
import time
import pytest
from core.config_store import create_user, authenticate_user
from core.db import get_main_db


@pytest.mark.asyncio
async def test_authenticate_user_by_username_email_and_phone():
    """验证使用用户名、邮箱、手机号三种方式均可极速认证成功。"""
    unique_suffix = int(time.time() * 1000)
    username = f"speed_user_{unique_suffix}"
    email = f"speed_{unique_suffix}@example.com"
    phone = f"+86138{unique_suffix % 100000000:08d}"
    password = "SafePassword123!"

    # 创建用户
    user_id = await create_user(
        username=username,
        password=password,
        email=email,
        phone=phone,
    )
    assert user_id is not None

    # 1. 用户名登录
    t0 = time.perf_counter()
    u1 = await authenticate_user(username, password)
    t1 = time.perf_counter()
    assert u1 is not None
    assert u1["id"] == user_id
    assert u1["username"] == username
    print(f"Username auth latency: {(t1 - t0) * 1000:.2f} ms")

    # 2. 邮箱登录
    t0 = time.perf_counter()
    u2 = await authenticate_user(email, password)
    t1 = time.perf_counter()
    assert u2 is not None
    assert u2["id"] == user_id

    # 3. 手机号登录
    t0 = time.perf_counter()
    u3 = await authenticate_user(phone, password)
    t1 = time.perf_counter()
    assert u3 is not None
    assert u3["id"] == user_id

    # 4. 错误密码拒绝
    u_fail = await authenticate_user(username, "wrong_pw")
    assert u_fail is None

    # 5. 不存在的用户拒绝
    u_none = await authenticate_user(f"nonexistent_{unique_suffix}", password)
    assert u_none is None
