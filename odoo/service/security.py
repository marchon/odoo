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
    res_users = odoo.registry(db)['res.users']
    return res_users._compute_session_token(db, sid, uid)

def check_session(db, sid, uid, token):
    res_users = odoo.registry(db)['res.users']
    if res_users._compute_session_token(db, sid, uid) == token:
        return True
    res_users._invalid_session(db, uid, sid)
    return False
