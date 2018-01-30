# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase


class TestHrLeaveType(TestHrHolidaysBase):
    def setUp(self):
        super(TestHrLeaveType, self).setUp()

        LeaveType = self.env['hr.leave.type']

        self.leave_leave = LeaveType.create({
            'name': 'Legal Leaves',
            'limit': True,
            'double_validation': False,
            'time_type': 'leave',
        })

        self.leave_other = LeaveType.create({
            'name': 'Formation',
            'limit': True,
            'double_validation': False,
            'time_type': 'other',
        })

    def test_time_type(self):
        Leave = self.env['hr.leave']
        RLeave = self.env['resource.calendar.leaves']

        leave_1 = Leave.create({
            'name': 'Doctor Appointment',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.leave_leave.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days_temp': 1,
        })

        leave_1.action_approve()

        self.assertEqual(RLeave.search([('holiday_id', '=', leave_1.id)]).time_type, 'leave')

        leave_1.action_refuse()
        leave_1.action_draft()

        leave_2 = Leave.create({
            'name': 'Cefora formation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.leave_other.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days_temp': 1,
        })

        leave_2.action_approve()

        self.assertEqual(RLeave.search([('holiday_id', '=', leave_2.id)]).time_type, 'other')

        leave_2.action_refuse()
        leave_2.action_draft()

        (leave_1 | leave_2).unlink()
