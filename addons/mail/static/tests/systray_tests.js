odoo.define('mail.systray_tests', function (require) {
"use strict";

var ChatManager = require('mail.ChatManager');
var systray = require('mail.systray');
var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

var createBusService = mailTestUtils.createBusService;

QUnit.module('mail', {}, function () {

QUnit.module('ActivityMenu', {
    beforeEach: function () {
        this.BusService = createBusService();
        this.data = {
            'mail.activity.menu': {
                fields: {
                    name: { type: "char" },
                    model: { type: "char" },
                    planned_count: { type: "integer"},
                    today_count: { type: "integer"},
                    overdue_count: { type: "integer"},
                    total_count: { type: "integer"},
                    active: { type: "boolean"}
                },
                records: [{
                        name: "Contact",
                        model: "res.partner",
                        planned_count: 0,
                        today_count: 1,
                        overdue_count: 0,
                        total_count: 1,
                    },
                    {
                        name: "Task",
                        model: "project.task",
                        planned_count: 1,
                        today_count: 0,
                        overdue_count: 0,
                        total_count: 1,
                    },
                    {
                        name: "Issue",
                        model: "project.issue",
                        planned_count: 1,
                        today_count: 1,
                        overdue_count: 1,
                        total_count: 3,
                    },
                    {
                        model: 'mail.activity',
                        planned_count: 1,
                        today_count: 1,
                        overdue_count: 1,
                        total_count: 3,
                    }],
                },
            };
        }
    });

QUnit.test('activity menu widget: menu with no records', function (assert) {
    assert.expect(1);

    var activityMenu = new systray.ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
            mockRPC: function (route, args) {
                if (args.method === 'activity_user_count') {
                    return $.when([]);
                }
                return this._super(route, args);
            },
            services: [ChatManager, this.BusService]
        });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$('.o_no_activity').hasClass('o_no_activity'), "should not have instance of widget");
    activityMenu.destroy();
});

QUnit.test('activity menu widget: activity menu with 3 records', function (assert) {
    assert.expect(22);
    var self = this;
    var activityMenu = new systray.ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
        mockRPC: function (route, args) {
            if (args.method === 'activity_user_count') {
                return $.when(self.data['mail.activity.menu']['records']);
            }
            if (args.method === "create") {
                assert.deepEqual(args.args, [{'note': 'New Reminder'}], 'Create reminder should get proper value');
                _.each(self.data['mail.activity.menu'].records, function (record) {
                    if (record.model === "mail.activity") {
                        record.today_count += 1;
                        record.total_count += 1;
                    }
                });
                return $.when();
            }
            return this._super(route, args);
        },
        services: [ChatManager, this.BusService],
    });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$el.hasClass('o_mail_navbar_item'), 'should be the instance of widget');
    assert.ok(activityMenu.$('.o_mail_channel_preview').hasClass('o_mail_channel_preview'), "should instance of widget");
    assert.ok(activityMenu.$('.o_notification_counter').hasClass('o_notification_counter'), "widget should have notification counter");
    assert.strictEqual(parseInt(activityMenu.el.innerText), 8, "widget should have 8 notification counter (with today reminder)");

    var context = {};
    testUtils.intercept(activityMenu, 'do_action', function(event) {
        assert.deepEqual(event.data.action.context, context, "wrong context value");
    }, true);

    // case 1: click on "late"
    context = {
        search_default_activities_overdue: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    assert.strictEqual(activityMenu.$el.hasClass("open"), true, 'ActivityMenu should be open');
    activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='overdue']").click();
    assert.strictEqual(activityMenu.$el.hasClass("open"), false, 'ActivityMenu should be closed');
    // case 2: click on "today"
    context = {
        search_default_activities_today: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='today']").click();
    // case 3: click on "future"
    context = {
        search_default_activities_upcoming_all: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='upcoming_all']").click();
    // case 4: click anywere else
    context = {
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_mail_navbar_dropdown_channels > div[data-model_name='Issue']").click();

    // Test case for reminders
    testUtils.intercept(activityMenu, 'do_action', function(event) {
        assert.deepEqual(event.data.options.additional_context, context, "reminder wrong context value");
    }, false);
    // reminder case 1: click on "late"
    context = {
        search_default_activities_overdue: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    assert.strictEqual(activityMenu.$el.hasClass("open"), true, 'ActivityMenu should be open');
    activityMenu.$(".o_activity_filter_button[data-res_model='mail.activity'][data-filter='overdue']").click();
    assert.strictEqual(activityMenu.$el.hasClass("open"), false, 'ActivityMenu should be closed');

    // case 2: click on "today"
    context = {
        search_default_activities_today: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_activity_filter_button[data-res_model='mail.activity'][data-filter='today']").click();
    // case 3: click on "future"
    context = {
        search_default_activities_upcoming_all: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_activity_filter_button[data-res_model='mail.activity'][data-filter='upcoming_all']").click();
    // case 4: click anywere else
    context = {
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_mail_navbar_dropdown_channels > div[data-res_model='mail.activity']").click();

    // loading reminder preview with action
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_reminder_preview").click();

    // toggle quick create for reminder
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$('.o_add_reminder').click();
    assert.strictEqual(activityMenu.$('.o_add_reminder').hasClass("hidden"), true, 'ActivityMenu add reminder button should be hidden');
    assert.strictEqual(activityMenu.$('.o_new_reminder').hasClass("hidden"), false, 'ActivityMenu add reminder input should be displayed');

    // creating quick reminder
    activityMenu.$("input.o_new_reminder_input").val("New Reminder");
    activityMenu.$(".o_new_reminder_save").click();
    assert.strictEqual(parseInt(activityMenu.el.innerText), 9, "widget should have 9 notification counter (after new reminder)");
    assert.strictEqual(activityMenu.$('.o_add_reminder').hasClass("hidden"), false, 'ActivityMenu add reminder button should be displayed');
    assert.strictEqual(activityMenu.$('.o_new_reminder').hasClass("hidden"), true, 'ActivityMenu add reminder input should be hidden');

    activityMenu.destroy();
});
});
});
