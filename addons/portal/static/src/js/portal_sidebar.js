odoo.define('portal.PortalSidebar', function (require) {
"use strict";

require('web.dom_ready');
var config = require('web.config');

if (!$('.o_portal_sidebar').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_portal_sidebar'");
}

var $bsSidebar = $(".o_portal_sidebar .bs-sidebar");
$(window).on('resize', _.throttle(adaptSidebarPosition, 200, {leading: false}));

adaptSidebarPosition();

function adaptSidebarPosition() {
    $bsSidebar.css({
        position: "",
        width: "",
    });
    if (config.device.size_class >= config.device.SIZES.MD) {
        $bsSidebar.css({
            position: "fixed",
            width: $bsSidebar.outerWidth(),
        });
    }
}

$bsSidebar.affix({
    offset: {
        top: 0,
        bottom: $('#wrapwrap').outerHeight() - $('main').height(),
    },
});
});
