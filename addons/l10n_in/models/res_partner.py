# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    __check_vat_in_re = re.compile('\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[A-Z]{1}[A-Z\d]{1}')

    #validation for gstn number
    @api.constrains('vat')
    def check_gstn(self):
        for partner in self:
            if not partner.vat:
                continue
            country_in_id = self.env.ref('base.in').id
            if partner.country_id and partner.country_id.id != country_in_id:
                continue
            gstn_no = partner.vat
            if not self.__check_vat_in_re.match(gstn_no):
                #No valid format
                msg = _("The GSTN number [%s] for partner [%s] does not seem to be valid.") % (gstn_no, partner.name)
                raise ValidationError (msg)
            else:
                gstn_no_state = gstn_no[:2]
                if not partner.state_id:
                    raise ValidationError (_("You must select a state!"))
                if not partner.state_id.l10n_in_tin:
                    raise ValidationError (_("Please contact administrator.\n State [%s] TIN Number not set")%(partner.state_id.name))
                find_state_code = partner.state_id.l10n_in_tin
                if gstn_no_state != find_state_code:
                    #state code can't match with GSTN
                    msg = _("GSTN First Two digit represnet a State TIN Number.\nYour First Two digit of GSTN is [%s] and Your State TIN Number is [%s]!")%(gstn_no_state,find_state_code)
                    raise ValidationError(msg)
