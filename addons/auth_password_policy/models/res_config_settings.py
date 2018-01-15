import re

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    minlength = fields.Integer("Minimum Length", help="Minimum number of characters passwords must contain.")
    minwords = fields.Integer("Minimum Words Count", help="Minimum number of words a password must contain. A word is a sequence of alphanumeric symbols, words are separated by any non-alphanumeric symbol.")
    minclasses = fields.Integer("Character classes", help="Minimum number of character classes the password must contain. There are 4 character classes: lowercase letters, uppercase letters, digits, and symbols. Any number higher than 4 will be clamped to that value.")

    preset = fields.Selection([
        # {minlength}-{minwords}-{minclasses}
        ('16-2-0', "At least 2 words and 16 characters (recommended)"),
        ('12-2-0', "At least 2 words and 12 characters"),
        ('20-0-3', "At least 3 classes and 20 characters"),
        ('16-0-3', "At least 3 classes and 16 characters"),
        ('12-0-3', "At least 3 classes and 12 characters"),
        ('20-0-0', "At least 20 characters"),
        ('16-0-0', "At least 16 characters"),
        ('12-0-0', "At least 12 characters"),
        ('8-0-4', "Every class and at least 8 characters"),
        ('0-0-0', "None"),
        ('custom', "Custom Password Policy")
    ], "Preset", required=True, help="""
Pre-defined password policies. 

"Custom" allows configuring your own. 
""")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        params = self.env['ir.config_parameter'].sudo()
        res['minlength'] = int(params.get_param('auth_password_policy.minlength', default=0))
        res['minwords'] = int(params.get_param('auth_password_policy.minwords', default=0))
        res['minclasses'] = int(params.get_param('auth_password_policy.minclasses', default=0))

        res['preset'] = '%(minlength)d-%(minwords)d-%(minclasses)d' % res
        if res['preset'] == '0-0-0':
            res['preset'] = False
        elif res['preset'] not in self._fields['preset'].get_values(self.env):
            res['preset'] = 'custom'

        return res

    @api.model
    def set_values(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('auth_password_policy.minclasses', self.minclasses)
        params.set_param('auth_password_policy.minwords', self.minwords)
        params.set_param('auth_password_policy.minlength', self.minlength)

        super(ResConfigSettings, self).set_values()

    @api.onchange('minlength', 'minwords', 'minclasses')
    def _on_change_mins(self):
        """ Password lower bounds must be naturals, minclasses is also
        high-bound to 4
        """
        self.minlength = max(0, self.minlength or 0)
        self.minwords = max(0, self.minwords or 0)
        self.minclasses = min(4, max(0, self.minclasses or 0))

    @api.onchange('preset')
    def _on_change_preset(self):
        # apparently can't disable "" option (=False), so handle preset=False
        m = re.match(r'(\d+)-(\d+)-(\d+)', self.preset or '')
        if m:
            self.minlength, self.minwords, self.minclasses = map(int, m.groups())
