from datetime import datetime
from odoo import api, fields, models, tools, SUPERUSER_ID

class MailPartnerMixin(models.AbstractModel):
    """ A mixin to add partner registration support to mail.thread
        mail_thread model is meant to be inherited (before mail.thread) by any model that needs to
        add partner registration and auto subscribe of partner on reply.
        -Register mail informations on "new_message" (email_from,email_cc,partner_id,name)
        -Create partner on update_message or new_message with respect to the "message_subscription_strategy".
        -The list of partner to subcribe and/or register are defined by "emails_to_subscribe" 
        and "partner_temails_to_subscribe". By default, only the "email_from" used for the creation of the record 
        will be subscribed. 
        -Once a partner is created, (using odoo interface when posting message or when repplying to a mail), 
        the field partner_id (can be changed with "message_partner_id_field") is updated with the new partner 
        corresponding to email_from for every record having the same value for "email_from" and partner field not set 
        (partner_id or message_partner_id_field if overwritten). 
    """
    ON_REPLY_STRATEGY,ON_CREATE_STRATEGY,NEVER_STRATEGY = range(3)
    _name = 'mail.partner.mixin'
    
    email_from = fields.Char('Email', help="Email address of the contact", index=True)
    email_cc = fields.Text('Global CC', help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    partner_id = fields.Many2one('res.partner', string='Customer', track_visibility='onchange', index=True, help="Linked partner (optional). Usually created when converting the lead.")
    name = fields.Char("Subject", translate=True)

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread new that is called by the mailgateway
            through process.
            This override adds the name, email_from, email_cc and partner_id to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(self.env.context or {})
        create_context['default_user_id'] = False
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        defaults.update(custom_values)
        thread = super(MailPartnerMixin, self.with_context(create_context)).message_new(msg, custom_values=defaults)
        if(thread.message_subscription_strategy(msg) == self.ON_CREATE_STRATEGY): #if we want to subscribe emails on create
            thread.partner_auto_subscribe(msg)
        return thread

    def message_update(self, msg, update_vals=None):
        """ Overrides mail_thread update that is called by the mailgateway
            through process.
            This override create the partner partner_id if it doesnt exist based on the email_from
        """
        if(self.message_subscription_strategy(msg) == self.ON_REPLY_STRATEGY): #if we want to subscribe emails on update
            self.partner_auto_subscribe(msg)
        super(MailPartnerMixin,self).message_update(msg, update_vals)

    def message_subscription_strategy(self,msg):
        return self.ON_REPLY_STRATEGY

    def emails_to_subscribe(self,msg):
        """
            Email to subscribe. A partner is create if it doesn't exists
            Overwrite this method to add more email to subscribe. 
            email_from should be present in the list to allow partner auto update with emails
        """
        return [self.email_from]
    
    def partner_emails_to_subscribe(self,msg):
        """
            Email to subscribe only if a partner exists
            Overwrite this method to add more partner to subscribe. 
        """
        #TODO functionnality to confirm
        return [] #tools.email_split(msg.get('cc')) # + [tools.email_split(self.email_cc)] ?

    def partner_auto_subscribe(self,msg):
        """
            Subscribe some partners based on emails. 
            -will subscribe and create partners if necessary for all emails in "emails_to_subscribe"
            -will subscribe all email contained in "partner_emails_to_subscribe" if a corresponding partner exists
        """
        email_list = self.emails_to_subscribe(msg)
        partner_ids = [p for p in self._find_partner_from_emails(email_list, force_create=True) if p]
        self.message_subscribe(partner_ids)
        #Case autosubscribe: a partner is created automaticaly when answering to an email
        self.message_update_partner_id(self.env['res.partner'].browse(partner_ids))
        partner_email_list = self.partner_emails_to_subscribe(msg)
        real_partner_ids = [p for p in self._find_partner_from_emails(partner_email_list, force_create=False) if p]
        self.message_subscribe(real_partner_ids)

    def message_partner_id_field(self):
        """
        The name of the field corresponding to the partner (with email_from) of record. See message_update_partner_id
        """
        return "partner_id"

    def message_partner_update_condition(self):
        """
        Additionnal condition to update the partner_id record. See message_update_partner_id
        """
        return [] #example: ('stage_id.fold', '=', False)

    def _message_post_after_hook(self, message, values, notif_layout):
        #Case after hook: a partner is created in odoo interface (front end side) when posting a message.
        #The partner id is added in the kwargs of message_post and will appear in "message.partner_ids"
        self.message_update_partner_id(message.partner_ids)
        return super(MailPartnerMixin, self)._message_post_after_hook(message, values, notif_layout)

    def message_update_partner_id(self,new_partner_candidates):
        """
        Method call by partner_auto_subscribe and _message_post_after_hook. 
        update the field "message_partner_id_field()" if this field is not set and te email is set. 
        Other condition can be added with message_partner_update_conditions() (as search parameter)
        """
        field = self.message_partner_id_field()
        if self.email_from and hasattr(self,field) and not self[field]:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            email_split = tools.email_split(self.email_from)
            if email_split:
                new_partner = new_partner_candidates.filtered(lambda partner: partner.email == email_split[0])
                if new_partner:
                    #update all the records using this email and without partner
                    self.search([
                        (field, '=', False),
                        ('email_from', '=', self.email_from)
                        ] + self.message_partner_update_condition()).write({field: new_partner.id})