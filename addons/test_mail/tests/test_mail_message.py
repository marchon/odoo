# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.addons.test_mail.tests import common
from odoo.exceptions import AccessError, except_orm
from odoo.tools import mute_logger
from odoo.tests import tagged


class TestMessageValues(common.BaseFunctionalTest, common.MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMessageValues, cls).setUpClass()

        cls.alias_record = cls.env['mail.test'].with_context(cls._quick_create_ctx).create({
            'name': 'Pigs',
            'alias_name': 'pigs',
            'alias_contact': 'followers',
        })

        cls.Message = cls.env['mail.message'].sudo(cls.user_employee)

    def test_mail_message_values_basic(self):
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.Message.create({
            'reply_to': 'test.reply@example.com',
            'email_from': 'test.from@example.com',
        })
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, 'test.reply@example.com')
        self.assertEqual(msg.email_from, 'test.from@example.com')

    def test_mail_message_values_default(self):
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s <%s>' % (self.user_employee.name, self.user_employee.email))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_alias(self):
        alias_domain = 'example.com'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.alias')]).unlink()

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s <%s>' % (self.user_employee.name, self.user_employee.email))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_alias_catchall(self):
        alias_domain = 'example.com'
        alias_catchall = 'pokemon'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', alias_catchall)

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id, 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, '%s <%s@%s>' % (self.env.user.company_id.name, alias_catchall, alias_domain))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_document_no_alias(self):
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()

        msg = self.Message.create({
            'model': 'mail.test',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id)
        self.assertEqual(msg.reply_to, '%s <%s>' % (self.user_employee.name, self.user_employee.email))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_document_alias(self):
        alias_domain = 'example.com'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.alias')]).unlink()

        msg = self.Message.create({
            'model': 'mail.test',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id)
        self.assertEqual(msg.reply_to, '%s %s <%s@%s>' % (self.env.user.company_id.name, self.alias_record.name, self.alias_record.alias_name, alias_domain))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_document_alias_catchall(self):
        alias_domain = 'example.com'
        alias_catchall = 'pokemon'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', alias_domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', alias_catchall)

        msg = self.Message.create({
            'model': 'mail.test',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id)
        self.assertEqual(msg.reply_to, '%s %s <%s@%s>' % (self.env.user.company_id.name, self.alias_record.name, self.alias_record.alias_name, alias_domain))
        self.assertEqual(msg.email_from, '%s <%s>' % (self.user_employee.name, self.user_employee.email))

    def test_mail_message_values_no_auto_thread(self):
        msg = self.Message.create({
            'model': 'mail.test',
            'res_id': self.alias_record.id,
            'no_auto_thread': True,
        })
        self.assertIn('reply_to', msg.message_id)
        self.assertNotIn('mail.test', msg.message_id)
        self.assertNotIn('-%d-' % self.alias_record.id, msg.message_id)


class TestMessageAccess(common.BaseFunctionalTest, common.MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMessageAccess, cls).setUpClass()

        Users = cls.env['res.users'].with_context(cls._quick_create_user_ctx)
        cls.user_public = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_public').id])]})
        cls.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])]})

        Channel = cls.env['mail.channel'].with_context(cls._quick_create_ctx)
        # Pigs: base group for tests
        cls.group_pigs = Channel.create({
            'name': 'Pigs',
            'public': 'groups',
            'group_public_id': cls.env.ref('base.group_user').id})
        # Jobs: public group
        cls.group_public = Channel.create({
            'name': 'Jobs',
            'description': 'NotFalse',
            'public': 'public'})
        # Private: private gtroup
        cls.group_private = Channel.create({
            'name': 'Private',
            'public': 'private'})
        cls.message = cls.env['mail.message'].create({
            'body': 'My Body',
            'model': 'mail.channel',
            'res_id': cls.group_private.id,
        })

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_message_access_search(self):
        # Data: various author_ids, partner_ids, documents
        msg1 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A', 'subtype_id': self.ref('mail.mt_comment')})
        msg2 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A+B', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg3 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A Pigs', 'subtype_id': False,
            'model': 'mail.channel', 'res_id': self.group_pigs.id})
        msg4 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A+P Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_pigs.id,
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg5 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A+E Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_pigs.id,
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})
        msg6 = self.env['mail.message'].create({
            'subject': '_Test', 'body': 'A Birds', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'mail.channel', 'res_id': self.group_private.id})
        msg7 = self.env['mail.message'].sudo(self.user_employee).create({
            'subject': '_Test', 'body': 'B', 'subtype_id': self.ref('mail.mt_comment')})
        msg8 = self.env['mail.message'].sudo(self.user_employee).create({
            'subject': '_Test', 'body': 'B+E', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})

        # Test: Public: 2 messages (recipient)
        messages = self.env['mail.message'].sudo(self.user_public).search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg2 | msg4)

        # Test: Employee: 3 messages on Pigs Raoul can read (employee can read group with default values)
        messages = self.env['mail.message'].sudo(self.user_employee).search([('subject', 'like', '_Test'), ('body', 'ilike', 'A')])
        self.assertEqual(messages, msg3 | msg4 | msg5)

        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group) + 2 messages as author
        messages = self.env['mail.message'].sudo(self.user_employee).search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg3 | msg4 | msg5 | msg7 | msg8)

        # Test: Admin: all messages
        messages = self.env['mail.message'].search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg1 | msg2 | msg3 | msg4 | msg5 | msg6 | msg7 | msg8)

        # Test: Portal: 0 (no access to groups, not recipient)
        messages = self.env['mail.message'].sudo(self.user_portal).search([('subject', 'like', '_Test')])
        self.assertFalse(messages)

        # Test: Portal: 2 messages (public group with a subtype)
        self.group_pigs.write({'public': 'public'})
        messages = self.env['mail.message'].sudo(self.user_portal).search([('subject', 'like', '_Test')])
        self.assertEqual(messages, msg4 | msg5)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_mail_message_access_read_crash(self):
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.So we need to change all
        # except_orm to warning in mail module.)
        with self.assertRaises(except_orm):
            self.message.sudo(self.user_employee).read()

    @mute_logger('odoo.models')
    def test_mail_message_access_read_crash_portal(self):
        with self.assertRaises(except_orm):
            self.message.sudo(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_ok_portal(self):
        self.message.write({'subtype_id': self.ref('mail.mt_comment'), 'res_id': self.group_public.id})
        self.message.sudo(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_notification(self):
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(b'My attachment'),
            'name': 'doc.txt',
            'datas_fname': 'doc.txt'})
        # attach the attachment to the message
        self.message.write({'attachment_ids': [(4, attachment.id)]})
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.message.sudo(self.user_employee).read()
        # Test: Bert has access to attachment, ok because he can read message
        attachment.sudo(self.user_employee).read(['name', 'datas'])

    def test_mail_message_access_read_author(self):
        self.message.write({'author_id': self.user_employee.partner_id.id})
        self.message.sudo(self.user_employee).read()

    def test_mail_message_access_read_doc(self):
        self.message.write({'model': 'mail.channel', 'res_id': self.group_public.id})
        # Test: Bert reads the message, ok because linked to a doc he is allowed to read
        self.message.sudo(self.user_employee).read()

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_mail_message_access_create_crash_public(self):
        # Do: Bert creates a message on Pigs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].sudo(self.user_public).create({'model': 'mail.channel', 'res_id': self.group_pigs.id, 'body': 'Test'})

        # Do: Bert create a message on Jobs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].sudo(self.user_public).create({'model': 'mail.channel', 'res_id': self.group_public.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_crash(self):
        # Do: Bert create a private message -> ko, no creation rights
        with self.assertRaises(except_orm):
            self.env['mail.message'].sudo(self.user_employee).create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_doc(self):
        # TODO Change the except_orm to Warning
        Message = self.env['mail.message'].sudo(self.user_employee)
        # Do: Raoul creates a message on Jobs -> ok, write access to the related document
        Message.create({'model': 'mail.channel', 'res_id': self.group_public.id, 'body': 'Test'})
        # Do: Raoul creates a message on Priv -> ko, no write access to the related document
        with self.assertRaises(except_orm):
            Message.create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test'})

    def test_mail_message_access_create_private(self):
        self.env['mail.message'].sudo(self.user_employee).create({'body': 'Test'})

    def test_mail_message_access_create_reply(self):
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.env['mail.message'].sudo(self.user_employee).create({'model': 'mail.channel', 'res_id': self.group_private.id, 'body': 'Test', 'parent_id': self.message.id})


@tagged('moderation')
class TestMessageModeration(common.Moderation):

    @classmethod
    def setUpClass(cls):
        super(TestMessageModeration, cls).setUpClass()

        cls.admin1pm = cls._create_new_message(cls, cls.cm1id)
        cls.admin1a = cls._create_new_message(cls, cls.cm1id, status='accepted')
        cls.clementine1a = cls._create_new_message(cls, cls.cm1id, status='accepted', author=cls.cp)
        cls.roboute1pm = cls._create_new_message(cls, cls.cm1id, author=cls.rp)
        cls.roboute1a = cls._create_new_message(cls, cls.cm1id, status='accepted', author=cls.rp)
        cls.admin2pm = cls._create_new_message(cls, cls.cm2id)
        cls.admin2a = cls._create_new_message(cls, cls.cm2id, status='accepted')
        cls.clementine2pm = cls._create_new_message(cls, cls.cm2id, author=cls.cp)
        cls.clementine2a = cls._create_new_message(cls, cls.cm2id, status='accepted', author=cls.cp)
        cls.roboute2a = cls._create_new_message(cls, cls.cm2id, status='accepted', author=cls.rp)

        cls.admin1a._notify()
        cls.clementine1a._notify()
        cls.roboute1a._notify()
        cls.admin2a._notify()
        cls.clementine2a._notify()
        cls.roboute2a._notify()

    def test_message_fetch(self):
        admin_msgs = self.Message.message_fetch({'id': self.cm1id})
        clementine_msgs = self.Message.sudo(self.clementine).message_fetch({'id': self.cm1id})
        roboute_msgs = self.Message.sudo(self.roboute).message_fetch({'id': self.cm1id})
        for msg in admin_msgs:
            self.assertIn(msg, (self.admin1pm | self.admin1a | self.clementine1a | self.roboute1a).message_format())
        for msg in clementine_msgs:
            self.assertIn(msg, (self.admin1pm | self.admin1a | self.clementine1a | self.roboute1a | self.roboute1pm | self.roboute1a).message_format())
        for msg in roboute_msgs:
            self.assertIn(msg, (self.admin1a | self.clementine1a | self.roboute1a | self.roboute1pm).message_format())

        clementine_to_review = self.Message.sudo(self.clementine).message_fetch({'type': 'moderation'})
        for msg in clementine_to_review:
            self.assertIn(msg, (self.admin1pm | self.roboute1pm).message_format())

        self.clementine.moderation_channel_ids |= self.channel_moderation_2
        clementine_to_review = self.Message.sudo(self.clementine).message_fetch({'type': 'moderation'})
        for msg in clementine_to_review:
            self.assertIn(msg, (self.admin1pm | self.roboute1pm | self.clementine2pm | self.admin2pm).message_format())

    @mute_logger('odoo.models.unlink')
    def test_notify(self):
        # A pending moderation message needs to have field channel_ids empty. Moderators need to be able to notify a pending moderation message (in a channel they moderate).

        self._clear_bus()
        self.assertFalse(self.admin1pm.channel_ids)
        self.admin1pm.sudo(self.clementine)._notify()
        self.assertEqual(self.admin1pm.channel_ids.id, self.cm1id)
        self.assertEqual(self.Bus.search([]).channel, self._json_dumps((self.Message._cr.dbname, 'mail.channel', self.cm1id)))

    @mute_logger('odoo.models.unlink')
    def test_create_rejection_emails(self):
        self.env['mail.mail'].search([]).unlink()
        (self.admin1pm | self.roboute1pm).sudo(self.clementine).create_rejection_emails("Test", "Message to author")
        self.Mail.process_email_queue()
        self.assertEqual(len(self._mails), 2)

    @mute_logger('odoo.models.unlink')
    def test_moderate(self):
        self.env['mail.mail'].search([]).unlink()
        all_msgs = self.Message.search([('model', '=', 'mail.channel'), ('res_id', 'in', [self.cm1id, self.cm2id])])
        # Even the admin cannot moderate messages if not moderator.
        all_msgs.moderate('accept')
        all_msgs_modified = self.Message.search([('model', '=', 'mail.channel'), ('res_id', 'in', [self.cm1id, self.cm2id])])
        self.assertEqual(all_msgs, all_msgs_modified)
        # Only a moderator of a channel can access the pending moderation messages of that channel if not the author
        with self.assertRaises(AccessError):
            self.assertRaises(self.admin1pm.sudo(self.roboute).moderate('discard'))
        self.roboute1pm.sudo(self.roboute).moderate('accept')
        self.assertTrue(self.roboute1pm.moderation_status == 'pending_moderation')

        self.roboute1pm.sudo(self.clementine).moderate('accept')
        self.Mail.process_email_queue()
        self.assertEqual(len(self._mails), 1)

        self._clear_bus()
        self.admin1pm.sudo(self.clementine).moderate('discard')
        self.assertFalse(self.Message.browse(self.admin1pm.id).exists())
        self.assertEqual(len(self.env['bus.bus'].search([])), 2)

        self._clear_bus()
        self._clear_moderation_email()
        admin1pm2 = self._create_new_message(self.cm1id)
        adminpm3 = self._create_new_message(self.cm1id)
        self._create_new_message(self.cm1id)
        roboute1pm2 = self._create_new_message(self.cm1id, author=self.rp)
        self._create_new_message(self.cm1id)
        (admin1pm2 | adminpm3 | roboute1pm2).sudo(self.clementine).moderate('ban')
        self.assertEqual(self.Message.search([('author_id', '=', self.partner_admin.id)]), self.admin1a | self.admin2a | self.admin2pm)
        self.assertEqual(self.Message.search([('author_id', '=', self.rpid)]), self.roboute1a | self.roboute1pm | self.roboute2a)
        self.assertTrue(self.ModerationEmail.search([('email', '=', self.partner_admin.email), ('channel_id', '=', self.cm1id)]))
        self.assertTrue(self.ModerationEmail.search([('email', '=', self.roboute.email), ('channel_id', '=', self.cm1id)]))
        self.assertEqual(len(self.Bus.search([])), 3)

    def test_from_same_authors(self):
        admin1pm2 = self._create_new_message(self.cm1id)
        admin_messages_1 = self.admin1pm._from_same_authors()
        self.assertEqual(admin_messages_1, self.admin1pm | admin1pm2)

    def test_accept_and_notify(self):
        new_message = self._create_new_message(self.cm1id)
        new_message.sudo(self.clementine)._accept_and_notify()
        self.assertEqual(new_message.moderation_status, 'accepted')

    def test_notify_deletion_and_unlink(self):
        clementine1pm = self._create_new_message(self.cm1id, author=self.cp)
        roboute1pm3 = self._create_new_message(self.cm1id, author=self.rp)
        self._clear_bus()
        (clementine1pm | roboute1pm3)._notify_deletion_and_unlink()
        clementine_notif_msg = self.Bus.search([('channel', '=', self._json_dumps((self.Message._cr.dbname, 'res.partner', self.cpid)))]).message
        clementine_notif_msg = self._json_loads(clementine_notif_msg)
        roboute_notif_msg = self.Bus.search([('channel', '=', self._json_dumps((self.Message._cr.dbname, 'res.partner', self.rpid)))]).message
        roboute_notif_msg = self._json_loads(roboute_notif_msg)

        self.assertEqual(len(self.Bus.search([])), 2)

        self.assertEqual(set(clementine_notif_msg['message_ids']), set([clementine1pm.id, roboute1pm3.id]))
        self.assertEqual(roboute_notif_msg['message_ids'], [roboute1pm3.id])
        self.assertEqual(clementine_notif_msg['type'], 'deletion')
        self.assertEqual(roboute_notif_msg['type'], 'deletion')

    @mute_logger('odoo.models.unlink')
    def test_notify_moderators_and_author(self):
        self._clear_bus()
        self._clear_moderation_email()
        msg = self.channel_moderation_1.message_post(message_type='email', author_id=self.partner_admin.id)
        msg = self._json_loads(self._json_dumps(msg.message_format()[0]))
        clementine_notif_msg = self.Bus.search([('channel', '=', self._json_dumps((self.Message._cr.dbname, 'res.partner', self.cpid)))]).message
        admin_notif_msg = self.Bus.search([('channel', '=', self._json_dumps((self.Message._cr.dbname, 'res.partner', self.partner_admin.id)))]).message

        self.assertEqual(len(self.Bus.search([])), 2)
        self.assertEqual(self._json_loads(clementine_notif_msg), {'type': 'moderator', 'message': msg})
        self.assertEqual(self._json_loads(admin_notif_msg), {'type': 'author', 'message': msg})

    @mute_logger('odoo.models.unlink')
    def test_notify_moderators_by_email(self):
        self.Mail.process_email_queue()
        self.Mail.search([]).unlink
        self.Message._notify_moderators_by_email()
        self.assertEqual(len(self.Mail.search([('state', '=', 'outgoing')])), 2)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_search(self):
        self._clear_message()
        self.Message.create({
            'model': 'mail.channel', 'res_id': self.cm1id, 'author_id': self.user_employee.partner_id.id,
            'moderation_status': 'pending_moderation'})

        # Test: Author: 1 message
        msg = self.Message.sudo(self.user_employee).search([('moderation_status', '=', 'pending_moderation')])
        self.assertTrue(msg)

        # Test: Moderator: 1 message
        msg = self.Message.sudo(self.clementine).search([('moderation_status', '=', 'pending_moderation')])
        self.assertTrue(msg)

        # Test: Admin: 1 message
        msg = self.Message.search([('moderation_status', '=', 'pending_moderation')])
        self.assertTrue(msg)

        # Test: Other: 0 message
        msg = self.Message.sudo(self.roboute).search([('moderation_status', '=', 'pending_moderation')])
        self.assertFalse(msg)

    def test_check_access_rule(self):
        self._clear_message()
        msg = self.Message.create({
            'model': 'mail.channel', 'res_id': self.cm1id, 'author_id': self.user_employee.partner_id.id,
            'moderation_status': 'pending_moderation'})

        ''' Moderators can read and unlink pending moderation messages (of the channel they moderate only) but don't have the right to write over them. A sudo is used by moderators (in a private method) when they need to change moderation status from 'pending_moderation' to 'accepted'. Moderators have all rights over accepted messages because they have have all accesses to the model mail.channel.
        '''
        msg.sudo(self.clementine).check_access_rule('read')
        with self.assertRaises(AccessError):
            msg.sudo(self.roboute).check_access_rule('read')

        with self.assertRaises(AccessError):
            msg.sudo(self.clementine).check_access_rule('write')
        with self.assertRaises(AccessError):
            msg.sudo(self.roboute).check_access_rule('write')

        msg.sudo(self.clementine).check_access_rule('unlink')
        with self.assertRaises(AccessError):
            msg.sudo(self.roboute).check_access_rule('unlink')

        msg.write({'moderation_status': 'accepted'})

        msg.sudo(self.clementine).check_access_rule('read')
        msg.sudo(self.roboute).check_access_rule('read')
