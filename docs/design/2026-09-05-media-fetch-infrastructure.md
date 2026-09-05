# 远程媒体获取基础设施设计

## 目标
将网络超时、临时网络故障、外链失效、防盗链、重复下载和离线回退统一下沉为后端基础设施，供 JSON 图片渲染器、内容 Provider 和未来媒体上游复用。

## 背景与约束
- 当前 `backend/core/blocks/components.py` 直接使用 `httpx.Client`，策略只存在于图片组件内部。
- 图片在测量和实际渲染阶段可能重复请求。
- 部分上游 URL 返回 404/418，单个失效链接会直接变成占位符。
- 现有 Docker 全量挂载环境需要修改代码后自动生效。
- 不新增外部服务，不要求数据库迁移，不把二进制缓存提交进 Git。

## 方案
新增 `core/media_fetcher.py`，提供同步、线程安全、可注入 HTTP 客户端的媒体获取服务：
1. 规范化 URL 候选列表并逐一尝试；
2. 使用连接/读取/写入/连接池分阶段超时；
3. 对 408、425、429、5xx 和传输异常进行有限指数退避重试；
4. 对 404、410、418 等永久或半永久失败快速切换候选源；
5. 按 URL SHA256 建立内存缓存与磁盘缓存，原子写入并校验非空；
6. 按域名生成 Referer，统一 User-Agent；
7. 对失败结果做短暂冷却，避免每次渲染都重复打击失效源；
8. 返回带来源、缓存命中和失败原因的结构化结果，失败时由上游决定占位符或继续候选。

`render_image` 只负责解析布局和调用 `media_fetcher.fetch()`，不再拥有网络重试、Referer、缓存实现。内置模式的候选 URL 由其 Service 提供；当前先把微信读书和已有图片渲染链路迁移，其他 Provider 通过同一公共接口接入。

## 接口与数据流
```python
@dataclass(frozen=True)
class MediaFetchResult:
    data: bytes
    url: str
    cache_hit: bool

class MediaFetcher:
    def fetch(self, urls: str | Sequence[str], *, referer: str | None = None) -> MediaFetchResult:
        ...

media_fetcher.fetch(image_url)
```

缓存顺序：内存 -> 磁盘 -> 候选 URL 网络请求。网络成功后原子写入磁盘并更新内存；网络失败时进入短暂 failure cooldown，避免热循环。单个 URL 的失败不会阻止候选 URL 继续尝试。

## 模块划分
- `backend/core/media_fetcher.py`: 底层策略、配置、缓存、结果类型。
- `backend/core/blocks/components.py`: 删除本地网络策略，调用基础设施并负责渲染。
- `backend/core/wechat_read_service.py`: 为失效书封提供稳定候选 URL。
- `backend/tests/test_media_fetcher.py`: 超时、重试、候选切换、缓存、Referer、冷却测试。
- `backend/tests/test_wechat_read_mode.py`: 图片渲染回归测试继续覆盖上游行为。
- `docs/changelog.md`: 记录基础设施变更。

## 边界
- 不实现通用网页抓取，不解析 HTML，不自动搜索互联网替换链接。
- 不无限重试；不掩盖所有上游错误。
- 不把远程图片代理成公开 HTTP 接口。
- 不将运行时缓存二进制纳入版本控制；缓存目录加入忽略规则。

## 风险与缓解
- 磁盘不可写：缓存写入失败只记录 debug，不阻断网络返回。
- 图片响应非图片：交给 Pillow 校验，失败后继续候选 URL。
- 多进程同时写入：临时文件加 `os.replace`，损坏文件读取失败后删除。
- 上游接口变化：候选 URL 与 Referer策略集中在底层，Provider 无需复制网络代码。

## 验收标准
- 失败测试能稳定证明：超时会按有限策略重试，失效 URL 会切换候选源，成功内容会被缓存，重复渲染不再重复网络请求。
- `render_image` 不再直接创建 `httpx.Client`。
- 微信读书所有内置书籍在断网时仍可从已存在缓存渲染，未缓存时能通过候选 URL 获取。
- 本地与 Docker 相关测试通过，预览接口返回 HTTP 200，日志无微信读书封面下载失败。
