from odoo import models,fields,api,_


class DentalLabOrderLine(models.Model):
    _name = "dental.order.line"
    _description = "Dental Lab Order Line"

    work_order_id = fields.Many2one('dental.lab.order',string="Work Order", required=True, ondelete='cascade')
    description = fields.Char(string="Description")
    product_tmpl_id = fields.Many2one('product.template',string="Element type",required=True,ondelete='restrict',)
    quantity = fields.Integer(string="Quantity",required=True,default=1)
    currency_id = fields.Many2one('res.currency',string="Currency",default= lambda self:self.env.company.currency_id.id)
    unit_price = fields.Monetary(string="Unit price")
    total_price = fields.Monetary(string="Total price",compute="_compute_total_price")
    teeth = fields.Char(string="Tooth")



    @api.depends('unit_price','quantity')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.unit_price * rec.quantity