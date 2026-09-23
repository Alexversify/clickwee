# Clickwee

모던한 마우스 커서를 웹에서 미리 써보고, 클릭 한 번으로 Windows에 적용하는 사이트.
https://clickwee.com

## 구조

| 파일 | 설명 |
| --- | --- |
| `index.html` | 사이트 전체. 커서 이미지가 data URI로 내장된 단일 파일 |
| `Clickwee-Connect.bat` | 방문자가 받는 1회용 연결 파일. `Clickwee.ps1`이 내장되어 있어 사이트에서 따로 내려받지 않음 (자동 생성) |
| `Clickwee.ps1` | 실제 동작 스크립트 원본. %LOCALAPPDATA%\Clickwee에 설치됨 |
| `tools/build_connect.py` | `Clickwee.ps1`을 수정한 뒤 실행하면 `Clickwee-Connect.bat`을 다시 만듦 |
| `favicon.svg` | 파비콘 |
| `CNAME` | GitHub Pages 커스텀 도메인 |
| `_headers`, `netlify.toml` | Cloudflare Pages / Netlify에서 zip 강제 다운로드 헤더 |

## 동작 방식

웹페이지는 OS 설정을 직접 바꿀 수 없다. 사용자가 `Clickwee-Connect.bat`을 한 번 실행하면
`clickwee://` URL 프로토콜이 HKCU에 등록되고, 사이트의 적용 버튼이 보내는
`clickwee://apply/<theme>/<size>` 신호를 `Clickwee.ps1`이 받아 커서를 교체한다.
관리자 권한 불필요, 기존 설정은 자동 백업 후 `clickwee://restore`로 복원.

## 커서 테마

모두 ful1e5의 오픈소스 커서 (GPL-3.0, 상업적 이용 허용)이며, 각 프로젝트의 공식 GitHub 릴리스 zip을
사용자 PC에서 직접 내려받는다. 사이트에는 미리보기 이미지만 내장.
- Bibata_Cursor v2.0.7 (Modern Classic / Ice / Amber, Original Classic / Ice)
- XCursor-pro v2.0.2 (Dark / Light / Red)
- apple_cursor v2.0.1 (macOS Black / White)
- Google_Cursor v2.0.0 (GoogleDot Black / White / Blue / Red)
- fuchsia-cursor v2.0.1 (Fuchsia / Amber)
- banana-cursor v2.0.0 (Banana / Blue)

GPL-3.0 조건: 저작자와 라이선스를 표시하고 원본 소스 위치를 안내 (footer에 링크). 커서 파일을 수정해서
재배포하지 않고 원본 릴리스를 그대로 쓰므로 추가 의무는 없음. macOS, Google은 상표이므로 광고 문구에
공식 제품처럼 쓰지 말 것.

테마 추가 순서: `Clickwee.ps1`의 `$urls`에 추가 → `python3 tools/build_connect.py` →
`index.html`의 `THEMES`, `CURSORS`(64px PNG data URI + 핫스팟 비율)에 추가.

## 배포

GitHub Pages: Settings > Pages > Source를 `main` 브랜치 루트로 설정.
Custom domain 저장 후 "Enforce HTTPS"가 체크될 때까지 기다린다 (인증서가 없으면 HTTPS 접속 시
SEC_E_WRONG_PRINCIPAL 오류). DNS는 A 레코드 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (@),
CNAME `www` -> `<username>.github.io`.

## 로컬 확인

```
python3 -m http.server 8000
```
