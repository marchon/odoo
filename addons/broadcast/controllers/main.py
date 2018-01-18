# -*- coding: utf-8 -*

from odoo.addons.bus.controllers.main import BusController
from odoo.http import request


class BroadcastController(BusController):
    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = list(channels)
            for partner in request.env['res.partner'].search([('user_ids', '!=', None)]):
                channels.append((request.db, 'broadcast.desc', partner.id))
            # channels.append((request.db, 'broadcast.desc', request.env.user.partner_id.id))

        return super(BroadcastController, self)._poll(dbname, channels, last, options)
