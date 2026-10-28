import base64
import datetime
import os
import re
import types

from odoo import http, _
# from odoo.addons.dental_lab.models.dental_lab_order_line import FDI_TEETH
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request


FDI_TEETH = {str(q * 10 + n) for q in range(1, 5) for n in range(1, 9)}


class DentalLabPortal(CustomerPortal):

    MAX_ATTACHMENT_SIZE = 100 * 1024 * 1024  # 50 MB
    ALLOWED_ATTACHMENT_EXT = ('.stl', '.obj', '.rar', '.zip')  # keep in sync with the <input accept>
    LINE_FIELD_RE = re.compile(r'^lines-(\d+)-')
    VALID_PRIORITIES = ('0', '1')
    DENTAL_PRODUCT_DOMAIN = [('sale_ok', '=', True),('type','=','service')]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_dental_products(self):
        return request.env['product.template'].sudo().search(self.DENTAL_PRODUCT_DOMAIN)

    def _parse_order_vals(self, post):
        """Validate the header fields.

        :return: (vals, errors, form_values) -- form_values echoes what the user typed
                 so the form can be re-displayed untouched when there are errors.
        """
        errors = []
        patient_name = (post.get('patient_name') or '').strip()
        shade = (post.get('shade') or '').strip()
        notes = post.get('notes') or ''
        raw_priority = post.get('priority')
        priority = raw_priority if raw_priority in self.VALID_PRIORITIES else '0'
        raw_due = (post.get('date_due') or '').strip()

        if not patient_name:
            errors.append(_("Patient name is required."))
        due_date = False
        if raw_due:
            try:
                due_date = datetime.date.fromisoformat(raw_due)
            except ValueError:
                errors.append(_("The due date is not a valid date."))

        vals = {
            'patient_name': patient_name,
            'shade': shade,
            'date_due': due_date,
            'priority': priority,
            'notes': notes,
        }
        form_values = {
            'patient_name': patient_name,
            'shade': shade,
            'date_due': raw_due,
            'priority': priority,
            'notes': notes,
        }
        return vals, errors, form_values

    def _parse_lines(self, post, existing_line_ids=None):
        """Validate the submitted lines.

        :return: (commands, errors, form_lines). ``commands`` is only meaningful when
                 ``errors`` is empty. ``form_lines`` are light objects used to re-display
                 the rows exactly as submitted.
        """
        existing_line_ids = set(existing_line_ids or [])
        Product = request.env['product.template'].sudo()
        allowed_product_ids = set(self._get_dental_products().ids)

        indices = sorted({int(m.group(1)) for key in post for m in [self.LINE_FIELD_RE.match(key)] if m})

        commands, errors, form_lines = [], [], []
        kept_line_ids = set()
        for i in indices:
            prefix = 'lines-%s-' % i
            raw_product = (post.get(prefix + 'product_tmpl_id') or '').strip()
            product_id = int(raw_product) if raw_product.isdigit() else False
            teeth_list = [t.strip() for t in (post.get(prefix + 'teeth') or '').split(',') if t.strip()]
            description = (post.get(prefix + 'description') or '').strip()

            if not product_id and not teeth_list and not description:
                continue  # blank row left in the UI

            row_no = len(form_lines) + 1
            if product_id not in allowed_product_ids:
                product_id = False
                errors.append(_("Line %s: select an element type.", row_no))
            if not teeth_list:
                errors.append(_("Line %s: select at least one tooth.", row_no))
            else:
                invalid = [t for t in teeth_list if t not in FDI_TEETH]
                if invalid:
                    errors.append(_("Line %(line)s: invalid tooth number(s): %(teeth)s",
                                    line=row_no, teeth=", ".join(invalid)))
                if len(set(teeth_list)) != len(teeth_list):
                    errors.append(_("Line %s: a tooth is selected twice.", row_no))

            raw_line_id = (post.get(prefix + 'line_id') or '').strip()
            line_id = int(raw_line_id) if raw_line_id.isdigit() else False
            # Never trust a client-submitted id: only lines of THIS order may be updated.
            if line_id not in existing_line_ids:
                line_id = False

            teeth = ", ".join(teeth_list)
            form_lines.append(types.SimpleNamespace(
                id=line_id, teeth=teeth, description=description,
                product_tmpl_id=Product.browse(product_id) if product_id else Product,
                quantity=len(teeth_list) or 1,
            ))
            vals = {'product_tmpl_id': product_id, 'teeth': teeth, 'description': description}
            if line_id:
                kept_line_ids.add(line_id)
                commands.append((1, line_id, vals))
            else:
                commands.append((0, 0, vals))

        if not form_lines:
            errors.append(_("Add at least one work line."))

        # Existing lines that were not resubmitted were removed in the UI.
        for removed_id in existing_line_ids - kept_line_ids:
            commands.append((2, removed_id, 0))
        return commands, errors, form_lines

    def _read_attachments(self, files):
        """Validate uploads *before* anything is saved.

        :return: (valid, errors) where valid is a list of (filename, bytes).
        """
        valid, errors = [], []
        max_mb = self.MAX_ATTACHMENT_SIZE // (1024 * 1024)
        for file in files:
            if not file or not file.filename:
                continue
            name = os.path.basename(file.filename)
            if os.path.splitext(name)[1].lower() not in self.ALLOWED_ATTACHMENT_EXT:
                errors.append(_("%(name)s: unsupported format (allowed: %(ext)s).",
                                name=name, ext=", ".join(self.ALLOWED_ATTACHMENT_EXT)))
                continue
            content = file.read(self.MAX_ATTACHMENT_SIZE + 1)  # never load more than the limit
            if not content:
                errors.append(_("%s: the file is empty.", name))
            elif len(content) > self.MAX_ATTACHMENT_SIZE:
                errors.append(_("%(name)s: the file is too large (max %(size)s MB).", name=name, size=max_mb))
            else:
                valid.append((name, content))
        return valid, errors

    def _create_order_attachments(self, order_sudo, files):
        Attachment = request.env['ir.attachment'].sudo()
        for name, content in files:
            Attachment.create({
                'name': name,
                'datas': base64.b64encode(content),
                'res_model': 'dental.lab.order',
                'res_id': order_sudo.id,
                'public': False,
            })

    def _render_order_form(self, order_sudo, errors, form_values, form_lines):
        """Re-display the create/edit form with the errors and the user's input."""
        if request.httprequest.files.getlist('attachments') and any(
                f and f.filename for f in request.httprequest.files.getlist('attachments')):
            errors = errors + [_("Nothing was saved: please select your attached files again.")]
        extra = {'errors': errors, 'form_values': form_values, 'form_lines': form_lines}
        if order_sudo:
            values = self._dental_order_get_page_view_values(order_sudo, None)
            values.update(extra)
            return request.render('dental_lab.portal_dental_order_edit_form', values)
        values = {'page_name': 'dental_order_new', 'products': self._get_dental_products(), 'order': False}
        values.update(extra)
        return request.render('dental_lab.portal_dental_order_form', values)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'dental_order_count' in counters:
            DentalOrder = request.env['dental.lab.order']
            values['dental_order_count'] = (
                DentalOrder.search_count([('partner_id', '=', request.env.user.partner_id.id)])
                if DentalOrder.has_access('read')
                else 0
            )
        return values

    def _dental_order_get_page_view_values(self, order, access_token, **kwargs):
        values = {'order': order, 'products': self._get_dental_products()}
        return self._get_page_view_values(
            order, access_token, values, 'my_dental_orders_history', False, **kwargs
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route(['/my/dental-orders', '/my/dental-orders/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_dental_orders(self, page=1, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        DentalOrder = request.env['dental.lab.order']
        domain = [('partner_id', '=', request.env.user.partner_id.id)]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('New'), 'domain': [('state', '=', 'draft')]},
            'in_progress': {'label': _('In Progress'), 'domain': [('state', '=', 'in_progress')]},
            'done': {'label': _('Done'), 'domain': [('state', '=', 'done')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
        }

        sortby = sortby if sortby in searchbar_sortings else 'date'
        order = searchbar_sortings[sortby]['order']
        filterby = filterby if filterby in searchbar_filters else 'all'
        domain += searchbar_filters[filterby]['domain']

        order_count = DentalOrder.search_count(domain)
        pager = portal_pager(
            url='/my/dental-orders',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=order_count,
            page=page,
            step=self._items_per_page,
        )
        orders = DentalOrder.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'orders': orders,
            'page_name': 'dental_order',
            'pager': pager,
            'default_url': '/my/dental-orders',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render('dental_lab.portal_my_dental_orders', values)

    @http.route(['/my/dental-orders/new'], type='http', auth='user', website=True, methods=['GET'])
    def portal_dental_order_new(self, **kw):
        return request.render('dental_lab.portal_dental_order_form', {
            'page_name': 'dental_order_new',
            'products': self._get_dental_products(),
        })

    @http.route(['/my/dental-orders/submit'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_dental_order_submit(self, **post):
        vals, errors, form_values = self._parse_order_vals(post)
        commands, line_errors, form_lines = self._parse_lines(post)
        files, file_errors = self._read_attachments(request.httprequest.files.getlist('attachments'))
        errors += line_errors + file_errors

        if not errors:
            vals.update({
                'partner_id': request.env.user.partner_id.id,
                'work_order_line_ids': commands,
            })
            try:
                # Savepoint: a failed constraint must not leave a half-created order behind.
                with request.env.cr.savepoint():
                    order = request.env['dental.lab.order'].sudo().with_context(
                        mail_create_nosubscribe=True,  # do not auto-follow the dentist (privacy)
                    ).create(vals)
                    self._create_order_attachments(order, files)
            except (ValidationError, UserError) as exc:
                errors.append(exc.args[0] if exc.args else str(exc))
            else:
                return request.redirect('/my/dental-orders/%s' % order.id)
        return self._render_order_form(False, errors, form_values, form_lines)

    @http.route(['/my/dental-orders/<int:order_id>'], type='http', auth='user', website=True)
    def portal_dental_order_detail(self, order_id, **kw):
        try:
            order_sudo = self._document_check_access('dental.lab.order', order_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._dental_order_get_page_view_values(order_sudo, None, **kw)
        return request.render('dental_lab.portal_dental_order_page', values)

    @http.route(['/my/dental-orders/<int:order_id>/edit'], type='http', auth='user', website=True, methods=['GET'])
    def portal_dental_order_edit(self, order_id, **kw):
        try:
            order_sudo = self._document_check_access('dental.lab.order', order_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state != 'draft':
            return request.redirect('/my/dental-orders/%s' % order_sudo.id)

        values = self._dental_order_get_page_view_values(order_sudo, None, **kw)
        return request.render('dental_lab.portal_dental_order_edit_form', values)

    @http.route(['/my/dental-orders/<int:order_id>/update'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_dental_order_update(self, order_id, **post):
        try:
            order_sudo = self._document_check_access('dental.lab.order', order_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state != 'draft':
            return request.redirect('/my/dental-orders/%s' % order_sudo.id)

        vals, errors, form_values = self._parse_order_vals(post)
        commands, line_errors, form_lines = self._parse_lines(
            post, existing_line_ids=order_sudo.work_order_line_ids.ids)
        files, file_errors = self._read_attachments(request.httprequest.files.getlist('attachments'))
        errors += line_errors + file_errors

        if not errors:
            vals['work_order_line_ids'] = commands
            try:
                with request.env.cr.savepoint():
                    order_sudo.write(vals)
                    self._create_order_attachments(order_sudo, files)
            except (ValidationError, UserError) as exc:
                errors.append(exc.args[0] if exc.args else str(exc))
            else:
                return request.redirect('/my/dental-orders/%s' % order_sudo.id)
        return self._render_order_form(order_sudo, errors, form_values, form_lines)

    @http.route(['/my/dental-orders/<int:order_id>/attachment/<int:attachment_id>/delete'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_dental_order_attachment_delete(self, order_id, attachment_id, **post):
        try:
            order_sudo = self._document_check_access('dental.lab.order', order_id)
        except (AccessError, MissingError):
            return request.make_json_response({'error': 'access_denied'}, status=403)

        attachment_sudo = request.env['ir.attachment'].sudo().browse(attachment_id)
        if attachment_sudo.exists() and attachment_sudo.res_model == 'dental.lab.order' and attachment_sudo.res_id == order_sudo.id:
            if order_sudo.state != 'draft':
                return request.make_json_response({'error': 'locked'}, status=403)
            attachment_sudo.unlink()
            return request.make_json_response({'success': True})
        return request.make_json_response({'error': 'not_found'}, status=404)