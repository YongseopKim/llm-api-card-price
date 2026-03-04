# LLM API Card Price

LLM 프로바이더별 API 가격을 자동 수집/갱신하는 시스템.

## 개발 환경

- Python 3.12+
- **반드시 `.venv/` 기반으로 작업할 것** — `source .venv/bin/activate` 후 작업
- 패키지 관리: `pyproject.toml` + `uv` 또는 `pip`
- Playwright 브라우저: `playwright install chromium`

## 프로젝트 구조

- `pricing.toml` — 가격 데이터 (source of truth)
- `README.md` — 마크다운 테이블 (자동 생성)
- `src/llm_pricing/` — 메인 소스코드
- `scripts/` — launchd/systemd 서비스 등록 스크립트
- `tests/` — 테스트

## LLM Proxy 사용

LLM API 호출은 프록시를 경유한다 (API key는 프록시가 관리).

- Proxy base URL: `http://192.168.0.2:8081`
- 엔드포인트: `POST /anthropic/v1/messages` (provider-compatible)
- 요청/응답 포맷: Anthropic Messages API 네이티브
- 모델명: `anthropic.` 접두사 없이 그대로 사용 (예: `claude-haiku-4-5`)

## 환경변수

`.env` 파일에서 관리:
- `LLM_PROXY_URL` — LLM Proxy Server URL (기본값: `http://192.168.0.2:8081`)
- `TELEGRAM_BOT_TOKEN` — 알림 봇 토큰
- `TELEGRAM_CHAT_ID` — 알림 대상 채팅 ID
