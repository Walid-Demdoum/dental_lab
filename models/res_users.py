from odoo import models, _


class ResUsers(models.Model):
    _inherit = "res.users"

    def read(self, fields=None, load="_classic_read"):
        result = super().read(fields=fields, load=load)
        Partner = self.env["res.partner"]
        # Only anonymize for restricted technicians.
        if not Partner._is_restricted_technician():
            return result

        users = self.sudo().browse([values["id"]for values in result if "id" in values])
        users_by_id = {user.id: user for user in users}

        for values in result:
            user = users_by_id.get(values.get("id"))
            # Only portal users whose partner is a dentist.
            if not user or not user.share:
                continue

            partner = user.partner_id
            if partner.partner_type != "dentist":
                continue

            anon_code = partner.anon_code or _("Hidden")
            # Hide name,email and phone.
            if "name" in values:
                values["name"] = anon_code
            if "email" in values:
                values["email"] = False
            if "phone" in values:
                values["phone"] = False
            # Sanitize the display label in the many2one value.
            if values.get("partner_id"):
                values["partner_id"] = [partner.id,anon_code]

        return result