odoo.define('portal.share_document', function (require) {
'use strict';

var core = require('web.core');
var data_manager = require('web.data_manager');
var SystrayMenu = require('web.SystrayMenu');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');

var _t = core._t;

var ProtalShareDoc = Widget.extend({
    template: 'portal.sharing_icon',
    events: {
        "click": "_onClick",
    },
    xmlDependencies: ['/portal/static/src/xml/portal_share_document.xml'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Update the system tray icon for share document, based on view type hides/shows icon
     * Show Share Icon only if 1) action context has share_icon True 2) form view of portal.mixin inherited object
     */
    update: function (tag, descriptor, widget) {
        var self = this;
        if (widget && tag === 'action') {
            this._controller = widget;
            this.shareAction = descriptor.context.share_action ? descriptor.context.share_action : 'portal.mail_share_link_action';
            if (this._controller.viewType === 'form') {
                var view = _.findWhere(this._controller.actionViews, {type: this._controller.viewType});
                if (view && view.fieldsView && view.fieldsView.share_icon) {
                    this.$el.removeClass('o_hidden');
                } else {
                    this.$el.addClass('o_hidden');
                }
            } else {
                this.getSession().user_has_group('base.group_erp_manager').then(function (has_group) {
                    self._controller = null;
                    if (has_group && widget && widget.action && widget.action.context.share_icon) {
                        self.$el.removeClass('o_hidden');
                    } else {
                        self.$el.addClass('o_hidden');
                    }
                });
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /*
     * Opens Share document wizard, loads action and call that action with additional context(active_id and active_model)
     */
    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var additional_context = {};
        if (this._controller) {
            var renderer = this._controller.renderer;
            var state = renderer.state;
            var resID = state.data.id;
            if (!resID) {
                this.do_warn(_t("Record does not exist!"), _t("Please, Save this record before sharing."));
                return $.Deferred().reject();
            }
            additional_context = {
                'active_id': resID,
                'active_model': state.model,
            };
        }
        return data_manager.load_action(this.shareAction, additional_context).then(function (result) {
            return self.do_action(result, {
                additional_context: additional_context,
                on_close: function () {
                    if (self._controller) {
                        self._controller.reload();
                    }
                },
            });
        });
    },
});

WebClient.include({

    /**
     * @override
     */
    current_action_updated: function (action, controller) {
        this._super.apply(this, arguments);
        var portalShareDoc = _.find(this.systray_menu.widgets, function (item) {
            return item instanceof ProtalShareDoc;
        });
        portalShareDoc.update('action', action, controller && controller.widget);
    },
    instanciate_menu_widgets: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.systray_menu = self.menu.systray_menu;
        });
    },
});

SystrayMenu.Items.push(ProtalShareDoc);

});
