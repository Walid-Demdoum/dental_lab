from odoo import models,fields,api,_


class DentalLabOrderLine(models.Model):
    _name = "dental.order.line"
    _description = "Dental Lab Order Line"

    work_order_id = fields.Many2one('dental.lab.order',string="Work Order", required=True, ondelete='cascade')
    description = fields.Char(string="Description")
    product_tmpl_id = fields.Many2one('product.template',string="Element type",required=True,ondelete='restrict',)
    quantity = fields.Integer(string="Quantity",required=True,default=1)
    currency_id = fields.Many2one('res.currency',string="Currency",default= lambda self:self.env.company.currency_id.id)
    unit_price = fields.Monetary(string="Unit price",compute="_compute_unit_price",precompute=True,store=True)
    total_price = fields.Monetary(string="Total price",compute="_compute_total_price")
    teeth = fields.Char(string="Tooth")



    @api.depends('unit_price','quantity')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.unit_price * rec.quantity

    @api.depends('product_tmpl_id','product_tmpl_id.list_price')
    def _compute_unit_price(self):
        for rec in self:
            rec.unit_price = rec.product_tmpl_id.list_price