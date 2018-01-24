# -*- coding: utf-8 -*

from odoo.addons.bus.controllers.main import BusController
from odoo.addons.bus.models.bus import json_dump
from odoo.http import request, route


class BroadcastController(BusController):

    @route('/broadcast/call', type="json", auth="user")
    def broadcast_call(self, partner_id, **kwargs):
        user_id = request.env['res.partner'].sudo().browse(partner_id).user_ids.id
        message = dict(kwargs, partner_id=request.env.user.partner_id.id, user_id=request.uid)

        if message['type'] == "call":
            channel = json_dump((request.db, 'broadcast', user_id))
            messages = request.env['bus.bus'].sudo().search([
                ('channel', '=', channel),
                ('message', 'like', 'partner_id:%s' % message['partner_id']),
                ('message', 'like', 'user_id:%s' % request.uid)
            ])
            messages.unlink()

        request.env['bus.bus'].sendone((request.db, 'broadcast', user_id), json_dump(message))
        return True

    @route('/broadcast/disconnect', type="json", auth="user")
    def broadcast_disconnect(self, partner_id, **kwargs):
        user_id = request.env['res.partner'].sudo().browse(partner_id).user_ids.id
        message = dict(kwargs,
            partner_id=request.env.user.partner_id.id,
            user_id=request.uid,
            type='disconnect')

        channel = json_dump((request.db, 'broadcast', user_id))
        messages = request.env['bus.bus'].sudo().search([
            ('channel', '=', channel),
            ('message', 'like', 'partner_id:%s' % message['partner_id']),
            ('message', 'like', 'user_id:%s' % request.uid)
        ])
        messages.unlink()

        request.env['bus.bus'].sendone((request.db, 'broadcast', user_id), json_dump(message))
        return True

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = list(channels)
            channels.append((request.db, 'broadcast', request.uid))
        return super(BroadcastController, self)._poll(dbname, channels, last, options)
