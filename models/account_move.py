from odoo import models,fields,api,_


class AccountMove(models.Model):
    _inherit = 'account.move'

    work_order_id = fields.One2many('dental.lab.order','invoice_id',string="Dental order")