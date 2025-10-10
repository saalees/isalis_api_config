from odoo import models, fields, api
import jwt
from datetime import datetime, timedelta
from ..utils.helpers import json_Response
import secrets
import json
# import string


# class EmployeeSecurity(models.Model):
#     _name = "employee.security"
#     _description = "Employee Security Model"

#     employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
#     erp_security_id = fields.Many2one(
#         "erp.security", string="ERP Security", readonly=True
#     )
#     active = fields.Boolean(string="Active", default=True, readonly=True)
#     secret_key = fields.Char(string="Secret Key", readonly=True)
#     created_at = fields.Datetime(
#         string="Created At", default=fields.Datetime.now, readonly=True
#     )
#     last_used = fields.Datetime(
#         string="Last Used", default=fields.Datetime.now, readonly=True
#     )
#     expiry_time_interval = fields.Float(
#         string="Expiry Time Interval (minutes)", default=5, readonly=True
#     )
#     expiry_after = fields.Datetime(
#         string="Expiry After",
#         default=lambda: fields.Datetime.now() + datetime.timedelta(minutes=5),
#         compute="_compute_expiry_after",
#         readonly=True,
#     )

#     @api.model
#     def generate_secret_key(self, length=32):
#         alphabet = string.ascii_letters + string.digits
#         return "".join(secrets.choice(alphabet) for _ in range(length))

#     @api.depends("created_at", "expiry_time_interval")
#     def _compute_expiry_after(self):
#         for record in self:
#             if record.created_at and record.expiry_time_interval:
#                 record.expiry_after = record.created_at + datetime.timedelta(
#                     minutes=record.expiry_time_interval
#                 )
#             else:
#                 record.expiry_after = fields.Datetime.now() + datetime.timedelta(
#                     minutes=5
#                 )


class ErpSecurity(models.Model):
    _name = "erp.security"
    _description = "ERP Security Model"

    salis_session_id = fields.Char(string="Salis Session ID", readonly=True)
    salis_user_id = fields.Char(string="User ID", readonly=True)
    national_id = fields.Char(string="Employee National ID", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    # secret_key = fields.Char(
    #     string="Secret Key",
    #     readonly=True,
    #     compute="_compute_secret_key",
    #     store=True,
    # )

    # @api.model
    # def get_or_create_secret_key(self, employee_id):
    #     employee_security = self.env["employee.security"].search(
    #         [("employee_id", "=", employee_id)], limit=1
    #     )
    #     if employee_security:
    #         return employee_security.secret_key
    #     else:
    #         secret_key = self.env["employee.security"].generate_secret_key()
    #         new_sec = self.env["employee.security"].create(
    #             {
    #                 "employee_id": employee_id,
    #                 "secret_key": secret_key,
    #             }
    #         )
    #         return new_sec.secret_key

    # @api.depends("employee_id")
    # def _compute_secret_key(self):
    #     for record in self:
    #         if record.employee_id:
    #             record.secret_key = self.get_or_create_secret_key(record.employee_id.id)
    #         else:
    #             record.secret_key = False

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
        default=lambda: fields.Datetime.now() + timedelta(minutes=5),
        compute="_compute_expiry_after",
        readonly=True,
    )

    @api.depends("created_at", "expiry_time_interval")
    def _compute_expiry_after(self):
        for record in self:
            if record.created_at and record.expiry_time_interval:
                record.expiry_after = record.created_at + timedelta(
                    minutes=record.expiry_time_interval
                )
            else:
                record.expiry_after = fields.Datetime.now() + timedelta(minutes=5)

    # SECRET KEY MANAGEMENT WITH HISTORY
    @api.model
    def _get_secret_key_list(self):
        """Return list of keys (latest first), rotating if expired."""
        ICP = self.env["ir.config_parameter"].sudo()

        keys_json = ICP.get_param("erp_secret_keys")
        key_time_str = ICP.get_param("erp_secret_key_time")

        if isinstance(keys_json, str) and keys_json.strip():
            try:
                keys = json.loads(keys_json)
                if not isinstance(keys, list):
                    keys = []
            except json.JSONDecodeError:
                keys = []
        else:
            keys = []

        # Parse key timestamp safely
        try:
            key_time = (
                fields.Datetime.from_string(key_time_str)
                if isinstance(key_time_str, str)
                else datetime.now()
            )
        except Exception:
            key_time = datetime.now()

        # Rotation configuration
        rotation_interval_hours = 24
        max_keys_to_keep = 3
        now = datetime.now()
        if key_time is not None:
            diff = now - key_time
        else:
            diff = timedelta.max  # Force key rotation if key_time is None
        # Generate or rotate if needed
        if not keys or diff.total_seconds() > rotation_interval_hours * 3600:
            new_key = secrets.token_urlsafe(64)
            keys.insert(0, new_key)
            keys = keys[:max_keys_to_keep]
            ICP.set_param("erp_secret_keys", json.dumps(keys))
            ICP.set_param("erp_secret_key_time", fields.Datetime.to_string(now))

        return keys

    @api.model
    def _get_active_secret_key(self):
        """Return only the latest key."""
        return self._get_secret_key_list()[0]

    def generate_token(self):
        """Generate JWT token using latest key."""
        secret_key = self._get_active_secret_key()
        for record in self:
            if record.employee_id:
                payload = {
                    "user_id": record.salis_user_id,
                    "employee_id": record.employee_id.id,
                    "national_id": record.national_id,
                    "session_id": record.salis_session_id,
                    "exp": datetime.now()
                    + timedelta(minutes=record.expiry_time_interval),
                }
                token = jwt.encode(payload, secret_key, algorithm="HS256")
                record.jwt_token = token

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
        self.ensure_one()
        # erp_record = self.search([("jwt_token", "=", token)], limit=1)
        # if not erp_record:
        #     return json_Response({"error": "ERP record not found for this token"}, 404)
        keys = self._get_secret_key_list()
        for key in keys:
            try:
                payload = jwt.decode(
                    token,
                    key,
                    # erp_record.secret_key,
                    algorithms=["HS256"],
                    options={"verify_exp": True},
                )
                return payload
            except jwt.ExpiredSignatureError:
                return json_Response({"error": "Token has expired"}, 401)
            except jwt.InvalidTokenError:
                continue
        return json_Response({"error": "Invalid token"}, 401)
