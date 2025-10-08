# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WebhookConfig(models.Model):
    _name = "webhook.config"
    _description = "Webhook Configuration for ESS System"
    _order = "name"

    name = fields.Char(
        string="Configuration Name", related="notification_type.name", store=True
    )
    notification_type = fields.Many2one(
        "webhook.notification_type",
        string="Notification Type",
        required=True,
    )
    event_type = fields.Char(related="notification_type.event_type")

    webhook_url = fields.Char(string="Webhook URL", required=True)
    is_active = fields.Boolean(string="Active", default=True)

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    _sql_constraints = [
        (
            "unique_notification_type",
            "unique(notification_type, company_id)",
            "Only one configuration per notification type per company is allowed!",
        )
    ]

    @api.model
    def get_webhook_url(self, event_type):
        """Get webhook URL for a specific notification type"""
        config = self.search(
            [
                ("event_type", "=", event_type),
                ("is_active", "=", True),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

        if config:
            return config.webhook_url

        return False
