#!/usr/bin/env python3
"""
C/H File Encoding Converter
- .c / .h 파일의 인코딩을 자동 감지하여 UTF-8로 변환
- 변환 전 백업 생성, dry-run 모드 지원
"""

import os
import sys
import shutil
import argparse
import datetime
from pathlib import Path


# ─────────────────────────────────────────────
#  인코딩 감지
# ─────────────────────────────────────────────

DETECT_ORDER = [
    ("utf-8-sig", "UTF-8 BOM"),
    ("utf-8",     "UTF-8"),
    ("cp949",     "CP949 / EUC-KR"),
    ("euc-kr",    "EUC-KR"),
    ("latin-1",   "Latin-1 (ISO-8859-1)"),
]


def detect_encoding(raw: bytes):
    """
    바이트 배열을 받아 (인코딩명, 설명) 튜플 반환.
    감지 실패 시 (None, "unknown") 반환.
    """
    # BOM 우선 확인
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16", "UTF-16 BOM"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", "UTF-8 BOM"

    # 시도 순서대로 디코딩 검사
    for enc, label in DETECT_ORDER:
        try:
            raw.decode(enc)
            return enc, label
        except (UnicodeDecodeError, LookupError):
            continue

    # chardet 설치돼 있으면 마지막 수단으로 사용
    try:
        import chardet
        result = chardet.detect(raw)
        enc = result.get("encoding")
        conf = result.get("confidence", 0)
        if enc and conf > 0.5:
            return enc, f"chardet({enc}, confidence={conf:.0%})"
    except ImportError:
        pass

    return None, "unknown"


def is_already_utf8(raw: bytes) -> bool:
    """이미 UTF-8(BOM 없음)인지 확인."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return False  # BOM 붙은 UTF-8은 변환 대상
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


# ─────────────────────────────────────────────
#  파일 처리
# ─────────────────────────────────────────────

class ConvertResult:
    def __init__(self):
        self.converted = []   # (path, from_enc)
        self.skipped   = []   # (path, reason)
        self.failed    = []   # (path, error)


def process_file(path: Path, backup_dir: Path, dry_run: bool, result: ConvertResult):
    """
    단일 파일을 UTF-8로 변환.
    """
    raw = path.read_bytes()

    # 이미 UTF-8(BOM 없음)이면 스킵
    if is_already_utf8(raw):
        result.skipped.append((path, "already UTF-8"))
        return

    enc, label = detect_encoding(raw)

    if enc is None:
        result.failed.append((path, "인코딩 감지 실패"))
        return

    # 실제로 디코딩 가능한지 재확인
    try:
        text = raw.decode(enc)
    except (UnicodeDecodeError, LookupError) as e:
        result.failed.append((path, f"디코딩 오류: {e}"))
        return

    if dry_run:
        result.converted.append((path, label))
        return

    # 백업
    if backup_dir:
        rel = path.relative_to(path.anchor)  # 드라이브 제거
        dest = backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    # UTF-8 저장 (BOM 없음, 줄바꿈 원본 유지)
    path.write_bytes(text.encode("utf-8"))
    result.converted.append((path, label))


def collect_files(root: Path, extensions: list[str], recursive: bool) -> list[Path]:
    files = []
    if root.is_file():
        files.append(root)
    elif root.is_dir():
        pattern = "**/*" if recursive else "*"
        for ext in extensions:
            files.extend(root.glob(f"{pattern}{ext}"))
    return sorted(set(files))


# ─────────────────────────────────────────────
#  출력 헬퍼
# ─────────────────────────────────────────────

GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
RESET  = "\033[0m"

def cprint(color, msg):
    print(f"{color}{msg}{RESET}")


# ─────────────────────────────────────────────
#  메인
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="C/H 파일 인코딩 감지 및 UTF-8 변환 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python convert.py .                          현재 폴더 (비재귀)
  python convert.py ../EMD-1010_Origin -r      하위 폴더 포함
  python convert.py EMD1010.c --dry-run        미리보기만
  python convert.py . -r --ext .c .h .cpp      확장자 지정
        """,
    )
    parser.add_argument("path", help="변환할 파일 또는 폴더 경로")
    parser.add_argument("-r", "--recursive",  action="store_true", help="하위 폴더 재귀 탐색")
    parser.add_argument("--dry-run",          action="store_true", help="실제 변환 없이 결과만 미리보기")
    parser.add_argument("--ext",              nargs="+", default=[".c", ".h"], metavar="EXT",
                        help="대상 확장자 (기본: .c .h)")
    parser.add_argument("--no-backup",        action="store_true", help="백업 생성 안 함")
    parser.add_argument("--backup-dir",       default=None, metavar="DIR",
                        help="백업 폴더 지정 (기본: <path>_backup_YYYYMMDD_HHMMSS)")

    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        cprint(RED, f"[ERROR] 경로를 찾을 수 없음: {root}")
        sys.exit(1)

    # 백업 폴더 결정
    if args.no_backup or args.dry_run:
        backup_dir = None
    elif args.backup_dir:
        backup_dir = Path(args.backup_dir).resolve()
    else:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = root if root.is_dir() else root.parent
        backup_dir = base.parent / f"{base.name}_backup_{ts}"

    # 파일 수집
    extensions = [e if e.startswith(".") else f".{e}" for e in args.ext]
    files = collect_files(root, extensions, args.recursive)

    if not files:
        cprint(YELLOW, f"[INFO] 대상 파일 없음: {root} (확장자: {extensions})")
        sys.exit(0)

    # 헤더 출력
    mode_label = "[DRY-RUN]" if args.dry_run else "[CONVERT]"
    cprint(CYAN, f"\n{mode_label} 대상: {root}")
    cprint(CYAN, f"  파일 수   : {len(files)}")
    cprint(CYAN, f"  확장자    : {extensions}")
    cprint(CYAN, f"  백업 폴더 : {backup_dir if backup_dir else '사용 안 함'}")
    print()

    # 처리
    result = ConvertResult()
    for fpath in files:
        process_file(fpath, backup_dir, args.dry_run, result)

    # 결과 출력
    for fpath, from_enc in result.converted:
        tag = "[DRY]" if args.dry_run else "[OK] "
        cprint(GREEN, f"  {tag} {fpath.name:<40}  {from_enc} → UTF-8")

    for fpath, reason in result.skipped:
        cprint(YELLOW, f"  [--]  {fpath.name:<40}  {reason}")

    for fpath, error in result.failed:
        cprint(RED, f"  [ERR] {fpath.name:<40}  {error}")

    # 요약
    print()
    cprint(CYAN, f"완료: 변환 {len(result.converted)} / 스킵 {len(result.skipped)} / 오류 {len(result.failed)}")
    if not args.dry_run and backup_dir and result.converted:
        cprint(CYAN, f"백업 위치: {backup_dir}")


if __name__ == "__main__":
    main()
