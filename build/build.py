#!/usr/bin/env python3
"""
Drawer · Build script v3
v3 변경:
  - 첫 카테고리 → index.html 자동 출력 (첫 화면 = dashboard)
  - items.json thumb 자동 매칭 (name 기반)
  - 모든 페이지에 Netlify Identity widget inject
"""

import html
import json
import os
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "img"
CONTENT_DIR = ROOT / "content"
MANIFEST = ROOT / "manifest.json"

IMAGE_RE = re.compile(r"\.(jpe?g|png|webp|gif)$", re.IGNORECASE)
HIDDEN_RE = re.compile(r"^[._]")
AI_APP_RE = re.compile(r"ai[-_]?app", re.IGNORECASE)


IDENTITY_WIDGET = """
  <script src="https://identity.netlify.com/v1/netlify-identity-widget.js"></script>
  <script>
    if (window.netlifyIdentity) {
      window.netlifyIdentity.on("init", user => {
        if (!user) {
          window.netlifyIdentity.on("login", () => {
            document.location.href = "/admin/";
          });
        }
      });
    }
  </script>"""


def inject_identity_widget(content):
    return content.replace("</body>", IDENTITY_WIDGET + "\n</body>", 1)


def normalize_for_match(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def nfc(s):
    return unicodedata.normalize("NFC", s)


def is_visible(name):
    return not HIDDEN_RE.match(name)


def label_from_folder(name):
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


def name_from_filename(filename):
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


def url_slug(name):
    base = re.sub(r"^\d+[-_]", "", name)
    slug = re.sub(r"[_\s]+", "-", base).lower()
    return slug + ".html"


def scan_images(folder):
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


def load_items_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = False

        if isinstance(data, list):
            data = {"items": data}
            changed = True
            print(f"  ↻ items.json 마이그레이션 ({path.parent.name}): array → object")

        if not isinstance(data, dict):
            data = {"items": []}
            changed = True

        items = data.get("items", [])
        if not isinstance(items, list):
            items = []
            data["items"] = items
            changed = True

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

        # v3: thumb 자동 매칭
        folder = path.parent
        try:
            available_images = sorted([
                f.name for f in folder.iterdir()
                if f.is_file() and IMAGE_RE.search(f.name) and is_visible(f.name)
            ])
        except OSError:
            available_images = []

        used_files = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            thumb = item.get("thumb", "")
            if thumb:
                tb = Path(thumb).name
                if (folder / tb).exists():
                    used_files.add(tb)

        for item in items:
            if not isinstance(item, dict):
                continue
            thumb = item.get("thumb", "")
            if thumb and (folder / Path(thumb).name).exists():
                continue
            item_norm = normalize_for_match(item.get("name", ""))
            if not item_norm:
                continue
            matched = None
            for img_name in available_images:
                if img_name in used_files:
                    continue
                img_stem_norm = normalize_for_match(Path(img_name).stem)
                if item_norm in img_stem_norm or img_stem_norm in item_norm:
                    matched = img_name
                    break
            if matched:
                item["thumb"] = matched
                used_files.add(matched)
                changed = True
                print(f"  ↻ thumb 매칭 ({folder.name}): '{item.get('name', '?')}' → {matched}")

        # v4: 폴더에 있는데 items에 없는 새 이미지 → 새 항목 자동 추가
        for img_name in available_images:
            if img_name not in used_files:
                new_item = {
                    "thumb": img_name,
                    "name": name_from_filename(img_name),
                    "desc": "",
                    "longDesc": "",
                    "links": []
                }
                items.append(new_item)
                used_files.add(img_name)
                changed = True
                print(f"  + 새 항목 자동 추가 ({folder.name}): {img_name} → {new_item['name']}")

        if changed:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return items
    except Exception as e:
        print(f"  warning: items.json 파싱 실패 ({path.name}): {e}", file=sys.stderr)
        return []


def autogen_items_for_ai_app(folder, images):
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


ABOUT_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>Drawer — About</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/styles.css">
</head>
<body data-page="about">

  <header class="header" role="banner">
    <a href="index.html" class="header-brand">Drawer</a>
    <nav class="header-nav" id="headerNav" role="navigation" aria-label="주 메뉴"></nav>
    <button class="header-menu-btn" id="menuBtn"
            aria-label="메뉴 열기" aria-expanded="false" aria-controls="mobileMenu">☰</button>
  </header>

  <nav class="mobile-menu" id="mobileMenu" aria-label="모바일 메뉴"></nav>

  <section class="page-head">
    <h1>ABOUT</h1>
  </section>

  <main class="about" aria-label="소개">
    <div class="about-row">
      <div class="about-label">Profile</div>
      <div class="about-body">
        <p class="name">{name}</p>
        <p>{tagline}</p>
      </div>
    </div>
{sections_html}
  </main>

  <footer class="footer">© Drawer · noindex</footer>

  <script src="js/main.js"></script>
</body>
</html>
"""


def render_about_section(section):
    label = html.escape(section.get("label", ""))
    type_ = section.get("type", "list")
    items = section.get("items", []) or []

    if type_ == "tags":
        tags = "\n".join(
            f"          <span>{html.escape(str(i))}</span>" for i in items
        )
        body = f'<div class="tool-tags">\n{tags}\n        </div>'
    else:
        lis = "\n".join(
            f"          <li>{html.escape(str(i))}</li>" for i in items
        )
        body = f"<ul>\n{lis}\n        </ul>"

    return f"""
    <div class="about-row">
      <div class="about-label">{label}</div>
      <div class="about-body">
        {body}
      </div>
    </div>"""


def build_about():
    data_path = CONTENT_DIR / "about.json"
    if not data_path.exists():
        return False

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  warning: about.json 파싱 실패: {e}", file=sys.stderr)
        return False

    profile = data.get("profile", {}) or {}
    sections = data.get("sections", []) or []

    sections_html = "".join(render_about_section(s) for s in sections)

    html_out = ABOUT_TEMPLATE.format(
        name=html.escape(profile.get("name", "")),
        tagline=html.escape(profile.get("tagline", "")),
        sections_html=sections_html,
    )

    html_out = inject_identity_widget(html_out)
    (ROOT / "about.html").write_text(html_out, encoding="utf-8")
    return True


def build():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    folders = sorted(
        [nfc(d.name) for d in IMG_DIR.iterdir()
         if d.is_dir() and is_visible(d.name)]
    )

    print(f"\n📂 {IMG_DIR.relative_to(ROOT)} 스캔...")

    categories = []
    generated_pages = []

    about_built = build_about()
    PROTECTED = {"index.html"}
    if not about_built:
        PROTECTED.add("about.html")

    for f in ROOT.glob("*.html"):
        if f.name not in PROTECTED and f.name != "about.html":
            f.unlink()

    for idx, folder_name in enumerate(folders):
        folder = IMG_DIR / folder_name
        items_json = folder / "items.json"
        is_ai_app = bool(AI_APP_RE.search(folder_name))

        if items_json.exists():
            view = "list"
            items = load_items_json(items_json)
        elif is_ai_app:
            images = scan_images(folder)
            items = autogen_items_for_ai_app(folder, images)
            items_json.write_text(
                json.dumps({"items": items}, ensure_ascii=False, indent=2),
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

        page_html = CATEGORY_TEMPLATE.format(
            label=label,
            slug=slug,
            label_upper=label.upper(),
        )
        page_html = inject_identity_widget(page_html)
        page_path = ROOT / cat["url"]
        page_path.write_text(page_html, encoding="utf-8")
        generated_pages.append(cat["url"])

        # v3: 첫 카테고리 → index.html도 동일 내용
        if idx == 0:
            (ROOT / "index.html").write_text(page_html, encoding="utf-8")
            generated_pages.append(f"index.html (= {cat['url']})")

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

    about_status = "from content/about.json" if about_built else "static"

    print(f"\n✅ 빌드 완료")
    print(f"   카테고리       : {len(categories)}")
    print(f"   생성된 페이지   : {len(generated_pages)}개")
    print(f"   첫 화면        : index.html = {folders[0] if folders else '(없음)'}")
    print(f"   about.html     : {about_status}\n")


if __name__ == "__main__":
    build()
