# Dental Lab Management

An Odoo 18.0 custom module for managing dental prosthesis work orders between dentists and a dental laboratory. Dentists submit and track orders through the customer portal, while laboratory staff manage production, tooth selections, scan files, PMMA trials, and customer invoicing in the Odoo backend.

| Property | Value |
|---|---|
| Module technical name | `dental_lab` |
| Display name | Dental Lab Management |
| Version | `18.0.1.0.0` |
| Odoo version | 18.0 |
| License | LGPL-3 |
| Author | W. Demdoum |

## Contents

- [Features](#features)
- [Work-order lifecycle](#work-order-lifecycle)
- [Access roles](#access-roles)
- [Installation](#installation)
- [Configuration](#configuration)
- [User workflows](#user-workflows)
- [Technical architecture](#technical-architecture)
- [Routes and assets](#routes-and-assets)
- [Development notes](#development-notes)
- [Troubleshooting](#troubleshooting)
- [Scope and limitations](#scope-and-limitations)

## Features

### Work orders

- Generates work-order references through the `dental.lab.order` sequence (configured format: `DL/YYYY/0001`).
- Tracks dentist, patient name, shade/colour, external form reference, order date, due date, priority, instructions, and assigned technician.
- Supports multiple work lines with a dental product, description, selected teeth, quantity, unit price, and total price.
- Provides list, kanban, form, and search views, including filters and grouping by status, technician, or dentist.
- Uses Odoo chatter and activities through `mail.thread` and `mail.activity.mixin`.

### FDI tooth selection and dental files

- Includes an OWL odontogram field for selecting teeth using FDI numbering.
- Validates tooth numbers and rejects duplicate tooth selections on a work-order line.
- Supports scan and case-file attachments.
- The portal accepts `.stl`, `.obj`, `.rar`, and `.zip` uploads, with a configured maximum size of 100 MiB per file.
- The backend includes a Three.js-based 3D preview for STL and OBJ files.

### PMMA trial tracking

- Links PMMA trial records to work orders, with date, description, quantity, attachment, price, and status.
- PMMA statuses are Draft, Failed, and Validated.
- PMMA actions require the related work order to be In Progress.
- The model validates that no more than one PMMA line is validated per work order.
- A work order with PMMA lines cannot be marked Done until at least one PMMA line is validated.

### Dentist portal

Authenticated portal users can:

- List and filter their work orders, with pagination and sorting.
- Submit a new work order with work lines and supported attachments.
- View work-order details and follow status changes.
- Edit a work order while it remains in New/Draft state.
- See the order total in the portal list.

Portal routes are implemented in `controllers/portal.py`; their QWeb templates are in `views/portal_templates.xml`.

### Customer invoicing

- Lab managers can create a customer invoice from a completed work order.
- A grouped-invoice server action supports selected eligible orders from the work-order list.
- Grouped invoices require a single company and currency and a common dentist or commercial partner.
- Invoice lines include work-order elements and validated PMMA trials only.
- The created invoice is linked to the order records and noted in their chatter.

The module creates customer invoices (`account.move` with `move_type = 'out_invoice'`). It does **not** implement vendor bills, payroll, or general expense tracking.

### exocad integration

- Provides a backend action that opens a custom-protocol URL for exocad.
- Generates signed, short-lived tokens for order access; the configured token lifetime is 15 minutes.
- Exposes HTTP endpoints for a token-protected order payload and associated binary attachments.
- Includes workstation helper files under `windows_client/`; review and configure them for the target environment before deployment.

The target workstation must have a matching custom protocol handler registered and configured. This integration should be tested on each supported workstation setup.

## Work-order lifecycle

| State | Technical value | Behaviour |
|---|---|---|
| New | `draft` | The order is prepared. Portal dentists may edit it in this state. |
| In Progress | `in_progress` | Requires at least one work line and an assigned technician. PMMA trials can be processed in this state. |
| Done | `done` | Production is complete. If PMMA lines exist, at least one must be validated first. |
| Cancelled | `cancel` | The order is cancelled. An active invoice must be cancelled before cancelling the order. |

Only lab managers can reset a cancelled order to New. Only lab managers can create invoices. Work-order records can only be deleted while they are in Draft.

## Access roles

The custom groups are defined in `security/dental_lab_security.xml`; model access entries are in `security/ir.model.access.csv`.

| Role | Intended access |
|---|---|
| Technician / Prosthesist | Work on assigned orders and related lines; access production and exocad actions. |
| Lab Manager | Implies the technician group; can access all orders, pricing, product and dentist menus, and invoicing actions. |
| Portal dentist | Uses the website portal to create and follow their own work orders. Portal ACLs and record rules are configured separately. |

Technician record rules restrict work-order visibility to orders assigned to the current user; manager rules allow access to all work orders. Portal rules scope work orders and related lines to the current user's partner.

**Before production deployment:** test group assignments, ACLs, record rules, and portal routes with representative technician, manager, and portal accounts. Custom access logic should be reviewed whenever the module is extended.

## Installation

### Requirements

- Odoo **18.0** and a supported PostgreSQL database.
- The addon directory must be named `dental_lab`, because templates, XML IDs, and asset paths use that technical name.
- Manifest dependencies: `base`, `web`, `mail`, `portal`, `product`, and `account`.
- The 3D viewer libraries are bundled under `static/lib/three/`; no separate npm build is declared by the current manifest.

### Install in an existing Odoo addons path

1. Place the `dental_lab` directory in an addons directory loaded by Odoo.
2. Ensure that directory is included in the configured `addons_path`.
3. Restart Odoo and update the Apps list (enable developer mode if necessary).
4. Search for **Dental Lab Management** and install it.

For an Odoo source checkout, a typical module update command is:

```bash
./odoo-bin -d <database_name> -u dental_lab --stop-after-init
```

Run it from the Odoo source directory using the same configuration, addons paths, Python environment, and database connection as the target service. Adapt the command for containers or packaged deployments. Back up the database before upgrading a production instance.

## Configuration

1. **Assign groups:** assign laboratory users to Technician / Prosthesist or Lab Manager.
2. **Classify partners:** use the partner type field to identify dentist and technician contacts where appropriate.
3. **Create dental products:** configure the service products used as dental element types. The portal's product domain selects saleable service products.
4. **Assign technicians:** assign a technician to each order before starting it.
5. **Review company settings:** work orders default to the current company and its currency.
6. **Configure exocad clients if needed:** inspect the files in `windows_client/`, update local paths, register the protocol handler, and test token-based access.

## User workflows

### Dentist / portal user

1. Sign in to the Odoo customer portal.
2. Open **Your work orders** and choose **Create**.
3. Enter patient and order details, add at least one work line, select teeth and element types, and upload supported scan files.
4. Submit the order and return to the list to track progress.
5. Use Edit while the order is still New/Draft.

### Technician

1. Open **YTS Lab → Work orders**.
2. Open an assigned order and review patient details, shade, due date, instructions, and attachments.
3. Start the order after confirming it has a work line and assigned technician.
4. Maintain PMMA trial lines during production; validate or mark a trial as failed as appropriate.
5. Mark the order Done once the completion requirements are satisfied.

### Lab manager

- Review and assign work orders.
- Maintain dental products and dentist contacts.
- Review prices and order totals.
- Create an invoice for one completed order, or select multiple eligible orders and run **Create Grouped Invoice** from the list action menu.

## Technical architecture

```text
dental_lab/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── exocad.py
│   └── portal.py
├── data/
│   └── dental_lab_sequence.xml
├── models/
│   ├── __init__.py
│   ├── account_move.py
│   ├── dental_lab_order.py
│   ├── dental_lab_order_line.py
│   ├── mail_message.py
│   ├── pmma.py
│   ├── res_partner.py
│   └── res_users.py
├── security/
│   ├── dental_lab_security.xml
│   └── ir.model.access.csv
├── static/
│   ├── description/
│   ├── lib/three/
│   ├── src/
│   │   ├── components/
│   │   ├── img/
│   │   ├── js/dental_lab_portal.js
│   │   └── scss/portal.scss
│   └── viewer/
├── views/
│   ├── dental_lab_menus.xml
│   ├── dental_lab_order_views.xml
│   ├── portal_templates.xml
│   └── res_partner_view.xml
└── windows_client/
    ├── dentallab-exocad.reg
    ├── open_exocad.ps1
    └── template.dentalProject
```

### Main models

| Model | Responsibility |
|---|---|
| `dental.lab.order` | Work-order fields and lifecycle, totals, invoice link, grouped invoicing, and exocad token/payload helpers. |
| `dental.order.line` | Dental products, FDI tooth selections, quantities, and line pricing. |
| `pmma.line` | PMMA trial details, pricing, attachments, and validation state. |
| `res.partner` extension | Partner type, dentist/technician flags, work-order relation, and anonymized dentist code. |
| `res.users` extension | Read-result anonymization for restricted technicians when linked to dentist portal partners. |
| `account.move` extension | Reverse relation from invoices to dental work orders. |
| `mail.message` extension | Custom message behaviour used by the module. |

### Important files

- `__manifest__.py` — module metadata, dependencies, data files, and frontend/backend assets.
- `models/dental_lab_order.py` — primary business logic and invoice actions.
- `models/dental_lab_order_line.py` — line quantities and FDI tooth validation.
- `models/pmma.py` — PMMA trial workflow and validation constraints.
- `controllers/portal.py` — portal listing, create/update handlers, input validation, and file upload handling.
- `controllers/exocad.py` — token-protected HTTP endpoints for exocad.
- `static/src/components/teeth_field.js` — OWL odontogram field.
- `static/src/components/many2many_binary_3d.js` and `static/viewer/` — STL/OBJ preview interface.
- `security/` — model access rights, groups, and record rules.

## Routes and assets

| Route | Purpose |
|---|---|
| `/my/dental-orders` | Portal list for the current dentist. |
| `/my/dental-orders/new` | Portal create form. |
| `/my/dental-orders/submit` | CSRF-protected portal submission. |
| `/my/dental-orders/<id>` | Portal work-order detail. |
| `/my/dental-orders/<id>/edit` | Edit a draft order. |
| `/my/dental-orders/<id>/update` | CSRF-protected draft update. |
| `/dental_lab/exocad/order/<id>` | Token-protected JSON order payload. |
| `/dental_lab/exocad/order/<id>/attachment/<attachment_id>` | Token-protected attachment download. |

The manifest registers portal JavaScript and SCSS in `web.assets_frontend`, and the odontogram, 3D attachment field, and exocad action in `web.assets_backend`.

## Development notes

- Keep new code compatible with Odoo 18.0.
- When adding a model, update `models/__init__.py`, model access CSV, record rules, views, and `__manifest__.py` as appropriate.
- Preserve the technical module name `dental_lab`; it is referenced by XML IDs, QWeb templates, controllers, and asset paths.
- The portal validates submitted product IDs against the allowed product domain and validates tooth selections server-side.
- Portal uploads are validated before saving; a database savepoint is used around order creation/update and attachment handling.
- The repository includes a local Three.js copy and loaders for STL and OBJ files.

## Troubleshooting

**The module does not appear in Apps**

- Confirm the addon directory is named `dental_lab` and is in an Odoo addons path.
- Restart Odoo, update the Apps list, and inspect server logs for manifest or XML errors.

**A technician cannot see an order**

- Confirm the user belongs to Technician / Prosthesist or Lab Manager.
- For technicians, check that the Assigned Technician field points to the correct user.

**The Start action fails**

- The order must be New/Draft, contain at least one work line, and have an assigned technician.

**The Done action fails**

- The order must be In Progress.
- If PMMA lines exist, at least one must be validated.

**An invoice cannot be created**

- Only a Lab Manager can create invoices.
- The order must be Done and must not already have a non-cancelled invoice.
- Grouped invoices also require the same company and currency and a common dentist/commercial partner.

**The 3D preview cannot load a file**

- The attachment must be STL or OBJ.
- Check that the current user can access the attachment and that Odoo can serve it through the web content route.

**The exocad action does not open the application**

- Confirm the custom protocol handler is registered on the workstation.
- Check the configuration in `windows_client/` and the local exocad path.

## Scope and limitations

This module focuses on dental work orders and customer invoicing. It is **not** a complete payroll, vendor-bill, inventory, or general expense-management system. The repository code and security configuration should be tested in a staging database before production deployment. This README describes the implementation inspected in the repository; it does not imply that automated tests or a live installation were executed.
