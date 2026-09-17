from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
import logging

class DentalLabPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'dental_order_count' in counters:
            DentalOrder = request.env['dental.lab.order']
            values['dental_order_count'] = (
                DentalOrder.search_count([('partner_id', '=', request.env.user.partner_id.id)])
                if DentalOrder.check_access_rights('read', raise_exception=False)
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
        }
        order_sudo.write(vals)
        return request.redirect('/my/dental-orders/%s' % order_sudo.id)