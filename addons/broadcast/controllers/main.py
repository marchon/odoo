# -*- coding: utf-8 -*

from odoo.addons.bus.controllers.main import BusController
from odoo.http import request, route
import json


class BroadcastController(BusController):

    @route('/broadcast/call', type="json", auth="user")
    def broadcast_call(self, partner_id, sdp, **kwargs):
        user_ids = request.env['res.partner'].browse(partner_id).user_ids
        request.env['bus.bus'].sendone((request.db, 'broadcast.call', user_ids.id), json.dumps({
            'partner_id': request.env.user.partner_id.id,
            'user_id': request.uid,
            'type': 'call',
            'sdp': sdp,
        }))
        return True

    @route('/broadcast/disconnect', type="json", auth="user")
    def broadcast_disconnect(self, partner_id, **kwargs):
        user_ids = request.env['res.partner'].browse(partner_id).user_ids
        request.env['bus.bus'].sendone((request.db, 'broadcast.call', user_ids.id), json.dumps({
            'partner_id': request.env.user.partner_id.id,
            'user_id': request.uid,
            'type': 'disconnect',
        }))
        return True

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = list(channels)
            channels.append((request.db, 'broadcast.call', request.uid))
        return super(BroadcastController, self)._poll(dbname, channels, last, options)




# class Channel(models.Model):
#     """ A mail.channel is a discussion group that may behave like a listener
#     on documents. """
#     _description = 'Discussion channel'
#     _name = 'mail.channel'