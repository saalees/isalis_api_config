from odoo import models, fields, api
import requests
import json
from odoo.exceptions import UserError


class ApiTypeModel(models.Model):
    _name = "api.type.model"
    _description = "API Type Model"

    name = fields.Char("API Type", required=True, unique=True)
    description = fields.Text("Description")
    endpoint = fields.Char("Endpoint")
    method = fields.Selection(
        [
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("PATCH", "PATCH"),
            ("DELETE", "DELETE"),
        ],
        string="HTTP Method",
        default="GET",
        required=True,
    )

    request_data = fields.Text("Request Data (JSON)")
    headers = fields.Text("Headers (JSON)", default="{}")


class ApiTestModel(models.Model):
    _name = "api.test.model"
    _description = "API Testing Model"

    api_type = fields.Many2one("api.type.model", string="API Type", required=True)
    name = fields.Char("Test Name", related="api_type.name", store=True)
    description = fields.Text(related="api_type.description", string="Description")

    endpoint = fields.Char(
        related="api_type.endpoint", string="Endpoint", readonly=False
    )
    method = fields.Selection(
        related="api_type.method", string="HTTP Method", store=True
    )
    request_data = fields.Text(related="api_type.request_data", string="Request Data")
    headers = fields.Text(related="api_type.headers", string="Headers (JSON)")
    masked_headers = fields.Text(
        string="Headers",
        compute="_compute_masked_headers",
        store=False,
        readonly=True,
    )

    base_url = fields.Char("Base URL", default="http://localhost:8066")
    response_status = fields.Integer("Response Status")
    response_data = fields.Text("Response Data")
    response_time = fields.Float("Response Time (seconds)")

    test_result = fields.Selection(
        [
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("error", "Error"),
        ],
        string="Test Result",
        default="pending",
    )

    error_message = fields.Text("Error Message")
    created_date = fields.Datetime("Created Date", default=fields.Datetime.now)
    executed_date = fields.Datetime("Executed Date")

    @api.depends("headers")
    def _compute_masked_headers(self):
        for rec in self:
            masked = {}
            if not rec.headers:
                rec.masked_headers = ""
                continue

            try:
                # Try to parse the headers JSON
                data = json.loads(rec.headers)
                for key, value in data.items():
                    # Mask sensitive fields
                    if key.lower() in ["api-key", "authorization"]:
                        masked[key] = "********"
                    else:
                        masked[key] = value

                # Pretty-print masked JSON
                rec.masked_headers = json.dumps(masked, indent=2, ensure_ascii=False)

            except Exception:
                # If it's not valid JSON, just return masked version of sensitive words
                text = rec.headers
                text = text.replace("API-KEY", "API-KEY: ********")
                text = text.replace("Authorization", "Authorization: ********")
                rec.masked_headers = text

    def execute_api_test(self):
        """Execute the API test"""
        import time

        response = None
        try:
            # Prepare the request
            url = f"{self.base_url}{self.endpoint}"
            headers = json.loads(self.headers) if self.headers else {}

            # Add default headers
            headers.update(
                {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )

            # Prepare request data
            data = None
            if self.request_data and self.method in ["POST", "PUT", "PATCH"]:
                try:
                    data = json.loads(self.request_data)
                except json.JSONDecodeError:
                    raise UserError("Invalid JSON in request data")

            # Execute the request
            start_time = time.time()

            if self.method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif self.method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif self.method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif self.method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=30)
            elif self.method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)

            end_time = time.time()

            # Update the record with results
            if response is not None:
                self.write(
                    {
                        "response_status": response.status_code,
                        "response_data": response.text,
                        "response_time": round(end_time - start_time, 3),
                        "test_result": "success"
                        if response.status_code < 400
                        else "failed",
                        "executed_date": fields.Datetime.now(),
                        "error_message": None,
                    }
                )
            else:
                self.write(
                    {
                        "test_result": "error",
                        "error_message": "No response received from the API request.",
                        "executed_date": fields.Datetime.now(),
                    }
                )

        except requests.exceptions.RequestException as e:
            self.write(
                {
                    "test_result": "error",
                    "error_message": f"Request error: {str(e)}",
                    "executed_date": fields.Datetime.now(),
                }
            )
        except Exception as e:
            self.write(
                {
                    "test_result": "error",
                    "error_message": f"Error: {str(e)}",
                    "executed_date": fields.Datetime.now(),
                }
            )

    def get_test_summary(self):
        """Get summary of test results"""
        total_tests = self.search_count([])
        successful_tests = self.search_count([("test_result", "=", "success")])
        failed_tests = self.search_count([("test_result", "=", "failed")])
        error_tests = self.search_count([("test_result", "=", "error")])
        pending_tests = self.search_count([("test_result", "=", "pending")])

        return {
            "total": total_tests,
            "successful": successful_tests,
            "failed": failed_tests,
            "error": error_tests,
            "pending": pending_tests,
            "success_rate": round((successful_tests / total_tests * 100), 2)
            if total_tests > 0
            else 0,
        }
