# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import psycopg2
import threading

from collections import defaultdict
from email.utils import formataddr

from odoo import _, api, fields, models
from odoo import tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    """ Model holding RFC2822 email messages to send. This model also provides
        facilities to queue and send new email messages.  """
    _name = 'mail.mail'
    _description = 'Outgoing Mails'
    _inherits = {'mail.message': 'mail_message_id'}
    _order = 'id desc'
    _rec_name = 'subject'

    # content
    mail_message_id = fields.Many2one('mail.message', 'Message', required=True, ondelete='cascade', index=True, auto_join=True)
    body_html = fields.Text('Rich-text Contents', help="Rich-text/HTML message")
    references = fields.Text('References', help='Message references, such as identifiers of previous messages', readonly=1)
    headers = fields.Text('Headers', copy=False)
    # Auto-detected based on create() - if 'mail_message_id' was passed then this mail is a notification
    # and during unlink() we will not cascade delete the parent and its attachments
    notification = fields.Boolean('Is Notification', help='Mail has been created to notify people of an existing mail.message')
    # recipients
    email_to = fields.Text('To', help='Message recipients (emails)')
    email_cc = fields.Char('Cc', help='Carbon copy message recipients')
    recipient_ids = fields.Many2many('res.partner', string='To (Partners)')
    # process
    state = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('exception', 'Delivery Failed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, copy=False, default='outgoing')
    auto_delete = fields.Boolean(
        'Auto Delete',
        help="Permanently delete this email after sending it, to save space")
    failure_reason = fields.Text(
        'Failure Reason', readonly=1,
        help="Failure reason. This is usually the exception thrown by the email server, stored to ease the debugging of mailing issues.")
    scheduled_date = fields.Char('Scheduled Send Date',
        help="If set, the queue manager will send the email after the date. If not set, the email will be send as soon as possible.")

    @api.model
    def create(self, values):
        # notification field: if not set, set if mail comes from an existing mail.message
        if 'notification' not in values and values.get('mail_message_id'):
            values['notification'] = True
        if not values.get('mail_message_id'):
            self = self.with_context(message_create_from_mail_mail=True)
        return super(MailMail, self).create(values)

    @api.multi
    def unlink(self):
        # cascade-delete the parent message for all mails that are not created for a notification
        to_cascade = self.search([('notification', '=', False), ('id', 'in', self.ids)]).mapped('mail_message_id')
        res = super(MailMail, self).unlink()
        to_cascade.unlink()
        return res

    @api.model
    def default_get(self, fields):
        # protection for `default_type` values leaking from menu action context (e.g. for invoices)
        # To remove when automatic context propagation is removed in web client
        if self._context.get('default_type') not in type(self).message_type.base_field.selection:
            self = self.with_context(dict(self._context, default_type=None))
        return super(MailMail, self).default_get(fields)

    @api.multi
    def mark_outgoing(self):
        return self.write({'state': 'outgoing'})

    @api.multi
    def cancel(self):
        return self.write({'state': 'cancel'})

    @api.model
    def process_email_queue(self, ids=None):
        """Send immediately queued messages, committing after each
           message is sent - this is not transactional and should
           not be called during another transaction!

           :param list ids: optional list of emails ids to send. If passed
                            no search is performed, and these ids are used
                            instead.
           :param dict context: if a 'filters' key is present in context,
                                this value will be used as an additional
                                filter to further restrict the outgoing
                                messages to send (by default all 'outgoing'
                                messages are sent).
        """
        if not self.ids:
            filters = ['&',
                       ('state', '=', 'outgoing'),
                       '|',
                       ('scheduled_date', '<', datetime.datetime.now()),
                       ('scheduled_date', '=', False)]
            if 'filters' in self._context:
                filters.extend(self._context['filters'])
            # TODO: make limit configurable
            ids = self.search(filters, limit=10000).ids
        res = None
        try:
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.currentThread(), 'testing', False)
            res = self.browse(ids).send(auto_commit=auto_commit)
        except Exception:
            _logger.exception("Failed processing mail queue")
        return res

    @api.multi
    def _postprocess_sent_message(self, mail_sent=True):
        """Perform any post-processing necessary after sending ``mail``
        successfully, including deleting it completely along with its
        attachment if the ``auto_delete`` flag of the mail was set.
        Overridden by subclasses for extra post-processing behaviors.

        :return: True
        """
        notif_emails = self.filtered(lambda email: email.notification)
        if notif_emails:
            notifications = self.env['mail.notification'].search([
                ('mail_message_id', 'in', notif_emails.mapped('mail_message_id').ids),
                ('is_email', '=', True)])
            if mail_sent:
                notifications.write({
                    'email_status': 'sent',
                })
            else:
                notifications.write({
                    'email_status': 'exception',
                })
        if mail_sent:
            self.sudo().filtered(lambda self: self.auto_delete).unlink()
        return True

    # ------------------------------------------------------
    # mail_mail formatting, tools and send mechanism
    # ------------------------------------------------------

    @api.multi
    def _send_mail_prepare_body(self):
        """Return a specific ir_email body. The main purpose of this method
        is to be inherited to add custom content depending on some module
        like URL / links management. """
        self.ensure_one()
        return self.body_html or ''

    def _send_mail_prepare_values(self):
        body = self._send_mail_prepare_body()
        body_alternative = tools.html2plaintext(body)

        # load attachment binary data with a separate read(), as prefetching all
        # `datas` (binary field) could bloat the browse cache, triggerring
        # soft/hard mem limits with temporary data.
        attachments = [(a['datas_fname'], base64.b64decode(a['datas']), a['mimetype'])
                       for a in self.attachment_ids.sudo().read(['datas_fname', 'datas', 'mimetype'])]

        generic_values = {
            'email_from': self.email_from,
            'subject': self.subject,
            'body': body,
            'body_alternative': body_alternative,
            'reply_to': self.reply_to,
            'attachments': attachments,
            'message_id': self.message_id,
            'references': self.references,
            'object_id': '%s-%s' % (self.res_id, self.model) if self.res_id else '',
            'subtype': 'html',
            'subtype_alternative': 'plain',
        }

        emails_based = {
            'email_from': self.email_from,
            'email_to': tools.email_split_and_format(self.email_to),
            'email_cc': tools.email_split(self.email_cc),
        }
        emails_based.update(generic_values)
        res = [emails_based]

        for recipient in self.recipient_ids:
            partner_based = {
                'email_to': [formataddr((recipient.name or 'False', recipient.email or 'False'))],
            }
            partner_based.update(generic_values)
            res.append(partner_based)

        return res

    @api.multi
    def _split_by_server(self):
        """Returns an iterator of pairs `(mail_server_id, record_ids)` for current recordset.

        The same `mail_server_id` may repeat in order to limit batch size according to
        the `mail.session.batch.size` system parameter.
        """
        groups = defaultdict(list)
        # Turn prefetch OFF to avoid MemoryError on very large mail queues, we only care
        # about the mail server ids in this case.
        # Browse as sudo to lessen query number - this is an internal method only dispatching mails
        # so no security breach
        for mail in self.sudo().with_context(prefetch_fields=False):
            groups[mail.mail_server_id.id].append(mail.id)
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.session.batch.size', 1000))
        for server_id, record_ids in groups.items():
            for mail_batch in tools.split_every(batch_size, record_ids):
                yield server_id, mail_batch

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail status
                after sending each mail (meant only for scheduler processing);
                should never be True during normal transactions (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        for server_id, batch_ids in self._split_by_server():
            smtp_session = None
            try:
                smtp_session = self.env['ir.mail_server'].connect(mail_server_id=server_id)
            except Exception as exc:
                if raise_exception:
                    # To be consistent and backward compatible with mail_mail.send() raised
                    # exceptions, it is encapsulated into an Odoo MailDeliveryException
                    raise MailDeliveryException(_('Unable to connect to SMTP Server'), exc)
                else:
                    self.browse(batch_ids).write({'state': 'exception', 'failure_reason': exc})
            else:
                self.browse(batch_ids)._send(
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    smtp_session=smtp_session)
                _logger.info(
                    'Sent batch %s emails via mail server ID #%s',
                    len(batch_ids), server_id)
            finally:
                if smtp_session:
                    smtp_session.quit()

    @api.multi
    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        IrMailServer = self.env['ir.mail_server']
        MailSudo = self.env['mail.mail'].sudo()
        ICP = self.env['ir.config_parameter'].sudo()
        bounce_alias = ICP.get_param("mail.bounce.alias")
        catchall_domain = ICP.get_param("mail.catchall.domain")

        for mail_id in self.ids:
            try:
                mail_sudo = MailSudo.browse(mail_id)
                if mail_sudo.state != 'outgoing':
                    if mail_sudo.state != 'exception' and mail_sudo.auto_delete:
                        mail_sudo.unlink()
                    continue

                # specific behavior to customize the send email for notified partners
                email_list = mail_sudo._send_mail_prepare_values()

                # headers
                headers = {}
                if bounce_alias and catchall_domain:
                    if mail_sudo.model and mail_sudo.res_id:
                        headers['Return-Path'] = '%s+%d-%s-%d@%s' % (bounce_alias, mail_sudo.id, mail_sudo.model, mail_sudo.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s+%d@%s' % (bounce_alias, mail_sudo.id, catchall_domain)
                if mail_sudo.headers:
                    try:
                        headers.update(safe_eval(mail_sudo.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail_sudo.write({
                    'state': 'exception',
                    'failure_reason': _('Error without exception. Probably due do sending an email without computed recipients.'),
                })
                mail_sent = False

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    msg = IrMailServer.build_email(
                        headers=headers,
                        **email)
                    try:
                        res = IrMailServer.send_email(
                            msg, mail_server_id=mail_sudo.mail_server_id.id, smtp_session=smtp_session)
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail_sudo.message_id, email.get('email_to'))
                        else:
                            raise
                if res:
                    mail_sudo.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    mail_sent = True

                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                if mail_sent:
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail_sudo.id, mail_sudo.message_id)
                mail_sudo._postprocess_sent_message(mail_sent=mail_sent)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail_sudo.id, mail_sudo.message_id)
                raise
            except psycopg2.Error:
                # If an error with the database occurs, chances are that the cursor is unusable.
                # This will lead to an `psycopg2.InternalError` being raised when trying to write
                # `state`, shadowing the original exception and forbid a retry on concurrent
                # update. Let's bubble it.
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception('failed sending mail (id: %s) due to %s', mail_sudo.id, failure_reason)
                mail_sudo.write({'state': 'exception', 'failure_reason': failure_reason})
                mail_sudo._postprocess_sent_message(mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True
