# kx_realestate QA User Guide (End-to-End)

## 1) Install and Access
- Install/upgrade `kx_realestate`.
- Use an admin user and enable developer mode.
- Open `Real Estate` app.

## 2) Verify Demo Masters
- Go to configuration menus and confirm demo records exist:
  - Site: `Sunrise Township`
  - Block: `Block A`
  - Amenities: `Swimming Pool`, `Gym`
  - Floors: `Floor 1`, `Floor 2`
  - Building types/statuses, regions, and installment template.

## 3) Verify Property Hierarchy
- Open Buildings and check `Skyline Solutions` and `Skyline`.
- Confirm each building is linked to Site/Block.
- Open Units and verify each unit has:
  - Building + Floor
  - Construction Stock State
  - Amenities

### 3a) Building address and location (QA)
- Open a building form, notebook page **Address & location**.
- Set **Country** and **State / Region** (`res.country.state`); optional **City**, **Zone**, **Sub-city**, **Woreda**, **Kebele**.
- Optionally fill **GPS latitude/longitude**, **Land title reference**, **Parcel / plot ID**, and **utility account refs** (separate from physical meter fields).
- Confirm list view optional columns **City** / **State** appear when enabled, and search can filter by them.

### 3c) UI: Kanban, search, list actions (QA)
- Open **Sites**, **Blocks**, **Buildings**, **Floors**, **Ownership contracts**, **Rental contracts**, and **Reservations** (if menu enabled): default view should be **Kanban**; switch to list/form from the view switcher.
- Confirm **search panels**: quick filters (e.g. contract state, unit availability, building site/block) and extra group-by options appear.
- **Lists** show **sample rows** when empty (demo data); **partner/user** columns use **avatars** where configured.
- **Ownership / rental installment** report lists: **Open contract** row button opens the related contract form.
- **Unit** list: optional **thumbnail** column (`image_128`) for quick visual scan; unit **Kanban** keeps image zoom on hover where configured.

### 3b) Smart buttons (QA)
- **Site** form: stat buttons open filtered lists for blocks, buildings, units, reservations, ownership contracts, rental contracts; counts should match list lengths.
- **Block** form: same pattern for buildings, units, reservations, sales, rentals.
- **Building** form: stat buttons for units, floors, reservations, sales, rentals.
- **Floor** form: **Building** opens the parent building; **Units** opens units on that floor.
- **Unit** form: **Reservations**, **Sales**, **Rentals** open related records (counts stay in sync when lines are added).
- **Ownership / Rental contract** forms: **Entries** (journal items on the contract), **Payments** (receipts); ownership also has **Commissions** to `salesperson.commission.line`.

## 4) Reservation Flow
- Pick an available unit and create a reservation.
- Confirm reservation number is generated and state changes to reserved.
- Test release/cancel behavior from reservation actions.

## 5) Ownership Flow
- From reservation/unit, create ownership contract.
- Confirm contract data and installment schedule lines are created.
- Generate due invoice from eligible schedule line.
- Register payment and verify contract balance updates.

### 5a) Terms & Penalty Rules (Sample Logic)
- Open ownership contract notebook:
  - **Terms & Penalty Rules**: use this for manual/custom clauses.
  - **Terms & Penalty Rules (Sample Logic)**: executable sample clauses tied to payment/invoice data.
- In **Terms & Penalty Rules (Sample Logic)**:
  - Review parameter defaults (obligation aligned):
    - Buyer Grace days (30)
    - Buyer Penalty `% / month` (12)
    - Buyer Penalty `% / day` (0.2)
    - Buyer Daily penalty end day (45)
    - Buyer termination day threshold (45)
    - Seller/Builder early-call notice days (30)
    - Seller termination notice to buyer (15 days)
    - Seller early-call `% of total` (85)
    - Refund deduction `%` (15)
    - Seller/Builder delay `% / day` (0.025), cap `%` (3)
  - Click **Calculate** to compute current outputs from live contract/payment/tax data.
  - If rules are triggered and amount is due, **Create Penalty Invoice** button becomes visible.
- Validate payment/tax integration:
  - Create/post at least one ownership installment invoice and register partial/non-payment.
  - Confirm **buyer_payment_default** line shows trigger and computed penalty when overdue after grace days.
  - Confirm **sample_effective_vat_percent** is derived from ownership installment invoice tax amounts.
  - Confirm **sample_buyer_penalty_base_amount** comes from overdue unpaid installments (not from contract total).
  - Confirm **sample_penalty_amount_due** sums triggered buyer-side penalties and invoice is linked in **sample_penalty_invoice_id**.
  - Cancel contract and re-evaluate:
    - **termination_refund** line must compute deduction, VAT amount, and net refund recommendation.
- Cron integration QA:
  - Run **Process Ownership Installment Triggers** and verify sample logic re-evaluates with updated overdue/payment data.

## 6) Rental Flow
- Create rental contract for another unit/customer.
- Generate rental invoice (manual or cron run).
- Register payment and confirm contract/payment status updates.

## 7) Progress and Trigger Validation
- Open floor progress history and verify percent/stage entries.
- Update a floor progress record to a later stage.
- Run trigger cron and verify eligible installment/reminder behavior.

## 8) Reminders and Automation
- Check scheduled actions:
  - Process Ownership Installment Triggers
  - Send Ownership Installment Reminders
  - Auto Generate Rental Invoices
- Force-run each cron in QA and verify expected records/emails/activities.

## 9) Commission Validation
- Confirm salesperson assignment on ownership contract.
- Post payment and verify commission line creation/update.
- Validate expected vs paid commission totals.

## 10) Reports and Documents
- Validate reports:
  - Units Analysis
  - Ownership BI
  - Rental BI
  - Due/Late payment reports
- Print sample documents (reservation, contracts, due/late letters).

## 11) Pass/Fail Criteria
- Full hierarchy works: `Site > Block > Building > Floor > Unit`.
- Ownership and rental flows both complete without tracebacks.
- Triggers/reminders/cron actions execute correctly.
- Reports load and return data.
- Site, block, building, floor, unit, and contract forms open without server errors; smart-button counts and drill-downs are consistent with underlying records.

## 12) Known implementation notes
- Aggregated counts on site/block/building use Odoo `read_group` with `lazy=False` so counts match Odoo 18’s result keys (`__count`).
- If the **place_autocomplete** widget is not available in your database, change the building **Address** field to a plain char in the view or install the module that provides that widget.
