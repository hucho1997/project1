# -*- coding: utf-8 -*-
"""JSON 파일들을 JS 변수 파일로 변환 (file:// 에서도 동작)"""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(SCRIPT_DIR, 'web', 'data')
DOCS_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'docs', 'data')

# 파일별 JS 변수 매핑
FILE_MAP = {
    'pokemon_list.json': ('data-core.js', 'POKEMON_LIST'),
    'evolution_chains.json': ('data-core.js', 'EVOLUTION_CHAINS'),
    'dex_numbers.json': ('data-core.js', 'DEX_NUMBERS'),
    'regions.json': ('data-core.js', 'REGIONS'),
    'encounters.json': ('data-encounters.js', 'ENCOUNTER_DATA'),
    'moves.json': ('data-moves.js', 'MOVES_DATA'),
    'locations.json': ('data-locations.js', 'LOCATION_DATA'),
}


def convert():
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 그룹별로 모으기
    groups = {}
    for json_file, (js_file, var_name) in FILE_MAP.items():
        if js_file not in groups:
            groups[js_file] = []
        json_path = os.path.join(JSON_DIR, json_file)
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read()
        groups[js_file].append((var_name, content))

    for js_file, entries in groups.items():
        out_path = os.path.join(DOCS_DIR, js_file)
        with open(out_path, 'w', encoding='utf-8') as f:
            for var_name, content in entries:
                f.write(f'const {var_name} = {content};\n')
        size_kb = os.path.getsize(out_path) / 1024
        print(f'  {js_file}: {size_kb:.0f}KB')

    print('완료!')


if __name__ == '__main__':
    convert()
