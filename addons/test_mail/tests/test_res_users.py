# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.test_mail.tests import common
from odoo.tests import tagged


@tagged('moderation')
class TestMessageModeration(common.Moderation):

    @classmethod
    def setUpClass(cls):
        super(TestMessageModeration, cls).setUpClass()

    def test_compute_is_moderator(self):
        self.assertTrue(self.clementine.is_moderator)
        self.assertFalse(self.env.user.is_moderator)
        self.assertTrue(self.roboute.is_moderator)

    def test_compute_moderation_counter(self):

        self._create_new_message(self.cm1id)
        self._create_new_message(self.cm1id, status='accepted')
        self._create_new_message(self.cm1id, status='accepted', author=self.cp)
        self._create_new_message(self.cm1id, author=self.rp)
        self._create_new_message(self.cm1id, status='accepted', author=self.rp)
        self._create_new_message(self.cm2id)
        self._create_new_message(self.cm2id, status='accepted')
        self._create_new_message(self.cm2id, author=self.cp)
        self._create_new_message(self.cm2id, status='accepted', author=self.cp)
        self._create_new_message(self.cm2id, status='accepted', author=self.rp)

        self.assertEqual(self.clementine.moderation_counter, 2)
        self.assertEqual(self.roboute.moderation_counter, 2)
        self.assertEqual(self.env.user.moderation_counter, 0)
