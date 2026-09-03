import pytest
from core.rss_parser import parse_rss_xml, get_rss_item_content, fetch_and_parse_rss
from fastapi.testclient import TestClient
from api.index import app

SAMPLE_RSS_2_0 = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tech News Feed</title>
    <link>https://example.com/feed</link>
    <description>Daily tech news and updates</description>
    <item>
      <title>E-Ink Technology Breakthrough</title>
      <link>https://example.com/articles/1</link>
      <description><![CDATA[<p>Researchers develop a <a href="#">new ultra-fast</a> refresh rate for <b>color e-paper displays</b>.</p><img src="https://example.com/images/eink.jpg" />]]></description>
      <author>Alice Editor</author>
      <pubDate>Thu, 04 Sep 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Open Source IoT Firmware 2.0</title>
      <link>https://example.com/articles/2</link>
      <description>New release offers seamless deep sleep support for ESP32 devices.</description>
      <author>Bob Coder</author>
      <pubDate>Thu, 04 Sep 2026 08:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Blog of Open Science</title>
  <link href="https://example.org/atom.xml" rel="self"/>
  <entry>
    <title>Quantum Computing in 2026</title>
    <link href="https://example.org/entries/1"/>
    <published>2026-09-04T08:00:00Z</published>
    <summary>A detailed review of 1000-qubit processors and their real-world impact.</summary>
    <author><name>Dr. Turing</name></author>
  </entry>
</feed>
"""


def test_parse_rss_2_0():
    feed = parse_rss_xml(SAMPLE_RSS_2_0, base_url="https://example.com")
    assert feed["title"] == "Tech News Feed"
    assert len(feed["items"]) == 2

    item0 = get_rss_item_content(feed, 0)
    assert item0["title"] == "E-Ink Technology Breakthrough"
    assert item0["author"] == "Alice Editor"
    assert "color e-paper displays" in item0["summary"]
    assert item0["image_url"] == "https://example.com/images/eink.jpg"
    assert item0["has_image"] is True
    assert item0["current_index"] == 1
    assert item0["total_items"] == 2

    item1 = get_rss_item_content(feed, 1)
    assert item1["title"] == "Open Source IoT Firmware 2.0"
    assert item1["image_url"] == ""
    assert item1["has_image"] is False


def test_parse_atom():
    feed = parse_rss_xml(SAMPLE_ATOM, base_url="https://example.org")
    assert feed["title"] == "Blog of Open Science"
    assert len(feed["items"]) == 1

    item0 = get_rss_item_content(feed, 0)
    assert item0["title"] == "Quantum Computing in 2026"
    assert item0["author"] == "Dr. Turing"
    assert "1000-qubit" in item0["summary"]


@pytest.mark.asyncio
async def test_live_user_test_rss_feed():
    feed_url = "https://kellson.dpdns.org:81/playno1/av"
    result = await fetch_and_parse_rss(feed_url)
    assert "error" not in result
    assert result["title"] != ""
    assert len(result["items"]) > 0
    item = get_rss_item_content(result, 0)
    assert item["title"] != ""
    assert item["total_items"] > 0


def test_open_api_endpoints():
    with TestClient(app) as client:
        # 1. 检查 RSS inspect
        resp = client.get("/api/open/rss/inspect?feed_url=https://kellson.dpdns.org:81/playno1/av")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] > 0
        assert "sample_item" in data

        # 2. 推送自定义 text
        resp_text = client.post("/api/open/device/TEST_OPEN_MAC/text", json={
            "title": "Home Assistant 通知",
            "message": "客厅温度 24°C，湿度 55%",
            "signature": "2026-09-04 12:00",
        })
        assert resp_text.status_code == 200
        assert resp_text.json()["code"] == 0

        # 3. 设置设备 RSS
        resp_rss = client.post("/api/open/device/TEST_OPEN_MAC/rss", json={
            "feed_url": "https://kellson.dpdns.org:81/playno1/av",
            "item_index": 0,
            "show_image": True,
        })
        assert resp_rss.status_code == 200
        assert resp_rss.json()["code"] == 0
