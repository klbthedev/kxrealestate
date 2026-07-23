# Telegram Notification Center (Odoo 19 Community)

Telegram Notification Center is a custom Odoo 19 Community module that sends business event alerts to a Telegram chat/group.

## Features

This module sends Telegram notifications for:

- Sale Order Confirmed
- Purchase Order Confirmed
- Invoice Paid
- Payment Due (Scheduled/Cron)
- Stock Low (Scheduled/Cron)
- CRM Lead Assigned
- Attendance Alerts (Scheduled/Cron)

Note:
- `Approval Required` was removed from dependency flow to keep compatibility with Odoo 19 Community environments where `approvals` is unavailable.

## Module Path

- Module name: `telegram_notification_center`

## Requirements

- Odoo 19 Community
- Python package: `requests`
- Installed Odoo apps:
  - Sales (`sale_management`)
  - Purchase (`purchase`)
  - Accounting (`account`)
  - Inventory (`stock`)
  - CRM (`crm`)
  - Attendances (`hr_attendance`)

## Installation

Run Odoo with the parent addons path:


Then in Odoo:

1. Apps -> Update Apps List
2. Search `Telegram Notification Center`
3. Install / Upgrade

## Telegram Setup

1. Create bot using `@BotFather`
2. Get bot token
3. Add bot to target group/channel
4. Get `chat_id`

Example to get chat by public username:

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getChat?chat_id=@your_group_username"
```

Use returned `id` (example: `-1003750784382`) as `Telegram Chat ID`.

Test send message:

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Odoo%20test"
```

## Odoo Configuration

Go to:

- Settings -> General Settings -> Telegram Notification Center

Fill:

- Enable Telegram Notifications
- Telegram Bot Token
- Telegram Chat ID
- Low Stock Threshold

Save.

## How to Test (English)

### 1) Purchase Order

1. Create RFQ in Purchase
2. Confirm PO
3. Verify Telegram message

### 2) Sale Order

1. Create quotation in Sales
2. Confirm SO
3. Verify Telegram message

If you get route/stock errors (`No rule has been found to replenish...`), test with a Service product or fix inventory routes.

### 3) Invoice Paid

1. Create + post customer invoice
2. Register payment
3. Verify `Invoice Paid` Telegram message

### 4) Payment Due (Cron)

1. Create posted invoice with due date <= today and unpaid
2. Run scheduled action manually:
   - Settings -> Technical -> Automation -> Scheduled Actions
   - `Telegram: Payment Due Alerts`
3. Verify Telegram message

### 5) Stock Low (Cron)

1. Ensure product on-hand below threshold
2. Run scheduled action:
   - `Telegram: Low Stock Alerts`
3. Verify Telegram message

### 6) CRM Lead Assigned

1. Create CRM lead
2. Assign or change `Salesperson`
3. Verify Telegram message

### 7) Attendance Alerts (Cron)

1. Keep one employee without check-in for today
2. Run scheduled action:
   - `Telegram: Attendance Alerts`
3. Verify Telegram message

## Troubleshooting

- Error: `Forbidden: bot is not a member of the supergroup chat`
  - Add the bot back to the group.
  - Verify the bot token and chat ID.

- Error: `No rule has been found to replenish ...`
  - This is not a Telegram module issue.
  - Fix inventory route and product type configuration.

- No message sent:
  - Ensure Telegram notifications are enabled.
  - Verify token and chat ID values.
  - Check Odoo logs for `Failed to send telegram notification`.

## Security Notes

- Never expose bot token publicly.
- If token is exposed, rotate immediately via `@BotFather` (`/revoke` or regenerate token).

## Author

- thetzin
