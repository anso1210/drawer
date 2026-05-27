#!/usr/bin/env python3
"""
Drawer · Build script
===================================
img/ 폴더 트리 = SSOT.
폴더 추가/삭제/이름변경 → 빌드 한 번으로 메뉴·페이지·콘텐츠 모두 자동 반영.

규칙:
  - 1단 폴더 prefix(01-, 02-)는 정렬 전용, 라벨에서 제거
  - 한글 폴더/파일명 NFD → NFC 자동 정규화
  - AI App 카테고리(폴더명에 'ai_app' 또는 'ai-app' 포함):
      → list view (썸네일 + 제목 + 설명 + 액션)
      → items.json 없으면 자동 생성 (사용자가 desc/links 편집)
  - 그 외 카테고리:
      → grid view (이미지 재귀 스캔)
      → items.json 직접 두면 list view로 전환 가능
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
HIDDEN_RE = re.compile(r"^[._]")
AI_APP_RE = re.compile(r"ai[-_]?app", re.IGNORECASE)


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def is_visible(name: str) -> bool:
    return not HIDDEN_RE.match(name)


def label_from_folder(name: str) -> str:
    base = re.sub(r"^\d+[-_]", "", name)
    words = re.split(r"[_\s-]+", base)
    out = []
    for w in words:
        if not w:
            continue
        if re.search(r"\d", w) or len(w) <= 2:
            out.append(w.upper())
        elif w[0].isascii():
            out.append(w[0].upper() + w[1:].lower())
        else:
            out.append(w)
    return " ".join(out)


def name_from_filename(filename: str) -> str:
    """파일명 → 항목 이름 (자동 변환). 예: '01-jobposting.png' → 'Jobposting'"""
    stem = Path(filename).stem
    stem = re.sub(r"^\d+[-_]", "", stem)
    stem = re.sub(r"[_-]+", " ", stem)
    words = stem.split()
    out = []
    for w in words:
        if not w:
            continue
        if w[0].isascii():
            out.append(w[0].upper() + w[1:])
        else:
            out.append(w)
    return " ".join(out) if out else stem


def url_slug(name: str) -> str:
    base = re.sub(r"^\d+[-_]", "", name)
    slug = re.sub(r"[_\s]+", "-", base).lower()
    return slug + ".html"


def scan_images(folder: Path):
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
        items = json.loads(path.read_text(encoding="utf-8"))
        # 기존 items에 longDesc 필드 누락된 경우 자동 추가 (마이그레이션)
        changed = False
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    if "longDesc" not in item:
                        item["longDesc"] = ""
                        changed = True
                    if "desc" not in item:
                        item["desc"] = ""
                        changed = True
                    if "links" not in item:
                        item["links"] = []
                        changed = True
        if changed:
            path.write_text(
                json.dumps(items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  ↻ items.json 마이그레이션 ({path.parent.name}): longDesc 필드 추가")
        return items
    except Exception as e:
        print(f"  warning: items.json 파싱 실패 ({path.name}): {e}", file=sys.stderr)
        return []


def autogen_items_for_ai_app(folder: Path, images: list) -> list:
    """AI App 카테고리에 items.json 없을 때 자동 생성."""
    items = []
    for img_rel in images:
        items.append({
            "thumb": img_rel,
            "name": name_from_filename(img_rel),
            "desc": "",
            "longDesc": "",
            "links": []
        })
    return items


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


def build():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    folders = sorted(
        [nfc(d.name) for d in IMG_DIR.iterdir()
         if d.is_dir() and is_visible(d.name)]
    )

    print(f"\n📂 {IMG_DIR.relative_to(ROOT)} 스캔...")

    categories = []
    generated_pages = []

    PROTECTED = {"index.html", "about.html"}
    for f in ROOT.glob("*.html"):
        if f.name not in PROTECTED:
            f.unlink()

    for folder_name in folders:
        folder = IMG_DIR / folder_name
        items_json = folder / "items.json"
        is_ai_app = bool(AI_APP_RE.search(folder_name))

        if items_json.exists():
            view = "list"
            items = load_items_json(items_json)
        elif is_ai_app:
            # AI App 폴더 + items.json 없음 → 자동 생성
            images = scan_images(folder)
            items = autogen_items_for_ai_app(folder, images)
            items_json.write_text(
                json.dumps(items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            view = "list"
            print(f"  + items.json 자동 생성 ({folder_name}): {len(items)}개 항목")
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

    manifest = {
        "categories": categories,
        "totalItems": sum(
            len(c["items"]) for c in categories if c["view"] == "grid"
        ),
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ 빌드 완료")
    print(f"   manifest.json  : {len(categories)} 카테고리")
    print(f"   생성된 페이지   : {', '.join(generated_pages) if generated_pages else '없음'}")
    print(f"   정적 페이지     : index.html, about.html\n")


if __name__ == "__main__":
    build()
