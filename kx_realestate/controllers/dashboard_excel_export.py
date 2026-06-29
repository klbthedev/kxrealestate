# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import io
import xlsxwriter


def safe(val):
    if isinstance(val, (tuple, list)):
        return val[0] if len(val) else 0
    return val if val is not None else 0

class DashboardExcelExport(http.Controller):

    @http.route('/kx_realestate/dashboard/export_excel', type='http', auth='user', csrf=False)
    def export_dashboard_excel(self, date_from=None, date_to=None):

        service = request.env['kx.dashboard.service'].sudo()
        data = service.get_dashboard_data(date_from, date_to)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # FORMATS
        bold = workbook.add_format({'bold': True})
        title = workbook.add_format({'bold': True, 'font_size': 14})
        header = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        cell = workbook.add_format({'border': 1})
        money = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        percent = workbook.add_format({'num_format': '0.00%', 'border': 1})

        # DASHBOARD 
        sheet = workbook.add_worksheet("Dashboard")
        sheet.write(0, 0, "REAL ESTATE DASHBOARD EXPORT", title)
        # KPI CARDS 
        sheet.write(2, 0, "Cancelled Contracts", bold)
        sheet.write(2, 1, safe(data.get("cancelled_contract_count")))

        sheet.write(3, 0, "Available Units", bold)
        sheet.write(3, 1, safe(data.get("available_units_count")))

        sheet.write(4, 0, "Sold Units", bold)
        sheet.write(4, 1, safe(data.get("sold_units_count")))

        sheet.write(5, 0, "Blocked Units", bold)
        sheet.write(5, 1, safe(data.get("blocked_units_count")))

        # GENERAL SUMMARY TABLE
        start_row = 8
        headers = ["Title", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
        for c, h in enumerate(headers):
            sheet.write(start_row, c, h, header)
        r = start_row + 1
        def write_row(label, row_data, key, fmt=cell):
            nonlocal r
            sheet.write(r, 0, label, cell)
            for i, m in enumerate([
                "sep", "oct", "nov", "dec",
                "jan", "feb", "mar", "apr",
                "may", "jun", "jul", "aug"
            ]):
                sheet.write(r, i + 1, row_data.get(f"{m}_{key}", 0), fmt)
            r += 1

        # TABLES 
        write_row("Customers Requested", data["payment_request_letter"][0], "count")
        write_row("Customers Paid", data["paid_customers_count"][0], "count")
        write_row("Customers Paid %", data["paid_customers_percentage"][0], "count")
        write_row("Total Requested Amount", data["total_requested_amount"][0], "amount")
        write_row("Total Collected Amount", data["total_collected_amount"][0], "amount")

        # FIXED: Remaining Amount
        write_row("Remaining Amount to be Collected", data["remaining_amount_tobe_collected"][0], "amount")

        # HANDOVER
        sheet.write(r, 0, "Customer Ready for Handover", cell)
        sheet.write(r, 1, data.get("handover_ready_unit", [{}])[0].get("jan_count", 0))
        r += 1

        sheet.write(r, 0, "Customer Handovered", cell)
        sheet.write(r, 1, data.get("handed_over_unit_item17_sep", 0))
        r += 2

        # WARNING LETTER SHEET
        warn_sheet = workbook.add_worksheet("Warning Letters")
        headers = ["Level", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for i, h in enumerate(headers):
            warn_sheet.write(0, i, h, header)
        rr = 1
        for line in data.get("warning_letter_levels", []):
            warn_sheet.write(rr, 0, line.get("letter_level_name") or "", cell)
            warn_sheet.write(rr, 1, safe(line.get("jan_count")))
            warn_sheet.write(rr, 2, safe(line.get("feb_count")))
            warn_sheet.write(rr, 3, safe(line.get("mar_count")))
            warn_sheet.write(rr, 4, safe(line.get("apr_count")))
            warn_sheet.write(rr, 5, safe(line.get("may_count")))
            warn_sheet.write(rr, 6, safe(line.get("jun_count")))
            warn_sheet.write(rr, 7, safe(line.get("jul_count")))
            warn_sheet.write(rr, 8, safe(line.get("aug_count")))
            warn_sheet.write(rr, 9, safe(line.get("sep_count")))
            warn_sheet.write(rr, 10, safe(line.get("oct_count")))
            warn_sheet.write(rr, 11, safe(line.get("nov_count")))
            warn_sheet.write(rr, 12, safe(line.get("dec_count")))
            rr += 1

        rr = 1
        for line in data.get("warning_letter_levels", []):
            warn_sheet.write(rr, 0, line.get("letter_level_name"), cell)
            warn_sheet.write(rr, 1, line.get("jan_count", 0))
            warn_sheet.write(rr, 2, line.get("feb_count", 0))
            warn_sheet.write(rr, 3, line.get("mar_count", 0))
            warn_sheet.write(rr, 4, line.get("apr_count", 0))
            warn_sheet.write(rr, 5, line.get("may_count", 0))
            warn_sheet.write(rr, 6, line.get("jun_count", 0))
            warn_sheet.write(rr, 7, line.get("jul_count", 0))
            warn_sheet.write(rr, 8, line.get("aug_count", 0))
            warn_sheet.write(rr, 9, line.get("sep_count", 0))
            warn_sheet.write(rr, 10, line.get("oct_count", 0))
            warn_sheet.write(rr, 11, line.get("nov_count", 0))
            warn_sheet.write(rr, 12, line.get("dec_count", 0))
            rr += 1

        # INSTALLMENT SHEET
        inst = workbook.add_worksheet("Installments")
        inst.write(0, 0, "Installment", header)
        inst.write(0, 1, "Paid", header)
        inst.write(0, 2, "Remaining", header)
        inst.write(0, 3, "Overdue", header)
        r = 1
        for l in data.get("installment_summary", []):
            inst.write(r, 0, safe(l.get("installment_number")))
            inst.write(r, 1, safe(l.get("total_paid_amount")), money)
            inst.write(r, 2, safe(l.get("total_remaining_amount")), money)
            inst.write(r, 3, safe(l.get("total_overdue_amount")), money)
            r += 1

        # CHARTS SHEET
        chart_sheet = workbook.add_worksheet("Charts")
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Paid Amount',
            'categories': ['Installments', 1, 0, r - 1, 0],
            'values': ['Installments', 1, 1, r - 1, 1],
        })

        chart.add_series({
            'name': 'Remaining Amount',
            'categories': ['Installments', 1, 0, r - 1, 0],
            'values': ['Installments', 1, 2, r - 1, 2],
        })

        chart.set_title({'name': 'Installment Summary'})
        chart.set_x_axis({'name': 'Installment'})
        chart.set_y_axis({'name': 'Amount'})

        chart_sheet.insert_chart('B2', chart)

        workbook.close()
        output.seek(0)

        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="dashboard_full.xlsx"')
            ]
        )