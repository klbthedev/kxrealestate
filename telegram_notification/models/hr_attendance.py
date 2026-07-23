from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = ["hr.attendance",]#  "telegram.notification.mixin"

    @api.model
    def _cron_notify_attendance_alerts(self):
        today = fields.Date.today()
        employees = self.env["hr.employee"].search([])

        for emp in employees:
            attendance = self.search(
                [
                    ("employee_id", "=", emp.id),
                    ("check_in", ">=", f"{today} 00:00:00"),
                ],
                limit=1,
            )
            if not attendance:
                self._telegram_send(
                    (
                        "<b>Attendance Alert</b>\n"
                        f"Employee: {emp.name}\n"
                        "Status: No check-in today"
                    )
                )
