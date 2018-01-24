odoo.define('account.AccountPortalSidebar', function (require) {
"use strict";

require('web.dom_ready');
var core = require('web.core');
var time = require('web.time');

var _t = core._t;

if (!$('.o_portal_sidebar').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_portal_sidebar'");
}

$("#sidebar_content .o_timeago").each(function (index, el) {
    var dateTime = moment(time.auto_str_to_date($(el).attr('datetime'))),
        today = moment().startOf('day'),
        diff = dateTime.diff(today, 'days', true),
        displayStr;

    if (diff === 0){
        displayStr = _t('Due today');
    } else if (diff > 0) {
        displayStr = _.str.sprintf(_t('Due in %d days'), Math.abs(diff));
    } else {
        displayStr = _.str.sprintf(_t('%d days overdue'), Math.abs(diff));
    }
     $(el).text(displayStr);
});

var $PDFIframe = $('iframe#invoice_pdf');
$PDFIframe.load(function () {
    $PDFIframe.contents().find('#openFile, #pageRotateCw, #pageRotateCcw, #pageRotateCcw, #viewBookmark').hide();
});

$('a#print_invoice_report').on('click', function (ev) {
    ev.stopPropagation();
    var pdfContent = window.frames["invoice_pdf"].contentWindow;
    pdfContent.focus();
    pdfContent.print();
});
});
