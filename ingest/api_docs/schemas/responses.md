# Response schemas

---

## AcceptedResponse

Returned by `POST /v1/spans` on success.

```json
{
  "accepted": 1
}
```

| Field | Type | Description |
|---|---|---|
| `accepted` | `integer` | Number of spans accepted in the batch |

---

## ErrorResponse

Returned for `401`, `429`, and other handled errors.

```json
{
  "error": "invalid api key"
}
```

| Field | Type | Description |
|---|---|---|
| `error` | `string` | Human-readable error message |

### Known error messages

| Message | Status |
|---|---|
| `"invalid api key"` | 401 |
| `"rate limited"` | 429 |

See [Errors](../errors.md) for the full list.
