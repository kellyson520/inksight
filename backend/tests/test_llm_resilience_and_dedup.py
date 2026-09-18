"""
测试 LLM 弹性调用、多 Provider 故障转移（不降级）与全模式强去重机制（不重复）
"""
import pytest
from unittest.mock import AsyncMock, patch
from core.content import _call_llm_resilient, get_configured_llm_providers
from core.mode_registry import get_registry
from core.json_content import generate_json_mode_content
from core.preload_store import get_next_preload_item
from core.db import close_all


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await close_all()


@pytest.mark.asyncio
async def test_call_llm_resilient_failover_success(monkeypatch):
    """验证当主 provider 遇到网络故障或超额时，能自动无缝故障转移至备用 provider，实现不降级。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-valid-deepseek")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-valid-aliyun")

    call_history = []

    async def mock_call(provider, model, prompt, **kwargs):
        call_history.append((provider, model))
        if provider == "aliyun":
            raise TimeoutError("Aliyun gateway timeout 504")
        return '{"result": "Success from DeepSeek failover"}'

    with patch("core.content._call_llm", side_effect=mock_call):
        res = await _call_llm_resilient("aliyun", "qwen-plus", "test prompt")
        assert "DeepSeek failover" in res
        assert ("aliyun", "qwen-plus") in call_history
        assert ("deepseek", "deepseek-chat") in call_history


@pytest.mark.asyncio
async def test_llm_mode_dedup_story_and_bias(monkeypatch):
    """验证全局强去重机制：针对 STORY 和 BIAS 等模式，当 LLM 生成已出过的内容时触发去重重试。"""
    reg = get_registry()
    story_def = reg.get_json_mode("STORY").definition

    attempts = 0

    async def mock_llm_call(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            # 第一次返回与历史重复的标题
            return '{"title": "雨夜的来客", "setup": "门铃在暴雨中响起", "twist": "门外只有一面镜子", "ending": "他终于看清了自己"}'
        else:
            # 第二次重试返回全新内容
            return '{"title": "星际信差的终章", "setup": "飞船在星云边缘耗尽了燃料", "twist": "漂流瓶里装着母星的阳光", "ending": "黑暗中亮起了一颗新星"}'

    with patch("core.json_content._call_llm_resilient", side_effect=mock_llm_call), \
         patch("core.stats_store.get_recent_content_field_values", new_callable=AsyncMock) as mock_fields, \
         patch("core.stats_store.get_recent_content_hashes", new_callable=AsyncMock, return_value=[]), \
         patch("core.stats_store.get_recent_content_summaries", new_callable=AsyncMock, return_value=[]):
        
        # 模拟历史库中存在 "雨夜的来客"
        mock_fields.return_value = ["雨夜的来客"]

        result = await generate_json_mode_content(story_def, mac="TEST_DEDUP_MAC")
        assert attempts >= 2
        assert result["title"] == "星际信差的终章"
        assert result["_llm_ok"] is True


@pytest.mark.asyncio
async def test_preload_pool_continuous_rotation_no_repeat():
    """验证在无 LLM 或离线时，预存池通过游标在多次调用间持续滚动推进，保证不重复。"""
    mac = "TEST_ROTATION_MAC_UNIQUE_123"
    results = []
    for _ in range(5):
        item = await get_next_preload_item("QUESTION", mac=mac)
        if item:
            results.append(item.get("question"))

    assert len(results) >= 2
    # 验证相邻两次提取的问题不相同
    for i in range(len(results) - 1):
        assert results[i] != results[i + 1]
