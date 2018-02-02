/**
 * Defines a proper password field (rather than just an InputField option) to
 * provide a "password strength" meter based on the database's current
 * policy & the 2word16 password policy recommended by Shay (2016) "Designing
 * Password Policies for Strength and Usability".
 */
odoo.define('auth_password_policy.PasswordField', function (require) {
var core = require('web.core');
var fields = require('web.basic_fields');

var qweb = core.qweb;
var _t = core._t;
var Policy = core.Class.extend({
    /**
     *
     * @param {Object} info
     * @param {Number} [info.minlength=0]
     * @param {Number} [info.minwords=0]
     * @param {Number} [info.minclasses=0]
     */
    init: function (info) {
        this._minlength = info.minlength || 1;
        this._minwords = info.minwords || 1;
        this._minclasses = info.minclasses || 1;
    },
    toString: function () {
        var msgs = [];
        if (this._minlength > 1) {
            msgs.push(_.str.sprintf(_t("at least %d characters"), this._minlength));
        }
        if (this._minwords > 1) {
            msgs.push(_.str.sprintf(_t("at least %d words"), this._minwords));
        }
        if (this._minclasses > 1) {
            msgs.push(_.str.sprintf(_t("at least %d character classes"), this._minclasses));
        }
        return msgs.join(', ')
    },
    score: function (password) {
        var lengthscore = Math.min(
            password.length / this._minlength,
            1.0);
        // we want the number of "words". Splitting on no-words doesn't work
        // because JS will add an empty string when matching a leading or
        // trailing pattern e.g. " foo ".split(/\W+/) will return ['', 'foo', '']
        // by splitting on the words, we should always get wordscount + 1
        var wordscore =  Math.min(
            // \w includes _ which we don't want, so combine \W and _ then
            // invert it to know what "word" is
            //
            // Sadly JS is absolute garbage, so this splitting is basically
            // solely ascii-based unless we want to include cset
            // (http://inimino.org/~inimino/blog/javascript_cset) which can
            // generate non-trivial character-class-set-based regex patterns
            // for us. We could generate the regex statically but they're huge
            // and gnarly as hell.
            (password.split(/[^\W_]+/u).length - 1) / this._minwords,
            1.0
        );
        // See above for issues pertaining to character classification:
        // we'll classify using the ascii range because that's basically our
        // only option
        var classes =
              ((/[a-z]/.test(password)) ? 1 : 0)
            + ((/[A-Z]/.test(password)) ? 1 : 0)
            + ((/\d/.test(password)) ? 1 : 0)
            + ((/[^A-Za-z\d]/.test(password)) ? 1 : 0);
        var classesscore = Math.min(classes / this._minclasses, 1.0);

        return lengthscore * wordscore * classesscore;
    },
});

// Recommendations from Shay (2016)
// Our research has shown that there are other policies that are more usable
// and more secure. We found three policies – 2class12, 3class12, and 2word16
// – that we can directly recommend over comp8
//
// Since 2class12 is a superset of 3class12 and 2word16, either pick it or
// pick the other two (and get the highest score of the two). We're picking
// the other two.
var recommendations = [
    new Policy({minlength: 16, minwords: 2}),
    new Policy({minlength: 12, minclasses: 3})
];

var PasswordField = fields.InputField.extend({
    className: 'o_field_password',

    init: function () {
        this._super.apply(this, arguments);
        this.nodeOptions.isPassword = true;
        this._policy = new Policy({});
    },
    willStart: function () {
        var _this = this;
        var getPolicy = this._rpc({
            model: 'res.users',
            method: 'get_password_policy',
        }).then(function (p) {
            _this._policy = new Policy(p);
        });
        return $.when(
            this._super.apply(this, arguments),
            getPolicy
        );
    },
    /**
     * Add a <meter> next to the input (TODO: move to template?)
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        var _this = this;
        return $.when(this._super.apply(this, arguments))
            .then(function () {
                _this.$meter =
                    $('<meter value="0" optimum="1">')
                        .css({
                            position: 'absolute',
                            height: 15,
                            top: 'calc(50% - 7px)',
                            right: 5,
                        });
                _this.$meter.attr('title', _.str.sprintf(
                    _t("Required: %s.\n\nHint: increase length, use multiple words and use non-letter characters to increase your password's strength."),
                    String(_this._policy) || _t("no requirements")
                ));
                _this.$el = _this.$el.add(_this.$meter);
            });
    },
    /**
     * Update meter value
     *
     * @override
     * @private
     */
    _onInput: function () {
        this._super();

        // Compute quality factor of password & update meter
        var password = this._getValue();
        var actual = this._policy.score(password);
        // get the highest score of all recommendations
        var recommended = Math.max.apply(null,
            recommendations.map(function (p) {
                return p.score(password);
            })
        );
        this.$meter.prop('value', actual * recommended);
        // we want red if not actual, yellow if between actual and rec'd and
        // green at 100%
        if (actual !== 1) {
            this.$meter.attr({
                low: 0.99,
                high: 0.99,
            });
        } else {
            this.$meter.attr({
                low: 0.01,
                high: 0.99,
            });
        }
    }
});

fields.InputField.include({
    init: function (parent, name, record, options) {
        var fieldsInfo = record.fieldsInfo[options.viewType];
        var attrs = options.attrs || (fieldsInfo && fieldsInfo[name]) || {};
        if ('password' in attrs
                && Object.getPrototypeOf(this) !== PasswordField.prototype) {
            return new PasswordField(parent, name, record, options);
        }
        this._super.apply(this, arguments);
    }
});

return PasswordField;
});
