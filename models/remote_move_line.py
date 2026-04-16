from odoo import models, fields


class RemoteOdooMoveLine(models.Model):
    _name = 'remote.odoo.move.line'
    _description = 'Línea de Movimiento Remoto (Caché)'
    _order = 'product_name asc'

    config_id = fields.Many2one(
        'remote.odoo.config', string='Dashboard',
        index=True, ondelete='cascade',
    )
    picking_remote_id = fields.Integer(string='ID Picking Remoto', index=True)
    product_name = fields.Char(string='Producto')
    default_code = fields.Char(string='Referencia Interna')
    product_qty = fields.Float(string='Cantidad Demandada')
    quantity_done = fields.Float(string='Cantidad Hecha')
    product_uom = fields.Char(string='UdM')
