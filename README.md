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
## LLM API Pricing (USD per 1M tokens)
> Last updated: 2026-03-01

### Anthropic
| Model | Input | Output |
|-------|------:|-------:|
| claude-opus-4 | $15.00 | $75.00 |
| claude-opus-4-1 | $15.00 | $75.00 |
| claude-opus-4-5 | $5.00 | $25.00 |
| claude-opus-4-6 | $5.00 | $25.00 |
| claude-sonnet-4 | $3.00 | $15.00 |
| claude-sonnet-4-5 | $3.00 | $15.00 |
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-haiku-4-5 | $1.00 | $5.00 |
| claude-haiku-3-5 | $0.80 | $4.00 |

### Google Gemini
| Model | Input | Output |
|-------|------:|-------:|
| gemini-3.1-pro-preview | $2.00 | $12.00 |
| gemini-2.5-pro | $1.25 | $10.00 |
| gemini-2.5-flash-native-audio-preview-12-2025 | $0.50 | $2.00 |
| gemini-3-flash-preview | $0.50 | $3.00 |
| gemini-2.5-flash | $0.30 | $2.50 |
| gemini-3.1-flash-image-preview | $0.25 | $1.50 |
| gemini-2.0-flash | $0.10 | $0.40 |
| gemini-2.5-flash-lite | $0.10 | $0.40 |
| gemini-2.5-flash-lite-preview-09-2025 | $0.10 | $0.40 |

### OpenAI
| Model | Input | Output |
|-------|------:|-------:|
| o1-pro | $150.00 | $600.00 |
| gpt-5.2-pro | $21.00 | $168.00 |
| o3-pro | $20.00 | $80.00 |
| gpt-5-pro | $15.00 | $120.00 |
| o1 | $15.00 | $60.00 |
| o3-deep-research | $10.00 | $40.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4.1 | $2.00 | $8.00 |
| o3 | $2.00 | $8.00 |
| o4-mini-deep-research | $2.00 | $8.00 |
| gpt-5.2 | $1.75 | $14.00 |
| gpt-5 | $1.25 | $10.00 |
| gpt-5.1 | $1.25 | $10.00 |
| o1-mini | $1.10 | $4.40 |
| o3-mini | $1.10 | $4.40 |
| o4-mini | $1.10 | $4.40 |
| gpt-4.1-mini | $0.40 | $1.60 |
| gpt-5-mini | $0.25 | $2.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4.1-nano | $0.10 | $0.40 |
| gpt-5-nano | $0.05 | $0.40 |

### xAI (Grok)
| Model | Input | Output |
|-------|------:|-------:|
| grok-3 | $3.00 | $15.00 |
| grok-4-0709 | $3.00 | $15.00 |
| grok-2-vision-1212 | $2.00 | $10.00 |
| grok-3-mini | $0.30 | $0.50 |
| grok-4-1-fast-non-reasoning | $0.20 | $0.50 |
| grok-4-1-fast-reasoning | $0.20 | $0.50 |
| grok-4-fast-non-reasoning | $0.20 | $0.50 |
| grok-4-fast-reasoning | $0.20 | $0.50 |

<!-- PRICING_TABLE_END -->
