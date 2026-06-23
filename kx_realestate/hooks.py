import logging

_logger = logging.getLogger(__name__)

MIGRATION_PARAM = 'kx_realestate.stage_models_migrated_v2'


def _map_stage_by_code(env, source_stage, target_model):
    if not source_stage:
        return False
    domain = [
        ('code', '=', source_stage.code),
        ('active', '=', True),
    ]
    if source_stage.building_type_id:
        domain.extend([
            '|',
            ('building_type_id', '=', False),
            ('building_type_id', '=', source_stage.building_type_id.id),
        ])
    else:
        domain.append(('building_type_id', '=', False))
    target = env[target_model].search(domain, order='sequence, id', limit=1)
    if not target:
        target = env[target_model].search(
            [('code', '=', source_stage.code), ('active', '=', True)],
            order='sequence, id',
            limit=1,
        )
    return target.id if target else False


def _table_exists(cr, table):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = %s
        """,
        (table,),
    )
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def _migrate_orphan_fk_stages(env):
    """Fix stage_id integers that still point at re_floor_stage rows after comodel change."""
    cr = env.cr
    if not _table_exists(cr, 're_building_stage'):
        return

    cr.execute(
        """
        SELECT b.id, fs.id, fs.code, fs.building_type_id
        FROM building_building b
        JOIN re_floor_stage fs ON fs.id = b.stage_id
        WHERE b.stage_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM re_building_stage bs WHERE bs.id = b.stage_id
          )
        """
    )
    Building = env['building.building']
    BuildingStage = env['re.building.stage']
    for building_id, _floor_stage_id, code, building_type_id in cr.fetchall():
        domain = [('code', '=', code), ('active', '=', True)]
        if building_type_id:
            domain.extend([
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', building_type_id),
            ])
        else:
            domain.append(('building_type_id', '=', False))
        target = BuildingStage.search(domain, order='sequence, id', limit=1)
        if target:
            Building.browse(building_id).stage_id = target.id

    if not _table_exists(cr, 're_unit_stage'):
        return

    cr.execute(
        """
        SELECT p.id, fs.id, fs.code, fs.building_type_id
        FROM product_template p
        JOIN re_floor_stage fs ON fs.id = p.stage_id
        WHERE p.is_property = TRUE
          AND p.stage_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM re_unit_stage us WHERE us.id = p.stage_id
          )
        """
    )
    Unit = env['product.template']
    UnitStage = env['re.unit.stage']
    for unit_id, _floor_stage_id, code, building_type_id in cr.fetchall():
        domain = [('code', '=', code), ('active', '=', True)]
        if building_type_id:
            domain.extend([
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', building_type_id),
            ])
        else:
            domain.append(('building_type_id', '=', False))
        target = UnitStage.search(domain, order='sequence, id', limit=1)
        if target:
            Unit.browse(unit_id).stage_id = target.id


def _migrate_loan_line_stages(env):
    cr = env.cr
    if not _column_exists(cr, 'loan_line_rs_own', 'progress_stage_id'):
        return
    if not _column_exists(cr, 'loan_line_rs_own', 'progress_building_stage_id'):
        return

    LoanLine = env['loan.line.rs.own']
    cr.execute(
        """
        SELECT id, trigger_level, progress_stage_id
        FROM loan_line_rs_own
        WHERE progress_stage_id IS NOT NULL
        """
    )
    for line_id, trigger_level, progress_stage_id in cr.fetchall():
        floor_stage = env['re.floor.stage'].browse(progress_stage_id).exists()
        if not floor_stage:
            continue
        line = LoanLine.browse(line_id)
        vals = {}
        if trigger_level == 'building':
            new_id = _map_stage_by_code(env, floor_stage, 're.building.stage')
            if new_id:
                vals['progress_building_stage_id'] = new_id
        elif trigger_level == 'unit':
            new_id = _map_stage_by_code(env, floor_stage, 're.unit.stage')
            if new_id:
                vals['progress_unit_stage_id'] = new_id
        else:
            vals['progress_floor_stage_id'] = floor_stage.id
        if vals:
            line.write(vals)


def _restore_from_stage_backup(env):
    """Restore stages if post-migrate did not run (e.g. fresh hook-only path)."""
    cr = env.cr
    if not _table_exists(cr, 'kx_realestate_stage_backup'):
        return False
    if not _table_exists(cr, 're_building_stage') or not _table_exists(cr, 're_unit_stage'):
        return False

    cr.execute(
        """
        SELECT res_model, res_id, stage_code, building_type_id, trigger_level
        FROM kx_realestate_stage_backup
        """
    )
    rows = cr.fetchall()
    Building = env['building.building']
    Unit = env['product.template']
    LoanLine = env['loan.line.rs.own']
    BuildingStage = env['re.building.stage']
    UnitStage = env['re.unit.stage']
    FloorStage = env['re.floor.stage']

    for res_model, res_id, stage_code, building_type_id, trigger_level in rows:
        if not stage_code:
            continue
        domain = [('code', '=', stage_code), ('active', '=', True)]
        if building_type_id:
            domain.extend([
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', building_type_id),
            ])
        else:
            domain.append(('building_type_id', '=', False))

        if res_model == 'building.building':
            target = BuildingStage.search(domain, order='sequence, id', limit=1)
            if target:
                Building.browse(res_id).stage_id = target.id
        elif res_model == 'product.template':
            target = UnitStage.search(domain, order='sequence, id', limit=1)
            if target:
                Unit.browse(res_id).stage_id = target.id
        elif res_model == 'loan.line.rs.own':
            line = LoanLine.browse(res_id)
            if trigger_level == 'building':
                target = BuildingStage.search(domain, order='sequence, id', limit=1)
                if target:
                    line.progress_building_stage_id = target.id
            elif trigger_level == 'unit':
                target = UnitStage.search(domain, order='sequence, id', limit=1)
                if target:
                    line.progress_unit_stage_id = target.id
            else:
                target = FloorStage.search(domain, order='sequence, id', limit=1)
                if target:
                    line.progress_floor_stage_id = target.id

    cr.execute('DROP TABLE IF EXISTS kx_realestate_stage_backup')
    return bool(rows)


def migrate_legacy_stage_data(env):
    """Idempotent one-shot migration; safe for install, upgrade, and registry reload."""
    if _restore_from_stage_backup(env):
        env['ir.config_parameter'].sudo().set_param(MIGRATION_PARAM, '1')
        _logger.info('kx_realestate: restored stages from backup table')
        return

    if env['ir.config_parameter'].sudo().get_param(MIGRATION_PARAM):
        return

    if not _table_exists(env.cr, 're_building_stage') or not _table_exists(env.cr, 're_unit_stage'):
        _logger.info('kx_realestate: stage tables not ready yet, skipping legacy stage migration')
        return

    _logger.info('kx_realestate: migrating legacy floor stages to building/unit stage models')

    for building in env['building.building'].search([('stage_id', '!=', False)]):
        stage = building.stage_id
        if stage._name == 're.building.stage':
            continue
        if stage._name == 're.floor.stage':
            new_id = _map_stage_by_code(env, stage, 're.building.stage')
            if new_id:
                building.stage_id = new_id

    for unit in env['product.template'].search([('is_property', '=', True), ('stage_id', '!=', False)]):
        stage = unit.stage_id
        if stage._name == 're.unit.stage':
            continue
        if stage._name == 're.floor.stage':
            new_id = _map_stage_by_code(env, stage, 're.unit.stage')
            if new_id:
                unit.stage_id = new_id

    _migrate_orphan_fk_stages(env)
    _migrate_loan_line_stages(env)

    env['ir.config_parameter'].sudo().set_param(MIGRATION_PARAM, '1')
    _logger.info('kx_realestate: legacy stage migration completed')


def post_init_hook(env):
    migrate_legacy_stage_data(env)
