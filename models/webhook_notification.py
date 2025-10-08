# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json
import requests
import logging


def check_value(val, is_bool=False):
    """Simple check_value function to replace the imported one"""
    if is_bool:
        return bool(val)
    return val if val not in [False, None] else ""


_logger = logging.getLogger(__name__)


class WebhookNotificationType(models.Model):
    _name = "webhook.notification_type"
    _description = "Webhook Notification Type"

    name = fields.Char(string="Notification Name", required=True, unique=True)
    event_type = fields.Char(string="Event Type", required=True, unique=True)
    description = fields.Text(string="Description")


class WebhookNotification(models.Model):
    _name = "webhook.notification"
    _description = "Webhook Notification for ESS System"
    _order = "create_date desc"

    name = fields.Char(string="Notification Name", compute="_compute_name", store=True)
    notification_type = fields.Many2one(
        "webhook.notification_type", string="Notification Type"
    )
    event_type = fields.Char(
        string="Event Type", related="notification_type.event_type"
    )
    model_name = fields.Char(string="Model Name")

    record_id = fields.Integer(string="Record ID")
    webhook_url = fields.Char(string="Webhook URL")
    payload = fields.Text(string="Payload Data")
    headers = fields.Text(string="Headers", default="{}")

    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("retry", "Retry"),
        ],
        string="Status",
        default="pending",
        required=True,
    )

    retry_count = fields.Integer(string="Retry Count", default=0)
    max_retries = fields.Integer(string="Max Retries", default=3)

    sent_date = fields.Datetime(string="Sent Date")
    error_message = fields.Text(string="Error Message")

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    @api.depends("notification_type", "model_name", "record_id")
    def _compute_name(self):
        for record in self:
            record.name = (
                f"{record.notification_type} - {record.model_name} #{record.record_id}"
            )

    def _handle_failure(self, error_message):
        """Handle webhook failure"""
        if self.retry_count < self.max_retries:
            self.write(
                {
                    "status": "retry",
                    "retry_count": self.retry_count + 1,
                    "error_message": error_message,
                }
            )
        else:
            self.write({"status": "failed", "error_message": error_message})
        _logger.error(f"Webhook failed: {self.name} - {error_message}")

    def action_send_webhook(self):
        """Send webhook notification"""
        for record in self:
            try:
                # Prepare payload based on notification type
                payload = record._prepare_payload()

                # Send webhook
                response = requests.post(
                    record.webhook_url,
                    json=payload,
                    # headers=json.loads(record.headers or "{}"),
                    timeout=30,
                )

                if response.status_code in [200, 201, 202]:
                    record.write(
                        {
                            "status": "sent",
                            "sent_date": fields.Datetime.now(),
                            "payload": json.dumps(payload, indent=2),
                        }
                    )
                    _logger.info(f"Webhook sent successfully: {record.name}")
                else:
                    record._handle_failure(
                        f"HTTP {response.status_code}: {response.text}"
                    )

            except Exception as e:
                record._handle_failure(str(e))

    def _prepare_payload(self):
        """Prepare payload based on notification type"""
        pass

    def action_retry(self):
        """Retry failed webhooks"""
        for record in self:
            if record.status in ["failed", "retry"]:
                record.write({"status": "pending", "retry_count": 0})
                record.action_send_webhook()

    @api.model
    def create_notification(
        self, event_type, model_name, record_id, webhook_url, headers=None
    ):
        """Create a webhook notification"""
        notification_type = self.env["webhook.notification_type"].search(
            [("event_type", "=", event_type)], limit=1
        )
        return self.create(
            {
                "notification_type": notification_type.id,
                "model_name": model_name,
                "record_id": record_id,
                "webhook_url": webhook_url,
                "headers": json.dumps(headers or {}),
                "status": "pending",
            }
        )

    @api.model
    def send_notification(
        self, event_type, model_name, record_id, webhook_url=None, headers=None
    ):
        """Create and send a webhook notification immediately"""
        if not webhook_url:
            # Get webhook URL from configuration
            config = self.env["webhook.config"].sudo()
            webhook_url = config.get_webhook_url(event_type)

        if not webhook_url:
            _logger.warning(
                f"No webhook URL configured for notification type: {event_type}"
            )
            return None

        notification = self.create_notification(
            event_type, model_name, record_id, webhook_url, headers
        )
        notification.action_send_webhook()
        return notification
