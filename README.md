# Clickwee

무료 오픈소스 마우스 커서(움직이는 커서 포함)를 웹에서 미리 써보고, 클릭 한 번으로 Windows에 적용하는 사이트.
https://clickwee.com

## 구조

| 파일 | 설명 |
| --- | --- |
| `index.html` | 사이트. `catalog.json`을 읽어 커서 갤러리와 체험 영역을 그림 |
| `catalog.json` | 커서 목록 (자동 생성). 사이트와 연결된 PC가 모두 이 파일을 읽음 |
| `previews/<id>/` | 미리보기 PNG와 움직이는 커서의 프레임 띠(`*-strip.png`) (자동 생성) |
| `packs/<id>/<크기>.zip` | Clickwee가 Windows용으로 변환한 커서 (자동 생성) |
| `tools/sources.json` | **커서 추가는 여기에만** 한 줄 추가 |
| `tools/build_catalog.py`, `tools/cursorlib.py` | 원본을 받아 변환하고 위 세 가지를 만드는 도구 |
| `Clickwee-Connect.bat` | 방문자가 받는 1회용 연결 파일. `Clickwee.ps1`이 내장되어 있어 사이트에서 따로 내려받지 않음 (자동 생성) |
| `Clickwee.ps1` | 실제 동작 스크립트 원본. %LOCALAPPDATA%\Clickwee에 설치됨 |
| `tools/build_connect.py` | `Clickwee.ps1`을 수정한 뒤 실행하면 `Clickwee-Connect.bat`을 다시 만듦 |
| `favicon.svg` | 파비콘 |
| `CNAME` | GitHub Pages 커스텀 도메인 |
| `_headers`, `netlify.toml` | Cloudflare Pages / Netlify에서 zip 강제 다운로드 헤더 |

## 동작 방식

웹페이지는 OS 설정을 직접 바꿀 수 없다. 사용자가 `Clickwee-Connect.bat`을 한 번 실행하면
`clickwee://` URL 프로토콜이 HKCU에 등록되고, 사이트의 적용 버튼이 보내는
`clickwee://apply/<theme>/<size>` 신호를 `Clickwee.ps1`이 받아 `catalog.json`에서 다운로드 주소를 찾고
커서를 교체한다. 목록을 매번 새로 읽으므로 커서를 추가해도 연결 파일을 다시 받을 필요가 없다.
다운로드는 github.com, 이 저장소의 raw.githubusercontent.com, jsDelivr 주소만 허용.
관리자 권한 불필요, 기존 설정은 자동 백업 후 `clickwee://restore`로 복원.

## 커서 테마

상업적 이용과 재배포가 허용된 라이선스(GPL-2.0/3.0, CC BY-SA 4.0)만 넣는다. 비상업(NC) 라이선스나
라이선스 표기가 없는 커서는 넣지 않는다.

| 종류 (`kind`) | 출처 | 받는 곳 |
| --- | --- | --- |
| `upstream` | 작가가 직접 낸 Windows 빌드 (ful1e5의 Bibata, BreezeX, XCursor-pro, apple_cursor, Google_Cursor, fuchsia, banana) | 작가의 GitHub 릴리스 |
| `xcursor` | 리눅스 전용 커서 (Bibata Extra, Phinger, Catppuccin, Vimix, WhiteSur, McMojave, Layan, Graphite, Qogir, Future) | 변환해서 `packs/` |
| `recolor` | 움직이는 에디션 (Rainbow, Neon). Bibata, GoogleDot에 색 애니메이션을 입힌 것 | `packs/` |

변환본에는 원본 LICENSE와 출처를 담은 README.txt가 들어가고, 사이트 하단 "만든 사람들"에
`catalog.json` 기준으로 프로젝트, 작가, 라이선스가 자동 표시된다. macOS, Google은 상표이므로 광고
문구에 공식 제품처럼 쓰지 말 것.

### 커서 추가하기

1. `tools/sources.json`에 항목 추가 (`id`, `name`, `desc`, `tags`, `dark`, 저작자, 라이선스, `kind`별 주소)
2. `pip install pillow numpy` 후 `python3 tools/build_catalog.py`
3. `catalog.json`, `previews/`, `packs/` 커밋. 끝 (연결된 PC는 바로 새 커서를 씀)

`tags`: `black`, `white`, `color`, `cute`, `modern`, `mac`, `lefty`, `anim`(포인터가 움직임, 자동 감지)

`Clickwee.ps1`을 고쳤을 때만 `python3 tools/build_connect.py`로 연결 파일을 다시 만든다.

## 배포

GitHub Pages: Settings > Pages > Source를 `main` 브랜치 루트로 설정.
Custom domain 저장 후 "Enforce HTTPS"가 체크될 때까지 기다린다 (인증서가 없으면 HTTPS 접속 시
SEC_E_WRONG_PRINCIPAL 오류). DNS는 A 레코드 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (@),
CNAME `www` -> `<username>.github.io`.

## 로컬 확인

```
python3 -m http.server 8000
```
