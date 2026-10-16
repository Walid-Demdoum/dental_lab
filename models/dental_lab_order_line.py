from odoo import models,fields,api,_
from odoo.exceptions import ValidationError


FDI_TEETH = {str(q * 10 + n) for q in range(1, 5) for n in range(1, 9)}


class DentalLabOrderLine(models.Model):
    _name = "dental.order.line"
    _description = "Dental Lab Order Line"

    work_order_id = fields.Many2one('dental.lab.order',string="Work Order", required=True, ondelete='cascade')
    description = fields.Char(string="Description")
    product_tmpl_id = fields.Many2one('product.template',string="Element type",required=True,ondelete='restrict',)
    quantity = fields.Integer(string="Quantity",required=True,compute='_compute_quantity', store=True, readonly=False, precompute=True)
    currency_id = fields.Many2one('res.currency',string="Currency",default= lambda self:self.env.company.currency_id.id)
    unit_price = fields.Monetary(string="Unit price",compute="_compute_unit_price",precompute=True,store=True,readonly=False,groups="dental_lab.group_dental_lab_manager")
    total_price = fields.Monetary(string="Total price",compute="_compute_total_price",groups="dental_lab.group_dental_lab_manager")
    teeth = fields.Char(string="Tooth")



    @api.depends('unit_price','quantity')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.unit_price * rec.quantity

    @api.depends('product_tmpl_id')
    def _compute_unit_price(self):
        for rec in self:
            rec.unit_price = rec.product_tmpl_id.list_price

    def _get_teeth_list(self):
        self.ensure_one()
        return [t.strip() for t in (self.teeth or '').split(',') if t.strip()]

    @api.depends('teeth')
    def _compute_quantity(self):
        for rec in self:
            rec.quantity = len(rec._get_teeth_list()) or 1

    @api.constrains('teeth')
    def _check_teeth(self):
        for rec in self:
            teeth = rec._get_teeth_list()
            invalid = [t for t in teeth if t not in FDI_TEETH]
            if invalid:
                raise ValidationError(_("Invalid FDI tooth number(s): %s", ", ".join(invalid)))
            if len(set(teeth)) != len(teeth):
                raise ValidationError(_("A tooth cannot be selected twice on the same line."))