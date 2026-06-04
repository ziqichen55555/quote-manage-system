{
    "name": "Microsoft Graph Mail (HTTPS)",
    "version": "17.0.1.0.0",
    "category": "Mail",
    "summary": "Send mail via Microsoft Graph API (port 443) instead of SMTP",
    "depends": ["mail", "microsoft_outlook"],
    "data": [
        "views/ir_mail_server_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
