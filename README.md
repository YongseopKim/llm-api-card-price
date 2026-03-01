# LLM API Card Price

LLM 프로바이더별 API 가격을 자동으로 추적하고 업데이트합니다.

## Setup

1. `.venv` 생성 및 의존성 설치:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   playwright install chromium
   ```

2. `.env` 파일 설정:
   ```bash
   cp .env.example .env
   # Edit with your API keys
   ```

3. 서비스 등록 (선택):
   - macOS: `bash scripts/install-launchd.sh`
   - Ubuntu: `bash scripts/install-systemd.sh`

## Manual Run

```bash
source .venv/bin/activate
PYTHONPATH=src python -m llm_pricing.main
```

<!-- PRICING_TABLE_START -->
<!-- 자동 생성됩니다 -->
<!-- PRICING_TABLE_END -->
