from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SpanStatus = Literal["ok", "error"]
SpanType = Literal["agent", "tool", "llm", "delegation", "other"]
Framework = Literal["langchain", "crewai", "manual", "openai"]


class Span(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    agent_id: str
    agent_name: str
    run_id: str
    framework: Framework
    span_type: SpanType
    start_time: str
    end_time: str
    duration_ms: int
    status: SpanStatus
    error_message: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    input_preview: str = ""
    output_preview: str = ""
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None


class TraceDetailMeta(BaseModel):
    name: str
    version: str | None = None
    model: str | None = None
    duration_ms: int
    total_cost_usd: float | None = None
    llm_calls: int
    tool_calls: int
    errors: int
    total_tokens: int
    tags: list[str] = Field(default_factory=list)
    start_time: str


class TraceSummary(BaseModel):
    trace_id: str
    run_id: str
    agent_name: str
    name: str | None = None
    status: SpanStatus
    duration_ms: int
    span_count: int
    start_time: str
    tags: list[str] = Field(default_factory=list)
    cost_usd: float | None = None
    error_count: int | None = None


class TraceMetrics(BaseModel):
    total_cost_usd: float
    tokens_generated: int
    fail_rate: float | None
    total_events: int
    monthly_spans: int | None = None
    monthly_span_limit: int | None = None


class SpanEndStatePoint(BaseModel):
    date: str
    success: int
    indeterminate: int
    fail: int


class SpanEndStateDistribution(BaseModel):
    success: int
    indeterminate: int
    fail: int


class MetricsHistogramBucket(BaseModel):
    label: str
    value: int


class MetricsOverviewData(BaseModel):
    overview: TraceMetrics
    span_end_states: list[SpanEndStatePoint]
    span_end_states_distribution: SpanEndStateDistribution
    spans_per_trace: list[MetricsHistogramBucket]
    trace_duration_distribution: list[MetricsHistogramBucket]
    failed_spans: list[MetricsHistogramBucket] = Field(default_factory=list)
    trace_cost_distribution: list[MetricsHistogramBucket] = Field(default_factory=list)


class TraceListResponse(BaseModel):
    traces: list[TraceSummary]
    total: int
    metrics: TraceMetrics | None = None


class TraceAgentDetail(BaseModel):
    name: str
    handoffs: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class TraceDetail(BaseModel):
    trace_id: str
    run_id: str
    spans: list[Span]
    meta: TraceDetailMeta | None = None
    agents: list[TraceAgentDetail] | None = None


class GraphNodeData(BaseModel):
    label: str
    status: SpanStatus
    spanId: str
    durationMs: int
    spanType: SpanType


class GraphNode(BaseModel):
    id: str
    type: Literal["agentNode", "toolNode", "llmNode"]
    data: GraphNodeData
    position: dict[str, float]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    data: dict[str, SpanStatus] | None = None


class TraceGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AgentSummary(BaseModel):
    agent_id: str
    agent_name: str
    framework: Framework
    total_runs: int
    error_rate: float
    avg_duration_ms: int
    last_seen: str


class AgentListResponse(BaseModel):
    agents: list[AgentSummary]


class ErrorResponse(BaseModel):
    error: str


class ProjectSummary(BaseModel):
    id: str
    name: str


class UpdateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class DeleteProjectRequest(BaseModel):
    confirm_name: str = Field(min_length=1, max_length=200)


class ApiKeySummary(BaseModel):
    id: str
    key_value: str
    name: str
    project_name: str


class MeResponse(BaseModel):
    clerk_user_id: str
    email: str
    org_id: str | None = None
    clerk_org_id: str | None = None
    org_name: str | None = None
    projects: list[ProjectSummary] = Field(default_factory=list)
    api_keys: list[ApiKeySummary] = Field(default_factory=list)
    provisioned: bool


class OnboardingRequest(BaseModel):
    org_name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    clerk_org_id: str | None = Field(default=None, pattern=r"^org_", max_length=100)
    usage: Literal["hobby", "work", "help"]
    company_size: str = Field(min_length=1, max_length=50)
    building_description: str = Field(min_length=1, max_length=2000)
    stage: str = Field(min_length=1, max_length=100)
    heard_from: str = Field(min_length=1, max_length=100)
    frameworks: list[str] = Field(min_length=1, max_length=30)
    providers: list[str] = Field(default_factory=list, max_length=30)
    help_goals: list[str] = Field(min_length=1, max_length=10)


OrgRole = Literal["owner", "admin", "member", "viewer"]
InviteRole = Literal["admin", "member", "viewer"]
InviteStatus = Literal["pending", "accepted", "revoked", "expired"]


class OrganizationDetail(BaseModel):
    id: str
    name: str
    created_at: str
    member_count: int
    pending_invite_count: int


class UpdateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class LinkClerkOrganizationRequest(BaseModel):
    clerk_org_id: str = Field(pattern=r"^org_", max_length=100)


class OrgMember(BaseModel):
    id: str
    email: str
    role: OrgRole
    clerk_user_id: str | None = None
    joined_at: str


class OrgInvite(BaseModel):
    id: str
    email: str
    role: InviteRole
    status: InviteStatus
    invited_by: str | None = None
    created_at: str
    expires_at: str


class OrgMembersResponse(BaseModel):
    members: list[OrgMember]
    invites: list[OrgInvite]


class CreateInviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: InviteRole = "member"


class UpdateMemberRoleRequest(BaseModel):
    role: InviteRole
