# InkSight 平台地基持续演进设计

## 目标
建立可复用、可观测、可持续迁移的核心平台层，降低新闻爬取、网页检测、热榜监听、内容渲染和模式组装的重复实现成本，并通过稳定性指标驱动后续迭代。

## 当前判断
代码库已有 `http_client.py`、`media_fetcher.py`、渲染统计和监控服务，但多个业务模块仍直接创建 HTTP client、各自实现重试/缓存/解析；请求、依赖、渲染和缓存缺少统一事件模型；热榜监听尚未形成后台快照/差异运行器。

## 分阶段方案
### 第一阶段：核心出口与观测契约
- `OutboundHttp`：统一请求策略、超时、重试、TLS 校验、重定向边界、响应大小、结构化错误和依赖耗时事件。
- `Observability`：统一 request/dependency/render/cache/exception 事件，输出 JSON 日志并保留低基数内存快照；观测失败不影响业务。
- 先接入媒体、RSS、新闻、热榜读取路径，禁止新增直接 `httpx.Client`。

### 第二阶段：数据源与监听器
- `SourceResult`：统一 fresh/stale/fallback/unavailable 状态、抓取时间、过期时间、错误类型和来源。
- `FeedParser` 与 `HotlistSource` registry：将 RSS、新闻源、平台热榜的请求和解析分离。
- `MonitorRunner` 与 `HotlistDiffRunner`：按间隔执行、生成稳定差异事件，写入 outbox，支持单进程租约。

### 第三阶段：渲染与组装
- `ProviderContext` / `ModeSnapshot`：一次解析 mode、语言、设备、配置和 definition，content/render 共用快照。
- 缓存键纳入颜色、语言、定义版本和配置 hash；增加 single-flight。
- BlockSpec 统一 render/measure/validate/resource collection，优先迁移文本、图片、布局和热榜行。

### 第四阶段：运营闭环
- 管理端观测摘要：请求 p50/p95/p99、依赖错误、重试、缓存、fallback、监听器健康和渲染阶段耗时。
- 基于指标做容量限制、源健康评分、自动熔断恢复和性能回归基线。

## 第一阶段接口
```python
class OutboundHttp:
    async def get_json(...): ...
    async def get_text(...): ...
    async def get_bytes(...): ...

class Observability:
    def emit(self, event: str, attributes: Mapping[str, Any]) -> None: ...
    def start_request(self, ...): ...
    def observe(self, operation: str, ...): ...
    def snapshot(self) -> dict[str, Any]: ...
```

## 安全与性能约束
- 默认 `verify=True`，禁止全局 `verify=False`；自签名服务使用显式 CA 配置。
- URL 校验阻断 loopback、私有、link-local、metadata 地址；重定向需重新校验或默认关闭。
- 响应体有最大字节数；请求有连接池；重试有上限和 jitter。
- 指标标签低基数，不记录 API key、Cookie、token、完整 prompt、原始 transcript 或完整用户内容。
- 观测不可阻断业务；所有外部依赖调用必须能报告耗时和结果。

## 验收标准
- 核心接口和故障注入测试通过。
- RSS、新闻和热榜新增代码不再直接创建 HTTP client。
- 请求与依赖事件包含 request_id、operation、status、duration_ms、retry_count、source_status。
- Docker 后端回归通过，线上预览 HTTP 200，管理摘要可读。
- 每一阶段保留设计、测试、指标和提交记录，下一阶段由实际观测数据驱动。
