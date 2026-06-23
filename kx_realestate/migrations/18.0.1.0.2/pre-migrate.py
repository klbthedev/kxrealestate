"""
Run BEFORE module schema update.

Clears stage_id values that still point at re_floor_stage so PostgreSQL
can recreate FK constraints toward re_building_stage / re_unit_stage.
Stage mapping is stored in kx_realestate_stage_backup and restored in post-migrate.
"""
import logging

_logger = logging.getLogger(__name__)

BACKUP_TABLE = 'kx_realestate_stage_backup'


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,),
    )
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    cr.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {BACKUP_TABLE} (
            id SERIAL PRIMARY KEY,
            res_model VARCHAR NOT NULL,
            res_id INTEGER NOT NULL,
            floor_stage_id INTEGER,
            stage_code VARCHAR,
            building_type_id INTEGER,
            trigger_level VARCHAR
        )
        """
    )
    cr.execute(f"DELETE FROM {BACKUP_TABLE}")

    if _table_exists(cr, 'building_building') and _column_exists(cr, 'building_building', 'stage_id'):
        cr.execute(
            f"""
            INSERT INTO {BACKUP_TABLE}
                (res_model, res_id, floor_stage_id, stage_code, building_type_id)
            SELECT
                'building.building',
                b.id,
                b.stage_id,
                fs.code,
                fs.building_type_id
            FROM building_building b
            LEFT JOIN re_floor_stage fs ON fs.id = b.stage_id
            WHERE b.stage_id IS NOT NULL
            """
        )
        cr.execute("UPDATE building_building SET stage_id = NULL WHERE stage_id IS NOT NULL")
        _logger.info('kx_realestate pre-migrate: cleared building.building stage_id')

    if _table_exists(cr, 'product_template') and _column_exists(cr, 'product_template', 'stage_id'):
        cr.execute(
            f"""
            INSERT INTO {BACKUP_TABLE}
                (res_model, res_id, floor_stage_id, stage_code, building_type_id)
            SELECT
                'product.template',
                p.id,
                p.stage_id,
                fs.code,
                fs.building_type_id
            FROM product_template p
            LEFT JOIN re_floor_stage fs ON fs.id = p.stage_id
            WHERE p.is_property = TRUE AND p.stage_id IS NOT NULL
            """
        )
        cr.execute(
            """
            UPDATE product_template
            SET stage_id = NULL
            WHERE is_property = TRUE AND stage_id IS NOT NULL
            """
        )
        _logger.info('kx_realestate pre-migrate: cleared product.template stage_id')

    if _table_exists(cr, 'loan_line_rs_own') and _column_exists(cr, 'loan_line_rs_own', 'progress_stage_id'):
        cr.execute(
            f"""
            INSERT INTO {BACKUP_TABLE}
                (res_model, res_id, floor_stage_id, stage_code, building_type_id, trigger_level)
            SELECT
                'loan.line.rs.own',
                l.id,
                l.progress_stage_id,
                fs.code,
                fs.building_type_id,
                l.trigger_level
            FROM loan_line_rs_own l
            LEFT JOIN re_floor_stage fs ON fs.id = l.progress_stage_id
            WHERE l.progress_stage_id IS NOT NULL
            """
        )
        cr.execute(
            "UPDATE loan_line_rs_own SET progress_stage_id = NULL WHERE progress_stage_id IS NOT NULL"
        )
        _logger.info('kx_realestate pre-migrate: cleared loan.line.rs.own progress_stage_id')
