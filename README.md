# Docling OpenAI OCR Integration

## Environment variables
| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | – | Secret key used for Vision Chat Completions. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name passed to the OpenAI API. |
| `OPENAI_API_TIMEOUT` | `30` | Request timeout in seconds. |
| `OPENAI_MAX_IMAGES_PER_REQUEST` | `10` | Maximum images batched in a single OCR call. |
| `OPENAI_OCR_MAX_FILE_SIZE` | `10485760` | Max raw image size (bytes). |
| `OPENAI_OCR_MAX_DIM` | `3500` | Maximum width/height decoded for pre-processing. |
| `OPENAI_COST_WARN_USD` | `1.0` | Soft warning threshold per request. |
| `OPENAI_DAILY_LIMIT` | `20.0` | Hard daily cost limit (USD). |
| `OPENAI_MONTHLY_LIMIT` | `200.0` | Hard monthly cost limit (USD). |
| `OPENAI_OCR_CACHE_DIR` | – | Path for persistent diskcache (optional). |
| `OPENAI_OCR_REDIS_URL` | – | Redis URL for shared cache (optional). |

### Per-request header override
`OPENAI_PROXY_URL` can be supplied as an HTTP header to route traffic through a custom proxy.

## Rate limits & concurrency
The server rejects payloads with more than `OPENAI_MAX_IMAGES_PER_REQUEST` page images and uses an internal lock to serialise costly OCR calls. Concurrent requests above this limit are queued until capacity is available.

## Cost control
All Vision calls are metered. When the **daily** or **monthly** budget is exceeded the service returns HTTP 429 with a descriptive message. A JSON-lines usage log is written to `${OPENAI_USAGE_LOG:-~/.cache/docling/openai_usage.jsonl}`.

## Quick start (curl)
```bash
export OPENAI_API_KEY=sk-...

curl -X POST http://localhost:8000/v1alpha/convert/source \
  -H "Content-Type: application/json" \
  -d '{
    "http_sources": [{"url": "https://arxiv.org/pdf/2408.09869v5.pdf"}],
    "openai_api_key": "'$OPENAI_API_KEY'",
    "options": {
      "to_formats": ["markdown"],
      "image_export_mode": "embedded"
    }
  }' -o result.json
```
The response contains `document.openai_ocr` – a list of recognised texts per page.
