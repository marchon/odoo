# -*- coding: utf-8 -*-
import collections
import logging

from datetime import datetime, timedelta

from odoo import models, registry
from odoo.exceptions import AccessDenied


_logger = logging.getLogger(__name__)
class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def _on_login_cooldown(cls, failures, previous):
        """ Decides whether the user trying to log in is currently
        "on cooldown" and not even allowed to attempt logging in.

        The default cooldown function simply puts the user on cooldown for 1mn
        after each failure following the 5th.

        Can be overridden to implement more complex backoff strategies, or
        e.g. wind down or reset the cooldown period as the previous failure
        recedes into the far past.

        :param int failures: number of recorded failures (since last success)
        :param datetime previous: timestamp of previous failure
        :returns: whether the user is currently in cooldown phase (true if cooldown, false if no cooldown and login can continue)
        :rtype: bool
        """
        return failures >= 5 and (datetime.now() - previous) < timedelta(minutes=1)

    @classmethod
    def _login(cls, db, login, password):
        reg = registry()
        failures_map = getattr(reg, '_login_failures', None)
        if failures_map is None:
            failures_map = reg._login_failures = collections.defaultdict(lambda : (0, datetime.min))

        (failures, previous) = failures_map[login]
        if cls._on_login_cooldown(failures, previous):
            _logger.warn("Login attempt ignored for %s on %s: %d login failed, last failure at %s", login, db, failures, previous)
            return False

        uid = super(ResUsers, cls)._login(db, login, password)

        if uid:
            reg._login_failures.pop(login, None)
        else:
            (count, _) = reg._login_failures[login]
            reg._login_failures[login] = (count + 1, datetime.now())

        return uid
