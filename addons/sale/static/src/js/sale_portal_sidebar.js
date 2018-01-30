odoo.define('sale.SalePortalSidebar', function (require) {
"use strict";

require('web.dom_ready');
var Widget = require("web.Widget");

if (!$('.o_portal_sidebar').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_portal_sidebar'");
}

    // Nav Menu ScrollSpy
    var NavigationSpyMenu = Widget.extend({
        start: function (watched_selector) {
            this.authorizedTextTag = ['em', 'b', 'i', 'u'];
            this.spyWatched = $(watched_selector);
            this.generateMenu();
        },

        generateMenu: function () {
            var self = this;
            $("[id^=quote_header_], [id^=quote_]", this.spyWatched).attr("id", "");
            // generate the new spy menu
            var lastLI = false;
            var lastUL = null;
            _.each(this.spyWatched.find("h1, h2"), function (el) {
                var id, text;
                switch (el.tagName.toLowerCase()) {
                    case "h1":
                        id = self.setElementId('quote_header_', el);
                        text = self.extractText($(el));
                        if (!text) {
                            break;
                        }
                        lastLI = $("<li>").append($('<a href="#' + id + '"/>').text(text)).appendTo(self.$el);
                        lastUL = false;
                        break;
                    case "h2":
                        id = self.setElementId('quote_', el);
                        text = self.extractText($(el));
                        if (!text) {
                            break;
                        }
                        if (lastLI) {
                            if (!lastUL) {
                                lastUL = $("<ul class='nav'>").appendTo(lastLI);
                            }
                            $("<li>").append($('<a href="#' + id + '"/>').text(text)).appendTo(lastUL);
                        }
                        break;
                }
            });
        },

        setElementId: function (prefix, $el) {
            var id = _.uniqueId(prefix);
            this.spyWatched.find($el).attr('id', id);
            return id;
        },

        extractText: function ($node) {
            var self = this;
            var rawText = [];
            _.each($node.contents(), function (el) {
                var current = $(el);
                if ($.trim(current.text())) {
                    var tagName = current.prop("tagName");
                    if (_.isUndefined(tagName) || (!_.isUndefined(tagName) && _.contains(self.authorized_text_tag, tagName.toLowerCase()))) {
                        rawText.push($.trim(current.text()));
                    }
                }
            });
            return rawText.join(' ');
        }
    });

    var navSpyMenu = new NavigationSpyMenu();
    navSpyMenu.setElement($('[data-id="portal_sidebar"]'));
    navSpyMenu.start($('body[data-target=".navspy"]'));

});
