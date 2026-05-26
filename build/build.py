#!/usr/bin/env python3
"""
Drawer · Build script
===================================
img/ 폴더 트리 = SSOT (Single Source of Truth).
폴더 추가/삭제/이름변경 → 빌드 한 번으로 메뉴·페이지·콘텐츠 모두 자동 반영.

생성물 (모두 .gitignore 처리):
  - manifest.json          : 카테고리 + 이미지 인덱스
  - <category>.html        : 카테고리 페이지 (1단 폴더당 1개)

규칙:
  - 1단 폴더 prefix(01-, 02-)는 정렬 전용, 라벨에서 제거
  - 폴더명 → 메뉴 라벨 자동 변환:
      01-dashboard  → "Dashboard"
      02-3d         → "3D"
      03-ai_app     → "AI App"
  - 한글 폴더/파일명 NFD → NFC 자동 정규화 (macOS Finder → Linux/Web 호환)
  - 폴더 안 items.json 존재 → list view (이미지 무시)
    없음 → grid view (이미지 재귀 스캔)
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "img"
MANIFEST = ROOT / "manifest.json"

IMAGE_RE = re.compile(r"\.(jpe?g|png|webp|gif)$", re.IGNORECASE)
HIDDEN_RE = re.compile(r"^[._]")  # .DS_Store, __MACOSX 등


# ---------- 유틸 ----------

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def is_visible(name: str) -> bool:
    return not HIDDEN_RE.match(name)


def label_from_folder(name: str) -> str:
    """폴더명 → 메뉴 라벨."""
    base = re.sub(r"^\d+[-_]", "", name)
    words = re.split(r"[_\s-]+", base)
    out = []
    for w in words:
        if not w:
            continue
        # 숫자 포함 or 2글자 이하 → 전체 대문자 (3d→3D, ai→AI, ui→UI)
        if re.search(r"\d", w) or len(w) <= 2:
            out.append(w.upper())
        elif w[0].isascii():
            out.append(w[0].upper() + w[1:].lower())
        else:
            out.append(w)  # 한글 등은 그대로
    return " ".join(out)


def url_slug(name: str) -> str:
    """폴더명 → URL 슬러그 (.html 포함)."""
    base = re.sub(r"^\d+[-_]", "", name)
    slug = re.sub(r"[_\s]+", "-", base).lower()
    return slug + ".html"


def scan_images(folder: Path):
    """카테고리 폴더 안 이미지 재귀 스캔. 클라이언트 하위 폴더 모두 포함."""
    items = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted([nfc(d) for d in dirnames if is_visible(d)])
        for f in sorted(filenames):
            if not is_visible(f) or not IMAGE_RE.search(f):
                continue
            full = Path(dirpath) / f
            rel = full.relative_to(folder)
            rel_str = "/".join(nfc(p) for p in rel.parts)
            items.append(rel_str)
    return items


def load_items_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  warning: items.json 파싱 실패 ({path.name}): {e}", file=sys.stderr)
        return []


# ---------- 카테고리 페이지 템플릿 ----------

CATEGORY_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>Drawer — {label}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/styles.css">
</head>
<body data-page="{slug}">

  <header class="header" role="banner">
    <a href="index.html" class="header-brand">Drawer</a>
    <nav class="header-nav" id="headerNav" role="navigation" aria-label="주 메뉴"></nav>
    <button class="header-menu-btn" id="menuBtn"
            aria-label="메뉴 열기" aria-expanded="false" aria-controls="mobileMenu">☰</button>
  </header>

  <nav class="mobile-menu" id="mobileMenu" aria-label="모바일 메뉴"></nav>

  <section class="page-head">
    <h1>{label_upper}</h1>
    <p class="page-meta"></p>
  </section>

  <main class="gallery" id="gallery" aria-label="작업물"></main>
  <section class="list" id="list" hidden aria-label="프로젝트 리스트"></section>
  <div class="empty-state" id="emptyState" hidden></div>

  <footer class="footer">© Drawer · noindex</footer>

  <script src="js/main.js"></script>
</body>
</html>
"""


# ---------- 메인 ----------

def build():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    folders = sorted(
        [nfc(d.name) for d in IMG_DIR.iterdir()
         if d.is_dir() and is_visible(d.name)]
    )

    print(f"\n📂 {IMG_DIR.relative_to(ROOT)} 스캔...")

    categories = []
    generated_pages = []

    # 기존 자동 생성 .html 정리 (orphan cleanup)
    # 단 index.html, about.html은 보호
    PROTECTED = {"index.html", "about.html"}
    for f in ROOT.glob("*.html"):
        if f.name not in PROTECTED:
            f.unlink()

    for folder_name in folders:
        folder = IMG_DIR / folder_name
        items_json = folder / "items.json"

        if items_json.exists():
            view = "list"
            items = load_items_json(items_json)
        else:
            view = "grid"
            items = scan_images(folder)

        slug = url_slug(folder_name).replace(".html", "")
        label = label_from_folder(folder_name)

        cat = {
            "id": folder_name,
            "label": label,
            "url": f"{slug}.html",
            "view": view,
            "items": items,
        }
        categories.append(cat)

        # 카테고리 페이지 .html 자동 생성
        page_path = ROOT / cat["url"]
        page_path.write_text(
            CATEGORY_TEMPLATE.format(
                label=label,
                slug=slug,
                label_upper=label.upper(),
            ),
            encoding="utf-8",
        )
        generated_pages.append(cat["url"])

        count = len(items)
        empty = " (empty)" if count == 0 else ""
        print(f"  ✓ {folder_name:30s} → {label:18s} {view:5s} {count:4d}{empty}  →  {cat['url']}")

    # manifest.json 생성
    manifest = {
        "categories": categories,
        "totalItems": sum(len(c["items"]) for c in categories if c["view"] == "grid"),
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ 빌드 완료")
    print(f"   manifest.json  : {len(categories)} 카테고리, {manifest['totalItems']} 그리드 아이템")
    print(f"   생성된 페이지   : {', '.join(generated_pages) if generated_pages else '없음'}")
    print(f"   정적 페이지     : index.html, about.html\n")


if __name__ == "__main__":
    build()
