
from openerp import models, api


class pos_order(models.Model):
    _inherit = 'pos.order'

    @api.multi
    def get_l10n_fr_hash(self):
        return self.read(['pos_reference','l10n_fr_hash'])
