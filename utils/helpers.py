from odoo.http import Response
import json
from odoo.http import request


def validate_api_key(br=None):
    csi = (
        request.env["omc.csi"]
        .sudo()
        .get_api_csi(h=request.httprequest.headers, br=br, ccd="salisess")
    )

    return csi


def get_employee(identification_id):
    emp = (
        request.env["hr.employee"]
        .sudo()
        .search([("identification_id", "=", identification_id)], limit=1)
    )
    if not emp:
        return json_Response({"error": "Employee Not found"}, 404)
    return emp


def prepare_ilogdata(csi, request):
    _logdata = {
        "csi": csi.id if csi else None,
        "ccd": csi.ccd if csi else None,
        "rurl": request.httprequest.url,
        "rfrom": request.httprequest.headers.get("Host"),
        "rtype": request.httprequest.method,
    }

    if _logdata["rtype"] != "GET":
        try:
            content_type = (request.httprequest.content_type or "").lower()

            if "application/json" in content_type:
                # JSON payload
                _logdata["rdata"] = json.dumps(request.get_json_data())
            else:
                # Form-data or x-www-form-urlencoded
                form_data = request.httprequest.form.to_dict()

                # Log file names if any were uploaded
                files_data = {}
                for field_name, file_storage in request.httprequest.files.items():
                    files_data[field_name] = file_storage.filename

                # Combine both into one log object
                combined_data = {"form_fields": form_data, "uploaded_files": files_data}
                _logdata["rdata"] = json.dumps(combined_data)

        except Exception as e:
            _logdata["rdata"] = f"Error reading request data: {str(e)}"

    return _logdata


def check_value(val, is_bool=False):
    if is_bool:
        return bool(val)
    return val if val not in [False, None] else ""


def json_Response(string, status, content_type="application/json; charset=utf-8"):
    return Response(
        json.dumps(string, ensure_ascii=False),
        content_type=content_type,
        status=status,
    )
