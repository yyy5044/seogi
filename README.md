# seogi

회의 녹음 파일을 넣으면 회의록 정리본이 노션에 올라가는 명령줄 도구. 명세는 [docs/spec.md](docs/spec.md), 현재 진행 상황은 [docs/progress.md](docs/progress.md).

## 새 컴퓨터에서 시작할 때

API 키는 저장소에 없고 컴퓨터마다 환경 변수로 따로 설정해야 한다.

1. Python 3.12 설치: `winget install Python.Python.3.12`
2. 의존성 설치: `py -3.12 -m pip install -r requirements.txt`
3. 환경 변수 설정 (PowerShell, 아무 경로에서나). 설정 후 터미널과 앱을 새로 열어야 적용된다.

   | 변수 | 용도 | 발급처 |
   |---|---|---|
   | `DAGLO_API_TOKEN` | 다글로 STT API | https://developers.daglo.ai/console → 토큰 메뉴 |

   ```powershell
   setx DAGLO_API_TOKEN "토큰"
   ```

4. 설정 확인 (값은 출력하지 않는다): `[bool]$env:DAGLO_API_TOKEN`

## 실행

저장소 루트에서 실행한다. 결과는 `runs/<회의ID>/`에 저장된다.

```powershell
py -3.12 daglo.py recordings/<녹음 파일>
```
