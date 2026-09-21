from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
import logging
import re

class DentalLabPortal(CustomerPortal):
    
    LINE_FIELD_RE = re.compile(r'^lines-(\d+)-work_type$')

    def _prepare_line_commands(self, post, existing_line_ids=None):
        existing_line_ids = set(existing_line_ids or [])
        indices = set()
        for key in post.keys():
            m = self.LINE_FIELD_RE.match(key)
            if m:
                indices.add(int(m.group(1)))

        commands = []
        kept_line_ids = set()
        for i in sorted(indices):
            prefix = 'lines-%s-' % i
            work_type = post.get(prefix + 'work_type')
            teeth = post.get(prefix + 'teeth')
            if not work_type and not teeth:
                continue
            quantity = int(post.get(prefix + 'quantity') or 1)
            vals = {
                'work_type': work_type or False,
                'teeth': teeth,
                'description': post.get(prefix + 'description'),
                'quantity': max(quantity, 1),
                'is_implant': bool(post.get(prefix + 'is_implant')),
            }
            raw_line_id = post.get(prefix + 'line_id')
            line_id = int(raw_line_id) if raw_line_id and raw_line_id.isdigit() else False
            # Only accept a line_id that genuinely belongs to this order — never
            # trust a client-submitted id blindly, or a portal user could pass
            # someone else's line id and overwrite it via (1, id, vals).
            if line_id and line_id in existing_line_ids:
                kept_line_ids.add(line_id)
                commands.append((1, line_id, vals))
            else:
                commands.append((0, 0, vals))
        # Any existing line whose id wasn't resubmitted was removed in the UI
        for removed_id in existing_line_ids - kept_line_ids:
            commands.append((2, removed_id, 0))
        return commands

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'dental_order_count' in counters:
            DentalOrder = request.env['dental.lab.order']
            values['dental_order_count'] = (
                DentalOrder.search_count([('partner_id', '=', request.env.user.partner_id.id)])
                if DentalOrder.check_access('read')
                else 0
            )
        return values

    def _dental_order_get_page_view_values(self, order, access_token, **kwargs):
        values = {'order': order}
        return self._get_page_view_values(
            order, access_token, values, 'my_dental_orders_history', False, **kwargs
        )

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
        }

        sortby = sortby or 'date'
        order = searchbar_sortings[sortby]['order']
        filterby = filterby or 'all'
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
        return request.render('dental_lab.portal_dental_order_form', {'page_name': 'dental_order_new'})

    @http.route(['/my/dental-orders/submit'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_dental_order_submit(self, **post):
        vals = {
            'partner_id': request.env.user.partner_id.id,
            'patient_name': post.get('patient_name'),
            'shade': post.get('shade'),
            'date_due': post.get('date_due') or False,
            'priority': post.get('priority') or '0',
            'notes': post.get('notes'),
            'work_order_line_ids': self._prepare_line_commands(post),
        }
        order = request.env['dental.lab.order'].sudo().create(vals)
        return request.redirect('/my/dental-orders/%s' % order.id)

    @http.route(['/my/dental-orders/<int:order_id>'], type='http', auth='user', website=True)
    def portal_dental_order_detail(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('dental.lab.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._dental_order_get_page_view_values(order_sudo, access_token, **kw)
        return request.render('dental_lab.portal_dental_order_page', values)


    #Edit route
    @http.route(['/my/dental-orders/<int:order_id>/edit'], type='http', auth='user', website=True, methods=['GET'])
    def portal_dental_order_edit(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('dental.lab.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state != 'draft':
            return request.redirect('/my/dental-orders/%s' % order_sudo.id)

        values = self._dental_order_get_page_view_values(order_sudo, access_token, **kw)
        return request.render('dental_lab.portal_dental_order_edit_form', values)

    #Update route
    @http.route(['/my/dental-orders/<int:order_id>/update'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_dental_order_update(self, order_id, **post):
        try:
            order_sudo = self._document_check_access('dental.lab.order', order_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state != 'draft':
            return request.redirect('/my/dental-orders/%s' % order_sudo.id)

        vals = {
            'patient_name': post.get('patient_name'),
            'shade': post.get('shade'),
            'date_due': post.get('date_due') or False,
            'priority': post.get('priority') or '0',
            'notes': post.get('notes'),
            'work_order_line_ids': self._prepare_line_commands(post, existing_line_ids=order_sudo.work_order_line_ids.ids),
        }
        order_sudo.write(vals)
        return request.redirect('/my/dental-orders/%s' % order_sudo.id)