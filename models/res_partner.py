import uuid
from odoo import models,fields,api,_
import logging

PARTNER_TYPE = [('dentist','Dentist'),('tech','Technician'),('other','Other')]
DENTIST_SENSITIVE_FIELDS = [
    'name', 'phone', 'mobile', 'email',
    'street', 'street2', 'city', 'zip', 'vat', 'website',
]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_type = fields.Selection(string="Type",selection=PARTNER_TYPE,default=False)
    is_dentist = fields.Boolean(string="Is dentist",compute="_compute_partner_type")
    is_technician = fields.Boolean(string="Is technician",compute="_compute_partner_type")
    work_order_ids = fields.One2many('dental.lab.order','partner_id',string="Work order lines")
    anon_code = fields.Char(string="Anonymized Code", copy=False, readonly=True)
    
    @api.depends('partner_type')
    def _compute_partner_type(self):
        for rec in self:
            rec.is_dentist = rec.partner_type == 'dentist'
            rec.is_technician = rec.partner_type == 'tech'

    def _is_restricted_technician(self):
        user = self.env.user
        return (user.has_group('dental_lab.group_dental_lab_technician') and not user.has_group('dental_lab.group_dental_lab_manager'))


    def _generate_anon_code(self):
        self.ensure_one()
        code = 'DX-%s' % uuid.uuid4().hex[:4].upper()
        while self.search_count([('anon_code', '=', code)]):
            code = 'DX-%s' % uuid.uuid4().hex[:4].upper()
        return code

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            if partner.partner_type == 'dentist' and not partner.anon_code:
                partner.anon_code = partner._generate_anon_code()
        return partners

    def write(self, vals):
        if self._is_restricted_technician():
            for partner in self:
                if partner.partner_type == 'dentist':
                    for f in DENTIST_SENSITIVE_FIELDS:
                        vals.pop(f, None)
        res = super().write(vals)
        if vals.get('partner_type') == 'dentist':
            for partner in self:
                if not partner.anon_code:
                    partner.anon_code = partner._generate_anon_code()
        return res

    def _compute_display_name(self):
        super()._compute_display_name()
        if self._is_restricted_technician():
            for partner in self:
                if partner.partner_type == 'dentist':
                    partner.display_name = partner.anon_code or _('Hidden')

    def read(self, fields=None, load='_classic_read'):
        result = super().read(fields=fields, load=load)
        if not self._is_restricted_technician():
            return result
        partners = self.browse([r['id'] for r in result])
        for rec, partner in zip(result, partners):
            if partner.partner_type != 'dentist':
                continue
            anon_code = partner.anon_code
            for f in DENTIST_SENSITIVE_FIELDS:
                if f in rec:
                    rec[f] = anon_code if f == 'name' else False
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])
        if name and ('partner_type', '=', 'dentist') in args and self._is_restricted_technician():
            partners = self.search(args + [('anon_code', operator, name)], limit=limit)
            return partners.name_get()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)