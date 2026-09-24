from odoo import models,fields,api,_


class PMMA(models.Model):
    _name = "pmma.line"
    _description = "PMMA Lines"

    sequence = fields.Integer(string="Sequence")
    work_order_id = fields.Many2one('dental.lab.order',string="Work order")
    date = fields.Date(string="Date")
    company_id = fields.Many2one(related='work_order_id.company_id')
    currency_id = fields.Many2one('res.currency',string="Currency",default=lambda self:self.env.company.currency_id.id)
    unit_price = fields.Monetary(string="Unit price",default=0)
    qty = fields.Integer(string="Qty")
    total_price = fields.Monetary(string="Total price",compute="_compute_total_price")





    @api.depends('unit_price','qty')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.qty * rec.unit_price