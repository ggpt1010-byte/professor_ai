# 교수님 AI

카카오톡 대화 기록으로 교수님 말투를 익혀서, 내가 보낼 카톡에 교수님이 어떻게 답장할지 미리 보여 주는 도구입니다.

| 모드 | 뜻 |
|---|---|
| `ff` | 기분좋음 |
| `nn` | 평범 |
| `ss` | 기분안좋음 |

## 학습과 질문은 따로

- **학습**: 카톡 `.txt` 파일을 넣을 때만 일어납니다. 정리된 대화가 `data/chats/<대화방 이름>/`에 저장됩니다. 1:1 대화방은 학생 이름(예: `김태현`), 단체방은 파일 이름(예: `AISL_전체톡방`)을 씁니다.
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
python -m professor_ai learn 김태현_카톡.txt          # 1:1 대화방 '김태현'
python -m professor_ai learn AISL_전체톡방_카톡.txt    # 단체방은 자동으로 알아봄
python -m professor_ai learn 대화.txt --chat 홍길동
python -m professor_ai ask ss "교수님 논문 마감을 하루 미뤄도 될까요?"
python -m professor_ai ask nn "..." --dry-run          # API 호출 없이 보낼 프롬프트만 보기
python -m professor_ai chats                          # 학습된 대화방 목록
python -m professor_ai ask nn "..." --student 홍길동   # 질문하는 학생 이름 지정
```

같은 대화방의 새 카톡 파일을 다시 학습시키면 이미 있는 메시지는 건너뛰고 새 메시지만 추가합니다.

## 학습할 때 자동으로 정리하는 것

- 빼는 것: 삭제된 메시지, 보이스톡 기록, 단체방 초대·나가기 안내, 교수님 답 없이 남긴 점수 목록 메모
- 가리는 것: 전화번호 `[전화번호]`, 이메일 `[이메일]`, 비밀번호·아이디 `[비밀번호]` `[아이디]`, 점수 목록 `[점수]`, 학생 석차 `[석차]`
- 직접 빼고 싶은 구간은 `data/chats/<대화방 이름>/exclude.txt`에 날짜(와 시간)를 적습니다.
- 400자가 넘는 긴 메시지(주로 퍼온 기사)는 저장은 그대로 하고, 질문할 때만 앞부분 150자만 씁니다.

## 비용

질문할 때마다 학습된 대화 전체(약 35만 바이트)를 Claude에 함께 보냅니다. 대화 기록은 캐시되므로 첫 질문이 가장 비싸고, 5분 안에 이어지는 질문은 훨씬 저렴합니다. 비용을 줄이려면 `PROFESSOR_AI_EFFORT=low` 또는 `PROFESSOR_AI_MODEL=claude-sonnet-5-5`를 쓰세요.

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

## 공유용 웹페이지 (API 키 없이)

`web/template.html`은 claude.ai 아티팩트로 올리는 페이지입니다. 링크를 연 사람의 Claude 계정으로 답장을 만들기 때문에 API 키가 필요 없고, 페이지에서 한 질문은 저장되지 않습니다.

페이지에는 원본 카톡 대신 `data/web_examples.json`(다른 학생 이름, 성적, 비밀번호, 사적인 대화를 뺀 교수님 답장 예시와 말투 요약)만 들어갑니다.

```bash
python web/build_page.py 페이지.html
```
