{
    "name": "Salis Employee Self Service",
    "version": "16.0.0.0.0",
    "description": "Employee Self Service",
    "depends": [
        "base",
        "basei",
        "hr",
        "iomc",
    ],
    "data": [
        "security/ir.model.access.xml",
        "security/ir.model.access.csv",
        "views/api_test_views.xml",
        "views/webhook_config_views.xml",
        "views/webhook_notification_views.xml",
        "views/erp_security_views.xml",
        "views/menu_items_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "isalis_ess/static/description/icon.png",
        ],
    },
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
    "external_dependencies": {
        "python": ["requests"],
    },
}
