# LLM API 가격 자동 업데이트 시스템 설계

## 개요

4개 프로바이더(OpenAI, Anthropic, Google Gemini, xAI/Grok)의 LLM API 가격을
매일 자동으로 스크래핑하여 `pricing.toml`을 갱신하고, 변경사항을 Telegram으로 알리는 시스템.

## 요구사항

- **데이터**: `pricing.toml` — 프로바이더별 모델 가격 (input/output per 1M tokens)
- **표시**: `README.md` — TOML 기반 마크다운 테이블 자동 생성
- **알림**: Telegram — 가격 변경/신규 모델/에러 알림
- **실행**: macOS launchd / Ubuntu systemd로 매일 스케줄 실행
- **실패 처리**: 재시도 후 계속 실패하면 Telegram 에러 알림
- **언어**: Python (.venv 기반)

## 아키텍처

```
[launchd/systemd] ─매일─▶ [main.py]
                             │
                       ┌─────┼─────────────┐
                       ▼     ▼             ▼
                 [scraper]  [parser]  [notifier]
                       │     │             │
              Playwright  LLM API    Telegram Bot
              (4개 URL)  (텍스트→JSON)  (변경 알림)
                       │     │
                       ▼     ▼
                 [pricing.toml]  ──▶  [README.md 테이블 생성]
                                           │
                                      git commit + push
```

## 핵심 모듈

### 1. scraper.py — 웹 스크래핑

Playwright headless 브라우저로 각 프로바이더 가격 페이지의 텍스트를 추출한다.

프로바이더별 URL:
| 프로바이더 | URL |
|-----------|-----|
| OpenAI | `https://developers.openai.com/api/docs/pricing` |
| Anthropic | `https://platform.claude.com/docs/en/about-claude/pricing` |
| Google | `https://ai.google.dev/gemini-api/docs/pricing` |
| xAI | `https://docs.x.ai/docs/models` |

- 타임아웃: 30초
- 실패 시 최대 3회 재시도 (지수 백오프)

### 2. parser.py — LLM 파싱

스크래핑한 텍스트를 LLM에게 넘겨 구조화된 JSON으로 변환한다.

- 기본 모델: `claude-haiku-4-5` (config에서 변경 가능)
- 프롬프트: 텍스트에서 텍스트/채팅 LLM 모델의 이름, input/output 가격 추출
- 응답 형식: `{"models": [{"name": "...", "input": 1.25, "output": 10.00}, ...]}`
- 실패 시 최대 2회 재시도

### 3. updater.py — TOML 갱신 + README 생성

기존 pricing.toml과 새 데이터를 비교하여 변경사항을 감지하고 갱신한다.

변경 유형:
- 가격 변동 (input 또는 output 변경)
- 신규 모델 추가
- 모델 제거

README.md는 마커(`<!-- PRICING_TABLE_START/END -->`) 기반으로 테이블 영역만 교체한다.

### 4. notifier.py — Telegram 알림

Telegram Bot API로 변경사항 알림을 발송한다.

알림 조건:
- 가격 변동 시 → 변경 내역
- 신규 모델 추가 시 → 신규 모델 정보
- 스크래핑/파싱 실패 시 → 에러 정보

### 5. config.py — 설정

프로바이더 URL, LLM 모델, Telegram 설정 등을 관리한다.
환경변수(.env)에서 시크릿(API 키, Bot 토큰) 로드.

## 파일 구조

```
llm-api-card-price/
├── pricing.toml
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   └── llm_pricing/
│       ├── __init__.py
│       ├── main.py
│       ├── scraper.py
│       ├── parser.py
│       ├── updater.py
│       ├── notifier.py
│       └── config.py
├── scripts/
│   ├── install-launchd.sh
│   ├── install-systemd.sh
│   ├── uninstall-launchd.sh
│   ├── uninstall-systemd.sh
│   └── com.llm-pricing.updater.plist
├── tests/
└── docs/
    └── plans/
```

## 실행 환경

- Python 3.12+ with `.venv`
- macOS: launchd plist로 매일 새벽 4시 실행 (수면 중 놓쳤으면 부팅 시 실행)
- Ubuntu: systemd timer로 매일 새벽 4시 실행

## 의존성

- `playwright` — 브라우저 스크래핑
- `anthropic` — LLM 파싱 (기본 모델)
- `tomli` / `tomli-w` — TOML 읽기/쓰기
- `httpx` — Telegram API 호출
- `python-dotenv` — 환경변수 로드

## 비용 추정

- LLM 파싱: 4개 페이지 × ~2K 토큰 × Haiku 가격 ≈ 하루 $0.001 미만
- 월간: ~$0.03
