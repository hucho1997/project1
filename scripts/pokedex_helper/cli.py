# -*- coding: utf-8 -*-
"""도감 완성 도우미 - CLI 인터페이스"""

import sys
import io
from db_query import (
    GENERATION_DATA, get_national_dex_pokemon, get_dex_pokemon,
    get_pokemon_basic, get_evolution_chain, get_encounter_locations,
    get_level_up_moves, get_machine_moves, get_selected_version_ids,
    get_catchable_pokemon_set, get_method_ko,
    get_regions_for_versions, get_locations_for_region,
    get_pokemon_at_location,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def print_header(text):
    print(f'\n{"=" * 50}')
    print(f'  {text}')
    print(f'{"=" * 50}')


def print_subheader(text):
    print(f'\n--- {text} ---')


# ─── 1. 세대/게임 선택 화면 ───

def select_setup():
    """세대, 게임, 도감 선택"""
    print_header('도감 완성 도우미')

    # 세대 표시
    print('\n[세대 및 게임 선택]')
    print('체크할 항목의 번호를 입력하세요 (쉼표로 구분)')
    print()

    # 번호 → (gen, region_key, vg_idx, ver_idx) 매핑
    option_map = {}
    option_num = 1

    for gen_id, gen in sorted(GENERATION_DATA.items()):
        print(f'  {gen["name"]}')
        for region_key, region in gen['regions'].items():
            print(f'    {region["name"]}:', end='')
            for vg_info in region['versions']:
                for ver_id, ver_name in vg_info['versions']:
                    print(f'  [{option_num}] {ver_name}', end='')
                    option_map[option_num] = {
                        'gen': gen_id,
                        'region': region_key,
                        'vg': vg_info['vg'],
                        'version_id': ver_id,
                        'version_name': ver_name,
                    }
                    option_num += 1
            print()
        print()

    selected_input = input('선택: ').strip()
    if not selected_input:
        print('선택된 항목이 없습니다.')
        return None

    selected_nums = [int(x.strip()) for x in selected_input.split(',') if x.strip().isdigit()]
    selected = [option_map[n] for n in selected_nums if n in option_map]

    if not selected:
        print('유효한 선택이 없습니다.')
        return None

    # 선택된 version_group 목록
    selected_vgs = list(set(s['vg'] for s in selected))
    max_gen = max(s['gen'] for s in selected)
    selected_regions = list(set(s['region'] for s in selected))

    # 도감 선택
    print('\n[도감 선택]')
    print(f'  [1] 전국도감 ({GENERATION_DATA[max_gen]["national_dex_size"]}마리)')

    # 지방도감 옵션
    regional_options = {}
    idx = 2
    for s in selected:
        gen_data = GENERATION_DATA[s['gen']]
        region_data = gen_data['regions'][s['region']]
        dex_id = region_data['regional_dex']
        if dex_id not in regional_options:
            regional_options[dex_id] = {
                'idx': idx,
                'name': region_data['name'],
                'dex_id': dex_id,
            }
            idx += 1

    for dex_id, info in regional_options.items():
        print(f'  [{info["idx"]}] {info["name"]} 지방도감')

    dex_choice = input('선택: ').strip()
    if dex_choice == '1':
        dex_mode = 'national'
        dex_size = GENERATION_DATA[max_gen]['national_dex_size']
    else:
        dex_choice = int(dex_choice) if dex_choice.isdigit() else 2
        for dex_id, info in regional_options.items():
            if info['idx'] == dex_choice:
                dex_mode = 'regional'
                dex_size = dex_id
                break
        else:
            dex_mode = 'national'
            dex_size = GENERATION_DATA[max_gen]['national_dex_size']

    # 선택한 버전의 실제 version_id 조회
    version_info = get_selected_version_ids(selected)
    version_ids = [str(v[0]) for v in version_info]

    return {
        'selected': selected,
        'selected_vgs': selected_vgs,
        'version_ids': version_ids,
        'version_info': version_info,
        'max_gen': max_gen,
        'dex_mode': dex_mode,
        'dex_size': dex_size,
    }


# ─── 2. 포켓몬 목록 표시 ───

def show_pokemon_list(setup):
    """도감 포켓몬 목록 표시"""
    if setup['dex_mode'] == 'national':
        pokemon_list = get_national_dex_pokemon(setup['dex_size'])
        print_header(f'전국도감 (#{pokemon_list[0][0]}~#{pokemon_list[-1][0]})')
    else:
        pokemon_list = get_dex_pokemon(setup['dex_size'])
        print_header('지방도감')

    version_ids = setup['version_ids']

    # 포획 가능 포켓몬 일괄 조회 (속도 개선)
    catchable_set = get_catchable_pokemon_set(version_ids)

    print(f'총 {len(pokemon_list)}마리 | 선택 게임: {", ".join(s["version_name"] for s in setup["selected"])}')
    print()
    print(f'{"번호":>5}  {"이름":<10} {"타입":<15}  포획 가능')
    print('-' * 55)

    for species_id, dex_num in pokemon_list:
        basic = get_pokemon_basic(species_id)
        type_str = '/'.join(t[1] for t in basic['types'])
        catchable = 'O' if basic['pokemon_id'] in catchable_set else '-'

        print(f'#{dex_num:>4}  {basic["name_ko"]:<10} {type_str:<15}  {catchable}')

    print(f'\n포켓몬 번호: 상세 정보 | m: 맵별 출현 | q: 종료')

    while True:
        cmd = input('\n> ').strip()
        if cmd.lower() == 'q':
            break
        if cmd.lower() == 'm':
            show_map_browser(setup)
            continue
        if cmd.isdigit():
            target_id = int(cmd)
            # dex_num으로 찾기
            found = None
            for sid, dnum in pokemon_list:
                if dnum == target_id or sid == target_id:
                    found = sid
                    break
            if found:
                show_pokemon_detail(found, setup)
            else:
                print('해당 번호의 포켓몬을 찾을 수 없습니다.')


# ─── 3. 포켓몬 상세 정보 ───

def show_pokemon_detail(species_id, setup):
    """포켓몬 상세 정보 표시"""
    basic = get_pokemon_basic(species_id)
    version_ids = setup['version_ids']

    print_header(f'#{species_id:04d} {basic["name_ko"]} ({basic["name_en"]})')

    # 타입
    type_str = ' / '.join(t[1] for t in basic['types'])
    print(f'타입: {type_str}')

    # 특성
    normal_abs = [a[1] for a in basic['abilities'] if not a[2]]
    hidden_abs = [a[1] for a in basic['abilities'] if a[2]]
    print(f'특성: {", ".join(normal_abs)}', end='')
    if hidden_abs:
        print(f'  (숨겨진: {", ".join(hidden_abs)})', end='')
    print()

    # 종족값
    stat_order = ['hp', 'attack', 'defense', 'special-attack', 'special-defense', 'speed']
    stat_labels = {'hp': 'HP', 'attack': '공격', 'defense': '방어',
                   'special-attack': '특공', 'special-defense': '특방', 'speed': '스피드'}
    stats = basic['stats']
    stat_str = ' / '.join(f'{stat_labels[s]}:{stats.get(s, "?")}' for s in stat_order)
    total = sum(stats.get(s, 0) for s in stat_order)
    print(f'종족값: {stat_str} (합계: {total})')

    # 진화
    print_subheader('진화')
    chain = get_evolution_chain(species_id)
    format_evolution_chain(chain, species_id)

    # 포획 위치
    print_subheader('포획 위치')
    encounters = get_encounter_locations(species_id, version_ids)
    if encounters:
        for ver_name, locs in encounters.items():
            print(f'  [{ver_name}]')
            for loc_name, method in locs:
                print(f'    {loc_name} ({get_method_ko(method)})')
    else:
        print('  선택한 게임에서 야생 출현 없음')

    # 레벨업 기술 (선택된 vg 중 첫 번째 기준)
    print_subheader('레벨업 기술')
    vg = setup['selected_vgs'][0]
    moves = get_level_up_moves(species_id, vg)
    if moves:
        for lv, name in moves:
            lv_str = f'Lv.{lv}' if lv > 0 else '기본'
            print(f'  {lv_str:<8} {name}')
    else:
        print('  데이터 없음')

    # TM/HM 안내
    print(f'\n  [t] 기술머신/비전머신 보기')

    cmd = input('> ').strip().lower()
    if cmd == 't':
        print_subheader('기술머신/비전머신')
        tm_moves = get_machine_moves(species_id, vg)
        if tm_moves:
            for i, name in enumerate(tm_moves):
                print(f'  {name}', end='')
                if (i + 1) % 4 == 0:
                    print()
            print()
        else:
            print('  데이터 없음')


def format_evolution_chain(chain, current_id):
    """진화 체인을 한 줄로 포맷"""
    if len(chain) == 1:
        print(f'  진화 없음')
        return

    # 기본 포켓몬 (evolves_from이 None)
    base = [s for s in chain if s['evolves_from'] is None]
    if not base:
        print('  진화 데이터 오류')
        return
    base = base[0]

    def get_children(parent_id):
        return [s for s in chain if s['evolves_from'] == parent_id]

    def format_name(sp):
        name = sp['name_ko']
        if sp['id'] == current_id:
            return f'**{name}**'
        return name

    def format_with_condition(sp):
        name = format_name(sp)
        if sp['evo_condition']:
            return f'{name}({sp["evo_condition"]})'
        return name

    # 직선 진화 체크
    children = get_children(base['id'])

    if len(children) == 0:
        print(f'  {format_name(base)}')
    elif len(children) == 1:
        line = format_name(base)
        curr = children[0]
        while curr:
            line += f' → {format_with_condition(curr)}'
            next_children = get_children(curr['id'])
            curr = next_children[0] if next_children else None
        print(f'  {line}')
    else:
        # 분기 진화
        line = format_name(base) + ' → '
        branches = [format_with_condition(c) for c in children]
        line += ' / '.join(branches)
        print(f'  {line}')


# ─── 4. 맵별 출현 포켓몬 ───

def show_map_browser(setup):
    """맵 선택 → 출현 포켓몬 표시"""
    version_ids = setup['version_ids']
    regions = get_regions_for_versions(version_ids)

    if not regions:
        print('선택한 게임에 맵 데이터가 없습니다.')
        return

    # 지방 선택
    print_header('맵별 출현 포켓몬')
    print('\n[지방 선택]')
    for i, (rid, ident, name) in enumerate(regions, 1):
        print(f'  [{i}] {name}')

    choice = input('선택: ').strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(regions):
        print('잘못된 선택입니다.')
        return

    region_id, region_ident, region_name = regions[int(choice) - 1]

    # 맵 목록
    locations = get_locations_for_region(region_id, version_ids)
    if not locations:
        print(f'{region_name} 지방에 출현 데이터가 없습니다.')
        return

    print_subheader(f'{region_name} 지방 맵 목록')
    for i, (lid, lname) in enumerate(locations, 1):
        print(f'  [{i:>3}] {lname}')

    print(f'\n맵 번호 입력 | b: 지방 선택으로 | q: 도감으로')

    while True:
        cmd = input('\n맵> ').strip()
        if cmd.lower() == 'q':
            return
        if cmd.lower() == 'b':
            show_map_browser(setup)
            return
        if not cmd.isdigit():
            continue

        loc_idx = int(cmd)
        if loc_idx < 1 or loc_idx > len(locations):
            print('잘못된 번호입니다.')
            continue

        location_id, location_name = locations[loc_idx - 1]
        pokemon_list = get_pokemon_at_location(location_id, version_ids)

        if not pokemon_list:
            print(f'{location_name}에 출현 데이터가 없습니다.')
            continue

        print_subheader(f'{location_name} 출현 포켓몬')

        # 포켓몬별로 그룹핑
        grouped = {}
        for p in pokemon_list:
            key = (p['pokemon_id'], p['name_ko'])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(p)

        print(f'{"이름":<12} {"버전":<14} {"방법":<12} {"레벨":>5}')
        print('-' * 50)

        for (pid, name_ko), entries in grouped.items():
            first = True
            for e in entries:
                display_name = name_ko if first else ''
                lv_str = f'{e["min_level"]}-{e["max_level"]}' if e['min_level'] != e['max_level'] else str(e['min_level'])
                print(f'{display_name:<12} {e["version"]:<14} {get_method_ko(e["method"]):<12} {lv_str:>5}')
                first = False

        print(f'\n총 {len(grouped)}종')


# ─── 메인 ───

def main():
    setup = select_setup()
    if setup:
        show_pokemon_list(setup)


if __name__ == '__main__':
    main()
