/* ============================================
   Drawer — main.js
   1. manifest.json 로드 → 메뉴/콘텐츠 동적 렌더
   2. 모바일 메뉴 토글
   3. Hero 그라데이션 hover 인터랙션 (index 전용)
   4. AI App 아코디언 토글
   5. 그리드 이미지 우클릭/드래그 방지 (보안 의도)
   ============================================ */

(async function () {
  let manifest;
  try {
    const res = await fetch('manifest.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    manifest = await res.json();
  } catch (err) {
    console.warn('manifest.json 로드 실패:', err);
    showEmpty('manifest.json이 없습니다. 빌드 스크립트를 먼저 실행하세요: python3 build/build.py');
    return;
  }

  const page = (document.body.dataset.page || '').toLowerCase();

  renderMenu(manifest, page);
  renderContent(manifest, page);
  updateMeta(manifest, page);
})();


/* ---------- 메뉴 ---------- */

function renderMenu(manifest, currentPage) {
  const header = document.getElementById('headerNav');
  const mobile = document.getElementById('mobileMenu');

  const items = manifest.categories.map(c => {
    const slug = c.url.replace(/\.html$/, '');
    return { label: c.label, url: c.url, active: slug === currentPage };
  });
  items.push({ label: 'About', url: 'about.html', active: currentPage === 'about' });

  if (header) {
    header.innerHTML = items.map(i =>
      `<a href="${i.url}"${i.active ? ' class="active"' : ''}>${escapeHtml(i.label)}</a>`
    ).join('');
  }
  if (mobile) {
    const homeActive = currentPage === 'index' ? ' class="active"' : '';
    mobile.innerHTML =
      `<a href="index.html"${homeActive}>Home</a>` +
      items.map(i =>
        `<a href="${i.url}"${i.active ? ' class="active"' : ''}>${escapeHtml(i.label)}</a>`
      ).join('');
  }
}


/* ---------- 콘텐츠 ---------- */

function renderContent(manifest, page) {
  const gallery = document.getElementById('gallery');
  const list = document.getElementById('list');
  const emptyEl = document.getElementById('emptyState');

  if (page === 'about') return;

  if (page === 'index') {
    const items = manifest.categories
      .filter(c => c.view === 'grid')
      .flatMap(c => c.items.map(rel => ({
        src: `img/${c.id}/${rel}`,
        alt: rel,
      })));
    if (items.length === 0) {
      hide(gallery);
      showEmpty('이미지가 없습니다.', emptyEl);
    } else {
      renderGrid(gallery, items);
    }
    return;
  }

  const cat = findCategory(manifest, page);
  if (!cat) {
    hide(gallery); hide(list);
    showEmpty(`'${page}' 카테고리를 찾을 수 없습니다.`, emptyEl);
    return;
  }

  if (cat.view === 'list') {
    hide(gallery);
    renderList(list, cat.items, cat.id);
    if (cat.items.length === 0) showEmpty('항목이 없습니다.', emptyEl);
  } else {
    hide(list);
    const items = cat.items.map(rel => ({
      src: `img/${cat.id}/${rel}`,
      alt: rel,
    }));
    if (items.length === 0) {
      hide(gallery);
      showEmpty('이미지가 없습니다. img 폴더에 추가하세요.', emptyEl);
    } else {
      renderGrid(gallery, items);
    }
  }
}

function findCategory(manifest, page) {
  return manifest.categories.find(c => c.url.replace(/\.html$/, '') === page);
}


/* ---------- 메타 ---------- */

function updateMeta(manifest, page) {
  const metaEl = document.querySelector('.hero-meta, .page-meta');
  if (!metaEl) return;
  if (page === 'index') {
    metaEl.textContent = `${manifest.totalItems} items`;
  } else if (page === 'about') {
    return;
  } else {
    const cat = findCategory(manifest, page);
    if (cat) {
      const count = cat.items.length;
      metaEl.textContent = `${count} ${cat.view === 'list' ? 'projects' : 'items'}`;
    }
  }
}


/* ---------- 렌더 헬퍼 ---------- */

/* Grid view (Dashboard, 3D, index) — <a> 대신 <div>로 렌더해서 클릭 비활성 */
function renderGrid(container, items) {
  if (!container) return;
  container.hidden = false;
  container.innerHTML = items.map(item => `
    <div class="thumb" role="img" aria-label="${escapeAttr(item.alt)}">
      <img src="${escapeAttr(item.src)}" alt="${escapeAttr(item.alt)}" loading="lazy" draggable="false">
    </div>
  `).join('');
}

/* List view (AI App) — 아코디언 */
function renderList(container, items, categoryId) {
  if (!container) return;
  container.hidden = false;
  container.innerHTML = items.map((item, i) => {
    const thumbSrc = item.thumb ? `img/${categoryId}/${item.thumb}` : null;
    const thumbHtml = thumbSrc
      ? `<div class="list-thumb">
           <img src="${escapeAttr(thumbSrc)}" alt="${escapeAttr(item.name || '')}" loading="lazy" draggable="false">
         </div>`
      : `<div class="list-thumb-placeholder" aria-hidden="true"></div>`;

    const longDesc = (item.longDesc || '').trim();
    const fullImage = thumbSrc
      ? `<img class="list-image-full" src="${escapeAttr(thumbSrc)}" alt="${escapeAttr(item.name || '')}" loading="lazy" draggable="false">`
      : '';
    const longDescHtml = longDesc
      ? `<p class="list-long-desc">${escapeHtml(longDesc)}</p>`
      : '';
    const actionsHtml = (item.links && item.links.length > 0)
      ? `<div class="list-actions">
           ${item.links.map(l => `<a href="${escapeAttr(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.label)}</a>`).join('')}
         </div>`
      : '';

    const panelId = `panel-${i}`;
    return `
      <article class="list-item" data-index="${i}">
        <button class="list-head" type="button" aria-expanded="false" aria-controls="${panelId}">
          ${thumbHtml}
          <div class="list-body">
            <h2 class="list-name">${escapeHtml(item.name || '')}</h2>
            <p class="list-desc">${escapeHtml(item.desc || '')}</p>
          </div>
          <span class="list-toggle" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 6L8 11L13 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
        <div class="list-panel" id="${panelId}" role="region">
          <div class="list-panel-inner">
            ${fullImage}
            ${longDescHtml}
            ${actionsHtml}
          </div>
        </div>
      </article>
    `;
  }).join('');

  // 아코디언 토글 바인딩
  container.querySelectorAll('.list-head').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.list-item');
      const expanded = item.classList.toggle('expanded');
      btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
  });
}

function showEmpty(message, el) {
  el = el || document.getElementById('emptyState');
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
}
function hide(el) { if (el) el.hidden = true; }
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function escapeAttr(s) { return escapeHtml(s); }


/* ============================================
   Mobile menu toggle
   ============================================ */
(function () {
  const btn = document.getElementById('menuBtn');
  const menu = document.getElementById('mobileMenu');
  if (!btn || !menu) return;
  btn.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.textContent = open ? '×' : '☰';
    btn.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth > 767 && menu.classList.contains('open')) {
      menu.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
      btn.textContent = '☰';
      btn.setAttribute('aria-label', '메뉴 열기');
    }
  });
})();


/* ============================================
   Hero gradient hover (index 전용)
   ============================================ */
(function () {
  const hero = document.querySelector('.hero');
  if (!hero) return;
  const mainPalettes = [
    ['#6B82E8', '#A78BFA', '#F0ABFC'],
    ['#FB7185', '#FBA374', '#FCD34D'],
    ['#34D399', '#5EEAD4', '#7DD3FC'],
    ['#C084FC', '#E879F9', '#F0ABFC'],
    ['#60A5FA', '#22D3EE', '#A7F3D0'],
    ['#F472B6', '#C084FC', '#818CF8'],
    ['#A5B4FC', '#C7D2FE', '#DDD6FE'],
    ['#FDA4AF', '#FCD34D', '#86EFAC'],
  ];
  const accents = [
    '#C5DAA0', '#A6D7E0', '#F5C5B0', '#FED7AA',
    '#C8B5E5', '#D5E0A0', '#F5C0A8', '#A0D5B8',
    '#E0C0E5', '#F0E5A0', '#B0D5E0', '#E5B5C0',
  ];
  let lastMain = -1, lastAcc = -1;
  hero.addEventListener('mouseenter', () => {
    let i, j;
    do { i = Math.floor(Math.random() * mainPalettes.length); } while (i === lastMain);
    lastMain = i;
    do { j = Math.floor(Math.random() * accents.length); } while (j === lastAcc);
    lastAcc = j;
    const [c1, c2, c3] = mainPalettes[i];
    hero.style.setProperty('--grad-c1', c1);
    hero.style.setProperty('--grad-c2', c2);
    hero.style.setProperty('--grad-c3', c3);
    hero.style.setProperty('--grad-accent', accents[j]);
  });
})();


/* ============================================
   이미지 보호 (보안 의도, 결정적이지는 않음)
   - 우클릭 컨텍스트 메뉴 차단
   - 드래그 차단
   - DevTools로 우회는 막을 수 없음 → 워터마크 권장
   ============================================ */
(function () {
  document.addEventListener('contextmenu', (e) => {
    if (e.target && e.target.tagName === 'IMG') {
      e.preventDefault();
    }
  });
  document.addEventListener('dragstart', (e) => {
    if (e.target && e.target.tagName === 'IMG') {
      e.preventDefault();
    }
  });
})();
