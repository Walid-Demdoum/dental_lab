from odoo import models,_

class MailMessage(models.Model):
    _inherit = "mail.message"

    def _author_to_store(self, store):
        super()._author_to_store(store)
        Partner = self.env["res.partner"]
        # Only anonymize for technicians who are not managers.
        if not Partner._is_restricted_technician():
            return super()._author_to_store(store)
        for message in self:
            author = message.sudo().author_id
            if (author and author.partner_type == "dentist"):
                store.add(author,{"name": author.anon_code or _("Hidden")})

