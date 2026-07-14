# Schemas

Data models used by the Ingest API. These are shared between the SDK, ingest service, and app API via `backend/shared/span_schema.py`.

| Schema | Direction | Used by |
|---|---|---|
| [SpanBatch](./span-batch.md) | Request body | `POST /v1/spans` |
| [Span](./span.md) | Request (nested) | `POST /v1/spans` |
| [AcceptedResponse](./responses.md#acceptedresponse) | Response | `POST /v1/spans` |
| [ErrorResponse](./responses.md#errorresponse) | Response | Error responses |
