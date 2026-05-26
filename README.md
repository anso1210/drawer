# Drawer · Personal Portfolio

> 핀터레스트 스타일 개인 포트폴리오.
> `img/` 폴더 트리 = SSOT. 폴더만 추가/삭제하면 메뉴와 페이지가 자동 반영됩니다.
> `noindex` — 외부 공개지만 검색엔진 차단, 링크 아는 사람만.

## 폴더 구조

```
drawer/
├── index.html              # 정적 첫 화면 (hero + 전체 그리드)
├── about.html              # 정적 About 페이지
│
├── css/styles.css          # 공통 스타일 (NDS 토큰)
├── js/main.js              # manifest 로드 + 메뉴/콘텐츠 동적 렌더 + 인터랙션
├── build/build.py          # 빌드 스크립트 (Python 3, 표준 라이브러리만)
│
├── img/                    # SSOT — 카테고리 폴더 자유 추가/삭제
│   ├── 01-dashboard/       #  ├ 하위 클라이언트 폴더(01-부산항만 등) 자유
│   │   └── 01-부산항만/
│   ├── 02-3d/
│   └── 03-ai_app/
│       └── items.json      # ← 폴더 안에 items.json 두면 list view
│
├── netlify.toml            # Netlify 배포 설정
├── .gitignore
└── README.md

# 빌드 산출물 (git 제외, Netlify가 자동 생성):
#   manifest.json
#   dashboard.html, 3d.html, ai-app.html (카테고리 페이지)
```

## 작업 흐름

### 1) 폴더 추가/이름 변경/삭제
`img/` 안에서 폴더만 조작하세요.

| 액션 | 결과 |
|---|---|
| `img/04-icons/` 폴더 추가 | "Icons" 메뉴 + `icons.html` 페이지 자동 생성 |
| `img/01-dashboard/` 이름을 `01-dashboards`로 변경 | 메뉴 라벨 "Dashboards"로 자동 변경 |
| `img/02-3d/` 폴더 삭제 | "3D" 메뉴와 페이지 자동 사라짐 |
| `img/01-dashboard/03-새클라이언트/` 추가 | Dashboard 그리드에 그 폴더 이미지들 자동 포함 |

### 2) 로컬 미리보기
```bash
cd drawer
python3 build/build.py           # img/ 스캔 → manifest.json + 카테고리 페이지 생성
python3 -m http.server 8000      # 브라우저: http://localhost:8000
```

### 3) 배포
```bash
git add img/                     # 추가/변경된 이미지만 commit
git commit -m "Add ..."
git push
```
Netlify가 push를 받아 자동으로 `python3 build/build.py` 실행 후 배포합니다.

## 폴더명 → 메뉴 라벨 자동 변환 규칙

| 폴더명 | 메뉴 라벨 | URL |
|---|---|---|
| `01-dashboard` | Dashboard | `dashboard.html` |
| `02-3d` | 3D | `3d.html` |
| `03-ai_app` | AI App | `ai-app.html` |
| `04-icons` | Icons | `icons.html` |
| `05-ui_kit` | UI Kit | `ui-kit.html` |

규칙
1. `^\d+[-_]` 접두사는 정렬 전용, 라벨에서 제거
2. `_`, `-`, 공백을 구분자로 단어 분리
3. 단어 길이 ≤ 2 또는 숫자 포함 → 전체 대문자 (`3d`→`3D`, `ai`→`AI`)
4. 그 외 → 첫 글자만 대문자 (`dashboard`→`Dashboard`)
5. 한글 단어는 그대로 (대소문자 변환 안 함)

라벨이 어색하면 폴더명을 영어로 다시 짓는 것이 가장 확실합니다.

## 한글 폴더/파일명 자동 정규화

macOS Finder는 한글을 NFD(자소 분리, `ㅂ+ㅜ+ㅅ+ㅏ+ㄴ`)로 저장하고, Git·Linux·웹 서버는 NFC(완성형, `부산`)로 처리합니다. 이 불일치 때문에 macOS에서 만든 한글 폴더가 배포 후 깨지는 일이 자주 있습니다.

빌드 스크립트는 모든 폴더·파일명을 NFC로 자동 정규화합니다. macOS에서 그대로 폴더를 만들어도 OK.

## 카테고리별 표시 방식

| 카테고리 | view | 데이터 소스 |
|---|---|---|
| Dashboard | grid (6/4/2 컬럼) | 폴더 안 이미지 자동 스캔 |
| 3D | grid | 폴더 안 이미지 자동 스캔 |
| AI App | list | 폴더 안 `items.json` (이미지 무시) |
| About | 좌·우 두 열 | 정적 (`about.html` 직접 편집) |

빈 폴더는 빈 그리드 + empty state로 표시됩니다.

## items.json 형식 (list view)
```json
[
  {
    "name": "프로젝트 이름",
    "desc": "한두 줄 설명",
    "links": [
      { "label": "Live", "url": "https://example.com" },
      { "label": "Repo", "url": "https://github.com/..." }
    ]
  }
]
```

## 이미지 크기 권장

- 원본 그대로 올려도 동작합니다 (단순 정적 서빙).
- 1장 1MB 이하 권장. 페이지당 50장 넘으면 합계 50MB 도달 → 첫 로딩 느려짐.
- 추후 sharp/Pillow로 WebP 자동 변환 단계 추가 예정.
