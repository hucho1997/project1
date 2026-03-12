"""
PokeAPI CSV → SQLite 변환 스크립트
data/csv/ 의 모든 CSV를 읽어 db/pokemon.db로 자동 변환한다.
CSV 헤더를 기반으로 테이블을 자동 생성하므로 CSV 추가/변경에 자동 대응.
"""

import csv
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = BASE_DIR / "data" / "csv"
DB_PATH = BASE_DIR / "db" / "pokemon.db"


def infer_value(val):
    """문자열 값을 적절한 Python 타입으로 변환한다."""
    if val is None or val.strip() == "":
        return None
    val = val.strip()
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def detect_delimiter(csv_path):
    """CSV 파일의 구분자를 감지한다."""
    with open(csv_path, encoding="utf-8-sig") as f:
        first_line = f.readline()
    if ';' in first_line and ',' not in first_line:
        return ';'
    return ','


def load_csv_auto(conn, csv_path, table_name=None):
    """CSV 파일을 읽어 테이블명을 파일명에서 추출하고 자동 생성·삽입한다."""
    if table_name is None:
        table_name = csv_path.stem  # e.g. pokemon_stats.csv → pokemon_stats

    delimiter = detect_delimiter(csv_path)

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=delimiter)
        headers = [h.strip().lstrip('\ufeff') for h in next(reader)]
        rows = list(reader)

    if not headers or not rows:
        return 0

    # 컬럼명에 SQLite 예약어가 있을 수 있으므로 모두 따옴표로 감싼다
    col_defs = ", ".join(f'"{h}" TEXT' for h in headers)
    conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_defs})')

    placeholders = ", ".join(["?"] * len(headers))
    col_names = ", ".join(f'"{h}"' for h in headers)
    sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

    converted_rows = []
    for row in rows:
        values = [infer_value(row[i]) if i < len(row) else None for i in range(len(headers))]
        converted_rows.append(values)

    conn.executemany(sql, converted_rows)
    return len(converted_rows)


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 기존 DB 삭제 후 재생성 (항상 깨끗한 빌드)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    csv_files = sorted(CSV_DIR.glob("*.csv"))
    # trainers/ 하위 CSV도 포함
    trainer_files = sorted((CSV_DIR / "trainers").glob("*.csv")) if (CSV_DIR / "trainers").exists() else []
    print(f"CSV 파일 {len(csv_files) + len(trainer_files)}개 발견\n")

    total_rows = 0
    for csv_path in csv_files:
        count = load_csv_auto(conn, csv_path)
        total_rows += count
        print(f"  {csv_path.stem}: {count}행")

    for csv_path in trainer_files:
        table_name = csv_path.stem.lower().replace(" ", "_")
        count = load_csv_auto(conn, csv_path, table_name=table_name)
        total_rows += count
        print(f"  {table_name}: {count}행")

    conn.commit()
    conn.close()
    print(f"\n완료: {DB_PATH}")
    print(f"총 {len(csv_files)}개 테이블, {total_rows}행 삽입")


if __name__ == "__main__":
    main()
