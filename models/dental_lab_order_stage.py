from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DentalLabOrderStage(models.Model):
    _name = 'dental.lab.order.stage'
    _description = 'Dental Lab Work Order Step'
    _order = 'sequence, id'

    name = fields.Char(string="Step", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_in_use(self):
        if self.env['dental.lab.order'].sudo().search_count([('stage_id', 'in', self.ids)]):
            raise UserError(_("This step is used by work orders. Archive it instead of deleting it."))