# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment
import odoo.tests

@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestWebsiteHrRecruitmentForm(odoo.tests.HttpSeleniumCase):
    def test_tour(self):
        self.selenium_run(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('website_hr_recruitment_tour')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.website_hr_recruitment_tour.ready")

        # get test cursor to read from same transaction browser is writing to
        cr = self.registry.cursor()
        assert cr == self.registry.test_cr
        env = Environment(cr, self.uid, {})

        record = env['hr.applicant'].search([('description', '=', '### HR RECRUITMENT TEST DATA ###')])
        assert len(record) == 1
        assert record.partner_name == "John Smith"
        assert record.email_from == "john@smith.com"
        assert record.partner_phone == '118.218'
