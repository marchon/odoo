# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_password_policy(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'minlength': int(params.get_param('auth_password_policy.minlength', default=0)),
        }

    def _set_password(self, password):
        if password:
            self._check_password_policy(password)

        super(ResUsers, self)._set_password(password)

    def _check_password_policy(self, password):
        failures = []
        params = self.env['ir.config_parameter'].sudo()

        minlength = int(params.get_param('auth_password_policy.minlength', default=0))
        if len(password) < minlength:
            failures.append(_(u"Passwords must have at least %d characters, got %d.") % (minlength, len(password)))

        if failures:
            raise UserError(u'\n\n '.join(failures))
