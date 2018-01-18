# -*- coding: utf-8 -*-
import re
import unicodedata

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

        minwords = int(params.get_param('auth_password_policy.minwords', default=0))
        wordscount = len(re.split(r'[\W_]+', password))
        if wordscount < minwords:
            failures.append(_(u"Passwords must be composed of at least %d words (words are groups of letters and numbers separated by spaces or symbols), got %d.") % (minwords, wordscount))

        minclasses = int(params.get_param('auth_password_policy.minclasses', default=0))
        classescount = len({
            (
                # non-latin characters are classified as Lo (no upper/lower),
                # fold them into lowercase
                c in ('Ll', 'Lo'),
                # upper and title
                c in ('Lu', 'Lt'),
                # digits
                c.startswith('N'),
                # none of the above, Lm lost in the void?
                not c.startswith(('L', 'N'))
            )
            for c in map(unicodedata.category, password)
        })
        if classescount < minclasses:
            failures.append(_(u"Passwords must be composed of at least %d types of characters. Types of characters are 'non-uppercase letters', 'uppercase letters', 'numbers', and 'other symbols'.") % classescount)

        if failures:
            raise UserError(u'\n\n '.join(failures))
