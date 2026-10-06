# AI 버튜버 프로젝트 인수인계 문서

> 클라우드 세션(2026-10-06)에서 정리한 내용입니다. 로컬 세션은 이 문서를 먼저 읽고 이어서 진행하세요.
> 로컬 작업 폴더: `D:\Claude-vtuber` / 에셋 폴더: `D:\Claude-vtuber\asset-마젯`

## 1. 목표

자주 보는 버튜버 '마젯'을 참고해, 비슷하게 생기고 비슷하게 말하는 **개인용 AI 캐릭터**를 만든다. 완벽한 재현은 필요 없다.

```
🎤 사용자 음성 → [ASR] → [Gemini LLM: 마젯 말투] → [GPT-SoVITS: 마젯 음색] → [아바타: 립싱크 + 표정]
```

보유 에셋 (아직 내용 확인 전):
- 삼면도: 아바타 제작 참고용
- 음성 파일: TTS 학습용
- 라이브 스트리밍 녹화본: 음성 학습 데이터, 말투/성격 추출, 표정 참고용

## 2. 전제와 제약 (중요)

- **비공개 개인 용도로 한정한다.** 목소리는 실제 사람의 것이고 캐릭터 디자인은 원작자/소속사의 것이다. 학습된 체크포인트 배포, 방송 송출, "본인이 한 말"처럼 보이는 결과물 공개는 하지 않는다.
- 해당 버튜버의 **2차 창작 가이드라인**을 확인할 것. AI 음성 학습 금지 조항이 있을 수 있다.
- **Gemini 3.8 Flash TTS 음성 복제는 쓰지 않는다.** 2026-09-22에 정식 출시됐지만 목소리 주인의 **음성 동의 녹음**이 필요하다. 그래서 음색 학습은 로컬 **GPT-SoVITS**로 한다.
  - 공개 용도가 생기면 Gemini TTS의 **보이스 디자인**(프롬프트로 새 목소리 생성, 동의 불필요)으로 전환하는 것을 검토한다.
- 녹화본, 음성 데이터, 학습된 모델은 **GitHub에 올리지 않는다.** 용량 문제도 있고 권리 문제도 있다.

## 3. 사용자 PC 사양

| 항목 | 사양 |
|---|---|
| CPU | Intel i5-9400F (6코어) |
| RAM | 16GB |
| GPU | RTX 3060 Ti (VRAM 8GB) |
| OS | Windows 64bit |

- VRAM 8GB는 TTS와 ASR에 우선 배정한다. **로컬 LLM은 쓰지 않는다.**
- 결제 수단: Gemini API 약 1만 원 충전 완료. 필요하면 추가 결제 가능.

## 4. 기술 스택 결정안

| 파트 | 선택 | 비고 |
|---|---|---|
| LLM | **Gemini API (Flash 계열)** | OpenAI 호환 엔드포인트로 연결 가능 |
| ASR | SenseVoice(sherpa-onnx, CPU) 또는 faster-whisper small | 한국어 지원. VRAM을 아끼려고 CPU 우선 |
| TTS | **GPT-SoVITS v2ProPlus** 파인튜닝 | 한국어 지원(v2부터). 추론은 8GB로 충분, **학습은 8GB가 빠듯함** → 배치 크기를 줄이고, 그래도 안 되면 클라우드 GPU(RunPod 등)를 몇 시간 대여 |
| 아바타 (추천) | **VRoid Studio(무료) → VRM** | 삼면도를 참고해 제작. 입모양(아·이·우·에·오)과 감정 표정이 기본으로 들어 있음 |
| 아바타 (대안) | Live2D | 레이어로 분리된 PSD 원화와 리깅이 필요해 난이도와 비용이 높음. 가장 간단한 대안은 PNGTuber |
| 실행 프레임워크 | 3D면 **AIRI**, Live2D면 **Open-LLM-VTuber v1** | 아래 5절 참고 |

이미지 하나로 3D를 만드는 AI(Tripo, Meshy 등)는 표정 리깅이 없어서 말하는 아바타로는 부적합하다.

## 5. 조사한 오픈소스

### Open-LLM-VTuber (조사 완료)
- https://github.com/Open-LLM-VTuber/Open-LLM-VTuber , 최신 **v1.2.1**
- **v2.0은 미출시.** `v2` 브랜치는 2026-01-10에 코드를 비운 뒤 진척이 없다. v1은 버그 수정만 받는 유지보수 모드.
- 구조: Python FastAPI + WebSocket 서버(`run_server.py`, 포트 12393), 프런트엔드는 git submodule
- 설정은 `conf.yaml`. LLM, ASR, TTS, VAD, 에이전트를 팩토리 패턴으로 교체할 수 있다.
- **GPT-SoVITS TTS가 기본 내장**(`src/open_llm_vtuber/tts/gpt_sovits_tts.py`)
- **Live2D만 지원**한다. VRM은 지원하지 않는다.
- 실행: `uv sync` → `conf.yaml` 설정 → `uv run run_server.py`

### AIRI (3D 경로 1순위)
- https://github.com/moeru-ai/airi , ⭐ 약 5만, MIT, 매우 활발
- VRM과 Live2D, 실시간 음성, 웹·데스크톱(Electron) 지원
- TTS 공급자에 `openai-compatible-audio-speech`가 있다. **GPT-SoVITS는 기본 내장이 아니다.**
  → GPT-SoVITS `api_v2.py`(`/tts`)를 OpenAI 형식 `/v1/audio/speech`로 바꿔 주는 **작은 변환 서버**를 만들어야 한다.

### 2026년 6월 이후 시작된 유사 프로젝트 (첫 커밋 날짜 기준)

| 프로젝트 | 시작 | 아바타 | 메모 | 라이선스 |
|---|---|---|---|---|
| [yw0nam/YUI](https://github.com/yw0nam/YUI) | 2026-06-03 | VRM | Tauri 데스크톱 펫, OpenAI 호환 백엔드 | 비상업(PolyForm NC) |
| [yuri-os/YuriOS](https://github.com/yuri-os/YuriOS) | 2026-07-18 | VRM / Live2D | faster-whisper, kokoro, silero를 전부 CPU에서 로컬로, 말 끊기, MCP | Apache-2.0 |
| [Rivulet138/yuizaki](https://github.com/Rivulet138/yuizaki) | 2026-07-19 | Live2D / VRM | Sherpa ASR, Genie TTS(GPT-SoVITS 계열), 중국어 문서 | MIT |
| [927tanmay/react-ai-voice-avatar](https://github.com/927tanmay/react-ai-voice-avatar) | 2026-08-02 | 3D | 직접 앱에 넣는 React 컴포넌트, 베타 | MIT |

그 밖의 참고: [morettt/my-neuro](https://github.com/morettt/my-neuro), [zeikar/charivo](https://github.com/zeikar/charivo)(Live2D TS 프레임워크), [chyinan/Kokoro-Engine](https://github.com/chyinan/Kokoro-Engine)

## 6. 진행 로드맵

### 0단계: 에셋 파악 ← **로컬 세션이 가장 먼저 할 일**
- `D:\Claude-vtuber\asset-마젯`의 파일 목록, 형식, 용량을 정리한다.
- 녹화본의 **총 길이**를 확인한다.
- 음성 파일이 BGM 없는 깨끗한 음성인지 확인한다.
- 삼면도의 해상도와 구성(정면, 측면, 후면, 표정 시트 여부)을 확인한다.

### 1단계: 목소리 (최우선)
1. GPT-SoVITS를 설치한다(Windows 통합 패키지 또는 소스).
2. 녹화본에서 오디오를 추출하고 UVR5로 BGM과 효과음을 제거한다.
3. 음성을 자르고 받아쓴다(GPT-SoVITS WebUI 내장 도구 사용).
4. 수동으로 정제한다. 합방 상대 목소리, 채팅 읽기, 비명과 웃음, 잡음 구간을 제거한다.
5. 깨끗한 음성 **30분~1시간** 분량으로 SoVITS와 GPT 모델을 학습해 체크포인트를 만든다.
6. `api_v2.py`로 추론 서버를 띄우고 품질을 확인한다.

### 2단계: 성격과 말투
- 1단계에서 받아쓴 대사를 Gemini로 분석한다. 말투, 자주 쓰는 표현, 리액션, 호칭을 뽑는다.
- 그 결과로 시스템 프롬프트와 예시 대화(few-shot)를 작성한다.

### 3단계: 아바타
- VRoid Studio에서 삼면도를 참고해 제작한다(머리, 의상 텍스처 커스텀).
- VRM으로 내보내고, 블렌드셰이프(입모양, 표정)가 동작하는지 확인한다.

### 4단계: 통합
- AIRI에 Gemini(LLM), GPT-SoVITS(변환 서버 경유), VRM을 연결한다.
- ASR을 연결하고 말 끊기와 지연 시간을 튜닝한다.

## 7. 사용자에게 아직 확인할 것

- [ ] 2D와 3D 중 무엇으로 할지 (현재 추천: 3D/VRoid)
- [ ] 용도가 혼자 대화용인지, 공개나 방송까지인지 (공개라면 목소리 전략을 다시 짜야 함)
- [ ] 에셋 상세 (0단계에서 확인)

## 8. 참고 링크
- GPT-SoVITS: https://github.com/RVC-Boss/GPT-SoVITS
- VRoid Studio: https://vroid.com/en/studio
- Gemini 3.8 TTS 음성 복제 동의 요건: https://thenextweb.com/news/gemini-tts-3-8-flash-voice-design-cloning
