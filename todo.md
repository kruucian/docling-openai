# OpenAI Vision OCR Integration Plan for docling-serve

> NOTE: Keep this file up-to-date while working. **All implementation code and inline comments must stay in English, but this document itself is free-form.**

## Goal
Extend `docling-serve` so that, when a user supplies a valid OpenAI API key, the server performs OCR on images using an OpenAI Vision model (e.g. `gpt-4o`). The feature must work in a CPU-only environment.

---

## Task List

### 1 Dependencies & Environment
- [ ] 1.1 Add `openai>=1.0.0` to `src/docling-serve/pyproject.toml` → `[project.dependencies]`.
- [ ] 1.2 Run `uv pip install -e src/docling-serve` (or equivalent) and verify installation succeeds on CPU-only machines.
- [ ] 1.3 Support env vars `OPENAI_API_TIMEOUT`, `OPENAI_MODEL` (default `gpt-4o-mini`).
- [ ] 1.4 Support env var `OPENAI_MAX_IMAGES_PER_REQUEST` (default `10`) to limit batch size.

### 2 `openai_ocr.py` Module
- [ ] 2.1 Place module in `src/docling-serve/docling_serve/` (or `utils/`).
- [ ] 2.2 Public API: `perform_ocr(image_path: Path, api_key: str, model: str | None = None, output_format: Literal["text", "json"] = "text") -> str | dict`.
- [ ] 2.3 **Image encoding:** Read the file in binary mode and send as **base64-encoded** string per OpenAI Vision requirements.
- [ ] 2.4 **Image pre-processing:**
  - Check resolution; upscale/downscale to OpenAI’s recommendations (≥2000 px for high-quality scans, ≥3500 px for lower quality).
  - Provide optional sharpening / contrast enhancement hooks.
- [ ] 2.5 **Prompt optimisation:** Include helper that prefixes the prompt with
  `"Extract all text exactly as shown, paying special attention to proper names and identifiers."`
- [ ] 2.6 Define `class OpenAIOCRError(Exception)` for unified error handling and extend with subclasses:
  - `OpenAIRateLimitError`
  - `OpenAIAuthenticationError`
  - `OpenAIImageProcessingError`

### 3 API Schema Changes
- [ ] 3.1 Update Pydantic request model (likely `ConvertRequest`) to add optional `openai_api_key: str | None = None`.
- [ ] 3.2 Provide updated schema example so Swagger/Redoc shows the new field.
- [ ] 3.3 Ensure incoming `openai_api_key` is validated for basic format before use and **never** returned in any response.

### 4 Endpoint Logic (`/v1alpha/convert/source`)
- [ ] 4.1 Branch logic: if `openai_api_key` is present, go the OpenAI OCR path, else follow existing flow.
- [ ] 4.2 Use `DocumentConverter(...).render_images(tmpdir)` to obtain image paths.
- [ ] 4.3 **Sequential image processing:** iterate images one-by-one (no multi-image requests) → call `perform_ocr` → collect list `ocr_text`.
- [ ] 4.4 **Progress tracking:** stream or log per-page progress; allow graceful interruption & resume.
- [ ] 4.5 **Partial failure handling:** continue processing remaining images even if one fails; surface failed indices in response.
- [ ] 4.6 Merge `{ "openai_ocr": ocr_text }` into the existing JSON response.

### 5 Error Handling & Logging
- [ ] 5.1 Catch `OpenAIOCRError` and raise `HTTPException(status_code=502, detail=str(e))`.
- [ ] 5.2 Log full traceback with `logger.exception`, include request UUID for traceability.
- [ ] 5.3 Estimate cost before execution and warn user if estimated cost exceeds a configurable threshold.
- [ ] 5.4 Honour `OPENAI_API_TIMEOUT`; cancel request if exceeded and surface meaningful error.
- [ ] 5.5 Mask API key in all log statements (e.g., show only first/last 4 chars).
- [ ] 5.6 Add docs block listing sensitive data handling practices.

### 6 Testing
- [ ] 6.1 Unit test `openai_ocr.perform_ocr` with `vcrpy` (record once, replay later).
- [ ] 6.2 Endpoint test: FastAPI `TestClient`, provide fake key (mock OpenAI) to ensure branch works.
- [ ] 6.3 Regression tests for existing behaviour when key is absent.
- [ ] 6.4 Cache tests: same image processed twice should hit cache and skip API call.
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
- [ ] 10.2 Implement SHA-256 based cache to skip reprocessing identical images.
- [ ] 10.3 Compute approximate token cost per page and display summary post-processing.

### 11 Advanced Features
- [ ] 11.1 Explicit multi-language OCR support (add `language` parameter, pass in prompt when needed).
- [ ] 11.2 Table/Form structure extraction with JSON output when `output_format="json"`.
- [ ] 11.3 Optional handwriting recognition toggle that switches model or prompt accordingly.

### 12 Monitoring & Analytics
- [ ] 12.1 Collect OCR accuracy metrics (e.g., Levenshtein distance vs. ground truth when available).
- [ ] 12.2 Track per-request latency & total OpenAI cost; export Prometheus metrics.
- [ ] 12.3 Monitor failure rates and surface alerts via logs/dashboards.

## Acceptance Criteria
- When no `openai_api_key` is provided, behaviour matches current production behaviour (no regressions).
- When a valid key is provided, response JSON includes an `openai_ocr` field containing a list of texts (one entry per image).
- All new code paths are covered by tests (>90 % coverage for the module).
- CI pipeline and Docker build are green.


