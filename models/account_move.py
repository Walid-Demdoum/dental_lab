from odoo import models,fields,api,_


class AccountMove(models.Model):
    _inherit = 'account.move'

    work_order_ids = fields.One2many('dental.lab.order', 'invoice_id', string="Dental orders")


    def _get_dental_report_patient(self):
        """Patient name when the invoice covers exactly one work order."""
        self.ensure_one()
        orders = self.work_order_ids.sudo()
        return orders.patient_name if len(orders) == 1 else ''

    def _get_dental_report_blocks(self):
        """Group invoice lines by section (one section per work order on grouped invoices).

        Returns a list of dicts: {'section': line|False, 'patient': str, 'lines': list, 'subtotal': float}
        Notes (line_note) stay inside the block where they were written.
        """
        self.ensure_one()
        orders = {o.name: o for o in self.work_order_ids.sudo()}
        blocks = []
        current = {'section': False, 'patient': '', 'lines': [], 'subtotal': 0.0}
        for line in self.invoice_line_ids.sorted(lambda l: (l.sequence, l.id)):
            if line.display_type == 'line_section':
                if current['section'] or current['lines']:
                    blocks.append(current)
                order = orders.get((line.name or '').split(' - ')[0].strip())
                current = {
                    'section': line,
                    'patient': order.patient_name if order else '',
                    'lines': [],
                    'subtotal': 0.0,
                }
                continue
            current['lines'].append(line)
            if line.display_type == 'product':
                current['subtotal'] += line.price_subtotal
        if current['section'] or current['lines']:
            blocks.append(current)
        return blocks