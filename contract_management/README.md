# Contract Management (Odoo 18)

Template-driven Contract Management System for Odoo 18 Enterprise/Community.

## Features

- **Contract Templates** composed of **Articles** and **Clauses**, with a
  Draft / Approved / Archived lifecycle.
- **Variables** (Text, Integer, Float, Date, Datetime, Boolean, Selection,
  Partner, Company, Employee, User, generic Many2one) with required flags,
  default values and regex validation.
- **Contracts** generated from an approved template: Draft → Review →
  Approved → Signed → Cancelled/Archived workflow, driven by chatter-tracked
  fields (`mail.thread` / `mail.activity.mixin`).
- **Variable replacement engine** (`contract.template.renderer`,
  `services/template_renderer.py`) using `{{VariableCode}}` syntax.
- **Live preview**: an OWL component (`static/src/js/contract_live_preview.js`)
  calls the `/contract_management/live_preview` JSON-RPC endpoint on every
  variable edit and re-renders the contract HTML without a page reload.
- **QWeb PDF report** with company logo, header/footer and page numbers
  (via `web.external_layout`), plus signature blocks.
- **Security**: three groups (Legal User, Legal Manager, Administrator),
  full ACLs and record rules (multi-company + "see only my own contracts"
  for Legal Users; portal users see only their own contracts).
- **Dashboard**: graph/pivot views on `contract.contract` grouped by
  template/status.
- **Customer Portal**: `/my/contracts` list, contract detail page and PDF
  download, integrated into the standard portal home.
- **REST API** (`controllers/main.py`): JSON-RPC endpoints to list/create
  templates and contracts.
- **Scheduled Actions**: daily cron jobs to notify about contracts expiring
  within 30 days and to auto-archive expired contracts.
- **Automated tests** covering the renderer service, the full contract
  workflow, variable validation constraints and access rights.

## Installation

1. Copy the `contract_management` folder into your Odoo 18 `addons` path.
2. Update the apps list (`Settings > Apps > Update Apps List`).
3. Install **Contract Management** from the Apps menu.
4. Assign users to **Contract Management > Legal User / Legal Manager /
   Administrator** groups under `Settings > Users & Companies > Users`.

## Directory Structure

```
contract_management/
├── __init__.py
├── __manifest__.py
├── controllers/        REST API + Portal controllers
├── models/              ORM models
├── services/            Reusable service layer (template renderer)
├── security/             Groups, ACLs, record rules
├── views/                Backend + portal XML views, menus
├── report/               QWeb PDF report
├── data/                 Sequence, mail templates, cron jobs
├── demo/                 Demo data
├── static/src/{js,xml,css}  OWL live-preview widget & assets
├── wizard/               (reserved for future wizards)
├── tests/                Python unit tests
└── README.md
```

## Running the Tests

```bash
odoo-bin -d your_db -i contract_management --test-enable --stop-after-init \
    --test-tags /contract_management
```

## License

LGPL-3
