odoo.define('mail.moderation_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var ChatAction = require("mail.chat_client_action");

QUnit.module('mail', {}, function () {

QUnit.module('Discuss moderation', {
    beforeEach: function () {
        this.data = {
            'mail.message': {
                fields: {
                    body: {type: "html"},
                    // author_id: {type: "many2one", relation: 'partner'},
                    moderation_status: {
                        type: "selection",
                        selection: [['accepted', 'Accepted'], ['rejected', 'Rejected'], ['pending_moderation', 'Pending Moderation']],
                    },
                },
                records: {
                    // id: 1,
                    body: "<p>Hi there!</p>",
                    // author_id: 1,
                    moderation_status: 'pending_moderation',
                }
            },
        };
        this.createChatAction = function (params) {
            var Parent = Widget.extend({
                do_push_state: function () {},
            });
            var parent = new Parent();
            testUtils.addMockEnvironment(parent, {
                data: this.data,
                archs: {
                    'mail.message,false,search': '<search/>',
                },
            });
            var chatAction = new ChatAction(parent, params);
            chatAction.set_cp_bus(new Widget());
            chatAction.appendTo($('body'));
            return chatAction;
        };

    },
});

QUnit.only('discuss moderation tools', function (assert) {

    assert.expect(2);
    
    var params = {
        id: 1,
        context: {},
        params: {},
    };
    
    var chatAction = this.createChatAction({
        id: 1,
        context: {},
        params: {},
        intercepts: {
            get_session: function (ev) {
                ev.data.callback({});
            },
        },
        session: {
            rpc: function (route, args) {
                if (args.method === 'message_fetch') {
                    return $.when([]);
                }
                return rpc.apply(this, arguments);
            },
        },
    });

    assert.ok(chatAction.$('.o_mail_thread').length, "there should be a mail thread");
    assert.equal(chatAction.thread.$("o_thread_message").length, 1);

});
});
});
