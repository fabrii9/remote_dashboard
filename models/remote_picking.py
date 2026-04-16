from odoo import models, fields, api

STATE_LABELS = {
    'draft': 'Borrador',
    'waiting': 'En espera',
    'confirmed': 'Esperando',
    'assigned': 'Disponible',
    'done': 'Hecho',
    'cancel': 'Cancelado',
}


class RemoteOdooPicking(models.Model):
    _name = 'remote.odoo.picking'
    _description = 'Picking Remoto (Caché)'
    _order = 'scheduled_date asc, name asc'

    config_id = fields.Many2one(
        'remote.odoo.config', string='Dashboard',
        index=True, ondelete='cascade',
    )
    remote_id = fields.Integer(string='ID Remoto', index=True)
    name = fields.Char(string='Referencia')
    partner_name = fields.Char(string='Contacto')
    scheduled_date = fields.Datetime(string='Fecha Programada')
    state = fields.Char(string='Estado (código)')
    state_label = fields.Char(
        string='Estado',
        compute='_compute_state_label',
        store=True,
    )
    origin = fields.Char(string='Documento Origen')
    sale_order_remote_id = fields.Integer(string='ID Sale Order Remoto')
    sub_state = fields.Char(string='Sub-estado')
    picking_type_name = fields.Char(string='Tipo de Operación')
    x_tipo_pedido = fields.Char(string='Tipo de Pedido')
    create_date_remote = fields.Datetime(string='Fecha Creación Remoto')
    column_type = fields.Selection(
        [
            ('en_preparacion', 'En Preparación'),
            ('despachar', 'Despachar'),
            ('mostrador', 'Mostrador'),
            ('mostrador_preparacion', 'Mostrador - En Preparación'),
            ('mostrador_despachar', 'Mostrador - Listo para Entregar'),
        ],
        string='Columna',
        index=True,
    )

    @api.depends('state')
    def _compute_state_label(self):
        for rec in self:
            rec.state_label = STATE_LABELS.get(rec.state, rec.state or '')
