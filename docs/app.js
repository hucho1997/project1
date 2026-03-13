// ─── 상수 ───
const TYPE_LIST = [
    { id: 'normal', ko: '노말' }, { id: 'fire', ko: '불꽃' },
    { id: 'water', ko: '물' }, { id: 'electric', ko: '전기' },
    { id: 'grass', ko: '풀' }, { id: 'ice', ko: '얼음' },
    { id: 'fighting', ko: '격투' }, { id: 'poison', ko: '독' },
    { id: 'ground', ko: '땅' }, { id: 'flying', ko: '비행' },
    { id: 'psychic', ko: '에스퍼' }, { id: 'bug', ko: '벌레' },
    { id: 'rock', ko: '바위' }, { id: 'ghost', ko: '고스트' },
    { id: 'dragon', ko: '드래곤' }, { id: 'dark', ko: '악' },
    { id: 'steel', ko: '강철' }, { id: 'fairy', ko: '페어리' },
];

const TYPE_KO = {};
TYPE_LIST.forEach(t => TYPE_KO[t.id] = t.ko);

const STAT_LABELS = {
    hp: 'HP', attack: '공격', defense: '방어',
    'sp-attack': '특공', 'sp-defense': '특방', speed: '스피드',
};

const EV_STATS = [
    { id: 'hp', ko: 'HP' }, { id: 'attack', ko: '공격' },
    { id: 'defense', ko: '방어' }, { id: 'sp-attack', ko: '특공' },
    { id: 'sp-defense', ko: '특방' }, { id: 'speed', ko: '스피드' },
];

const METHOD_KO = {
    'walk': '걷기', 'surf': '파도타기', 'old-rod': '낡은낚싯대',
    'good-rod': '좋은낚싯대', 'super-rod': '대단한낚싯대',
    'rock-smash': '바위깨기', 'headbutt': '박치기', 'gift': '선물',
    'gift-egg': '알', 'only-one': '고정심볼', 'dark-grass': '짙은풀숲',
    'grass-spots': '흔들리는풀숲', 'cave-spots': '흔들리는동굴',
    'roaming-grass': '배회(풀숲)', 'roaming-water': '배회(수상)',
    'npc-trade': 'NPC교환', 'overworld': '심볼인카운터',
    'seaweed': '해초', 'yellow-flowers': '노란꽃밭',
    'purple-flowers': '보라꽃밭', 'red-flowers': '빨간꽃밭',
    'horde': '무리배틀', 'sos-encounter': 'SOS배틀',
};

// ─── DOM ───
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const grid = $('#pokemonGrid');
const btnMenu = $('#btnMenu');
const sideMenu = $('#sideMenu');
const menuOverlay = $('#menuOverlay');
const btnSearch = $('#btnSearch');
const filterPanel = $('#filterPanel');
const filterOverlay = $('#filterOverlay');
const filterApply = $('#filterApply');
const filterResetAll = $('#filterResetAll');
const filterNameInput = $('#filterNameInput');
const genChips = $('#genChips');
const typeChips = $('#typeChips');
const evChips = $('#evChips');
const viewGrid = $('#viewGrid');
const viewList = $('#viewList');
const detailOverlay = $('#detailOverlay');
const detailPanel = $('#detailPanel');

// ─── 데이터 저장소 ───
let allPokemon = [];
let filteredPokemon = [];
let evolutionChains = {};
let encounterData = {};
let movesData = {};

// ─── 상태 ───
let currentView = 'grid';
let filters = {
    name: '',
    gens: new Set([1, 2, 3, 4, 5, 6, 7, 8, 9]),
    types: new Set(),
    ev: new Set(),
    stats: {},
};

// ─── JSON 로드 ───
async function loadJSON(path) {
    const res = await fetch(path);
    return res.json();
}

async function init() {
    // 목록 데이터 (필수, 먼저 로드)
    allPokemon = await loadJSON('data/pokemon_list.json');
    filteredPokemon = [...allPokemon];
    renderGrid();

    // 나머지 데이터 (백그라운드 로드)
    const [evo, enc, mov] = await Promise.all([
        loadJSON('data/evolution_chains.json'),
        loadJSON('data/encounters.json'),
        loadJSON('data/moves.json'),
    ]);
    evolutionChains = evo;
    encounterData = enc;
    movesData = mov;
}

// ─── 필터 패널 열기/닫기 ───
function openFilterPanel() {
    filterPanel.classList.remove('hidden');
    filterPanel.classList.add('open');
    filterOverlay.classList.remove('hidden');
    document.body.classList.add('no-scroll');
}

function closeFilterPanel() {
    filterPanel.classList.remove('open');
    document.body.classList.remove('no-scroll');
    setTimeout(() => {
        filterPanel.classList.add('hidden');
        filterOverlay.classList.add('hidden');
    }, 250);
}

btnSearch.onclick = openFilterPanel;
filterOverlay.onclick = closeFilterPanel;
$('#filterClose').onclick = closeFilterPanel;

// 오버레이 열린 상태에서 배경 터치 스크롤 방지
document.addEventListener('touchmove', (e) => {
    if (!document.body.classList.contains('no-scroll')) return;
    // 스크롤 가능한 패널 내부 터치는 허용
    const scrollable = e.target.closest('.filter-scroll, .detail-panel, .side-menu');
    if (!scrollable) {
        e.preventDefault();
    }
}, { passive: false });

// ─── 필터 적용 ───
filterApply.onclick = () => {
    applyFilters();
    closeFilterPanel();
};

function applyFilters() {
    filters.name = filterNameInput.value.trim().toLowerCase();

    // 종족값 필터 수집
    filters.stats = {};
    $$('.stat-input').forEach(input => {
        const stat = input.dataset.stat;
        const bound = input.dataset.bound;
        const val = input.value.trim();
        if (val) {
            if (!filters.stats[stat]) filters.stats[stat] = {};
            filters.stats[stat][bound] = parseInt(val);
        }
    });

    filteredPokemon = allPokemon.filter(p => {
        // 이름/번호
        if (filters.name) {
            const match = p.name.includes(filters.name)
                || p.nameEn.toLowerCase().includes(filters.name)
                || String(p.id).includes(filters.name);
            if (!match) return false;
        }

        // 세대
        if (!filters.gens.has(p.gen)) return false;

        // 타입 (AND: 선택한 타입을 모두 가진 포켓몬)
        if (filters.types.size > 0) {
            for (const t of filters.types) {
                if (!p.types.includes(t)) return false;
            }
        }

        // 노력치 (완전 일치)
        if (filters.ev.size > 0) {
            const pEvStats = new Set();
            if (p.ev) {
                Object.keys(p.ev).forEach(stat => pEvStats.add(stat));
            }
            if (pEvStats.size !== filters.ev.size) return false;
            for (const s of filters.ev) {
                if (!pEvStats.has(s)) return false;
            }
        }

        // 종족값 범위
        for (const [stat, bounds] of Object.entries(filters.stats)) {
            let val;
            if (stat === 'total') {
                val = Object.values(p.stats).reduce((a, b) => a + b, 0);
            } else {
                val = p.stats[stat];
            }
            if (val === undefined) return false;
            if (bounds.min !== undefined && val < bounds.min) return false;
            if (bounds.max !== undefined && val > bounds.max) return false;
        }

        return true;
    });

    renderGrid();
}

// ─── 전체 초기화 ───
filterResetAll.onclick = () => {
    filterNameInput.value = '';
    filters.name = '';
    filters.gens = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9]);
    filters.types = new Set();
    filters.ev = new Set();
    filters.stats = {};

    $$('.chip[data-gen]').forEach(c => c.classList.add('active'));
    $$('.chip-type').forEach(c => c.classList.remove('active'));
    $$('.chip[data-ev]').forEach(c => c.classList.remove('active'));
    $$('.stat-input').forEach(input => input.value = '');

    filteredPokemon = [...allPokemon];
    renderGrid();
};

// ─── 개별 항목 초기화 ───
$$('.filter-reset').forEach(btn => {
    btn.onclick = (e) => {
        e.stopPropagation();
        const group = btn.dataset.group;
        switch (group) {
            case 'gen':
                filters.gens = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9]);
                $$('.chip[data-gen]').forEach(c => c.classList.add('active'));
                break;
            case 'type':
                filters.types = new Set();
                $$('.chip-type').forEach(c => c.classList.remove('active'));
                break;
            case 'dex':
                $('#dexSelect').value = 'national';
                break;
            case 'egggroup':
                $$('.chip[data-egg]').forEach(c => c.classList.remove('active'));
                break;
            case 'ability':
                $('#abilityInput').value = '';
                break;
            case 'stats':
                $$('.stat-input').forEach(input => input.value = '');
                filters.stats = {};
                break;
            case 'ev':
                filters.ev = new Set();
                $$('.chip[data-ev]').forEach(c => c.classList.remove('active'));
                break;
        }
    };
});

// ─── 아코디언 토글 ───
$$('.filter-title-text[data-toggle]').forEach(title => {
    title.onclick = () => {
        const group = title.closest('.filter-group');
        group.classList.toggle('open');
    };
});

// ─── 세대 칩 생성 (9세대까지) ───
for (let g = 1; g <= 9; g++) {
    const chip = document.createElement('button');
    chip.className = 'chip active';
    chip.dataset.gen = g;
    chip.textContent = `${g}세대`;
    chip.onclick = () => {
        chip.classList.toggle('active');
        if (chip.classList.contains('active')) {
            filters.gens.add(g);
        } else {
            filters.gens.delete(g);
        }
    };
    genChips.appendChild(chip);
}

// ─── 타입 칩 생성 ───
TYPE_LIST.forEach(t => {
    const chip = document.createElement('button');
    chip.className = 'chip chip-type';
    chip.dataset.type = t.id;
    chip.textContent = t.ko;
    chip.onclick = () => {
        chip.classList.toggle('active');
        if (chip.classList.contains('active')) {
            filters.types.add(t.id);
        } else {
            filters.types.delete(t.id);
        }
    };
    typeChips.appendChild(chip);
});

// ─── 노력치 칩 생성 ───
EV_STATS.forEach(s => {
    const chip = document.createElement('button');
    chip.className = 'chip';
    chip.dataset.ev = s.id;
    chip.textContent = s.ko;
    chip.onclick = () => {
        chip.classList.toggle('active');
        if (chip.classList.contains('active')) {
            filters.ev.add(s.id);
        } else {
            filters.ev.delete(s.id);
        }
    };
    evChips.appendChild(chip);
});

// ─── 그리드 렌더링 ───
function renderGrid() {
    grid.innerHTML = '';
    grid.className = currentView === 'list' ? 'pokemon-grid list-view' : 'pokemon-grid';

    filteredPokemon.forEach(p => {
        const card = document.createElement('div');
        card.className = 'pokemon-card';
        card.onclick = () => showDetail(p);

        if (currentView === 'grid') {
            card.innerHTML = `
                <div class="pokemon-img"></div>
                <span class="pokemon-num">#${String(p.id).padStart(4, '0')}</span>
                <span class="pokemon-name">${p.name}</span>
            `;
        } else {
            const typeBadges = p.types.map(t =>
                `<span class="type-badge type-${t}">${TYPE_KO[t] || t}</span>`
            ).join('');
            card.innerHTML = `
                <div class="pokemon-img"></div>
                <div class="pokemon-info">
                    <span class="pokemon-num">#${String(p.id).padStart(4, '0')}</span>
                    <span class="pokemon-name">${p.name}</span>
                </div>
                <div class="pokemon-types">${typeBadges}</div>
            `;
        }

        grid.appendChild(card);
    });
}

// ─── 진화 체인 찾기 ───
function findEvolutionChain(speciesId) {
    for (const [chainId, members] of Object.entries(evolutionChains)) {
        if (members.some(m => m.id === speciesId)) {
            return members;
        }
    }
    return null;
}

// ─── 진화 체인 HTML ───
function renderEvolutionChain(chain, currentId) {
    if (!chain || chain.length <= 1) {
        return '<div style="font-size:13px; color:var(--text-dim);">진화 없음</div>';
    }

    const base = chain.find(m => m.from === null);
    if (!base) return '';

    function getChildren(parentId) {
        return chain.filter(m => m.from === parentId);
    }

    function nameHtml(m) {
        const cls = m.id === currentId ? 'evo-name current' : 'evo-name';
        return `<span class="${cls}">${m.name}</span>`;
    }

    function withCondition(m) {
        let html = nameHtml(m);
        if (m.cond) {
            html = `<span class="evo-condition">${m.cond}</span><span class="evo-arrow">→</span>` + html;
        }
        return html;
    }

    const children = getChildren(base.id);
    let html = '<div class="evo-chain">';
    html += nameHtml(base);

    if (children.length === 1) {
        let curr = children[0];
        while (curr) {
            html += `<span class="evo-arrow">→</span>`;
            if (curr.cond) html += `<span class="evo-condition">${curr.cond}</span>`;
            html += nameHtml(curr);
            const next = getChildren(curr.id);
            curr = next.length > 0 ? next[0] : null;
        }
    } else if (children.length > 1) {
        html += `<span class="evo-arrow">→</span>`;
        html += children.map(c => {
            let s = '';
            if (c.cond) s += `<span class="evo-condition">${c.cond}</span>`;
            s += nameHtml(c);
            return s;
        }).join(' / ');
    }

    html += '</div>';
    return html;
}

// ─── 상세 패널 ───
function showDetail(p) {
    const typeBadges = p.types.map(t =>
        `<span class="type-badge type-${t}">${TYPE_KO[t] || t}</span>`
    ).join('');

    const statOrder = ['hp', 'attack', 'defense', 'sp-attack', 'sp-defense', 'speed'];
    const total = statOrder.reduce((sum, s) => sum + (p.stats[s] || 0), 0);

    const statRows = statOrder.map(s => {
        const val = p.stats[s] || 0;
        const pct = Math.min(val / 160 * 100, 100);
        const color = val >= 100 ? '#63bc5a' : val >= 60 ? '#f4d23c' : '#e53935';
        return `
            <div class="stat-row">
                <span class="stat-label">${STAT_LABELS[s]}</span>
                <span class="stat-value">${val}</span>
                <div class="stat-bar-bg">
                    <div class="stat-bar" style="width:${pct}%; background:${color}"></div>
                </div>
            </div>
        `;
    }).join('');

    // 노력치
    const evParts = [];
    if (p.ev) {
        Object.entries(p.ev).forEach(([stat, val]) => {
            evParts.push(`${STAT_LABELS[stat]} <span class="ev-value">+${val}</span>`);
        });
    }
    const evDisplay = evParts.length > 0 ? evParts.join('  ') : '없음';

    // 특성
    const abilityStr = p.abilities.join(', ')
        + (p.hiddenAbility ? ` <span style="color:var(--text-dim);">(숨겨진: ${p.hiddenAbility})</span>` : '');

    // 진화
    const chain = findEvolutionChain(p.id);
    const evoHtml = renderEvolutionChain(chain, p.id);

    // 출현 위치
    const enc = encounterData[String(p.id)];
    let encHtml = '';
    if (enc) {
        for (const [ver, locs] of Object.entries(enc)) {
            encHtml += `<div class="encounter-version">[${ver}]</div>`;
            locs.forEach(l => {
                const methodKo = METHOD_KO[l.method] || l.method;
                encHtml += `<div class="encounter-row">${l.loc} <span class="encounter-method">(${methodKo})</span></div>`;
            });
        }
    } else {
        encHtml = '<div style="font-size:13px; color:var(--text-dim);">출현 데이터 없음</div>';
    }

    // 기술 (첫 번째 가용 version_group)
    const movesForPokemon = movesData[String(p.id)];
    let movesHtml = '';
    if (movesForPokemon) {
        const vgKeys = Object.keys(movesForPokemon).sort((a, b) => parseInt(b) - parseInt(a));
        const latestVg = vgKeys[0];
        const vgMoves = movesForPokemon[latestVg];

        if (vgMoves.lv) {
            vgMoves.lv.forEach(([lv, name]) => {
                const lvStr = lv > 0 ? `Lv.${lv}` : '기본';
                movesHtml += `<div class="move-row"><span class="move-level">${lvStr}</span><span class="move-name">${name}</span></div>`;
            });
        }
    }
    if (!movesHtml) {
        movesHtml = '<div style="font-size:13px; color:var(--text-dim);">기술 데이터 없음</div>';
    }

    detailPanel.innerHTML = `
        <div class="detail-header">
            <div class="detail-header-info">
                <span class="detail-header-num">#${String(p.id).padStart(4, '0')}</span>${p.name}
            </div>
            <button class="detail-close-btn" id="detailClose">&times;</button>
        </div>
        <div class="detail-body">
            <div class="detail-name-en">${p.nameEn}</div>
            <div class="detail-types">${typeBadges}</div>

            <div class="detail-section">
                <div class="detail-section-title">특성</div>
                <div style="font-size:13px;">${abilityStr}</div>
            </div>

            <div class="detail-section">
                <div class="detail-section-title">종족값 (합계: ${total})</div>
                ${statRows}
            </div>

            <div class="detail-section">
                <div class="detail-section-title">격파 시 노력치</div>
                <div class="ev-row">${evDisplay}</div>
            </div>

            <div class="detail-section">
                <div class="detail-section-title">진화</div>
                ${evoHtml}
            </div>

            <div class="detail-section">
                <div class="detail-section-title">포획 위치</div>
                ${encHtml}
            </div>

            <div class="detail-section">
                <div class="detail-section-title">레벨업 기술</div>
                ${movesHtml}
            </div>
        </div>
    `;

    detailOverlay.classList.remove('hidden');
    detailPanel.scrollTop = 0;
    document.body.classList.add('no-scroll');

    const closeDetail = () => {
        detailOverlay.classList.add('hidden');
        document.body.classList.remove('no-scroll');
    };
    $('#detailClose').onclick = closeDetail;
    detailOverlay.onclick = (e) => {
        if (e.target === detailOverlay) closeDetail();
    };
}

// ─── 사이드 메뉴 ───
btnMenu.onclick = () => {
    sideMenu.classList.add('open');
    menuOverlay.classList.remove('hidden');
    document.body.classList.add('no-scroll');
};
menuOverlay.onclick = () => {
    sideMenu.classList.remove('open');
    menuOverlay.classList.add('hidden');
    document.body.classList.remove('no-scroll');
};

// ─── 보기 전환 ───
viewGrid.onclick = () => {
    currentView = 'grid';
    viewGrid.classList.add('active');
    viewList.classList.remove('active');
    renderGrid();
};
viewList.onclick = () => {
    currentView = 'list';
    viewList.classList.add('active');
    viewGrid.classList.remove('active');
    renderGrid();
};

// ─── 초기화 ───
init();
