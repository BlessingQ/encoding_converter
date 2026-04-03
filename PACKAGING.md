# Packaging Guide

이 프로젝트는 `tkinter` GUI 앱이므로 `PyInstaller` 로 패키징하는 것이 가장 단순합니다.

중요:

- Windows `exe` 는 Windows 에서 빌드
- macOS `.app` 는 macOS 에서 빌드
- 한 플랫폼에서 다른 플랫폼용 결과물을 직접 만드는 방식은 기본 경로로 보지 않는 것이 안전합니다

## 1. 아이콘 준비

`assets/icon.png` 파일을 준비합니다.

Windows 아이콘 리소스까지 포함하려면 아래 파일도 함께 준비합니다.

- `assets/icon.ico`

권장 사양:

- 1024x1024 PNG
- 투명 배경
- 앱 실행 파일과 작은 작업 표시줄 크기에서도 식별 가능한 단순한 형태

`gui.py` 는 실행 중에도 이 파일을 읽어서 창 아이콘으로 사용합니다.

## 2. 빌드 환경 생성

Windows:

```powershell
& "C:\Users\GVL\AppData\Local\Programs\Python\Python313\python.exe" -m venv .venv
Copy-Item .venv\Scripts\python.exe .venv\Scripts\python3.exe -Force
.\.venv\Scripts\python3.exe -m pip install -r requirements-build.txt
```

macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
```

## 3. Windows exe 빌드

```powershell
.\build_windows.ps1
```

출력:

- `dist/ENCConverter.exe`

설명:

- `--onefile` 로 단일 exe 생성
- `--windowed` 로 콘솔 창 제거
- `--collect-all tkinterdnd2` 로 드래그 앤 드롭 관련 리소스 포함

## 4. macOS app 빌드

```bash
chmod +x build_macos.sh
./build_macos.sh
```

출력:

- `dist/ENCConverter.app`

설명:

- `--windowed` 가 macOS 에서는 `.app` 번들 생성을 트리거
- macOS 는 보통 `--onedir` 쪽이 GUI 앱 배포에서 더 안정적

## 5. 배포 전 체크

- 실제 파일 드래그 앤 드롭 동작 확인
- 백업 폴더 생성 확인
- 한글 경로에서 동작 확인
- 아이콘이 실행 파일과 앱 창에 모두 반영되는지 확인

## 6. macOS 추가 작업

외부 사용자에게 배포할 계획이면 아래를 추가로 고려해야 합니다.

- 코드 서명
- notarization
- 필요 시 `.dmg` 생성

내부 사용이라면 `.app` 번들만으로도 충분한 경우가 많습니다.
