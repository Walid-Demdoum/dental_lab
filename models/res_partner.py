from odoo import models,fields,api,_

PARTNER_TYPE = [('dentist','Dentist'),('tech','Technician')]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_type = fields.Selection(string="Type",selection=PARTNER_TYPE,default='dentist')
    is_dentist = fields.Boolean(string="Is dentist",compute="_compute_partner_type")
    is_technician = fields.Boolean(string="Is technician",compute="_compute_partner_type")
    work_order_ids = fields.One2many('dental.lab.order','partner_id',string="Work order lines")

    @api.depends('partner_type')
    def _compute_partner_type(self):
        for rec in self:
            rec.is_dentist = False
            rec.is_technician = False
            if rec.partner_type == 'dentist':
                rec.is_dentist = True
            if rec.partner_type == 'tech':
                rec.is_technician = True
            