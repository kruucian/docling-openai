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

### 2 `openai_ocr.py` Module
- [ ] 2.1 Place module in `src/docling-serve/docling_serve/` (or `utils/`).
- [ ] 2.2 Public API: `perform_ocr(image_path: Path, api_key: str, model: str | None = None) -> str`.
- [ ] 2.3 Define `class OpenAIOCRError(Exception)` for unified error handling.

### 3 API Schema Changes
- [ ] 3.1 Update Pydantic request model (likely `ConvertRequest`) to add optional `openai_api_key: str | None = None`.
- [ ] 3.2 Provide updated schema example so Swagger/Redoc shows the new field.

### 4 Endpoint Logic (`/v1alpha/convert/source`)
- [ ] 4.1 Branch logic: if `openai_api_key` is present, go the OpenAI OCR path, else follow existing flow.
- [ ] 4.2 Use `DocumentConverter(...).render_images(tmpdir)` to obtain image paths.
- [ ] 4.3 Iterate images → call `perform_ocr` → collect list `ocr_text`.
- [ ] 4.4 Merge `{ "openai_ocr": ocr_text }` into the existing JSON response.

### 5 Error Handling & Logging
- [ ] 5.1 Catch `OpenAIOCRError` and raise `HTTPException(status_code=502, detail=str(e))`.
- [ ] 5.2 Log full traceback with `logger.exception`, include request UUID for traceability.

### 6 Testing
- [ ] 6.1 Unit test `openai_ocr.perform_ocr` with `vcrpy` (record once, replay later).
- [ ] 6.2 Endpoint test: FastAPI `TestClient`, provide fake key (mock OpenAI) to ensure branch works.
- [ ] 6.3 Regression tests for existing behaviour when key is absent.

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

## Acceptance Criteria
- When no `openai_api_key` is provided, behaviour matches current production behaviour (no regressions).
- When a valid key is provided, response JSON includes an `openai_ocr` field containing a list of texts (one entry per image).
- All new code paths are covered by tests (>90 % coverage for the module).
- CI pipeline and Docker build are green.


