from odoo import models, fields, api


class RemoteOdooLog(models.Model):
    _name = 'remote.odoo.log'
    _description = 'Log de Cambios del Dashboard Remoto'
    _order = 'timestamp desc, id desc'

    timestamp = fields.Datetime(
        string='Fecha/Hora',
        default=fields.Datetime.now,
        index=True,
    )
    event_type = fields.Selection(
        [
            ('new', 'Nuevo'),
            ('state_change', 'Cambio de estado'),
            ('sub_state_change', 'Cambio de sub-estado'),
            ('column_change', 'Cambio de columna'),
            ('completed', 'Completado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Tipo de Evento',
        index=True,
    )
    remote_id = fields.Integer(string='ID Remoto')
    picking_name = fields.Char(string='Picking')
    partner_name = fields.Char(string='Cliente')
    origin = fields.Char(string='Pedido de Venta')
    column_type = fields.Selection(
        [
            ('en_preparacion', 'En Preparación'),
            ('despachar', 'Despachar'),
            ('mostrador', 'Mostrador'),
            ('mostrador_preparacion', 'Mostrador – En Preparación'),
            ('mostrador_despachar', 'Mostrador – Listo para Entregar'),
        ],
        string='Columna',
    )
    old_value = fields.Char(string='Valor Anterior')
    new_value = fields.Char(string='Valor Nuevo')
    description = fields.Char(string='Descripción', compute='_compute_description', store=True)

    @api.depends('event_type', 'picking_name', 'old_value', 'new_value')
    def _compute_description(self):
        labels = {
            'new': 'Nuevo picking',
            'state_change': 'Estado',
            'sub_state_change': 'Sub-estado',
            'column_change': 'Columna',
            'completed': 'Completado',
            'cancelled': 'Cancelado',
        }
        for rec in self:
            ev = labels.get(rec.event_type, rec.event_type or '')
            if rec.event_type in ('state_change', 'sub_state_change', 'column_change'):
                rec.description = f"{ev}: {rec.old_value or '—'} → {rec.new_value or '—'}"
            elif rec.event_type == 'new':
                rec.description = f"Nuevo picking en {rec.new_value or ''}"
            else:
                rec.description = ev
