# -*- coding: utf-8 -*

from odoo.addons.bus.controllers.main import BusController
from odoo.http import request, route


class BroadcastController(BusController):

    @route('/broadcast/call', type="json", auth="user")
    def broadcast_call(self, partner_id, sdp, **kwargs):
        user_ids = request.env['res.partner'].browse(partner_id).user_ids
        request.env['bus.bus'].sendone((request.db, 'broadcast.call', user_ids.id), sdp)
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