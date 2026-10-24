from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request


class DentalLabExocad(http.Controller):

    def _get_order(self, order_id, token):
        order = request.env['dental.lab.order'].sudo()._exocad_resolve_token(order_id, token)
        if not order:
            raise Forbidden()
        return order

    @http.route('/dental_lab/exocad/order/<int:order_id>',type='http', auth='public', methods=['GET'])
    def exocad_order(self, order_id, token=None, **kw):
        order = self._get_order(order_id, token)
        payload = order._exocad_payload()
        payload['attachments'] = [{
            'name': att.name,
            'url': f"/dental_lab/exocad/order/{order.id}/attachment/{att.id}?token={token}",
        } for att in order.sudo().attachment_ids if att.type == 'binary']
        return request.make_json_response(payload)

    @http.route('/dental_lab/exocad/order/<int:order_id>/attachment/<int:attachment_id>',type='http', auth='public', methods=['GET'])
    def exocad_attachment(self, order_id, attachment_id, token=None, **kw):
        order = self._get_order(order_id, token)
        attachment = order.sudo().attachment_ids.filtered(
            lambda a: a.id == attachment_id and a.type == 'binary')
        if not attachment:
            raise Forbidden()
        stream = request.env['ir.binary'].sudo()._get_stream_from(attachment, 'raw')
        return stream.get_response(as_attachment=True)