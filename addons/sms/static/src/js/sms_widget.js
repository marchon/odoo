odoo.define('sms.sms_widget', function (require) {
    "use strict";

    var FieldText = require('web.basic_fields').FieldText;
    var fieldRegistry = require('web.field_registry');
    var core = require('web.core');
    var QWeb = core.qweb;
    var framework = require('web.framework');

    var SmsWidget = FieldText.extend({
        /**
         * @constructor
         */
        init: function () {
            this._super.apply(this, arguments);
            this.nbr_char = 0;
            this.nbr_sms = 0;
            this.encoding = "GSM7";
            this.$textarea = undefined;
            this.$smscount = undefined;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Compute the number of characters and sms
         */
        _compute: function() {
            var content = this._getValue();
            this.encoding = this._extractEncoding(content);
            this.nbr_char = content.length;
            this.nbr_char += (content.match(/\n/g) || []).length;
            this.nbr_sms = this._countSMS(this.nbr_char, this.encoding);
            this._renderSMS();
        },
        /**
         * Count the number of SMS of the content
         * @returns {Integer} Number of SMS
         * @private
         */
        _countSMS: function() {
            if (this.encoding === 'UNICODE') {
                if (this.nbr_char <= 70) {
                    return 1;
                }
                return Math.ceil(this.nbr_char / 67);
            }
            if (this.nbr_char <= 160) {
                return 1;
            }
            return Math.ceil(this.nbr_char / 153);
        },
        /**
         * Extract the encoding depending on the characters in the content
         * @param {String} content Content of the SMS
         * @returns {String} Encoding of the content (GSM7 or UNICODE)
         * @private
         */
        _extractEncoding: function(content) {
            if (String(content).match(RegExp("^[@£$¥èéùìòÇ\\nØø\\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\\\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà]*$"))) {
                return 'GSM7';
            }
            return 'UNICODE';
        },
        /**
         * Render the number of characters, sms and the encoding.
         */
        _renderSMS: function() {
            this.$('.sms_count').html(this.nbr_char + ' / ' + this.nbr_sms + ' SMS (' + this.encoding + ') ');
        },
        /**
         * @override
         */
        _renderEdit: function() {
            this._super.apply(this, arguments);
            this.$textarea = this.$el;
            this.$smscount = $(QWeb.render("sms.sms_count", {}));
            var $new_root = $('<div>');
            $new_root.append(this.$textarea);
            $new_root.append(this.$smscount);
            this.setElement($new_root);
            this._renderSMS();
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------   
    
        /**
         * @override
         */
        _onChange: function() {
            this._super.apply(this, arguments);
            this._compute();
        },
        /**
         * @override
         */
        _onInput: function() {
            this._super.apply(this, arguments);
            this._compute();
        },
    });

    fieldRegistry.add('sms_widget', SmsWidget);

    return {
        SmsWidget: SmsWidget,
    };
});