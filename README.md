# Clickwee

모던한 마우스 커서를 웹에서 미리 써보고, 클릭 한 번으로 Windows에 적용하는 사이트.
https://clickwee.com

## 구조

| 파일 | 설명 |
| --- | --- |
| `index.html` | 사이트 전체. 커서 이미지가 data URI로 내장된 단일 파일 |
| `Clickwee-Connect.bat` | 방문자가 받는 1회용 연결 파일. clickwee.com/Clickwee.ps1을 받아 설치 |
| `Clickwee.ps1` | 실제 동작 스크립트. %LOCALAPPDATA%\Clickwee에 설치됨 |
| `favicon.svg` | 파비콘 |
| `CNAME` | GitHub Pages 커스텀 도메인 |
| `_headers`, `netlify.toml` | Cloudflare Pages / Netlify에서 zip 강제 다운로드 헤더 |

## 동작 방식

웹페이지는 OS 설정을 직접 바꿀 수 없다. 사용자가 `Clickwee-Connect.bat`을 한 번 실행하면
`clickwee://` URL 프로토콜이 HKCU에 등록되고, 사이트의 적용 버튼이 보내는
`clickwee://apply/<theme>/<size>` 신호를 `Clickwee.ps1`이 받아 커서를 교체한다.
관리자 권한 불필요, 기존 설정은 자동 백업 후 `clickwee://restore`로 복원.

## 커서 테마

ful1e5의 오픈소스 커서 (GPL-3.0)를 릴리스 zip에서 직접 내려받아 사용한다.
- apple_cursor (macOS Black / White)
- XCursor-pro (Dark / Light)
- Google_Cursor (GoogleDot Black / White)

## 배포

GitHub Pages: Settings > Pages > Source를 `main` 브랜치 루트로 설정.
DNS는 A 레코드 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (@),
CNAME `www` -> `<username>.github.io`.

## 로컬 확인

```
python3 -m http.server 8000
```
