# 교수님 AI

카카오톡 대화 기록으로 교수님 말투를 익혀서, 내가 보낼 카톡에 교수님이 어떻게 답장할지 미리 보여 주는 도구입니다.

| 모드 | 뜻 |
|---|---|
| `ff` | 기분좋음 |
| `nn` | 평범 |
| `ss` | 기분안좋음 |

## 학습과 질문은 따로

- **학습**: 카톡 `.txt` 파일을 넣을 때만 일어납니다. 정리된 대화가 `data/students/<학생 이름>/`에 저장됩니다.
- **질문**: `ff` / `nn` / `ss`로 시작하는 메시지는 Claude에게 보내 답장만 받고, 파일이나 기록 어디에도 저장하지 않습니다.

## 준비

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
```

API 키는 https://console.anthropic.com 에서 만들 수 있고, 저장소에 넣지 마세요.

## 사용법

대화형으로 쓰기:

```bash
python -m professor_ai
> 김태현_카톡.txt                                  # 학습
> ff 교수님 내일 친구 결혼식이 있어서 세미나 줌으로 참석해도 될까요?   # 질문 (저장 안 됨)
> /학생 김태현                                      # 학생이 여러 명일 때 질문하는 학생 고르기
> q
```

명령 한 줄로 쓰기:

```bash
python -m professor_ai learn 김태현_카톡.txt          # 파일 이름 앞부분이 학생 이름
python -m professor_ai learn 대화.txt --student 홍길동
python -m professor_ai ask ss "교수님 논문 마감을 하루 미뤄도 될까요?"
python -m professor_ai ask nn "..." --dry-run          # API 호출 없이 보낼 프롬프트만 보기
python -m professor_ai students                       # 학습된 학생 목록
```

같은 학생의 새 카톡 파일을 다시 학습시키면 이미 있는 메시지는 건너뛰고 새 메시지만 추가합니다.

## 학습할 때 자동으로 정리하는 것

- 빼는 것: 삭제된 메시지, 보이스톡 기록, 교수님 답 없이 남긴 점수 목록 메모
- 가리는 것: 전화번호 → `[전화번호]`, 점수 목록 → `[점수]`, 석차 → `[석차]`
- 직접 빼고 싶은 구간은 `data/students/<학생 이름>/exclude.txt`에 날짜(와 시간)를 적습니다.

## 설정 (환경 변수)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `PROFESSOR_AI_MODEL` | `claude-opus-5-5` | 사용할 Claude 모델 |
| `PROFESSOR_AI_EFFORT` | `medium` | `low`로 바꾸면 더 빠르고 저렴 |
| `PROFESSOR_AI_DATA` | `./data` | 학습 데이터 폴더 |

## 테스트

```bash
pip install -r requirements-dev.txt
python -m pytest
```
