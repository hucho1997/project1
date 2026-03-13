# -*- coding: utf-8 -*-
"""DB → JSON 추출 스크립트 (웹 UI용)"""

import json
import os
import sys
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..', '..')
DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'pokemon.db')
OUT_DIR = os.path.join(SCRIPT_DIR, 'web', 'data')

LANG_KO = 3
LANG_EN = 9


def get_conn():
    return sqlite3.connect(DB_PATH)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def export_pokemon_list():
    """전체 포켓몬 목록 (필터용 기본 데이터)"""
    print('포켓몬 목록 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    # 모든 species
    cur.execute('''
        SELECT ps.id, ps.identifier, ps.generation_id, ps.evolution_chain_id,
               ps.gender_rate, ps.color_id, ps.shape_id, ps.habitat_id
        FROM pokemon_species ps
        ORDER BY CAST(ps.id AS INTEGER)
    ''')
    species_list = cur.fetchall()

    pokemon_all = []
    for sp in species_list:
        species_id = int(sp[0])
        gen = int(sp[2])

        # 이름 (한/영)
        cur.execute('SELECT name FROM pokemon_species_names WHERE pokemon_species_id=? AND local_language_id=?',
                     (species_id, LANG_KO))
        row = cur.fetchone()
        name_ko = row[0] if row else sp[1]

        cur.execute('SELECT name FROM pokemon_species_names WHERE pokemon_species_id=? AND local_language_id=?',
                     (species_id, LANG_EN))
        row = cur.fetchone()
        name_en = row[0] if row else sp[1]

        # pokemon_id (기본 폼)
        cur.execute('SELECT id FROM pokemon WHERE species_id=? ORDER BY CAST(id AS INTEGER) LIMIT 1',
                     (species_id,))
        row = cur.fetchone()
        if not row:
            continue
        pokemon_id = int(row[0])

        # 타입
        cur.execute('''
            SELECT t.identifier FROM pokemon_types pt
            JOIN types t ON pt.type_id = t.id
            WHERE pt.pokemon_id=?
            ORDER BY CAST(pt.slot AS INTEGER)
        ''', (pokemon_id,))
        types = [r[0] for r in cur.fetchall()]

        # 종족값
        cur.execute('''
            SELECT s.identifier, CAST(ps2.base_stat AS INTEGER), CAST(ps2.effort AS INTEGER)
            FROM pokemon_stats ps2
            JOIN stats s ON ps2.stat_id = s.id
            WHERE ps2.pokemon_id=?
            ORDER BY CAST(s.id AS INTEGER)
        ''', (pokemon_id,))
        stats = {}
        ev = {}
        for r in cur.fetchall():
            stat_key = r[0].replace('special-attack', 'sp-attack').replace('special-defense', 'sp-defense')
            stats[stat_key] = r[1]
            if r[2] > 0:
                ev[stat_key] = r[2]

        # 특성
        cur.execute('''
            SELECT an.name, pa.is_hidden FROM pokemon_abilities pa
            JOIN ability_names an ON pa.ability_id = an.ability_id AND an.local_language_id=?
            WHERE pa.pokemon_id=?
            ORDER BY CAST(pa.slot AS INTEGER)
        ''', (LANG_KO, pokemon_id))
        abilities = []
        hidden_ability = None
        for r in cur.fetchall():
            if r[1] == '1':
                hidden_ability = r[0]
            else:
                abilities.append(r[0])

        # 알그룹
        cur.execute('''
            SELECT egp.name FROM pokemon_egg_groups peg
            JOIN egg_group_prose egp ON peg.egg_group_id = egp.egg_group_id
                AND egp.local_language_id=?
            WHERE peg.species_id=?
        ''', (LANG_EN, species_id))
        egg_groups = [r[0] for r in cur.fetchall()]

        entry = {
            'id': species_id,
            'pid': pokemon_id,
            'name': name_ko,
            'nameEn': name_en,
            'gen': gen,
            'types': types,
            'stats': stats,
            'abilities': abilities,
        }
        if hidden_ability:
            entry['hiddenAbility'] = hidden_ability
        if ev:
            entry['ev'] = ev
        if egg_groups:
            entry['eggGroups'] = egg_groups

        pokemon_all.append(entry)

    conn.close()
    save_json(os.path.join(OUT_DIR, 'pokemon_list.json'), pokemon_all)
    print(f'  → {len(pokemon_all)}마리 저장 완료')
    return pokemon_all


def export_evolution_chains():
    """진화 체인 데이터"""
    print('진화 체인 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    # 모든 체인 ID
    cur.execute('SELECT id FROM evolution_chains ORDER BY CAST(id AS INTEGER)')
    chain_ids = [int(r[0]) for r in cur.fetchall()]

    chains = {}
    for chain_id in chain_ids:
        cur.execute('''
            SELECT ps.id, ps.evolves_from_species_id, ps.identifier,
                   psn.name
            FROM pokemon_species ps
            LEFT JOIN pokemon_species_names psn
                ON ps.id = psn.pokemon_species_id AND psn.local_language_id=?
            WHERE ps.evolution_chain_id=?
            ORDER BY CAST(ps.id AS INTEGER)
        ''', (LANG_KO, chain_id))

        members = []
        for r in cur.fetchall():
            sid = int(r[0])
            member = {
                'id': sid,
                'from': int(r[1]) if r[1] else None,
                'name': r[3] or r[2],
            }

            # 진화 조건
            cur.execute('''
                SELECT evolution_trigger_id, minimum_level, trigger_item_id,
                       held_item_id, known_move_id, minimum_happiness,
                       time_of_day, trade_species_id
                FROM pokemon_evolution WHERE evolved_species_id=?
            ''', (sid,))
            evo = cur.fetchone()
            if evo:
                trigger_id = int(evo[0])
                cond = ''
                if trigger_id == 1:
                    if evo[1]:
                        cond = f'Lv.{evo[1]}'
                    elif evo[5]:
                        cond = f'친밀도 {evo[5]}'
                        if evo[6]:
                            cond += f'+{evo[6]}'
                    elif evo[4]:
                        cur.execute('SELECT name FROM move_names WHERE move_id=? AND local_language_id=?',
                                     (evo[4], LANG_KO))
                        mn = cur.fetchone()
                        cond = f'{mn[0]} 습득' if mn else '특수조건'
                    else:
                        cond = '레벨업'
                elif trigger_id == 2:
                    cond = '통신교환'
                    if evo[3]:
                        cur.execute('SELECT name FROM item_names WHERE item_id=? AND local_language_id=?',
                                     (evo[3], LANG_KO))
                        itn = cur.fetchone()
                        if itn:
                            cond += f'({itn[0]})'
                elif trigger_id == 3:
                    if evo[2]:
                        cur.execute('SELECT name FROM item_names WHERE item_id=? AND local_language_id=?',
                                     (evo[2], LANG_KO))
                        itn = cur.fetchone()
                        cond = itn[0] if itn else '아이템'
                    else:
                        cond = '아이템'
                elif trigger_id == 4:
                    cond = '껍질(탈피)'
                else:
                    cond = '특수조건'
                member['cond'] = cond

            members.append(member)

        if len(members) > 0:
            chains[str(chain_id)] = members

    conn.close()

    save_json(os.path.join(OUT_DIR, 'evolution_chains.json'), chains)
    print(f'  → {len(chains)}개 체인 저장 완료')


def export_encounters():
    """버전별 출현 데이터"""
    print('출현 데이터 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('''
        SELECT DISTINCT
            CAST(p.species_id AS INTEGER) as species_id,
            CAST(e.version_id AS INTEGER) as version_id,
            v.identifier as version_name,
            COALESCE(ln_ko.name, ln_en.name, l.identifier) as location_name,
            em.identifier as method
        FROM encounters e
        JOIN encounter_slots es ON e.encounter_slot_id = es.id
        JOIN encounter_methods em ON es.encounter_method_id = em.id
        JOIN location_areas la ON e.location_area_id = la.id
        JOIN locations l ON la.location_id = l.id
        JOIN versions v ON e.version_id = v.id
        JOIN pokemon p ON e.pokemon_id = p.id
        LEFT JOIN location_names ln_ko ON l.id = ln_ko.location_id AND ln_ko.local_language_id = ?
        LEFT JOIN location_names ln_en ON l.id = ln_en.location_id AND ln_en.local_language_id = ?
        ORDER BY species_id, version_id, location_name
    ''', (str(LANG_KO), str(LANG_EN)))

    encounters = {}
    for r in cur.fetchall():
        species_id = r[0]
        key = str(species_id)
        if key not in encounters:
            encounters[key] = {}
        ver_name = r[2]
        if ver_name not in encounters[key]:
            encounters[key][ver_name] = []

        entry = {'loc': r[3], 'method': r[4]}
        if entry not in encounters[key][ver_name]:
            encounters[key][ver_name].append(entry)

    conn.close()

    save_json(os.path.join(OUT_DIR, 'encounters.json'), encounters)
    print(f'  → {len(encounters)}종 출현 데이터 저장 완료')


def export_moves():
    """포켓몬별 기술 (단일 쿼리로 전체 추출)"""
    print('기술 데이터 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    # 기본 폼 pokemon_id → species_id 매핑
    cur.execute('''
        SELECT MIN(CAST(id AS INTEGER)), CAST(species_id AS INTEGER)
        FROM pokemon GROUP BY species_id
    ''')
    base_pokemon = {r[0]: r[1] for r in cur.fetchall()}
    base_ids = set(base_pokemon.keys())

    # 레벨업 기술 일괄 조회
    print('  레벨업 기술 조회...')
    cur.execute('''
        SELECT CAST(pm.pokemon_id AS INTEGER),
               CAST(pm.version_group_id AS INTEGER),
               CAST(pm.level AS INTEGER),
               mn.name
        FROM pokemon_moves pm
        JOIN move_names mn ON pm.move_id = mn.move_id
            AND mn.local_language_id = ?
        WHERE pm.pokemon_move_method_id = 1
        ORDER BY pm.pokemon_id, pm.version_group_id,
                 CAST(pm.level AS INTEGER), mn.name
    ''', (LANG_KO,))

    moves_data = {}
    for r in cur.fetchall():
        pid = r[0]
        if pid not in base_ids:
            continue
        sid = str(base_pokemon[pid])
        vg = str(r[1])
        if sid not in moves_data:
            moves_data[sid] = {}
        if vg not in moves_data[sid]:
            moves_data[sid][vg] = {}
        if 'lv' not in moves_data[sid][vg]:
            moves_data[sid][vg]['lv'] = []
        moves_data[sid][vg]['lv'].append([r[2], r[3]])

    # TM/HM 번호 매핑 구축 (move_id+version_group_id → TM01/HM01)
    print('  TM/HM 번호 매핑 구축...')
    cur.execute('''
        SELECT CAST(m.version_group_id AS INTEGER),
               CAST(m.move_id AS INTEGER),
               i.identifier
        FROM machines m
        JOIN items i ON m.item_id = i.id
    ''')
    machine_map = {}
    for r in cur.fetchall():
        vg_id, move_id, item_ident = r
        prefix = 'HM' if item_ident.startswith('hm') else 'TM'
        num = item_ident.replace('tm', '').replace('hm', '')
        label = f'{prefix}{num.zfill(2)}'
        machine_map[(vg_id, move_id)] = label

    # TM/HM 기술 일괄 조회
    print('  TM/HM 기술 조회...')
    cur.execute('''
        SELECT CAST(pm.pokemon_id AS INTEGER),
               CAST(pm.version_group_id AS INTEGER),
               CAST(pm.move_id AS INTEGER),
               mn.name
        FROM pokemon_moves pm
        JOIN move_names mn ON pm.move_id = mn.move_id
            AND mn.local_language_id = ?
        WHERE pm.pokemon_move_method_id = 4
        ORDER BY pm.pokemon_id, pm.version_group_id, mn.name
    ''', (LANG_KO,))

    for r in cur.fetchall():
        pid = r[0]
        if pid not in base_ids:
            continue
        sid = str(base_pokemon[pid])
        vg = str(r[1])
        vg_int = r[1]
        move_id = r[2]
        move_name = r[3]

        if sid not in moves_data:
            moves_data[sid] = {}
        if vg not in moves_data[sid]:
            moves_data[sid][vg] = {}

        label = machine_map.get((vg_int, move_id), 'TM??')
        key = 'hm' if label.startswith('HM') else 'tm'

        if key not in moves_data[sid][vg]:
            moves_data[sid][vg][key] = []
        moves_data[sid][vg][key].append([label, move_name])

    conn.close()

    save_json(os.path.join(OUT_DIR, 'moves.json'), moves_data)
    print(f'  → {len(moves_data)}종 기술 데이터 저장 완료')


def export_locations():
    """지방별 맵 + 맵별 출현 포켓몬"""
    print('맵 데이터 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    # 지방 목록
    cur.execute('''
        SELECT r.id, r.identifier, COALESCE(rn.name, r.identifier)
        FROM regions r
        LEFT JOIN region_names rn ON r.id = rn.region_id AND rn.local_language_id=?
        ORDER BY CAST(r.id AS INTEGER)
    ''', (LANG_KO,))
    regions = [{'id': int(r[0]), 'name': r[2]} for r in cur.fetchall()]

    # 맵별 출현 데이터
    cur.execute('''
        SELECT DISTINCT
            CAST(l.region_id AS INTEGER) as region_id,
            CAST(l.id AS INTEGER) as location_id,
            COALESCE(ln_ko.name, ln_en.name, l.identifier) as location_name,
            CAST(p.species_id AS INTEGER) as species_id,
            COALESCE(psn.name, ps.identifier) as pokemon_name,
            CAST(e.version_id AS INTEGER) as version_id,
            v.identifier as version_name,
            em.identifier as method,
            MIN(CAST(e.min_level AS INTEGER)) as min_lv,
            MAX(CAST(e.max_level AS INTEGER)) as max_lv
        FROM encounters e
        JOIN encounter_slots es ON e.encounter_slot_id = es.id
        JOIN encounter_methods em ON es.encounter_method_id = em.id
        JOIN location_areas la ON e.location_area_id = la.id
        JOIN locations l ON la.location_id = l.id
        JOIN versions v ON e.version_id = v.id
        JOIN pokemon p ON e.pokemon_id = p.id
        JOIN pokemon_species ps ON p.species_id = ps.id
        LEFT JOIN pokemon_species_names psn ON ps.id = psn.pokemon_species_id AND psn.local_language_id=?
        LEFT JOIN location_names ln_ko ON l.id = ln_ko.location_id AND ln_ko.local_language_id=?
        LEFT JOIN location_names ln_en ON l.id = ln_en.location_id AND ln_en.local_language_id=?
        GROUP BY l.region_id, l.id, p.species_id, e.version_id, em.identifier
        ORDER BY region_id, location_name, species_id, version_id
    ''', (LANG_KO, LANG_KO, LANG_EN))

    locations = {}
    for r in cur.fetchall():
        region_id = str(r[0])
        loc_id = str(r[1])

        if region_id not in locations:
            locations[region_id] = {}
        if loc_id not in locations[region_id]:
            locations[region_id][loc_id] = {'name': r[2], 'pokemon': []}

        locations[region_id][loc_id]['pokemon'].append({
            'id': r[3],
            'name': r[4],
            'ver': r[6],
            'method': r[7],
            'lv': [r[8], r[9]],
        })

    conn.close()

    save_json(os.path.join(OUT_DIR, 'regions.json'), regions)
    save_json(os.path.join(OUT_DIR, 'locations.json'), locations)
    loc_count = sum(len(locs) for locs in locations.values())
    print(f'  → {len(regions)}개 지방, {loc_count}개 맵 저장 완료')


def export_past_data():
    """세대별 종족값/특성/타입 변경 이력"""
    print('세대별 변경 이력 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    # --- stats_past ---
    # generation_id = "이 세대까지 적용된 값" (이후 세대에서 변경됨)
    cur.execute('''
        SELECT CAST(psp.pokemon_id AS INTEGER),
               CAST(psp.stat_id AS INTEGER),
               s.identifier,
               CAST(psp.base_stat AS INTEGER),
               CAST(psp.generation_id AS INTEGER)
        FROM pokemon_stats_past psp
        JOIN stats s ON psp.stat_id = s.id
        ORDER BY psp.pokemon_id, psp.generation_id, psp.stat_id
    ''')
    stats_past = {}
    for r in cur.fetchall():
        pid, stat_id, stat_ident, val, gen = r
        key = str(pid)
        stat_key = stat_ident.replace('special-attack', 'sp-attack').replace('special-defense', 'sp-defense')
        if key not in stats_past:
            stats_past[key] = {}
        gen_key = str(gen)
        if gen_key not in stats_past[key]:
            stats_past[key][gen_key] = {}
        stats_past[key][gen_key][stat_key] = val

    # --- abilities_past ---
    cur.execute('''
        SELECT CAST(pap.pokemon_id AS INTEGER),
               CAST(pap.generation_id AS INTEGER),
               CAST(pap.slot AS INTEGER),
               pap.ability_id,
               CASE WHEN pap.ability_id IS NOT NULL THEN an.name ELSE NULL END as ability_name
        FROM pokemon_abilities_past pap
        LEFT JOIN ability_names an ON pap.ability_id = an.ability_id AND an.local_language_id=?
        ORDER BY pap.pokemon_id, pap.generation_id, pap.slot
    ''', (LANG_KO,))
    abilities_past = {}
    for r in cur.fetchall():
        pid, gen, slot, ability_id, name = r
        key = str(pid)
        gen_key = str(gen)
        if key not in abilities_past:
            abilities_past[key] = {}
        if gen_key not in abilities_past[key]:
            abilities_past[key][gen_key] = {}
        # slot 3 = hidden, slot 1,2 = normal
        if slot == 3:
            abilities_past[key][gen_key]['hidden'] = name  # None if didn't exist
        else:
            if 'normal' not in abilities_past[key][gen_key]:
                abilities_past[key][gen_key]['normal'] = []
            if name is not None:
                abilities_past[key][gen_key]['normal'].append(name)

    # --- types_past ---
    cur.execute('''
        SELECT CAST(ptp.pokemon_id AS INTEGER),
               CAST(ptp.generation_id AS INTEGER),
               t.identifier,
               CAST(ptp.slot AS INTEGER)
        FROM pokemon_types_past ptp
        JOIN types t ON ptp.type_id = t.id
        ORDER BY ptp.pokemon_id, ptp.generation_id, ptp.slot
    ''')
    types_past = {}
    for r in cur.fetchall():
        pid, gen, type_ident, slot = r
        key = str(pid)
        gen_key = str(gen)
        if key not in types_past:
            types_past[key] = {}
        if gen_key not in types_past[key]:
            types_past[key][gen_key] = []
        types_past[key][gen_key].append(type_ident)

    conn.close()

    save_json(os.path.join(OUT_DIR, 'stats_past.json'), stats_past)
    save_json(os.path.join(OUT_DIR, 'abilities_past.json'), abilities_past)
    save_json(os.path.join(OUT_DIR, 'types_past.json'), types_past)
    print(f'  → stats_past: {len(stats_past)}종, abilities_past: {len(abilities_past)}종, types_past: {len(types_past)}종 저장 완료')


def export_forms():
    """폼별 종족값/특성/타입 (메가진화, 리전폼, 사이즈 차이 등)"""
    print('폼 데이터 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    # 기본 폼이 아닌 pokemon 엔트리 (species_id 기준 그룹화)
    cur.execute('''
        SELECT CAST(p.id AS INTEGER),
               CAST(p.species_id AS INTEGER),
               pf.form_identifier,
               COALESCE(pfn.pokemon_name, pfn.form_name, pf.form_identifier, '') as form_name
        FROM pokemon p
        JOIN pokemon_forms pf ON pf.pokemon_id = p.id
        LEFT JOIN pokemon_form_names pfn ON pf.id = pfn.pokemon_form_id AND pfn.local_language_id=?
        WHERE p.is_default = 0
        ORDER BY p.species_id, p.id
    ''', (LANG_KO,))

    forms = {}
    for r in cur.fetchall():
        pid, sid, form_ident, form_name = r
        key = str(sid)
        if key not in forms:
            forms[key] = []

        # 종족값
        cur.execute('''
            SELECT s.identifier, CAST(ps2.base_stat AS INTEGER)
            FROM pokemon_stats ps2
            JOIN stats s ON ps2.stat_id = s.id
            WHERE ps2.pokemon_id=?
            ORDER BY CAST(s.id AS INTEGER)
        ''', (pid,))
        stats = {}
        for sr in cur.fetchall():
            stat_key = sr[0].replace('special-attack', 'sp-attack').replace('special-defense', 'sp-defense')
            stats[stat_key] = sr[1]

        # 특성
        cur.execute('''
            SELECT an.name, pa.is_hidden FROM pokemon_abilities pa
            JOIN ability_names an ON pa.ability_id = an.ability_id AND an.local_language_id=?
            WHERE pa.pokemon_id=?
            ORDER BY CAST(pa.slot AS INTEGER)
        ''', (LANG_KO, pid))
        abilities = []
        hidden = None
        for ar in cur.fetchall():
            if ar[1] == '1':
                hidden = ar[0]
            else:
                abilities.append(ar[0])

        # 타입
        cur.execute('''
            SELECT t.identifier FROM pokemon_types pt
            JOIN types t ON pt.type_id = t.id
            WHERE pt.pokemon_id=?
            ORDER BY CAST(pt.slot AS INTEGER)
        ''', (pid,))
        types = [tr[0] for tr in cur.fetchall()]

        entry = {
            'pid': pid,
            'form': form_ident or '',
            'name': form_name or form_ident or '',
            'types': types,
            'stats': stats,
            'abilities': abilities,
        }
        if hidden:
            entry['hiddenAbility'] = hidden

        forms[key].append(entry)

    conn.close()

    save_json(os.path.join(OUT_DIR, 'forms.json'), forms)
    print(f'  → {len(forms)}종의 폼 데이터 저장 완료')


def export_dex_numbers():
    """도감별 포켓몬 번호"""
    print('도감 번호 추출 중...')
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('''
        SELECT pokedex_id, species_id, pokedex_number
        FROM pokemon_dex_numbers
        ORDER BY CAST(pokedex_id AS INTEGER), CAST(pokedex_number AS INTEGER)
    ''')

    dex = {}
    for r in cur.fetchall():
        dex_id = str(r[0])
        if dex_id not in dex:
            dex[dex_id] = []
        dex[dex_id].append([int(r[1]), int(r[2])])

    conn.close()

    save_json(os.path.join(OUT_DIR, 'dex_numbers.json'), dex)
    print(f'  → {len(dex)}개 도감 저장 완료')


def main():
    ensure_dir(OUT_DIR)

    print('=' * 40)
    print('  DB → JSON 추출 시작')
    print('=' * 40)

    export_pokemon_list()
    export_evolution_chains()
    export_dex_numbers()
    export_encounters()
    export_moves()
    export_locations()
    export_past_data()
    export_forms()

    print('=' * 40)
    print('  완료!')
    print('=' * 40)


if __name__ == '__main__':
    main()
