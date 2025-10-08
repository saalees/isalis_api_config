from odoo import models, fields, api
import jwt
import datetime


class ErpSecurity(models.Model):
    _name = "isalis_ess.erp.security"
    _description = "ERP Security Model"

    salis_session_id = fields.Char(string="Salis Session ID", readonly=True)
    salis_user_id = fields.Char(string="User ID", readonly=True)
    national_id = fields.Char(string="Employee National ID", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    jwt_token = fields.Text(string="ERP JWT Token", readonly=True)
    active = fields.Boolean(string="Active", default=True, readonly=True)
    created_at = fields.Datetime(
        string="Created At",
        default=fields.Datetime.now,
        readonly=True,
    )
    last_used = fields.Datetime(
        string="Last Used",
        default=fields.Datetime.now,
        readonly=True,
    )
    expiry_time_interval = fields.Float(
        string="Expiry Time Interval (minutes)", default=5, readonly=True
    )
    expiry_after = fields.Datetime(
        string="Expiry After",
        default=lambda: fields.Datetime.now() + datetime.timedelta(minutes=5),
        compute="_compute_expiry_after",
        readonly=True,
    )

    @api.depends("created_at", "expiry_time_interval")
    def _compute_expiry_after(self):
        for record in self:
            if record.created_at and record.expiry_time_interval:
                record.expiry_after = record.created_at + datetime.timedelta(
                    minutes=record.expiry_time_interval
                )
            else:
                record.expiry_after = False

    def generate_token(self):
        for record in self:
            secret_key = "PBZjsKzceL3jMUBcVeo4eKeRy1WRz7ic"  # temporary dummy key

            if record.employee_id:
                payload = {
                    "user_id": record.salis_user_id,
                    "employee_id": record.employee_id.id,
                    "national_id": record.national_id,
                    "session_id": record.salis_session_id,
                    "exp": datetime.datetime.now() + datetime.timedelta(hours=3),
                }
                token = jwt.encode(payload, secret_key, algorithm="HS256")
                record.jwt_token = token
            else:
                pass

    def create(self, vals_list):
        user_employee = self.env["hr.employee"].search(
            [("identification_id", "=", vals_list["national_id"])], limit=1
        )
        vals_list["employee_id"] = user_employee.id

        result = super().create(vals_list)

        for record in result:
            record.generate_token()
        return result

    def decode_token(self, token):
        secret_key = "PBZjsKzceL3jMUBcVeo4eKeRy1WRz7ic"  # temporary dummy key
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return {"error": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}

    def auto_archive_expired(self):
        expired_records = self.search(
            [("expiry_after", "<", fields.Datetime.now()), ("active", "=", True)]
        )
        for record in expired_records:
            record.active = False
