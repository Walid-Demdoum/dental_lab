from odoo import api, fields, models,_
from odoo.exceptions import UserError


STATE_SELECTION = [ ('draft', 'New'),
                    ('in_progress', 'In Progress'),
                    ('done', 'Done'),
                    ('cancel', 'Cancelled')]
STATE_SELECTION_KANBAN_ORDER = [
    ('1.draft', 'New'),
    ('2.in_progress', 'In Progress'),
    ('3.done', 'Done'),
    ('4.cancel', 'Cancelled')
]


class DentalLabOrder(models.Model):
    _name = 'dental.lab.order'
    _description = 'Dental Lab Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_order desc, id desc'
    _rec_name = 'name'

    state = fields.Selection(selection=STATE_SELECTION,string='Status',default='draft',tracking=True,copy=False,index=True,)
    state_kanban_order = fields.Selection(selection=STATE_SELECTION_KANBAN_ORDER,string='Status kanban order',compute="_compute_state_kanban_order",store=True)

    name = fields.Char(string="Reference",required=True,copy=False,readonly=True,default=lambda self: 'New')
    ref = fields.Char(string="Form Number",copy=False)
    partner_id = fields.Many2one('res.partner',string='Dentist',required=True,tracking=True,index=True,default=lambda self: self.env.user.partner_id if self.env.user.has_group('base.group_portal') else False,)
    patient_name = fields.Char(string='Patient Name', required=True, tracking=True)
    shade = fields.Char(string='Shade / Color')
    date_order = fields.Date(string='Order Date',default=fields.Date.context_today,required=True)
    date_due = fields.Date(string='Due Date', tracking=True)
    priority = fields.Selection(selection=[('0', 'Normal'), ('1', 'Urgent')],string='Priority',default='0')
    technician_id = fields.Many2one('res.users',string='Assigned Technician',tracking=True, index=True,default=lambda self: self.env.user if self.env.user.has_group('dental_lab.group_dental_lab_technician') else False)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Scans',domain=lambda self: [('res_model', '=', self._name)],)
    notes = fields.Text(string='Instructions / Notes')

    currency_id = fields.Many2one('res.currency',string="Currency",default=lambda self:self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company,required=True,)

    work_order_line_ids = fields.One2many('dental.order.line','work_order_id',string="Work line",required=True)
    pmma_line_ids = fields.One2many('pmma.line', 'work_order_id', string="PMMA Lines")

    price_total_wol = fields.Monetary(string="Elements total",compute="_compute_amounts",store=True)
    price_total_pmma = fields.Monetary(string="Pmma lines total",compute="_compute_amounts",store=True)
    total_wo_price = fields.Monetary(string="Subtotal",compute="_compute_amounts",store=True)

    @api.depends('state')
    def _compute_state_kanban_order(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state_kanban_order = '1.draft'
            if rec.state == 'in_progress':
                rec.state_kanban_order = '2.in_progress'
            if rec.state == 'done':
                rec.state_kanban_order = '3.done'
            if rec.state == 'cancel':
                rec.state_kanban_order = '4.cancel'

    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('dental.lab.order') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        if self.env.user.share:
            for order in self:
                if order.state != 'draft':
                    raise UserError(_("You can only edit a work order while it is still in the 'New' state."))
        return super().write(vals)

    def action_start(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_("Only new orders can be started."))
            if not order.work_order_line_ids:
                raise UserError(_("You must add at least one work order line before starting this order."))
            if not order.technician_id:
                raise UserError(_("A technician is required to start this work order"))
        self.write({'state': 'in_progress'})

    def action_done(self):
        for order in self:
            if order.state != 'in_progress':
                raise UserError("Only orders in progress can be marked as done.")
            if order.pmma_line_ids and not order.pmma_line_ids.filtered(lambda l: l.state == 'validated'):
                raise UserError(_("This order has PMMA lines but none of them has been validated yet."))
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    @api.depends('work_order_line_ids','work_order_line_ids.total_price','pmma_line_ids','pmma_line_ids.total_price')
    def _compute_amounts(self):
        for rec in self:
            work_lines_sum = sum(rec.work_order_line_ids.mapped('total_price'))
            pmma_sum = sum(rec.pmma_line_ids.mapped('total_price'))
            rec.price_total_wol = work_lines_sum
            rec.price_total_pmma = pmma_sum
            rec.total_wo_price = work_lines_sum + pmma_sum