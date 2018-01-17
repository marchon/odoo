from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _push_apply(self):
        """
        Select and apply the correct push rule according to the routes configurations.

        This override differs from the standard implementation found in the standard `stock` module
        by taking the push rules of the routes into account (by contrast, only the push rules of the
        product or product category are taken into account in the standard implementation).
        """
        Push = self.env['stock.location.path']
        for move in self:
            # if the move is already chained, there is no need to check push rules
            if move.move_dest_id:
                continue
            # if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            # to receive goods without triggering the push rules again (which would duplicate chained operations)
            domain = [('location_from_id', '=', move.location_dest_id.id)]
            # first priority goes to the preferred routes defined on the move itself (e.g. coming from a PO)
            routes = move.route_ids
            rules = Push.search(domain + [('route_id', 'in', routes.ids)], order='route_sequence, sequence', limit=1)
            # second priority goes to the route defined on the product and product category
            if not rules:
                routes = move.route_ids | move.product_id.route_ids | move.product_id.categ_id.total_route_ids
                rules = Push.search(domain + [('route_id', 'in', routes.ids)], order='route_sequence, sequence', limit=1)
            if not rules:
                # TDE FIXME/ should those really be in a if / elif ??
                # then we search on the warehouse if a rule can apply
                if move.warehouse_id:
                    rules = Push.search(domain + [('route_id', 'in', move.warehouse_id.route_ids.ids)], order='route_sequence, sequence', limit=1)
                elif move.picking_id.picking_type_id.warehouse_id:
                    rules = Push.search(domain + [('route_id', 'in', move.picking_id.picking_type_id.warehouse_id.route_ids.ids)], order='route_sequence, sequence', limit=1)
            if not rules:
                # if no specialized push rule has been found yet, we try to find a general one (without route)
                rules = Push.search(domain + [('route_id', '=', False)], order='sequence', limit=1)
            # Make sure it is not returning the return
            if rules and (not move.origin_returned_move_id or move.origin_returned_move_id.location_dest_id.id != rules.location_dest_id.id):
                rules._apply(move)
        return True