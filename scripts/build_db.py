"""
PokeAPI CSV → SQLite 변환 스크립트
data/csv/ 의 원본 CSV를 읽어 db/pokemon.db로 변환한다.
"""

import csv
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = BASE_DIR / "data" / "csv"
DB_PATH = BASE_DIR / "db" / "pokemon.db"


def create_tables(cur):
    cur.executescript("""
    -- 타입 마스터
    CREATE TABLE IF NOT EXISTS types (
        id              INTEGER PRIMARY KEY,
        identifier      TEXT NOT NULL,
        generation_id   INTEGER,
        damage_class_id INTEGER
    );

    -- 타입 이름 (다국어)
    CREATE TABLE IF NOT EXISTS type_names (
        type_id             INTEGER NOT NULL,
        local_language_id   INTEGER NOT NULL,
        name                TEXT NOT NULL,
        PRIMARY KEY (type_id, local_language_id),
        FOREIGN KEY (type_id) REFERENCES types(id)
    );

    -- 스탯 마스터 (hp, attack, defense ...)
    CREATE TABLE IF NOT EXISTS stats (
        id              INTEGER PRIMARY KEY,
        identifier      TEXT NOT NULL,
        is_battle_only  INTEGER NOT NULL,
        game_index      INTEGER
    );

    -- 특성 마스터
    CREATE TABLE IF NOT EXISTS abilities (
        id              INTEGER PRIMARY KEY,
        identifier      TEXT NOT NULL,
        generation_id   INTEGER,
        is_main_series  INTEGER
    );

    -- 특성 이름 (다국어)
    CREATE TABLE IF NOT EXISTS ability_names (
        ability_id          INTEGER NOT NULL,
        local_language_id   INTEGER NOT NULL,
        name                TEXT NOT NULL,
        PRIMARY KEY (ability_id, local_language_id),
        FOREIGN KEY (ability_id) REFERENCES abilities(id)
    );

    -- 포켓몬 종 (species)
    CREATE TABLE IF NOT EXISTS pokemon_species (
        id                      INTEGER PRIMARY KEY,
        identifier              TEXT NOT NULL,
        generation_id           INTEGER,
        evolves_from_species_id INTEGER,
        evolution_chain_id      INTEGER,
        color_id                INTEGER,
        shape_id                INTEGER,
        habitat_id              INTEGER,
        gender_rate             INTEGER,
        capture_rate            INTEGER,
        base_happiness          INTEGER,
        is_baby                 INTEGER,
        hatch_counter           INTEGER,
        has_gender_differences  INTEGER,
        growth_rate_id          INTEGER,
        forms_switchable        INTEGER,
        is_legendary            INTEGER,
        is_mythical             INTEGER,
        "order"                 INTEGER,
        conquest_order          INTEGER
    );

    -- 포켓몬 종 이름 (다국어)
    CREATE TABLE IF NOT EXISTS pokemon_species_names (
        pokemon_species_id  INTEGER NOT NULL,
        local_language_id   INTEGER NOT NULL,
        name                TEXT NOT NULL,
        genus               TEXT,
        PRIMARY KEY (pokemon_species_id, local_language_id),
        FOREIGN KEY (pokemon_species_id) REFERENCES pokemon_species(id)
    );

    -- 포켓몬 (폼 포함)
    CREATE TABLE IF NOT EXISTS pokemon (
        id              INTEGER PRIMARY KEY,
        identifier      TEXT NOT NULL,
        species_id      INTEGER NOT NULL,
        height          INTEGER,
        weight          INTEGER,
        base_experience INTEGER,
        "order"         INTEGER,
        is_default      INTEGER,
        FOREIGN KEY (species_id) REFERENCES pokemon_species(id)
    );

    -- 포켓몬 스탯
    CREATE TABLE IF NOT EXISTS pokemon_stats (
        pokemon_id  INTEGER NOT NULL,
        stat_id     INTEGER NOT NULL,
        base_stat   INTEGER NOT NULL,
        effort      INTEGER NOT NULL,
        PRIMARY KEY (pokemon_id, stat_id),
        FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
        FOREIGN KEY (stat_id) REFERENCES stats(id)
    );

    -- 포켓몬 타입
    CREATE TABLE IF NOT EXISTS pokemon_types (
        pokemon_id  INTEGER NOT NULL,
        type_id     INTEGER NOT NULL,
        slot        INTEGER NOT NULL,
        PRIMARY KEY (pokemon_id, type_id),
        FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
        FOREIGN KEY (type_id) REFERENCES types(id)
    );

    -- 포켓몬 특성
    CREATE TABLE IF NOT EXISTS pokemon_abilities (
        pokemon_id  INTEGER NOT NULL,
        ability_id  INTEGER NOT NULL,
        is_hidden   INTEGER NOT NULL,
        slot        INTEGER NOT NULL,
        PRIMARY KEY (pokemon_id, slot),
        FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
        FOREIGN KEY (ability_id) REFERENCES abilities(id)
    );

    -- 진화 체인
    CREATE TABLE IF NOT EXISTS evolution_chains (
        id                      INTEGER PRIMARY KEY,
        baby_trigger_item_id    INTEGER
    );

    -- 포켓몬 진화
    CREATE TABLE IF NOT EXISTS pokemon_evolution (
        id                      INTEGER PRIMARY KEY,
        evolved_species_id      INTEGER NOT NULL,
        evolution_trigger_id    INTEGER,
        trigger_item_id         INTEGER,
        minimum_level           INTEGER,
        gender_id               INTEGER,
        location_id             INTEGER,
        held_item_id            INTEGER,
        time_of_day             TEXT,
        known_move_id           INTEGER,
        known_move_type_id      INTEGER,
        minimum_happiness       INTEGER,
        minimum_beauty          INTEGER,
        minimum_affection       INTEGER,
        relative_physical_stats INTEGER,
        party_species_id        INTEGER,
        party_type_id           INTEGER,
        trade_species_id        INTEGER,
        needs_overworld_rain    INTEGER,
        turn_upside_down        INTEGER,
        FOREIGN KEY (evolved_species_id) REFERENCES pokemon_species(id)
    );
    """)


def load_csv(cur, table_name, csv_path, columns):
    """CSV 파일을 읽어 지정 테이블에 삽입한다."""
    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(f'"{c}"' for c in columns)
    sql = f'INSERT OR REPLACE INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            values = []
            for col in columns:
                val = row.get(col, "").strip()
                values.append(None if val == "" else val)
            rows.append(values)
        cur.executemany(sql, rows)
    return len(rows)


# 테이블별 로드 설정: (테이블명, CSV 파일명, 컬럼 리스트)
TABLE_CONFIGS = [
    ("types", "types.csv",
     ["id", "identifier", "generation_id", "damage_class_id"]),
    ("type_names", "type_names.csv",
     ["type_id", "local_language_id", "name"]),
    ("stats", "stats.csv",
     ["id", "identifier", "is_battle_only", "game_index"]),
    ("abilities", "abilities.csv",
     ["id", "identifier", "generation_id", "is_main_series"]),
    ("ability_names", "ability_names.csv",
     ["ability_id", "local_language_id", "name"]),
    ("pokemon_species", "pokemon_species.csv",
     ["id", "identifier", "generation_id", "evolves_from_species_id",
      "evolution_chain_id", "color_id", "shape_id", "habitat_id",
      "gender_rate", "capture_rate", "base_happiness", "is_baby",
      "hatch_counter", "has_gender_differences", "growth_rate_id",
      "forms_switchable", "is_legendary", "is_mythical", "order",
      "conquest_order"]),
    ("pokemon_species_names", "pokemon_species_names.csv",
     ["pokemon_species_id", "local_language_id", "name", "genus"]),
    ("pokemon", "pokemon.csv",
     ["id", "identifier", "species_id", "height", "weight",
      "base_experience", "order", "is_default"]),
    ("pokemon_stats", "pokemon_stats.csv",
     ["pokemon_id", "stat_id", "base_stat", "effort"]),
    ("pokemon_types", "pokemon_types.csv",
     ["pokemon_id", "type_id", "slot"]),
    ("pokemon_abilities", "pokemon_abilities.csv",
     ["pokemon_id", "ability_id", "is_hidden", "slot"]),
    ("evolution_chains", "evolution_chains.csv",
     ["id", "baby_trigger_item_id"]),
    ("pokemon_evolution", "pokemon_evolution.csv",
     ["id", "evolved_species_id", "evolution_trigger_id", "trigger_item_id",
      "minimum_level", "gender_id", "location_id", "held_item_id",
      "time_of_day", "known_move_id", "known_move_type_id",
      "minimum_happiness", "minimum_beauty", "minimum_affection",
      "relative_physical_stats", "party_species_id", "party_type_id",
      "trade_species_id", "needs_overworld_rain", "turn_upside_down"]),
]


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 기존 DB 삭제 후 재생성 (항상 깨끗한 빌드)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    print("테이블 생성 중...")
    create_tables(cur)

    print("CSV 데이터 로드 중...")
    for table_name, csv_file, columns in TABLE_CONFIGS:
        csv_path = CSV_DIR / csv_file
        count = load_csv(cur, table_name, csv_path, columns)
        print(f"  {table_name}: {count}행 삽입")

    conn.commit()
    conn.close()
    print(f"\n완료: {DB_PATH}")


if __name__ == "__main__":
    main()
