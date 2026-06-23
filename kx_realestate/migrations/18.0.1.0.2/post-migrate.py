"""
Run AFTER module schema update and XML data load.

Restores stages from kx_realestate_stage_backup into the new stage tables.
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


def _find_stage_id(cr, target_table, code, building_type_id):
    if not code:
        return None
    if building_type_id:
        cr.execute(
            f"""
            SELECT id FROM {target_table}
            WHERE code = %s AND active = TRUE
              AND (building_type_id IS NULL OR building_type_id = %s)
            ORDER BY sequence, id
            LIMIT 1
            """,
            (code, building_type_id),
        )
    else:
        cr.execute(
            f"""
            SELECT id FROM {target_table}
            WHERE code = %s AND active = TRUE AND building_type_id IS NULL
            ORDER BY sequence, id
            LIMIT 1
            """,
            (code,),
        )
    row = cr.fetchone()
    if row:
        return row[0]
    cr.execute(
        f"""
        SELECT id FROM {target_table}
        WHERE code = %s AND active = TRUE
        ORDER BY sequence, id
        LIMIT 1
        """,
        (code,),
    )
    row = cr.fetchone()
    return row[0] if row else None


def migrate(cr, version):
    if not _table_exists(cr, BACKUP_TABLE):
        return
    if not _table_exists(cr, 're_building_stage') or not _table_exists(cr, 're_unit_stage'):
        _logger.warning('kx_realestate post-migrate: stage tables missing, keeping backup table')
        return

    cr.execute(
        f"""
        SELECT res_model, res_id, stage_code, building_type_id, trigger_level
        FROM {BACKUP_TABLE}
        """
    )
    rows = cr.fetchall()

    for res_model, res_id, stage_code, building_type_id, trigger_level in rows:
        if res_model == 'building.building':
            new_id = _find_stage_id(cr, 're_building_stage', stage_code, building_type_id)
            if new_id:
                cr.execute(
                    "UPDATE building_building SET stage_id = %s WHERE id = %s",
                    (new_id, res_id),
                )
        elif res_model == 'product.template':
            new_id = _find_stage_id(cr, 're_unit_stage', stage_code, building_type_id)
            if new_id:
                cr.execute(
                    "UPDATE product_template SET stage_id = %s WHERE id = %s",
                    (new_id, res_id),
                )
        elif res_model == 'loan.line.rs.own':
            if trigger_level == 'building':
                new_id = _find_stage_id(cr, 're_building_stage', stage_code, building_type_id)
                if new_id:
                    cr.execute(
                        "UPDATE loan_line_rs_own SET progress_building_stage_id = %s WHERE id = %s",
                        (new_id, res_id),
                    )
            elif trigger_level == 'unit':
                new_id = _find_stage_id(cr, 're_unit_stage', stage_code, building_type_id)
                if new_id:
                    cr.execute(
                        "UPDATE loan_line_rs_own SET progress_unit_stage_id = %s WHERE id = %s",
                        (new_id, res_id),
                    )
            elif stage_code:
                new_id = _find_stage_id(cr, 're_floor_stage', stage_code, building_type_id)
                if new_id:
                    cr.execute(
                        "UPDATE loan_line_rs_own SET progress_floor_stage_id = %s WHERE id = %s",
                        (new_id, res_id),
                    )

    cr.execute(f"DROP TABLE IF EXISTS {BACKUP_TABLE}")
    _logger.info('kx_realestate post-migrate: restored %s stage references', len(rows))
