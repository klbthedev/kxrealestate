# models/dashboard_service.py
from odoo import models, api
import logging
_logger = logging.getLogger(__name__)

class DashboardService(models.AbstractModel):
    _name = 'kx.dashboard.service'
    _description = 'Dashboard Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # --------------------------------------------------------------------------
    
    @api.model
    def get_dashboard_data(self, date_from=False, date_to=False):
        
        #############################################################
        # 1. General Report
        #############################################################
        
        # 1.1. For Payment Request -----------------------------------------------------------------
        query = """
            SELECT
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=1) AS jan_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=2) AS feb_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=3) AS mar_count,

                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=4) AS apr_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=5) AS may_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=6) AS jun_count,

                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=7) AS jul_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=8) AS aug_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=9) AS sep_count,

                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=10) AS oct_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=11) AS nov_count,
                COUNT(*) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=12) AS dec_count
            FROM loan_line_rs_own
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        self.env.cr.execute(query, params)
        payment_request_letter = self.env.cr.dictfetchall()

        # 1.2. For Paid Customers (count value) -----------------------------------------------------------------
        query = """
            SELECT
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=1) AS jan_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=2) AS feb_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=3) AS mar_count,

                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=4) AS apr_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=5) AS may_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=6) AS jun_count,

                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=7) AS jul_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=8) AS aug_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=9) AS sep_count,

                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=10) AS oct_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=11) AS nov_count,
                COUNT(*) FILTER (WHERE payment_state='paid' AND payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=12) AS dec_count
            FROM loan_line_rs_own
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        self.env.cr.execute(query, params)
        paid_customers_count = self.env.cr.dictfetchall()


        # 1.3. For Paid Customers (% value) -----------------------------------------------------------------
        months = [
            'jan_count', 'feb_count', 'mar_count', 'apr_count',
            'may_count', 'jun_count', 'jul_count', 'aug_count',
            'sep_count', 'oct_count', 'nov_count', 'dec_count'
        ]
        paid_customers_percentage = {}
        for month in months:
            requested = payment_request_letter[0].get(month, 0) or 0
            paid = paid_customers_count[0].get(month, 0) or 0

            paid_customers_percentage[month] = (round(paid / requested * 100, 2)
                if requested
                else 0
            )
        
        # converting the list into dictionary to make it compatible with presentation template
        paid_customers_percentage = [paid_customers_percentage]
        
        
        # 1.4. For Total Requested Amount (in Birr) -----------------------------------------------------------------
        query = """
            SELECT
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=1),0) AS jan_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=2),0) AS feb_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=3),0) AS mar_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=4),0) AS apr_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=5),0) AS may_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=6),0) AS jun_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=7),0) AS jul_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=8),0) AS aug_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=9),0) AS sep_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=10),0) AS oct_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=11),0) AS nov_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND EXTRACT(MONTH FROM date)=12),0) AS dec_amount
            FROM loan_line_rs_own
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        self.env.cr.execute(query, params)
        total_requested_amount = self.env.cr.dictfetchall()


        # 1.5. For Total Collected Amount (in Birr) -----------------------------------------------------------------
        query = """
            SELECT
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=1),0) AS jan_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=2),0) AS feb_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=3),0) AS mar_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=4),0) AS apr_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=5),0) AS may_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=6),0) AS jun_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=7),0) AS jul_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=8),0) AS aug_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=9),0) AS sep_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=10),0) AS oct_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=11),0) AS nov_amount,
                COALESCE(SUM(amount) FILTER (WHERE payment_request_letter='yes' AND payment_state='paid' AND EXTRACT(MONTH FROM date)=12),0) AS dec_amount
            FROM loan_line_rs_own
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        self.env.cr.execute(query, params)
        total_collected_amount = self.env.cr.dictfetchall()
        

        # 1.6. For Remaining Amount to be Collected (Birr) -----------------------------------------------------------------
        months = [
            'jan_amount', 'feb_amount', 'mar_amount', 'apr_amount',
            'may_amount', 'jun_amount', 'jul_amount', 'aug_amount',
            'sep_amount', 'oct_amount', 'nov_amount', 'dec_amount'
        ]
        remaining_amount_tobe_collected = {}
        for month in months:
            requested = total_requested_amount[0].get(month, 0) or 0
            paid = total_collected_amount[0].get(month, 0) or 0

            remaining_amount_tobe_collected[month] = (requested - paid)
        
        # converting the list into dictionary to make it compatible with presentation template
        remaining_amount_tobe_collected = [remaining_amount_tobe_collected]
              
                
        # 1.7. For Warning Letter -----------------------------------------------------------------
        query = """
            SELECT
                b.id,
                b.name AS letter_level_name,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 1 THEN 1 END) AS jan_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 2 THEN 1 END) AS feb_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 3 THEN 1 END) AS mar_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 4 THEN 1 END) AS apr_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 5 THEN 1 END) AS may_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 6 THEN 1 END) AS jun_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 7 THEN 1 END) AS jul_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 8 THEN 1 END) AS aug_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 9 THEN 1 END) AS sep_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 10 THEN 1 END) AS oct_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 11 THEN 1 END) AS nov_count,
                COUNT(CASE WHEN EXTRACT(MONTH FROM a.warning_letter_date) = 12 THEN 1 END) AS dec_count
            FROM warning_letter_level b
            LEFT JOIN warning_letter a
                ON a.letter_level_id = b.id
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND a.warning_letter_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND a.warning_letter_date <= %s"
            params.append(date_to)
        query += """ 
            GROUP BY b.id, b.name
            ORDER BY b.name
        """
        self.env.cr.execute(query, params)
        warning_letter_levels = self.env.cr.dictfetchall()
                  
        
        # 1.8 For Unit Status Part -------------------------------------------------------------
        query = """
            SELECT
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 1 THEN b.id END) AS jan_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 2 THEN b.id END) AS feb_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 3 THEN b.id END) AS mar_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 4 THEN b.id END) AS apr_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 5 THEN b.id END) AS may_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 6 THEN b.id END) AS jun_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 7 THEN b.id END) AS jul_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 8 THEN b.id END) AS aug_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 9 THEN b.id END) AS sep_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 10 THEN b.id END) AS oct_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 11 THEN b.id END) AS nov_count,
                COUNT(DISTINCT CASE WHEN EXTRACT(MONTH FROM b.checklist_date) = 12 THEN b.id END) AS dec_count
            FROM ownership_contract a
            INNER JOIN ownership_handover_checklist b
                ON b.ownership_contract_id = a.id
            INNER JOIN loan_line_rs_own c
                ON c.loan_id = a.id
            WHERE c.amount_residual > 0 AND b.done = false
        """    
        params = []
        if date_from:
            query += " AND b.checklist_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND b.checklist_date <= %s"
            params.append(date_to)
        # query += """ 
        #     GROUP BY b.id, b.name
        #     ORDER BY b.name
        # """
        self.env.cr.execute(query, params)
        handover_ready_unit = self.env.cr.dictfetchall()

        #############################################################
        # 2. Cards
        #############################################################
        
        # 2.1. For unit state ----------------------------------------------------
        query_unit_state = """
            SELECT
                COUNT(*) FILTER (WHERE state='free') AS available_units_count,
                COUNT(*) FILTER (WHERE state='sold') AS sold_units_count,
                COUNT(*) FILTER (WHERE state='blocked') AS blocked_units_count
            FROM product_template
            WHERE 1=1
        """
        self.env.cr.execute(query_unit_state)
        units_state_count = self.env.cr.fetchone() or (0,0,0)

        # 2.2. For contract state ------------------------------------------------
        query_contract_state = """
            SELECT
                COUNT(*) FILTER (WHERE state='cancel') AS cancelled_contract_count
            FROM ownership_contract
            WHERE 1=1
        """
        self.env.cr.execute(query_contract_state)
        cancelled_contract_count = self.env.cr.fetchone() or (0)


        #############################################################
        # 3. Installment Report
        #############################################################
        
        # 3.1. For Remaining Amount vs Paid Amount ----------------------------------------
        query = """
            SELECT
                number AS installment_number,                
                ROUND(COALESCE((SUM(amount-amount_residual) FILTER (WHERE payment_state='paid'))::numeric, 0), 2) AS total_paid_amount,
                ROUND(COALESCE((SUM(amount_residual) FILTER (WHERE amount_residual > 0))::numeric, 0), 2) AS total_remaining_amount,
                ROUND(COALESCE((SUM(amount_residual) FILTER (WHERE amount_residual > 0 AND CURRENT_DATE > "date"))::numeric, 0), 2) AS total_overdue_amount,
                ROUND(COALESCE((SUM(amount) FILTER (WHERE 1=1))::numeric, 0), 2) AS total_installment_amount
            FROM loan_line_rs_own
            GROUP BY number
            ORDER BY number ASC
        """
        self.env.cr.execute(query)
        installment_summary = self.env.cr.dictfetchall()

        # calculate total value of each row
        total_paid = sum(
            row["total_paid_amount"] or 0
            for row in installment_summary
        )
        total_remaining = sum(
            row["total_remaining_amount"] or 0
            for row in installment_summary
        )
        total_overdue = sum(
            row["total_overdue_amount"] or 0
            for row in installment_summary
        )
        total_installment = sum(
            row["total_installment_amount"] or 0
            for row in installment_summary
        )

        # 3.2. For To Be Collected vs Overdue Amount ----------------------------------------
        query = """            
            SELECT
                number AS installment_number,
                ROUND(COALESCE((SUM(amount_residual) 
                    FILTER 
                    (
                        WHERE amount_residual > 0
                    ))::numeric, 0), 2) AS total_to_be_collected_amount,

                ROUND(COALESCE((SUM(amount_residual) 
                    FILTER 
                    (
                        WHERE amount_residual > 0 AND "date" < CURRENT_DATE
                    ))::numeric, 0), 2) AS total_collectable_overdue_amount
            FROM loan_line_rs_own
            GROUP BY number
            ORDER BY number ASC
        """
        self.env.cr.execute(query)
        installment_tobe_collected = self.env.cr.dictfetchall()

        # calculate total value of each row
        total_collectable = sum(
            row["total_to_be_collected_amount"] or 0
            for row in installment_tobe_collected
        )
        total_collectable_overdue = sum(
            row["total_collectable_overdue_amount"] or 0
            for row in installment_tobe_collected
        )
        
        ###############################################################
        # Return all results
        ###############################################################
        
        return {
            "payment_request_letter": payment_request_letter,
            "paid_customers_count": paid_customers_count,
            "paid_customers_percentage": paid_customers_percentage,
            "total_requested_amount": total_requested_amount,
            "total_collected_amount": total_collected_amount,
            "remaining_amount_tobe_collected": remaining_amount_tobe_collected,
                      
            "cancelled_contract_count": cancelled_contract_count,
            "available_units_count": units_state_count[0],
            "sold_units_count": units_state_count[1],
            "blocked_units_count": units_state_count[2],

            "warning_letter_levels": warning_letter_levels,
                        
            "handover_ready_unit": handover_ready_unit,
            "handed_over_unit_item17_sep": 0, #result113[1],
            
            "installment_summary": installment_summary,
            "total_paid_amount": total_paid,
            "total_remaining_amount": total_remaining,
            "total_overdue_amount": total_overdue,
            "total_installment_amount": total_installment,

            "installment_tobe_collected": installment_tobe_collected,
            "total_to_be_collected_amount": total_collectable,
            "total_collectable_overdue_amount": total_collectable_overdue,

        }
    #############################################################
    # _logger.info("remaining_amount_tobe_collected %s", remaining_amount_tobe_collected)