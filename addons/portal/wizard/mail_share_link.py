# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import werkzeug.urls

from odoo import api, fields, models


class MailShareLink(models.TransientModel):
    _name = 'mail.share.link'

    def default_share_link(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        res = False
        if active_model:
            model = self.env[active_model]
            if isinstance(model, self.pool['portal.mixin']):
                doc_url = model.browse(active_id).portal_url
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                res = base_url + doc_url
        return res

    share_link = fields.Char(string="Document link", default=default_share_link)
    partner_ids = fields.Many2many('res.partner', string="Recipients", required=True)
    note = fields.Text(help="Add extra content that user want to display in sent mail")

    @api.multi
    def send_mail_action(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        active_record = self.env[active_model].browse(active_id)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        template = self.env.ref('portal.mail_template_share_document_portal')
        note = self.env.ref('mail.mt_note')

        user_partner_ids = self.partner_ids.filtered(lambda x: x.user_ids)
        # if partner already user send common link in batch to all user
        if user_partner_ids:
            query = dict(redirect=active_record.portal_url, db=self.env.cr.dbname)
            share_link = werkzeug.urls.url_join(base_url, "/web/login?%s" % werkzeug.urls.url_encode(query))
            active_record.with_context(share_link=share_link, mail_post_autofollow=True, note=self.note).message_post_with_template(template.id, subtype_id=note.id, partner_ids=[(6, 0, user_partner_ids.ids)])
        # when partner not user send invidual mail with signup token
        for partner in self.partner_ids - user_partner_ids:
            share_link = partner.with_context(signup_valid=True).signup_url+'&redirect='+active_record.portal_url
            active_record.with_context(share_link=share_link, mail_post_autofollow=True, note=self.note).message_post_with_template(template.id, subtype_id=note.id, partner_ids=[(6, 0, partner.ids)])
        return {'type': 'ir.actions.act_window_close'}
