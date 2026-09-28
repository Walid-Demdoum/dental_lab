from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

PMMA_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('failed', 'Failed'),
    ('validated', 'Validated'),
]


class PMMA(models.Model):
    _name = "pmma.line"
    _description = "PMMA Lines"
    _order = 'sequence, id'

    sequence = fields.Integer(string="Sequence", default=10)
    work_order_id = fields.Many2one('dental.lab.order', string="Work order",required=True, ondelete='cascade', index=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    description = fields.Char(string="Description")
    state = fields.Selection(selection=PMMA_STATE_SELECTION, string="Status",default='draft', copy=False, required=True)
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id.id)
    unit_price = fields.Monetary(string="Unit price", default=0)
    qty = fields.Integer(string="Qty", default=1)
    total_price = fields.Monetary(string="Total price", compute="_compute_total_price")
    attachment = fields.Binary(string="Attachment", attachment=True)
    attachment_filename = fields.Char(string="Attachment Filename")

    @api.depends('unit_price','qty')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.qty * rec.unit_price

    @api.constrains('state')
    def _check_single_validated(self):
        for rec in self:
            if rec.state == 'validated':
                others = rec.work_order_id.pmma_line_ids.filtered(lambda l: l.state == 'validated' and l.id != rec.id)
                if others:
                    raise ValidationError(_("Only one PMMA line can be validated per work order."))

    def _check_order_in_progress(self):
        for rec in self:
            if rec.work_order_id.state != 'in_progress':
                raise UserError(_("PMMA lines can only be updated while the work order is in progress."))

    def action_validate(self):
        self._check_order_in_progress()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only a PMMA that was sent to the dentist can be validated."))
        self.write({'state': 'validated'})

    def action_fail(self):
        self._check_order_in_progress()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only a PMMA that was sent to the dentist can be marked as failed."))
        self.write({'state': 'failed'})


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            pending = rec.work_order_id.pmma_line_ids.filtered(lambda l: l.id != rec.id and l.state != 'failed')
            if pending:
                raise UserError(_("You cannot add a new PMMA line while another one for this work order is still pending."))
        return records