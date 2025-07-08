# OpenAI Vision OCR Integration Plan for docling-serve

> NOTE: Keep this file up-to-date while working. **All implementation code and inline comments must stay in English, but this document itself is free-form.**

## Goal
Extend `docling-serve` so that, when a user supplies a valid OpenAI API key, the server performs OCR on images using an OpenAI Vision model (e.g. `gpt-4o`). The feature must work in a CPU-only environment.

---

## Task List

### 1 Dependencies & Environment
- [v] 1.1 Add `requests>=2.25.0` to `src/docling-serve/pyproject.toml` → `[project.dependencies]` (HTTP client for proxy communication). *Implemented in `pyproject.toml`*
- [v] 1.1.1 (Optional) Add `pillow>=8.0.0` when image pre-processing (resize / sharpen) is required. *Added in `pyproject.toml`*
- [ ] 1.2 Run `uv pip install -e src/docling-serve` (or equivalent) and verify installation succeeds on CPU-only machines.

### ⚠️ 0.0 Test Harness Bootstrap BREAKAGE (NEW)

The lightweight `pytest_asyncio` stub and plugin-registration logic is **still
incomplete** which makes all async-fixture based tests fail.  Fixing this is
now the top priority before resuming the OpenAI OCR feature work.

Pending subtasks:

1.  Ensure the stub is *always* registered as a **pytest plugin** – regardless
    of which directory becomes the `rootdir` (project-level vs.
    `src/docling-serve`).
2.  Confirm that `@pytest_asyncio.fixture` correctly converts
    **async-generator** fixtures into *synchronous* generator wrappers so that
    the returned value (e.g., an `httpx.AsyncClient`) is injected into the
    test instead of the raw async generator.
3.  Export a benign `pytest.mark.asyncio` marker when the real plugin is
    absent to silence *UnknownMark* warnings.
4.  Add minimal test inside `tests/test_bootstrap.py` that asserts:
    ```python
    import pytest, pytest_asyncio, inspect

    @pytest_asyncio.fixture
    async def dummy():
        yield "ok"

    def test_dummy_fixture(dummy):
        assert dummy == "ok"
    ```
    This protects against future regressions in the bootstrap layer.

Resolution of this section is a **blocker** for all remaining todo items –
the primary FastAPI tests cannot execute until fixed.
- [v] 1.3 Support env vars `OPENAI_API_TIMEOUT`, `OPENAI_MODEL` (default `gpt-4o-mini`). *Implemented in `openai_ocr.py`*
- [v] 1.4 Support env var `OPENAI_MAX_IMAGES_PER_REQUEST` (default `10`) to limit batch size. *Implemented in `openai_ocr.py`*

### 1.1 Proxy-Specific Configuration
- [v] 1.5 Env var `OPENAI_PROXY_URL` (e.g. `https://your-proxy-domain`) must be respected.  Fallback to direct OpenAI endpoint when unset. *Implemented*
- [v] 1.6 Env var `OPENAI_PROVIDER_NAME` default `openai`; allowed: `openai`, `openai-us`, `openai-eu`. *Implemented*
- [v] 1.7 Allow optional `X-REQUEST-TIMEOUT`, `X-CUSTOM-EVENT-ID`, `X-METADATA` headers to be passed through from user request to the proxy. *Supported via `extra_headers` param*
- [v] 1.8 The fully qualified proxy endpoint is `${OPENAI_PROXY_URL}/api/providers/${OPENAI_PROVIDER_NAME}/v1/chat/completions`. *Implemented*

### 2 `openai_ocr.py` Module
- [v] 2.1 Place module in `src/docling-serve/docling_serve/` (or `utils/`).
- [v] 2.1.1 If using proxy, endpoint should be constructed as `${OPENAI_PROXY_URL}/api/providers/${OPENAI_PROVIDER_NAME}/v1/chat/completions`.
- [v] 2.2 Public API: `perform_ocr(image_path: Path, api_key: str, model: str | None = None, output_format: Literal["text", "json"] = "text") -> str | dict`.
- [v] 2.3 **Image encoding:** Read the file in binary mode and send as **base64-encoded** string per OpenAI Vision requirements.
- [v] 2.4 **Image pre-processing:**
  - Check resolution; upscale/downscale to OpenAI’s recommendations (≥2000 px for high-quality scans, ≥3500 px for lower quality).
  - Provide optional sharpening / contrast enhancement hooks.
- [v] 2.4 **Image pre-processing:**
  - Implemented optional pre-processing in `openai_ocr.py` controlled via env vars:
    - `OPENAI_OCR_PREPROCESS` (default "1") enables resize to [2000, 3500] px longest side.
    - `OPENAI_OCR_SHARPEN` / `OPENAI_OCR_CONTRAST` toggle optional enhancements.
  - Uses Pillow; emits clear error if Pillow missing and pre-processing enabled.
- [v] 2.5 **Prompt optimisation:** Include helper that prefixes the prompt with
  `"Extract all text exactly as shown, paying special attention to proper names and identifiers."`
- [v] 2.6 Define `class OpenAIOCRError(Exception)` for unified error handling and extend with subclasses:
  - `OpenAIRateLimitError`
  - `OpenAIAuthenticationError`
  - `OpenAIImageProcessingError`

- [v] 2.7 Accept optional dict `extra_headers: dict[str, str] | None` parameter; merge/override default headers when calling proxy.
- [v] 2.8 Ensure headers `X-REQUEST-TIMEOUT`, `X-CUSTOM-EVENT-ID`, `X-METADATA` can be supplied via `extra_headers` and forwarded untouched.
- [v] 2.9 Build prompt and messages array exactly per proxy requirements (text + image_url as base64 `data:` URI).

### 3 API Schema Changes
- [v] 3.1 Update Pydantic request model (likely `ConvertRequest`) to add optional `openai_api_key: str | None = None`.
- [v] 3.2 Provide updated schema example so Swagger/Redoc shows the new field.
- [v] 3.3 Ensure incoming `openai_api_key` is validated for basic format before use and **never** returned in any response.
- [v] 3.4 Validate uploaded image MIME types & max size before any processing (Security).
- [v] 3.5 Implement basic request rate-limiting per client API key/IP (configurable).
- [v] 3.6 Add simple API key format validation helper (length, allowed charset).

### 4 Endpoint Logic (`/v1alpha/convert/source`)
- [v] 4.1 Branch logic: if `openai_api_key` is present, go the OpenAI OCR path, else follow existing flow.
- [v] 4.1.1 If `openai_proxy_url` header is supplied by client, override env `OPENAI_PROXY_URL` just for that request.
- [v] 4.2 Use `DocumentConverter(...).convert(source)` to get a `Document` object and then extract or generate page images. *`render_images` does **not** exist*.
- [v] 4.3 **Sequential image processing:** iterate images one-by-one (no multi-image requests) → call `perform_ocr` → collect list `ocr_text`.
- [v] 4.4 **Progress tracking:** stream or log per-page progress; allow graceful interruption & resume.
- [v] 4.5 **Partial failure handling:** continue processing remaining images even if one fails; surface failed indices in response.
- [v] 4.6 Merge `{ "openai_ocr": ocr_text }` into the existing JSON response.

#### 4.1.5 Image Extraction Strategy
- [ ] 4.1.5 Option A: use `PdfPipelineOptions(generate_page_images=True)` to generate images during conversion.
- [ ] 4.1.6 Option B: extract embedded images from the returned `Document` structure.
- [ ] 4.1.7 Option C: post-process PDF pages with an external tool if neither of the above applies.
- [ ] 4.1.8 Handle PNG / JPEG / TIFF consistently and ensure base64 compatibility.

### 5 Error Handling & Logging

#### 5.6 Sensitive Data Handling

- All incoming OpenAI API keys are validated for length and allowed characters.
- Keys are **never** persisted to disk, database, or logs; only a masked form (`sk-****abcd`) is used in log messages.
- Network traffic to OpenAI/Proxy endpoints is sent exclusively over HTTPS (TLS 1.2+).
- Usage logs stored under `OPENAI_USAGE_LOG` contain only masked keys and aggregate cost/usage metrics.
- Temporary variables holding raw keys are cleared immediately after use; no long-lived references.
- Environment variables containing secrets are read once and not re-exported.
- Error responses never include user-provided keys or raw image bytes.

- [v] 5.1 Catch `OpenAIOCRError` and raise `HTTPException(status_code=502, detail=str(e))`.
- [v] 5.2 Log full traceback with `logger.exception`, include request UUID for traceability.
- [v] 5.3 Estimate cost before execution and warn user if estimated cost exceeds a configurable threshold.
- [v] 5.4 Honour `OPENAI_API_TIMEOUT`; cancel request if exceeded and surface meaningful error.
- [v] 5.5 Mask API key in all log statements (e.g., show only first/last 4 chars).
- [v] 5.6 Add docs block listing sensitive data handling practices.
- [v] 5.7 Implement cost estimation based on image count & size; warn when above threshold.
- [v] 5.8 Enforce configurable daily/monthly usage limits via env vars (`OPENAI_DAILY_LIMIT`, `OPENAI_MONTHLY_LIMIT`).
- [v] 5.9 Persist and log actual API usage & estimated costs for monitoring/analytics.

### 6 Testing
- [ ] 6.1 Unit test `openai_ocr.perform_ocr` mocking HTTP calls with `pytest-httpx` or `responses` (do not require real API access).
- [ ] 6.2 Endpoint test: FastAPI `TestClient`, provide fake key (mock OpenAI) to ensure branch works.
- [ ] 6.3 Regression tests for existing behaviour when key is absent.
  # Cache tests will be added in Phase 2 once the caching layer exists.
- [ ] 6.5 Concurrency test: process >`OPENAI_MAX_IMAGES_PER_REQUEST` images to ensure sequential logic & batching obey limits.

### 7 Documentation
- [ ] 7.1 Update `README.md` (or docs) explaining the new feature, env vars, cost notes, rate-limit caveats.
- [ ] 7.2 Add example `curl` snippet:
  ```bash
  curl -X POST http://localhost:8000/v1alpha/convert/source \
       -F "file=@sample.png" \
       -F "openai_api_key=$OPENAI_API_KEY"
  ```

### 8 Validation
- [ ] 8.1 Build Docker image, run locally, ensure OCR results are returned and CPU usage is reasonable.
- [ ] 8.2 Manual test with a PDF & standalone PNG to visually verify accuracy.
- [ ] 8.3 Simulate OpenAI errors (401, 404, 429) to confirm proper HTTP responses.

### 9 Clean-up
- [ ] 9.1 Remove dead code & temporary prints.
- [ ] 9.2 Run `pre-commit run --all-files`; fix only new issues.
- [ ] 9.3 Commit and push.

---

### 10 Performance & Cost Optimization
- [ ] 10.1 Enforce image dimension limit & JPEG compression to reduce payload size.  
  - `OPENAI_OCR_MAX_DIM` env (default **3500**) – resize longest side down via Pillow `thumbnail`.  
  - Convert to JPEG with `quality=85` when source >1 MB; preserve PNG when transparency detected.  
  - Add fast unit test for a 5000 px dummy image verifying output ≤ max_dim and <1 MB.
- [ ] 10.2 Implement file-based or Redis-based caching for OCR results.  
  - Default: `OPENAI_OCR_CACHE_DIR` under `$XDG_CACHE_HOME` using `diskcache`.  
  - Optional Redis via `OPENAI_OCR_REDIS_URL`; fallback gracefully if server unreachable.  
  - Cache decorator wraps `perform_ocr`; returns early on hit.
- [ ] 10.3 Cache key = SHA-256(image bytes) + model + prompt (avoid false hits).  
  - Use `hashlib.sha256` on raw bytes; append model & prompt hashed.  
  - Store alongside `expires_at` timestamp for TTL enforcement.
- [ ] 10.4 Add TTL and cleanup logic for cache entries.  
  - `OPENAI_OCR_CACHE_TTL_HOURS` (default **720**).  
  - Nightly async task purges expired keys; exposed via `@app.on_event("startup")`.
- [ ] 10.5 Compute approximate token cost per page and display summary post-processing.  
  - Estimate tokens = `len(text)/4`; price from `OPENAI_OCR_COST_PER_1K_TOKENS`.  
  - Accumulate per-request total and include `estimated_cost_usd` in response.

### 11 Advanced Features
- [ ] 11.1 Explicit multi-language OCR support.  
  - Extend request schema with optional `language: str`.  
  - Inject `language` into system prompt: `"Language hint: {language}"`.  
  - Validate ISO-639-1 codes.
- [ ] 11.2 Table/Form structure extraction when `output_format="json"`.  
  - Post-process Vision JSON to normalise tables into rows/cols.  
  - Return under `openai_ocr_structured`.
- [ ] 11.3 Handwriting recognition toggle.  
  - `OPENAI_OCR_HANDWRITING=1` chooses dedicated handwriting model.  
  - Adjust prompt to `"The image contains cursive handwriting…"`.

### 12 Monitoring & Analytics
- [ ] 12.1 Collect OCR accuracy metrics.  
  - When `ground_truth` provided in test harness, compute Levenshtein distance with `python-Levenshtein`.  
  - Emit metric `ocr_accuracy` to Prometheus.
- [ ] 12.2 Track per-request latency & total OpenAI cost; export Prometheus metrics.  
  - Use `prometheus_client` `Histogram` for latency, `Counter` for cost USD. 
- [ ] 12.3 Monitor failure rates and surface alerts.  
  - Increment `ocr_failures_total` counter on exceptions.  
  - Configure Alertmanager rule when >5% failures in 5 min.

## Acceptance Criteria
- When no `openai_api_key` is provided, behaviour matches current production behaviour (no regressions).
- When a valid key is provided, response JSON includes an `openai_ocr` field containing a list of texts (one entry per image).
- All new code paths are covered by tests (>90 % coverage for the module).
- CI pipeline and Docker build are green.

