# Encoding Converter

C / H / CPP / HPP 파일의 인코딩을 감지해서 UTF-8로 변환하는 `tkinter` 기반 GUI 도구입니다.

현재 프로젝트는 아래 파일을 중심으로 구성되어 있습니다.

- [gui.py](D:/Developments/Python/encoding_converter/gui.py): GUI 실행 파일
- [convert.py](D:/Developments/Python/encoding_converter/convert.py): CLI 실행 파일
- [build_windows.ps1](D:/Developments/Python/encoding_converter/build_windows.ps1): Windows `exe` 빌드 스크립트
- [build_macos.sh](D:/Developments/Python/encoding_converter/build_macos.sh): macOS `.app` 빌드 스크립트

## 1. 아이콘 준비

현재 아이콘 시안은 [icon-concept-b.svg](D:/Developments/Python/encoding_converter/assets/icon-concept-b.svg) 를 기준으로 사용합니다.

빌드 스크립트와 앱 런타임은 최종적으로 아래 파일을 읽습니다.

- `assets/icon.png`
- `assets/icon.ico`

권장 방식:

1. [icon-concept-b.svg](D:/Developments/Python/encoding_converter/assets/icon-concept-b.svg)를 기준으로 최종 PNG를 만든다.
2. 파일명을 `assets/icon.png` 로 저장한다.
3. 크기는 `1024x1024` 투명 배경 PNG를 권장한다.

이 파일이 있으면:

- 앱 실행 중 창 아이콘으로 사용됨
- Windows `exe` 아이콘으로 사용됨
- macOS `.app` 아이콘으로 사용됨

## 2. 개발 환경 준비

이 프로젝트는 `PyInstaller` 로 패키징합니다.

중요:

- Windows `exe` 는 Windows 에서 빌드
- macOS `.app` 는 macOS 에서 빌드
- 한 OS에서 다른 OS용 결과물을 직접 빌드하는 방식은 기본 경로로 권장하지 않음

### Windows

```powershell
& "C:\Users\GVL\AppData\Local\Programs\Python\Python313\python.exe" -m venv .venv
Copy-Item .venv\Scripts\python.exe .venv\Scripts\python3.exe -Force
.\.venv\Scripts\python3.exe -m pip install -r requirements-build.txt
```

이 프로젝트에서는 Windows에서도 `python3` 기준으로 작업하는 것을 권장합니다.

예시:

```powershell
.\.venv\Scripts\python3.exe gui.py
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
```

빌드 의존성은 [requirements-build.txt](D:/Developments/Python/encoding_converter/requirements-build.txt)에 정리되어 있습니다.

## 3. 로컬 실행

GUI 실행:

```powershell
.\.venv\Scripts\python3.exe gui.py
```

CLI 실행:

```powershell
.\.venv\Scripts\python3.exe convert.py . -r
```

## 4. Windows exe 패키징

Windows에서는 아래 스크립트를 실행하면 됩니다.

```powershell
.\build_windows.ps1
```

출력 결과:

- `dist/Encoding Converter.exe`

이 스크립트는 내부적으로 다음 옵션을 사용합니다.

- `--onefile`: 단일 `exe`
- `--windowed`: 콘솔 창 제거
- `--collect-all tkinterdnd2`: 드래그 앤 드롭 관련 리소스 포함

## 5. macOS app 패키징

macOS에서는 아래 스크립트를 실행합니다.

```bash
chmod +x build_macos.sh
./build_macos.sh
```

출력 결과:

- `dist/Encoding Converter.app`

참고:

- macOS에서는 `--windowed` 옵션이 `.app` 번들을 생성함
- GUI 앱은 보통 `--onedir` 빌드가 더 안정적임

## 6. 빌드 결과 확인

패키징 후 아래를 확인하는 것을 권장합니다.

- 프로그램 시작 직후 모든 버튼과 아이콘이 잘 보이는지
- 파일 드래그 앤 드롭이 동작하는지
- 한글 경로에서도 정상 동작하는지
- 백업 폴더가 정상 생성되는지
- `UTF-8` 변환 후 파일 내용이 깨지지 않는지
- 아이콘이 실행 파일, 창 제목줄, 작업 표시줄에 반영되는지

## 7. 자주 있는 문제

### `python` 또는 `py` 명령이 없음

Python이 PATH에 없다는 뜻입니다.

해결:

- Python을 설치하면서 PATH 추가 옵션을 켠다
- 또는 Python 전체 경로로 직접 실행한다

### `PyInstaller` 모듈 없음

가상환경 활성화 후 아래를 다시 실행합니다.

```powershell
pip install -r requirements-build.txt
```

### `tkinterdnd2` 누락 오류

드래그 앤 드롭용 패키지가 빠진 상태입니다.

```powershell
pip install tkinterdnd2
```

### Windows에서는 되는데 macOS에서는 안 됨

정상적인 경우입니다. 각각의 OS에서 별도로 빌드해야 합니다.

## 8. 참고 문서

- [PACKAGING.md](D:/Developments/Python/encoding_converter/PACKAGING.md)
- [assets/README.md](D:/Developments/Python/encoding_converter/assets/README.md)

## 9. License

이 프로젝트는 MIT License를 사용합니다.

- [LICENSE](D:/Developments/Python/encoding_converter/LICENSE)
