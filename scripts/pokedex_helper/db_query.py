# -*- coding: utf-8 -*-
"""도감 완성 도우미 - DB 쿼리 로직 (출력과 분리)"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'pokemon.db')
LANG_KO = 3
LANG_EN = 9


def get_conn():
    return sqlite3.connect(DB_PATH)


# ─── 세대/버전/도감 메타 ───

GENERATION_DATA = {
    1: {
        'name': '1세대',
        'regions': {
            'kanto': {
                'name': '관동',
                'versions': [
                    {'vg': 1, 'versions': [('red', '레드'), ('blue', '블루')]},
                    {'vg': 2, 'versions': [('yellow', '옐로')]},
                ],
                'regional_dex': 2,  # kanto dex
            }
        },
        'national_dex_size': 151,
    },
    2: {
        'name': '2세대',
        'regions': {
            'johto': {
                'name': '성도',
                'versions': [
                    {'vg': 3, 'versions': [('gold', '골드'), ('silver', '실버')]},
                    {'vg': 4, 'versions': [('crystal', '크리스탈')]},
                ],
                'regional_dex': 3,  # original-johto
            }
        },
        'national_dex_size': 251,
    },
    3: {
        'name': '3세대',
        'regions': {
            'hoenn': {
                'name': '호연',
                'versions': [
                    {'vg': 5, 'versions': [('ruby', '루비'), ('sapphire', '사파이어')]},
                    {'vg': 6, 'versions': [('emerald', '에메랄드')]},
                ],
                'regional_dex': 4,  # hoenn
            },
            'kanto_frlg': {
                'name': '관동 (FRLG)',
                'versions': [
                    {'vg': 7, 'versions': [('firered', '파이어레드'), ('leafgreen', '리프그린')]},
                ],
                'regional_dex': 2,  # kanto
            }
        },
        'national_dex_size': 386,
    },
    4: {
        'name': '4세대',
        'regions': {
            'sinnoh': {
                'name': '신오',
                'versions': [
                    {'vg': 8, 'versions': [('diamond', '다이아몬드'), ('pearl', '펄')]},
                    {'vg': 9, 'versions': [('platinum', '플라티나')]},
                ],
                'regional_dex': 6,  # extended-sinnoh (Pt 기준)
            },
            'johto_hgss': {
                'name': '성도 (HGSS)',
                'versions': [
                    {'vg': 10, 'versions': [('heartgold', '하트골드'), ('soulsilver', '소울실버')]},
                ],
                'regional_dex': 7,  # updated-johto
            }
        },
        'national_dex_size': 493,
    },
    5: {
        'name': '5세대',
        'regions': {
            'unova': {
                'name': '하나',
                'versions': [
                    {'vg': 11, 'versions': [('black', '블랙'), ('white', '화이트')]},
                    {'vg': 14, 'versions': [('black-2', '블랙2'), ('white-2', '화이트2')]},
                ],
                'regional_dex': 9,  # updated-unova (BW2 기준)
            }
        },
        'national_dex_size': 649,
    },
    6: {
        'name': '6세대',
        'regions': {
            'kalos': {
                'name': '칼로스',
                'versions': [
                    {'vg': 15, 'versions': [('x', 'X'), ('y', 'Y')]},
                ],
                'regional_dex': 12,  # kalos-central (대표)
            },
            'hoenn_oras': {
                'name': '호연 (ORAS)',
                'versions': [
                    {'vg': 16, 'versions': [('omega-ruby', '오메가루비'), ('alpha-sapphire', '알파사파이어')]},
                ],
                'regional_dex': 15,  # updated-hoenn
            }
        },
        'national_dex_size': 721,
    },
    7: {
        'name': '7세대',
        'regions': {
            'alola': {
                'name': '알로라',
                'versions': [
                    {'vg': 17, 'versions': [('sun', '썬'), ('moon', '문')]},
                    {'vg': 18, 'versions': [('ultra-sun', '울트라썬'), ('ultra-moon', '울트라문')]},
                ],
                'regional_dex': 21,  # updated-alola (USUM 기준)
            }
        },
        'national_dex_size': 809,
    },
}


def get_dex_pokemon(dex_id):
    """도감 ID로 해당 도감에 등록된 포켓몬 species_id 목록 반환"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT species_id, pokedex_number
        FROM pokemon_dex_numbers
        WHERE pokedex_id = ?
        ORDER BY CAST(pokedex_number AS INTEGER)
    ''', (dex_id,))
    result = cur.fetchall()
    conn.close()
    return [(int(r[0]), int(r[1])) for r in result]


def get_national_dex_pokemon(max_id):
    """전국도감 기준, max_id까지의 포켓몬 목록"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT species_id, pokedex_number
        FROM pokemon_dex_numbers
        WHERE pokedex_id = 1 AND CAST(species_id AS INTEGER) <= ?
        ORDER BY CAST(pokedex_number AS INTEGER)
    ''', (max_id,))
    result = cur.fetchall()
    conn.close()
    return [(int(r[0]), int(r[1])) for r in result]


# ─── 포켓몬 상세 정보 ───

def get_pokemon_basic(species_id):
    """기본 정보: 이름(한/영), 타입, 특성"""
    conn = get_conn()
    cur = conn.cursor()

    # 이름
    cur.execute('''
        SELECT name FROM pokemon_species_names
        WHERE pokemon_species_id = ? AND local_language_id = ?
    ''', (species_id, LANG_KO))
    name_ko = cur.fetchone()
    name_ko = name_ko[0] if name_ko else '?'

    cur.execute('''
        SELECT name FROM pokemon_species_names
        WHERE pokemon_species_id = ? AND local_language_id = ?
    ''', (species_id, LANG_EN))
    name_en = cur.fetchone()
    name_en = name_en[0] if name_en else '?'

    # pokemon_id (species_id와 다를 수 있음, 기본 폼 사용)
    cur.execute('''
        SELECT id FROM pokemon WHERE species_id = ?
        ORDER BY CAST(id AS INTEGER) LIMIT 1
    ''', (species_id,))
    pokemon_id = int(cur.fetchone()[0])

    # 타입
    cur.execute('''
        SELECT t.id, tn.name FROM pokemon_types pt
        JOIN types t ON pt.type_id = t.id
        JOIN type_names tn ON t.id = tn.type_id AND tn.local_language_id = ?
        WHERE pt.pokemon_id = ?
        ORDER BY CAST(pt.slot AS INTEGER)
    ''', (LANG_KO, pokemon_id))
    types = [(int(r[0]), r[1]) for r in cur.fetchall()]

    # 특성
    cur.execute('''
        SELECT a.id, an.name, pa.is_hidden FROM pokemon_abilities pa
        JOIN abilities a ON pa.ability_id = a.id
        JOIN ability_names an ON a.id = an.ability_id AND an.local_language_id = ?
        WHERE pa.pokemon_id = ?
        ORDER BY CAST(pa.slot AS INTEGER)
    ''', (LANG_KO, pokemon_id))
    abilities = [(int(r[0]), r[1], r[2] == '1') for r in cur.fetchall()]

    # 종족값
    cur.execute('''
        SELECT s.identifier, ps.base_stat FROM pokemon_stats ps
        JOIN stats s ON ps.stat_id = s.id
        WHERE ps.pokemon_id = ?
        ORDER BY CAST(s.id AS INTEGER)
    ''', (pokemon_id,))
    stats = {r[0]: int(r[1]) for r in cur.fetchall()}

    conn.close()
    return {
        'species_id': species_id,
        'pokemon_id': pokemon_id,
        'name_ko': name_ko,
        'name_en': name_en,
        'types': types,
        'abilities': abilities,
        'stats': stats,
    }


def get_evolution_chain(species_id):
    """진화 체인 정보 반환"""
    conn = get_conn()
    cur = conn.cursor()

    # chain_id 찾기
    cur.execute('SELECT evolution_chain_id FROM pokemon_species WHERE id = ?', (species_id,))
    chain_id = cur.fetchone()[0]

    # 체인에 속한 모든 포켓몬
    cur.execute('''
        SELECT ps.id, ps.evolves_from_species_id, ps.identifier,
               psn.name
        FROM pokemon_species ps
        LEFT JOIN pokemon_species_names psn
            ON ps.id = psn.pokemon_species_id AND psn.local_language_id = ?
        WHERE ps.evolution_chain_id = ?
        ORDER BY CAST(ps.id AS INTEGER)
    ''', (LANG_KO, chain_id))
    species_list = []
    for r in cur.fetchall():
        species_list.append({
            'id': int(r[0]),
            'evolves_from': int(r[1]) if r[1] else None,
            'identifier': r[2],
            'name_ko': r[3] or r[2],
        })

    # 진화 조건
    for sp in species_list:
        cur.execute('''
            SELECT evolution_trigger_id, minimum_level, trigger_item_id,
                   held_item_id, known_move_id, minimum_happiness,
                   time_of_day, trade_species_id
            FROM pokemon_evolution
            WHERE evolved_species_id = ?
        ''', (sp['id'],))
        evo = cur.fetchone()
        if evo:
            trigger_id = int(evo[0])
            condition = ''
            if trigger_id == 1:  # level-up
                if evo[1]:
                    condition = f'Lv.{evo[1]}'
                elif evo[5]:
                    condition = f'친밀도 {evo[5]}'
                    if evo[6]:
                        condition += f'+{evo[6]}'
                elif evo[4]:
                    # 기술 습득 상태
                    cur.execute('SELECT name FROM move_names WHERE move_id=? AND local_language_id=?',
                                (evo[4], LANG_KO))
                    move_name = cur.fetchone()
                    condition = f'{move_name[0]} 습득' if move_name else '특수조건'
                else:
                    condition = '레벨업'
            elif trigger_id == 2:  # trade
                condition = '통신교환'
                if evo[3]:
                    cur.execute('SELECT name FROM item_names WHERE item_id=? AND local_language_id=?',
                                (evo[3], LANG_KO))
                    item_name = cur.fetchone()
                    condition += f'({item_name[0]})' if item_name else ''
            elif trigger_id == 3:  # use-item
                if evo[2]:
                    cur.execute('SELECT name FROM item_names WHERE item_id=? AND local_language_id=?',
                                (evo[2], LANG_KO))
                    item_name = cur.fetchone()
                    condition = item_name[0] if item_name else '아이템'
                else:
                    condition = '아이템'
            elif trigger_id == 4:  # shed
                condition = '껍질(탈피)'
            else:
                condition = '특수조건'
            sp['evo_condition'] = condition
        else:
            sp['evo_condition'] = None

    conn.close()
    return species_list


def get_encounter_locations(species_id, version_ids):
    """버전별 포획 위치"""
    conn = get_conn()
    cur = conn.cursor()

    # species_id → pokemon_id
    cur.execute('SELECT id FROM pokemon WHERE species_id = ? ORDER BY CAST(id AS INTEGER) LIMIT 1',
                (species_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {}
    pokemon_id = int(row[0])

    results = {}
    for vid in version_ids:
        cur.execute('''
            SELECT DISTINCT
                COALESCE(ln_ko.name, ln_en.name, l.identifier),
                em.identifier
            FROM encounters e
            JOIN encounter_slots es ON e.encounter_slot_id = es.id
            JOIN encounter_methods em
                ON es.encounter_method_id = em.id
            JOIN location_areas la ON e.location_area_id = la.id
            JOIN locations l ON la.location_id = l.id
            LEFT JOIN location_names ln_ko
                ON l.id = ln_ko.location_id
                AND ln_ko.local_language_id = ?
            LEFT JOIN location_names ln_en
                ON l.id = ln_en.location_id
                AND ln_en.local_language_id = ?
            WHERE e.pokemon_id = ? AND e.version_id = ?
            ORDER BY 1
        ''', (str(LANG_KO), str(LANG_EN),
              str(pokemon_id), str(vid)))
        locations = cur.fetchall()
        if locations:
            # 버전 이름
            cur.execute('SELECT identifier FROM versions WHERE id = ?', (vid,))
            vname = cur.fetchone()[0]
            results[vname] = [(r[0], r[1]) for r in locations]

    conn.close()
    return results


METHOD_KO = {
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
}


def get_method_ko(method):
    return METHOD_KO.get(method, method)


def get_level_up_moves(species_id, version_group_id):
    """레벨업 습득 기술"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('SELECT id FROM pokemon WHERE species_id = ? ORDER BY CAST(id AS INTEGER) LIMIT 1',
                (species_id,))
    pokemon_id = int(cur.fetchone()[0])

    cur.execute('''
        SELECT CAST(pm.level AS INTEGER) as lv, mn.name, m.id
        FROM pokemon_moves pm
        JOIN moves m ON pm.move_id = m.id
        JOIN move_names mn ON m.id = mn.move_id AND mn.local_language_id = ?
        WHERE pm.pokemon_id = ? AND pm.version_group_id = ?
            AND pm.pokemon_move_method_id = 1
        ORDER BY CAST(pm.level AS INTEGER), mn.name
    ''', (LANG_KO, pokemon_id, version_group_id))
    moves = [(r[0], r[1]) for r in cur.fetchall()]
    conn.close()
    return moves


def get_machine_moves(species_id, version_group_id):
    """기술머신/비전머신 습득 기술"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('SELECT id FROM pokemon WHERE species_id = ? ORDER BY CAST(id AS INTEGER) LIMIT 1',
                (species_id,))
    pokemon_id = int(cur.fetchone()[0])

    cur.execute('''
        SELECT mn.name, m.id
        FROM pokemon_moves pm
        JOIN moves m ON pm.move_id = m.id
        JOIN move_names mn ON m.id = mn.move_id AND mn.local_language_id = ?
        WHERE pm.pokemon_id = ? AND pm.version_group_id = ?
            AND pm.pokemon_move_method_id = 4
        ORDER BY mn.name
    ''', (LANG_KO, pokemon_id, version_group_id))
    moves = [r[0] for r in cur.fetchall()]
    conn.close()
    return moves


def get_version_ids_for_vgroups(version_group_ids):
    """version_group_id 목록 → version_id 목록"""
    conn = get_conn()
    cur = conn.cursor()
    # DB의 모든 값이 TEXT이므로 문자열로 비교
    str_ids = [str(vg) for vg in version_group_ids]
    placeholders = ','.join('?' * len(str_ids))
    cur.execute(f'''
        SELECT id, identifier, version_group_id
        FROM versions WHERE version_group_id IN ({placeholders})
        ORDER BY CAST(id AS INTEGER)
    ''', str_ids)
    result = [(r[0], r[1], r[2]) for r in cur.fetchall()]
    conn.close()
    return result


def get_selected_version_ids(selected):
    """선택한 게임의 version_id만 반환 (version_group 전체가 아님)"""
    conn = get_conn()
    cur = conn.cursor()
    result = []
    for s in selected:
        cur.execute(
            'SELECT id FROM versions WHERE identifier = ?',
            (s['version_id'],))
        row = cur.fetchone()
        if row:
            result.append((row[0], s['version_id'], s['version_name']))
    conn.close()
    return result


def get_catchable_pokemon_set(version_ids):
    """선택한 버전들에서 야생 출현하는 pokemon_id 집합을 한번에 조회"""
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ','.join('?' * len(version_ids))
    cur.execute(f'''
        SELECT DISTINCT CAST(e.pokemon_id AS INTEGER)
        FROM encounters e
        WHERE e.version_id IN ({placeholders})
    ''', [str(v) for v in version_ids])
    result = {r[0] for r in cur.fetchall()}
    conn.close()
    return result


def get_exclusive_pokemon(version_ids_a, version_ids_b):
    """version_ids_a에만 출현하고 version_ids_b에는 없는 포켓몬"""
    conn = get_conn()
    cur = conn.cursor()

    ph_a = ','.join('?' * len(version_ids_a))
    ph_b = ','.join('?' * len(version_ids_b))

    cur.execute(f'''
        SELECT DISTINCT e.pokemon_id FROM encounters e
        WHERE e.version_id IN ({ph_a})
        AND e.pokemon_id NOT IN (
            SELECT DISTINCT e2.pokemon_id FROM encounters e2
            WHERE e2.version_id IN ({ph_b})
        )
        ORDER BY CAST(e.pokemon_id AS INTEGER)
    ''', version_ids_a + version_ids_b)

    result = [int(r[0]) for r in cur.fetchall()]
    conn.close()
    return result
