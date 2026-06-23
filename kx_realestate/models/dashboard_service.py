# models/dashboard_service.py
from odoo import models, api
import logging

class DashboardService(models.AbstractModel):
    _name = 'kx.dashboard.service'
    _description = 'Dashboard Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    #############################################################
    @api.model
    def get_dashboard_data(self, date_from=False, date_to=False):
               
        # 1. SEPTEMBER only #####################################
        # 1.1 Installement Part #################################
        query11 = """
            SELECT
                COUNT(*) FILTER (WHERE payment_request_letter='yes') AS payment_request_item1_sep,
                COUNT(*) FILTER (WHERE payment_state='paid') AS paid_customers_count_item_2_sep,
                SUM(amount) FILTER (WHERE payment_request_letter='yes') AS total_requested_amount_item_3_value,
                SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid') AS total_collected_amount_item_4_value
            FROM loan_line_rs_own
            WHERE EXTRACT(MONTH FROM date) = 9
        """
        params11 = []
        if date_from:
            query11 += " AND date >= %s"
            params11.append(date_from)
        if date_to:
            query11 += " AND date <= %s"
            params11.append(date_to)
        self.env.cr.execute(query11, params11)
        result11 = self.env.cr.fetchone() or (0, 0, 0)
        
        # avoid division by zero, check value or assign zero
        paid_customers_percent_item_3_value_sep = 0
        if result11[0] == 0:
            paid_customers_percent_item_3_value_sep = 0
        else:
            paid_customers_percent_item_3_value_sep = ((result11[1]/result11[0])*100)
        
        # total-request amount -check for null value
        if result11[2] is None:
            total_requested_amount_item_3_value = 0
        else:
            total_requested_amount_item_3_value = result11[2]
        
        # total-collected amount -check for null value
        if result11[3] is None:
            total_collected_amount_item_3_value = 0
        else:
            total_collected_amount_item_3_value = result11[3]

        # 1.2 Contract Part #####################################
        query12 = """
            SELECT
                COUNT(*) FILTER (WHERE state='cancel') AS cancelled_contract_item11_sep
            FROM ownership_contract
            WHERE EXTRACT(MONTH FROM date) = 9
        """
        params12 = []
        if date_from:
            query12 += " AND date >= %s"
            params12.append(date_from)
        if date_to:
            query12 += " AND date <= %s"
            params12.append(date_to)
        self.env.cr.execute(query12, params12)
        result12 = self.env.cr.fetchone() or (0, 0, 0)

        # 1.3 Unit Status Part #####################################
        query13 = """
            SELECT
                COUNT(*) FILTER (WHERE unit_status_id=0) AS handover_ready_unit_item16_sep,
                COUNT(*) FILTER (WHERE unit_status_id=1) AS handed_over_unit_item17_sep
            FROM re_unit_status
            WHERE EXTRACT(MONTH FROM unit_status_id_date) = 9
        """
        # COUNT(*) FILTER (WHERE unit_status_id='Handover Ready') AS handover_ready_unit_item16_sep,
        # COUNT(*) FILTER (WHERE unit_status_id='Handed Over') AS handed_over_unit_item17_sep
        params13 = []
        if date_from:
            query13 += " AND date >= %s"
            params13.append(date_from)
        if date_to:
            query13 += " AND date <= %s"
            params13.append(date_to)
        self.env.cr.execute(query13, params13)
        result13 = self.env.cr.fetchone() or (0, 0, 0)
        
        
        # Return all results ##################################    
        return {
            "payment_request_item1_sep": result11[0],
            "paid_customers_count_item_2_sep": result11[1],
            "paid_customers_percent_item_3_sep": paid_customers_percent_item_3_value_sep,
            "total_requested_amount_item_3_sep": total_requested_amount_item_3_value,
            "total_collected_amount_item_4_sep": total_collected_amount_item_3_value,
            "remaining_amount_tobe_collected_item_5_sep": (total_requested_amount_item_3_value - total_collected_amount_item_3_value),
            "cancelled_contract_item11_sep": result12[0],
            "handover_ready_unit_item16_sep": result13[0],
            "handed_over_unit_item17_sep": result13[1],
        }
    #############################################################

    # query = """
    #         SELECT
    #             COUNT(*) FILTER (WHERE payment_request_letter='yes') AS requested_payment_count,
    #             COUNT(*) FILTER (WHERE trigger_type='construction') AS construction_count,
    #             COUNT(*) FILTER (WHERE trigger_type='date') AS date_count             
    #         FROM loan_line_rs_own
    #         WHERE 1=1
    #     """