from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from api.db.clickhouse import ClickHouseReader, get_clickhouse_reader, parse_attributes
from api.models import (
    AgentListResponse,
    AgentSummary,
    Framework,
    GraphEdge,
    GraphNode,
    GraphNodeData,
    MetricsHistogramBucket,
    MetricsOverviewData,
    Span,
    SpanEndStateDistribution,
    SpanEndStatePoint,
    SpanStatus,
    SpanType,
    TraceAgentDetail,
    TraceDetail,
    TraceDetailMeta,
    TraceGraphResponse,
    TraceListResponse,
    TraceMetrics,
    TraceSummary,
)
from shared.config import get_settings
from shared.usage import cost_from_attributes, parse_usage, resolve_cost, sum_cost_usd, sum_total_tokens


def _isoformat(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    text = str(value)
    if " " in text and "T" not in text:
        return text.replace(" ", "T") + "Z"
    return text


_SPAN_COUNT_LABELS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12+"]
_DURATION_BUCKETS_MS: list[tuple[int, int | None, str]] = [
    (0, 100, "<100ms"),
    (100, 500, "100–500ms"),
    (500, 1000, "0.5–1s"),
    (1000, 2500, "1–2.5s"),
    (2500, 5000, "2.5–5s"),
    (5000, 10000, "5–10s"),
    (10000, 30000, "10–30s"),
    (30000, 60000, "30–60s"),
    (60000, 120000, "1–2m"),
    (120000, None, "2m+"),
]
_COST_BUCKETS_USD: list[tuple[float, float | None, str]] = [
    (0.0, 0.01, "<$0.01"),
    (0.01, 0.05, "$0.01–0.05"),
    (0.05, 0.10, "$0.05–0.10"),
    (0.10, 0.25, "$0.10–0.25"),
    (0.25, 0.50, "$0.25–0.50"),
    (0.50, 1.0, "$0.50–1"),
    (1.0, 2.0, "$1–2"),
    (2.0, None, "$2+"),
]


def _bucket_label(
    value: float,
    buckets: list[tuple[float, float | None, str]],
) -> str:
    for low, high, label in buckets:
        if high is None:
            if value >= low:
                return label
        elif low <= value < high:
            return label
    return buckets[-1][2]


def _empty_histogram(labels: list[str]) -> list[MetricsHistogramBucket]:
    return [MetricsHistogramBucket(label=label, value=0) for label in labels]


def _increment_histogram(
    buckets: list[MetricsHistogramBucket],
    label: str,
    amount: int = 1,
) -> None:
    for bucket in buckets:
        if bucket.label == label:
            bucket.value += amount
            return


def _format_short_date(date_str: str) -> str:
    try:
        _year, month, day = date_str.split("-")
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        return f"{months[int(month) - 1]} {int(day)}"
    except (ValueError, IndexError):
        return date_str


def _fill_span_end_state_days(
    points: list[SpanEndStatePoint],
    days: int = 30,
) -> list[SpanEndStatePoint]:
    by_date = {point.date: point for point in points}
    today = datetime.now(UTC).date()
    filled: list[SpanEndStatePoint] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        key = day.isoformat()
        filled.append(
            by_date.get(
                key,
                SpanEndStatePoint(date=key, success=0, indeterminate=0, fail=0),
            )
        )
    return filled


def _row_to_span(row: dict[str, Any]) -> Span:
    attributes = parse_attributes(row.get("attributes"))
    framework = str(row.get("framework", "manual"))
    span_type = str(row.get("span_type", "agent"))
    usage = parse_usage(attributes)

    return Span(
        trace_id=str(row["trace_id"]),
        span_id=str(row["span_id"]),
        parent_span_id=row.get("parent_span_id"),
        agent_id=str(row["agent_id"]),
        agent_name=str(row["agent_name"]),
        run_id=str(row["run_id"]),
        framework=framework if framework in {"langchain", "crewai", "manual", "openai"} else "manual",  # type: ignore[arg-type]
        span_type=span_type if span_type in {"agent", "tool", "llm", "delegation", "other"} else "other",  # type: ignore[arg-type]
        start_time=_isoformat(row["start_time"]),
        end_time=_isoformat(row["end_time"]),
        duration_ms=int(row.get("duration_ms") or 0),
        status=str(row.get("status", "ok")),  # type: ignore[arg-type]
        error_message=row.get("error_message"),
        attributes=attributes,
        input_preview=str(row.get("input_preview") or ""),
        output_preview=str(row.get("output_preview") or ""),
        model=usage["model"],
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        cost_usd=resolve_cost(usage),
    )


def _extract_tags(spans: list[Span]) -> list[str]:
    tags: list[str] = []
    for span in spans:
        tag = span.attributes.get("agentops.tag")
        if isinstance(tag, str) and tag not in tags:
            tags.append(tag)
    return tags


def _derive_agents(spans: list[Span]) -> list[TraceAgentDetail]:
    agent_spans = [span for span in spans if span.span_type == "agent"]
    tool_spans = [span for span in spans if span.span_type == "tool"]
    agents: list[TraceAgentDetail] = []

    for agent_span in agent_spans:
        related_tools: list[str] = []
        for tool in tool_spans:
            current: Span | None = tool
            while current and current.parent_span_id:
                if current.parent_span_id == agent_span.span_id:
                    related_tools.append(tool.agent_name)
                    break
                current = next((s for s in spans if s.span_id == current.parent_span_id), None)
        agents.append(TraceAgentDetail(name=agent_span.agent_name, tools=related_tools))

    return agents


def _build_trace_meta(spans: list[Span]) -> TraceDetailMeta | None:
    if not spans:
        return None

    sorted_spans = sorted(spans, key=lambda span: span.start_time)
    start = sorted_spans[0].start_time
    end = max(span.end_time for span in spans)
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    duration_ms = max(int((end_dt - start_dt).total_seconds() * 1000), 0)

    root = next((span for span in sorted_spans if span.parent_span_id is None), sorted_spans[0])
    llm_calls = sum(1 for span in spans if span.span_type == "llm")
    tool_calls = sum(1 for span in spans if span.span_type == "tool")
    errors = sum(1 for span in spans if span.status == "error")
    trace_cost = sum_cost_usd(spans)
    model = next(
        (span.model for span in sorted_spans if span.model),
        None,
    )

    return TraceDetailMeta(
        name=root.agent_name,
        model=model,
        duration_ms=duration_ms,
        llm_calls=llm_calls,
        tool_calls=tool_calls,
        errors=errors,
        total_tokens=sum_total_tokens(spans),
        total_cost_usd=trace_cost if trace_cost > 0 else None,
        tags=_extract_tags(spans),
        start_time=start,
    )


def _span_type_to_node_type(span_type: SpanType) -> str:
    if span_type == "tool":
        return "toolNode"
    if span_type == "llm":
        return "llmNode"
    return "agentNode"


class TraceService:
    def __init__(self, reader: ClickHouseReader | None = None) -> None:
        self._reader = reader or get_clickhouse_reader()
        self._db = get_settings().clickhouse_db

    async def _sum_org_cost_usd(self, org_id: str) -> float:
        rows = await self._reader.query(
            f"""
            SELECT attributes
            FROM {self._db}.spans
            WHERE org_id = {{org_id:String}}
              AND span_type = 'llm'
            FORMAT JSON
            """,
            {"org_id": org_id},
        )
        total = 0.0
        for row in rows:
            cost = cost_from_attributes(parse_attributes(row.get("attributes")))
            if cost is not None:
                total += cost
        return total

    async def _cost_by_trace_id(self, org_id: str, trace_ids: list[str]) -> dict[str, float]:
        if not trace_ids:
            return {}

        trace_id_set = set(trace_ids)
        rows = await self._reader.query(
            f"""
            SELECT trace_id, attributes
            FROM {self._db}.spans
            WHERE org_id = {{org_id:String}}
              AND span_type = 'llm'
            FORMAT JSON
            """,
            {"org_id": org_id},
        )

        costs: dict[str, float] = {}
        for row in rows:
            trace_id = str(row["trace_id"])
            if trace_id not in trace_id_set:
                continue
            cost = cost_from_attributes(parse_attributes(row.get("attributes")))
            if cost is None:
                continue
            costs[trace_id] = costs.get(trace_id, 0.0) + cost
        return costs

    async def list_traces(
        self,
        org_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        status: SpanStatus | None = None,
    ) -> TraceListResponse:
        status_filter = ""
        params: dict[str, Any] = {"org_id": org_id, "limit": limit, "offset": offset}
        if status is not None:
            status_filter = "WHERE if(error_count > 0, 'error', 'ok') = {status:String}"
            params["status"] = status

        rows = await self._reader.query(
            f"""
            SELECT
                trace_id,
                run_id,
                agent_name,
                if(error_count > 0, 'error', 'ok') AS status,
                trace_start,
                dateDiff('millisecond', trace_start, trace_end) AS duration_ms,
                span_count,
                error_count
            FROM (
                SELECT
                    trace_id,
                    run_id,
                    argMax(agent_name, start_time) AS agent_name,
                    min(start_time) AS trace_start,
                    max(end_time) AS trace_end,
                    count() AS span_count,
                    countIf(status = 'error') AS error_count
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                GROUP BY trace_id, run_id
            )
            {status_filter}
            ORDER BY trace_start DESC
            LIMIT {{limit:UInt32}}
            OFFSET {{offset:UInt32}}
            FORMAT JSON
            """,
            params,
        )

        total = int(
            await self._reader.query_scalar(
                f"""
                SELECT countDistinct(trace_id)
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        total_events = int(
            await self._reader.query_scalar(
                f"""
                SELECT count()
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        error_count = int(
            await self._reader.query_scalar(
                f"""
                SELECT countIf(status = 'error')
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        traces = [
            TraceSummary(
                trace_id=str(row["trace_id"]),
                run_id=str(row["run_id"]),
                agent_name=str(row["agent_name"]),
                name=str(row["agent_name"]),
                status=str(row["status"]),  # type: ignore[arg-type]
                duration_ms=int(row.get("duration_ms") or 0),
                span_count=int(row.get("span_count") or 0),
                start_time=_isoformat(row.get("trace_start") or row.get("start_time")),
                error_count=int(row.get("error_count") or 0),
            )
            for row in rows
        ]

        trace_costs = await self._cost_by_trace_id(org_id, [trace.trace_id for trace in traces])
        traces = [
            trace.model_copy(update={"cost_usd": trace_costs.get(trace.trace_id)})
            for trace in traces
        ]

        tokens_generated = int(
            await self._reader.query_scalar(
                f"""
                SELECT sum(
                    greatest(
                        JSONExtractInt(attributes, 'agentops.total_tokens'),
                        JSONExtractInt(attributes, 'gen_ai.usage.total_tokens'),
                        JSONExtractInt(attributes, 'agentops.prompt_tokens')
                            + JSONExtractInt(attributes, 'agentops.completion_tokens'),
                        0
                    )
                )
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        fail_rate = (error_count / total_events) if total_events else None
        total_cost_usd = await self._sum_org_cost_usd(org_id)
        metrics = TraceMetrics(
            total_cost_usd=total_cost_usd,
            tokens_generated=tokens_generated,
            fail_rate=fail_rate,
            total_events=total_events,
        )

        return TraceListResponse(traces=traces, total=total, metrics=metrics)

    async def get_trace(self, trace_id: str, org_id: str | None = None) -> TraceDetail | None:
        params: dict[str, Any] = {"trace_id": trace_id}
        org_filter = ""
        if org_id is not None:
            org_filter = "AND org_id = {org_id:String}"
            params["org_id"] = org_id

        rows = await self._reader.query(
            f"""
            SELECT *
            FROM {self._db}.spans
            WHERE trace_id = {{trace_id:String}}
            {org_filter}
            ORDER BY start_time ASC
            FORMAT JSON
            """,
            params,
        )
        if not rows:
            return None

        spans = [_row_to_span(row) for row in rows]
        return TraceDetail(
            trace_id=trace_id,
            run_id=spans[0].run_id,
            spans=spans,
            meta=_build_trace_meta(spans),
            agents=_derive_agents(spans),
        )

    async def get_trace_graph(self, trace_id: str, org_id: str | None = None) -> TraceGraphResponse:
        trace = await self.get_trace(trace_id, org_id)
        if trace is None:
            return TraceGraphResponse(nodes=[], edges=[])

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        for span in trace.spans:
            nodes.append(
                GraphNode(
                    id=span.span_id,
                    type=_span_type_to_node_type(span.span_type),  # type: ignore[arg-type]
                    data=GraphNodeData(
                        label=span.agent_name,
                        status=span.status,
                        spanId=span.span_id,
                        durationMs=span.duration_ms,
                        spanType=span.span_type,
                    ),
                    position={"x": 0.0, "y": 0.0},
                )
            )

        for span in trace.spans:
            if span.parent_span_id:
                edges.append(
                    GraphEdge(
                        id=f"{span.parent_span_id}-{span.span_id}",
                        source=span.parent_span_id,
                        target=span.span_id,
                        data={"status": span.status},
                    )
                )

        return TraceGraphResponse(nodes=nodes, edges=edges)

    async def list_agents(self, org_id: str) -> AgentListResponse:
        rows = await self._reader.query(
            f"""
            SELECT
                agent_id,
                argMax(agent_name, start_time) AS agent_name,
                argMax(framework, start_time) AS framework,
                countDistinct(run_id) AS total_runs,
                countIf(status = 'error') / count() AS error_rate,
                toInt64(avg(duration_ms)) AS avg_duration_ms,
                max(start_time) AS last_seen
            FROM {self._db}.spans
            WHERE org_id = {{org_id:String}}
            GROUP BY agent_id
            ORDER BY last_seen DESC
            FORMAT JSON
            """,
            {"org_id": org_id},
        )

        agents = [
            AgentSummary(
                agent_id=str(row["agent_id"]),
                agent_name=str(row["agent_name"]),
                framework=str(row.get("framework", "manual")),  # type: ignore[arg-type]
                total_runs=int(row.get("total_runs") or 0),
                error_rate=float(row.get("error_rate") or 0.0),
                avg_duration_ms=int(row.get("avg_duration_ms") or 0),
                last_seen=_isoformat(row["last_seen"]),
            )
            for row in rows
        ]
        return AgentListResponse(agents=agents)

    async def get_metrics_overview(self, org_id: str) -> MetricsOverviewData:
        total_events = int(
            await self._reader.query_scalar(
                f"""
                SELECT count()
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        error_count = int(
            await self._reader.query_scalar(
                f"""
                SELECT countIf(status = 'error')
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        monthly_spans = int(
            await self._reader.query_scalar(
                f"""
                SELECT count()
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                  AND toStartOfMonth(start_time) = toStartOfMonth(now())
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        end_state_rows = await self._reader.query(
            f"""
            SELECT
                toString(toDate(start_time)) AS date,
                countIf(status = 'ok') AS success,
                0 AS indeterminate,
                countIf(status = 'error') AS fail
            FROM {self._db}.spans
            WHERE org_id = {{org_id:String}}
            GROUP BY date
            ORDER BY date ASC
            FORMAT JSON
            """,
            {"org_id": org_id},
        )

        span_end_states = [
            SpanEndStatePoint(
                date=str(row["date"]),
                success=int(row.get("success") or 0),
                indeterminate=int(row.get("indeterminate") or 0),
                fail=int(row.get("fail") or 0),
            )
            for row in end_state_rows
        ]
        span_end_states = _fill_span_end_state_days(span_end_states, days=30)

        success_count = total_events - error_count
        distribution = SpanEndStateDistribution(
            success=success_count,
            indeterminate=0,
            fail=error_count,
        )

        spans_per_trace_rows = await self._reader.query(
            f"""
            SELECT
                span_count,
                count() AS value
            FROM (
                SELECT trace_id, count() AS span_count
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                GROUP BY trace_id
            )
            GROUP BY span_count
            ORDER BY span_count ASC
            FORMAT JSON
            """,
            {"org_id": org_id},
        )

        spans_per_trace = _empty_histogram(_SPAN_COUNT_LABELS)
        for row in spans_per_trace_rows:
            count = int(row.get("span_count") or 0)
            label = "12+" if count >= 12 else str(count)
            if label in _SPAN_COUNT_LABELS:
                _increment_histogram(spans_per_trace, label, int(row.get("value") or 0))

        duration_rows = await self._reader.query(
            f"""
            SELECT
                dateDiff('millisecond', min(start_time), max(end_time)) AS duration_ms
            FROM {self._db}.spans
            WHERE org_id = {{org_id:String}}
            GROUP BY trace_id
            FORMAT JSON
            """,
            {"org_id": org_id},
        )

        trace_duration_distribution = _empty_histogram(
            [label for _low, _high, label in _DURATION_BUCKETS_MS]
        )
        for row in duration_rows:
            duration_ms = float(row.get("duration_ms") or 0)
            label = _bucket_label(duration_ms, _DURATION_BUCKETS_MS)
            _increment_histogram(trace_duration_distribution, label)

        cost_by_trace = await self._cost_by_trace_id(
            org_id,
            [
                str(row["trace_id"])
                for row in await self._reader.query(
                    f"""
                    SELECT DISTINCT trace_id
                    FROM {self._db}.spans
                    WHERE org_id = {{org_id:String}}
                    FORMAT JSON
                    """,
                    {"org_id": org_id},
                )
            ],
        )
        trace_cost_distribution = _empty_histogram(
            [label for _low, _high, label in _COST_BUCKETS_USD]
        )
        for cost in cost_by_trace.values():
            label = _bucket_label(cost, _COST_BUCKETS_USD)
            _increment_histogram(trace_cost_distribution, label)
        # Traces with no LLM cost still count in the lowest bucket when they exist
        traces_without_cost = max(0, len(duration_rows) - len(cost_by_trace))
        if traces_without_cost:
            _increment_histogram(trace_cost_distribution, "<$0.01", traces_without_cost)

        failed_spans = [
            MetricsHistogramBucket(
                label=_format_short_date(point.date),
                value=point.fail,
            )
            for point in span_end_states
        ]

        tokens_generated = int(
            await self._reader.query_scalar(
                f"""
                SELECT sum(
                    greatest(
                        JSONExtractInt(attributes, 'agentops.total_tokens'),
                        JSONExtractInt(attributes, 'gen_ai.usage.total_tokens'),
                        JSONExtractInt(attributes, 'agentops.prompt_tokens')
                            + JSONExtractInt(attributes, 'agentops.completion_tokens'),
                        0
                    )
                )
                FROM {self._db}.spans
                WHERE org_id = {{org_id:String}}
                FORMAT JSON
                """,
                {"org_id": org_id},
            )
            or 0
        )

        overview = TraceMetrics(
            total_cost_usd=await self._sum_org_cost_usd(org_id),
            tokens_generated=tokens_generated,
            fail_rate=(error_count / total_events) if total_events else None,
            total_events=total_events,
            monthly_spans=monthly_spans,
            monthly_span_limit=5000,
        )

        return MetricsOverviewData(
            overview=overview,
            span_end_states=span_end_states,
            span_end_states_distribution=distribution,
            spans_per_trace=spans_per_trace,
            trace_duration_distribution=trace_duration_distribution,
            failed_spans=failed_spans,
            trace_cost_distribution=trace_cost_distribution,
        )


_trace_service: TraceService | None = None


def get_trace_service() -> TraceService:
    global _trace_service
    if _trace_service is None:
        _trace_service = TraceService()
    return _trace_service


def reset_trace_service() -> None:
    global _trace_service
    _trace_service = None
