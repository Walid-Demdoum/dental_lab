from odoo import api, fields,Command, models,_
from odoo.exceptions import UserError,AccessError,ValidationError

from urllib.parse import urlencode
from odoo.tools import consteq, hmac as hmac_tool

import time

EXOCAD_TOKEN_TTL = 15 * 60  # seconds
EXOCAD_SCOPE = 'dental_lab_exocad'

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
    partner_id = fields.Many2one('res.partner',string='Dentist',required=True,index=True,default=lambda self: self.env.user.partner_id if self.env.user.has_group('base.group_portal') else False,)
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

    price_total_wol = fields.Monetary(string="Elements total",compute="_compute_amounts",store=True,groups="dental_lab.group_dental_lab_manager")
    price_total_pmma = fields.Monetary(string="Pmma lines total",compute="_compute_amounts",store=True,groups="dental_lab.group_dental_lab_manager")
    total_wo_price = fields.Monetary(string="Subtotal",compute="_compute_amounts",store=True,groups="dental_lab.group_dental_lab_manager")

    invoice_id = fields.Many2one('account.move',string="Invoices")
    
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

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_("You can only unlink draft records"))
        return super().unlink()

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
                raise UserError(_("Only orders in progress can be marked as done."))
            if order.pmma_line_ids and not order.pmma_line_ids.filtered(lambda l: l.state == 'validated'):
                raise UserError(_("This order has PMMA lines but none of them has been validated yet."))
        self.write({'state': 'done'})

    def action_cancel(self):
        for order in self:
            if order.invoice_id and order.invoice_id.state != 'cancel':
                raise UserError(_("%s has an active invoice; cancel the invoice first.", order.name))
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        if not self.env.user.has_group('dental_lab.group_dental_lab_manager'):
            raise AccessError(_("Only Lab Managers can reset an order to draft."))
        for order in self:
            if order.invoice_id and order.invoice_id.state != 'cancel':
                raise UserError(_("%s has an active invoice.", order.name))
        self.write({'state': 'draft'})

    @api.depends('work_order_line_ids','work_order_line_ids.total_price','pmma_line_ids','pmma_line_ids.state','pmma_line_ids.total_price')
    def _compute_amounts(self):
        for rec in self:
            work_lines_sum = sum(rec.work_order_line_ids.mapped('total_price'))
            pmma_sum = sum(rec.pmma_line_ids.filtered(lambda l: l.state == 'validated').mapped('total_price'))
            rec.price_total_wol = work_lines_sum
            rec.price_total_pmma = pmma_sum
            rec.total_wo_price = work_lines_sum + pmma_sum

    def _prepare_invoice_vals(self):
        self.ensure_one()
        lines = []
        for line in self.work_order_line_ids:
            name = line.product_tmpl_id.name
            if line.description:
                name += " - %s" % line.description
            if line.teeth:
                name += _(" (teeth: %s)", line.teeth)
            lines.append(Command.create({
                'product_id': line.product_tmpl_id.product_variant_id.id,
                'name': name,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
            }))
        # Only the validated PMMA line is billed; failed trial pieces are not
        for pmma in self.pmma_line_ids.filtered(lambda l: l.state == 'validated'):
            lines.append(Command.create({
                'name': _("PMMA - %s", pmma.description or self.name),
                'quantity': pmma.qty,
                'price_unit': pmma.unit_price,
            }))
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        }

    def action_create_invoice(self):
        if not self.env.user.has_group('dental_lab.group_dental_lab_manager'):
            raise AccessError(_("Only Lab Managers can create invoices."))
        for order in self:
            if order.state != 'done':
                raise UserError(_("Only orders in the 'Done' state can be invoiced (%s).", order.name))
            if order.invoice_id and order.invoice_id.state != 'cancel':
                raise UserError(_("%s is already invoiced.", order.name))
            invoice = self.env['account.move'].with_company(order.company_id).create(
                order._prepare_invoice_vals())
            order.invoice_id = invoice
            order.message_post(body=_("Invoice created: %s", invoice.name or _("Draft")))
        if len(self) == 1:
            return self.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice for this work order."))
        return self.invoice_id.get_formview_action()



    def _get_grouped_invoice_partner(self):
        """Common dentist, or the common parent company if the orders come from different contacts of it."""
        partners = self.mapped('partner_id')
        if len(partners) == 1:
            return partners
        commercial = partners.mapped('commercial_partner_id')
        if len(commercial) == 1:
            return commercial
        raise UserError(_("All selected work orders must belong to the same dentist or to the same lab."))

    def action_create_grouped_invoice(self):
        if not self.env.user.has_group('dental_lab.group_dental_lab_manager'):
            raise AccessError(_("Only Lab Managers can create invoices."))
        if not self:
            raise UserError(_("Select at least one work order."))

        not_done = self.filtered(lambda o: o.state != 'done')
        if not_done:
            raise UserError(_("Only orders in the 'Done' state can be invoiced: %s", ", ".join(not_done.mapped('name'))))
        already = self.filtered(lambda o: o.invoice_id and o.invoice_id.state != 'cancel')
        if already:
            raise UserError(_("Already invoiced: %s", ", ".join(already.mapped('name'))))
        if len(self.company_id) != 1:
            raise UserError(_("All selected work orders must belong to the same company."))
        if len(self.currency_id) != 1:
            raise UserError(_("All selected work orders must use the same currency."))

        partner = self._get_grouped_invoice_partner()
        orders = self.sorted(lambda o: (o.date_order, o.id))

        lines = []
        for order in orders:
            order_lines = order._prepare_invoice_vals()['invoice_line_ids']
            if not order_lines:
                continue
            section = order.name + (" - %s" % order.ref if order.ref else "")
            lines.append(Command.create({'display_type': 'line_section', 'name': section}))
            lines += order_lines
        if not lines:
            raise UserError(_("There is nothing to invoice on the selected work orders."))

        invoice = self.env['account.move'].with_company(orders.company_id).create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'currency_id': orders.currency_id.id,
            'company_id': orders.company_id.id,
            'invoice_origin': ", ".join(orders.mapped('name')),
            'invoice_line_ids': lines,
        })
        orders.invoice_id = invoice
        for order in orders:
            order.message_post(body=_("Invoice created: %s (grouped: %s)",invoice.name or _("Draft"), ", ".join(orders.mapped('name'))))
        return invoice.get_formview_action()



        # ------------------------------------------------------------------
    # exocad integration
    # ------------------------------------------------------------------
    def _exocad_make_token(self):
        self.ensure_one()
        uid = self.env.uid
        expiry = int(time.time()) + EXOCAD_TOKEN_TTL
        sig = hmac_tool(self.env, EXOCAD_SCOPE, f"{self.id}:{uid}:{expiry}")
        return f"{uid}.{expiry}.{sig}"

    @api.model
    def _exocad_resolve_token(self, order_id, token):
        """Return the order browsed as the user who generated the token, or False."""
        try:
            uid, expiry, sig = (token or '').split('.')
            uid, expiry = int(uid), int(expiry)
        except ValueError:
            return False
        if expiry < time.time():
            return False
        expected = hmac_tool(self.env, EXOCAD_SCOPE, f"{order_id}:{uid}:{expiry}")
        if not consteq(expected, sig):
            return False
        user = self.env['res.users'].sudo().browse(uid).exists()
        if not user or not user.active:
            return False
        order = self.with_user(user).browse(order_id).exists()
        if not order:
            return False
        try:
            order.check_access('read')
        except AccessError:
            return False
        return order

    def _exocad_payload(self):
        """Order data sent to the exocad workstation (no prices)."""
        self.ensure_one()
        is_manager = self.env.user.has_group('dental_lab.group_dental_lab_manager')
        partner = self.partner_id.sudo()
        # Technicians never see the real dentist identity
        dentist = partner.name if is_manager else partner.anon_code
        lines = []
        all_teeth = set()
        for line in self.work_order_line_ids:
            teeth = line._get_teeth_list()
            all_teeth.update(teeth)
            lines.append({
                'element_type': line.product_tmpl_id.name or '',
                'description': line.description or '',
                'teeth': teeth,
                'quantity': line.quantity,
            })
        return {
            'id': self.id,
            'reference': self.name,
            'form_number': self.ref or '',
            'dentist': dentist or '',
            'patient_name': self.patient_name or '',
            'technician': self.technician_id.name or '',
            'shade': self.shade or '',
            'order_date': self.date_order.isoformat() if self.date_order else '',
            'due_date': self.date_due.isoformat() if self.date_due else '',
            'priority': 'urgent' if self.priority == '1' else 'normal',
            'notes': self.notes or '',
            'teeth': sorted(all_teeth, key=int),
            'lines': lines,
        }

    def action_open_exocad(self):
        self.ensure_one()
        if not self.env.user.has_group('dental_lab.group_dental_lab_technician'):
            raise AccessError(_("Only technicians and lab managers can open exocad."))
        self.message_post(body=_("exocad project requested by %s", self.env.user.name))
        query = urlencode({'order': self.id, 'token': self._exocad_make_token()})
        return {
            'type': 'ir.actions.client',
            'tag': 'dental_lab.open_exocad',
            'params': {'url': f"dentallab://exocad?{query}"},
        }