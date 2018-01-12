odoo.define('l10n_fr_pos_cert2.models', function (require) {
"use strict";

var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var gui = require('point_of_sale.gui');
var Model = require('web.DataModel');
var core = require('web.core');

var _t = core._t;


var certification_deferred = null;

    var _super_order = models.Order;
    models.Order = models.Order.extend({
        export_for_printing: function () {
            var json = _super_order.prototype.export_for_printing.apply(this, arguments);
            json.l10n_fr_hash = this.l10n_fr_hash;
            return json
        },

        export_as_JSON: function () {
            var json = _super_order.prototype.export_as_JSON.apply(this,arguments);
            json.l10n_fr_hash = this.l10n_fr_hash;
            return json;
        },

    });

    var _super_pos = models.PosModel;
    models.PosModel = models.PosModel.extend({
        _save_to_server: function (orders, options) {
            certification_deferred = new $.Deferred();
            var order = this.get('selectedOrder');
            return _super_pos.prototype._save_to_server.apply(this, arguments).then(function (server_ids) {
                if (server_ids) {
                    if (server_ids.length > 0) {
                        // Try to get hash of saved orders, if required
                        var posOrderModel = new Model('pos.order');
                        return posOrderModel.call(
                            'get_l10n_fr_hash', server_ids, false
                        ).then(function (results) {
                            var hash = false;
                            _.each(results, function (result) {
                                if (result.pos_reference.indexOf(order.uid) > 0) {
                                    hash = result.l10n_fr_hash;
                                    order.l10n_fr_hash = hash;
                                }
                            });
                            certification_deferred.resolve(hash);
                            return server_ids;
                        }).fail(function (error, event) {
                            certification_deferred.reject();
                            return server_ids;
                        });
                    }
                    certification_deferred.resolve(false);
                    return server_ids;
                }
                certification_deferred.reject();
            }, function error() {
                 certification_deferred.reject();
            });
        },
    });

    var ReceiptScreenWidgetParent = screens.ReceiptScreenWidget;
    screens.ReceiptScreenWidget = screens.ReceiptScreenWidget.extend({
        // Overload Function
        show: function(){
            var self = this;
            certification_deferred.then(function success(hash) {
                    self.show_certification();
            }, function error() {
                self.show_certification();
            });
        },

        show_certification: function(){
            if (typeof(this.pos.get('selectedOrder').l10n_fr_hash) === 'undefined') {
                    this.pos.get('selectedOrder')._printed = true;
                    ReceiptScreenWidgetParent.prototype.show.apply(this, []);
                    self = this;
                    this.$('.pos-sale-ticket').hide();
                    this.pos.gui.show_popup('confirm', {
                        title: _t('Connection required'),
                        body: _t('Can not print the bill because your point of sale is currently offline'),
                        confirm: function () {
                            self.pos.get('selectedOrder').finalized = false;
                            self.gui.show_screen('payment');
                        }
                    });
                }
                else {
                    ReceiptScreenWidgetParent.prototype.show.apply(this, []);
                }
            certification_deferred = null;
        },
    });

gui.define_screen({name:'receipt', widget: screens.ReceiptScreenWidget});

});
