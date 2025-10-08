from odoo import http
from odoo.http import request
from ..utils.helpers import (
    json_Response,
    validate_api_key,
    prepare_ilogdata,
)
import requests

auth = "public"


class AppSecurityController(http.Controller):
    def _get_jwt_payload(self, authorization):
        if not authorization:
            return json_Response({"error": "payload Missing Authorization header"}, 401)

        try:
            resp = requests.post(
                "https://apiman.saalees.com/apiman-gateway/saalees/verify_token/1.01",
                params={
                    "tenant_id": "91",
                    "apikey": "9e7cd89b-efaf-4381-8ddf-30a65ddeef81",
                },
                headers={"Authorization": authorization},
                timeout=10,
            )
            if not resp.ok:
                if resp.status_code == 401:
                    return json_Response({"error": "Invalid access token"}, 401)
                return json_Response({"error": "Auth error"}, resp.status_code)

            payload = resp.json()
            return payload
        except Exception as e:
            return json_Response({"error": str(e)}, 500)

    def _get_user_info(self, authorization):
        if not authorization:
            return json_Response(
                {"error": "userinfo Missing Authorization header"}, 401
            )

        try:
            resp = requests.get(
                "https://apiman.saalees.com/apiman-gateway/saalees/Get_user_data/1.0",
                params={"apikey": "9e7cd89b-efaf-4381-8ddf-30a65ddeef81"},
                headers={
                    "Authorization": authorization,
                    "tenant-id": "91",
                },
                timeout=10,
            )
            if not resp.ok:
                if resp.status_code == 401:
                    return json_Response({"error": "Invalid access token"}, 401)
                return json_Response({"error": "Auth error"}, resp.status_code)

            userinfo = resp.json()
            return userinfo

        except Exception as e:
            return json_Response({"error": str(e)}, 500)

    @http.route(
        "/api/erp/jwt2_token",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def get_token(self):
        csi = None
        if auth == "user_restapi":
            csi = validate_api_key()

        _logdata = prepare_ilogdata(csi=csi, request=request)
        if auth == "public" or csi:
            authorization = request.httprequest.headers.get("Authorization")
            payload_resp = self._get_jwt_payload(authorization)
            userinfo_resp = self._get_user_info(authorization)

            if isinstance(payload_resp, http.Response):
                return payload_resp

            if isinstance(userinfo_resp, http.Response):
                return userinfo_resp

            payload = payload_resp
            userinfo = userinfo_resp

            salis_user_id = payload.get("sub")
            salis_session_id = payload.get("sid")
            national_id = userinfo.get("poi_num")

            ErpSecurity = request.env["isalis_ess.erp.security"].sudo()

            # Check if a valid, non-expired token already exists for this user
            existing = ErpSecurity.search(
                [
                    ("national_id", "=", national_id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if existing:
                existing.active = False

            required_fields = [salis_session_id, salis_user_id, national_id]
            missing = [
                name
                for name, value in zip(
                    ["salis_session_id", "salis_user_id", "national_id"],
                    required_fields,
                )
                if not value
            ]
            if missing:
                return json_Response(
                    {"error": f'Missing fields: {", ".join(missing)}'}, 400
                )

            # employee = get_employee(national_id)
            # if isinstance(employee, http.Response):
            #     return employee

            vals = {
                "salis_session_id": salis_session_id,
                "salis_user_id": salis_user_id,
                "national_id": national_id,
            }
            try:
                record = ErpSecurity.create(vals)
                if not record.jwt_token:
                    record.generate_token()
                token = record.jwt_token
                return json_Response({"jwt2_token": token}, 200)
            except Exception as e:
                return json_Response({"error": str(e)}, 500)
        else:
            _logdata["error"] = "Unauthorized Access"
            request.env["basei.log"].sudo().create(_logdata)
            return json_Response({"error": "Unauthorized Access"}, 401)

    @http.route(
        "/api/erp/token/verify",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def verify_erp_token(self):
        data = request.httprequest.get_json()
        if not data or "token" not in data:
            return json_Response({"error": "Missing token"}, 400)

        token = data["token"]
        ErpSecurity = request.env["isalis_ess.erp.security"].sudo()
        record = ErpSecurity.search([("jwt_token", "=", token)], limit=1)
        if record and record.active:
            return json_Response({"valid": True}, 200)
        else:
            return json_Response({"error": "Invalid token"}, 401)

    @http.route(
        "/api/erp/logout",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def logout(self):
        data = request.httprequest.get_json()
        if not data or "token" not in data:
            return json_Response({"error": "Missing token"}, 400)

        token = data["token"]
        ErpSecurity = request.env["isalis_ess.erp.security"].sudo()
        record = ErpSecurity.search([("jwt_token", "=", token)], limit=1)
        if record and record.active:
            record.active = False
            record.jwt_token = False
            return json_Response({"success": True}, 200)
        else:
            return json_Response({"error": "Invalid token"}, 401)
