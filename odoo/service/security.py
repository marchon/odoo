# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.exceptions

def login(db, login, password):
    res_users = odoo.registry(db)['res.users']
    return res_users._login(db, login, password)

def check(db, uid, passwd):
    res_users = odoo.registry(db)['res.users']
    return res_users.check(db, uid, passwd)

def compute_session_token(db, sid, uid):
    with odoo.registry(db).cursor() as cr:
        self = odoo.api.Environment(cr, uid, {})['res.users']
        return self._compute_session_token(sid, uid)

def check_session(db, sid, uid, token):
    with odoo.registry(db).cursor() as cr:
        self = odoo.api.Environment(cr, uid, {})['res.users']
        if self._compute_session_token(sid, uid) == token:
            return True
        self._invalidate_session_cache()
        return False
