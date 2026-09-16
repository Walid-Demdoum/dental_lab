from odoo import api, fields, models
from odoo.exceptions import UserError


class DentalLabOrder(models.Model):
    _name = 'dental.lab.order'
    _description = 'Dental Lab Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_order desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'New',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Dentist',
        required=True,
        tracking=True,
        index=True,
        default=lambda self: self.env.user.partner_id,
    )
    patient_name = fields.Char(string='Patient Name', required=True, tracking=True)
    tooth_numbers = fields.Char(
        string='Tooth Number(s)',
        help='FDI notation, e.g. 11, 12, 21',
    )
    work_type = fields.Selection(
        selection=[
            ('crown', 'Crown'),
            ('bridge', 'Bridge'),
            ('denture', 'Denture'),
            ('implant', 'Implant'),
            ('other', 'Other'),
        ],
        string='Work Type',
        required=True,
        tracking=True,
    )
    shade = fields.Char(string='Shade / Color')
    material = fields.Char(string='Material')
    date_order = fields.Date(
        string='Order Date',
        default=fields.Date.context_today,
        required=True,
    )
    date_due = fields.Date(string='Due Date', tracking=True)
    priority = fields.Selection(
        selection=[('0', 'Normal'), ('1', 'Urgent')],
        string='Priority',
        default='0',
    )
    technician_id = fields.Many2one(
        'res.users',
        string='Assigned Technician',
        tracking=True,
    )
    notes = fields.Text(string='Instructions / Notes')
    state = fields.Selection(
        selection=[
            ('draft', 'New'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'dental.lab.order'
                ) or 'New'
        return super().create(vals_list)

    def action_start(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(
                    "Only new orders can be started."
                )
        self.write({'state': 'in_progress'})

    def action_done(self):
        for order in self:
            if order.state != 'in_progress':
                raise UserError(
                    "Only orders in progress can be marked as done."
                )
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})