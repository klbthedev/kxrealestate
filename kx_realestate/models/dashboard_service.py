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
    def get_dashboard_data(self, region=False, city=False, site=False, building=False, floor=False,):
        
        # Cards ##########################################################################

        # 2.1. For unit state ----------------------------------------------------
        query_unit_state = """
            SELECT
                COUNT(*) FILTER (WHERE unit_sales_status='free') AS available_units_count,
                COUNT(*) FILTER (WHERE unit_sales_status='sold') AS sold_units_count,
                COUNT(*) FILTER (WHERE unit_sales_status='blocked') AS blocked_units_count,
                COUNT(*) FILTER (WHERE 1=1) AS total_units_count
            FROM (
                SELECT
                    a.id AS unit_id, a.name AS unit_name, a.code AS unit_code, a.selling_price AS unit_selling_price, 
                    a.state AS unit_sales_status, a.gross_area AS unit_gross_area,
                    b.id AS floor_id, b.name AS floor_name,
                    c.id AS building_id, c.name AS building_name,
                    d.id AS block_id, d.name AS block_name,
                    e.id AS site_id, e.name AS site_name,
                    f.id AS city_id, f.name AS city_name,
		            g.id AS region_id, g.name AS region_name
                FROM product_template a
                INNER JOIN re_floor b ON a.floor_id = b.id
                INNER JOIN building_building c ON b.building_id = c.id
                INNER JOIN re_block d ON c.block_id = d.id
                INNER JOIN re_site e ON d.site_id = e.id
                INNER JOIN site_city f ON e.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) property_details
            WHERE 1=1 
        """
        params = []
        if region:
            query_unit_state += " AND region_name = %s"
            params.append(region)
        if city:
            query_unit_state += " AND city_name = %s"
            params.append(city)
        if site:
            query_unit_state += " AND site_name = %s"
            params.append(site)
        if building:
            query_unit_state += " AND building_name = %s"
            params.append(building)
        if floor:
            query_unit_state += " AND floor_name = %s"
            params.append(floor)
        
        self.env.cr.execute(query_unit_state, params)
        units_state_count = self.env.cr.fetchone() or (0,0,0,0)

        available_units_count = units_state_count[0]
        sold_units_count = units_state_count[1]
        blocked_units_count = units_state_count[2]

        if units_state_count[3] != 0:
            available_units_percent = (units_state_count[0]/units_state_count[3])*100
            sold_units_percent = (units_state_count[1]/units_state_count[3])*100
            blocked_units_percent = (units_state_count[2]/units_state_count[3])*100
        else:
            available_units_percent = 0
            sold_units_percent = 0
            blocked_units_percent = 0

        
        # 2.2. For contract state ------------------------------------------------
        
        query_contract_state = """
            SELECT
                COUNT(*) FILTER (WHERE contract_state='cancel') AS cancelled_contract_count,
                COUNT(*) FILTER (WHERE 1=1) AS total_contract_count
            FROM 
            (   SELECT
                    a.origin AS contract_id, a.name AS contract_ref,
                    a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name,
		            g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) contract_details
            WHERE 1=1
        """
        params = []
        if region:
            query_contract_state += " AND region_name = %s"
            params.append(region)
        if city:
            query_contract_state += " AND city_name = %s"
            params.append(city)
        if site:
            query_contract_state += " AND site_name = %s"
            params.append(site)
        if building:
            query_contract_state += " AND building_name = %s"
            params.append(building)
        if floor:
            query_contract_state += " AND floor_name = %s"
            params.append(floor)
        
        self.env.cr.execute(query_contract_state, params)
        cancelled_contract = self.env.cr.fetchone() or (0,0)

        cancelled_contract_count = cancelled_contract[0]
        total_contract_count = cancelled_contract[1]

        if total_contract_count != 0:
            cancelled_contract_percent = (cancelled_contract[0]/total_contract_count)*100
        else:
            cancelled_contract_percent = 0

        
        # 2.3. For handover checklist --------------------------------------------
        
        query_handover = """
            SELECT
                COALESCE(COUNT(DISTINCT contract_id) FILTER (WHERE checklist_type IS NOT NULL AND total_residual=0 AND handover_state=False),0) AS handover_ready_count,
                COALESCE(COUNT(DISTINCT contract_id) FILTER (WHERE checklist_type IS NOT NULL AND total_residual=0 AND handover_state=True),0) AS handovered_count,
                COALESCE(COUNT(contract_id) FILTER (WHERE 1=1),0) AS total_units_count
            FROM 
            (	SELECT contract_id, contract_code, total_residual, checklist_type, COUNT(name), done AS handover_state
                FROM (
                    SELECT	aa.id AS contract_id, aa.contract_id AS contract_code, SUM(b.amount_residual) AS total_residual,
                            aa.site_name, aa.block_name, aa.building_name, aa.floor_name, aa.city_name, aa.region_name
                    FROM (
                        SELECT
                            a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                            b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                            f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                        FROM ownership_contract a
                        INNER JOIN re_site b ON a.site_id = b.id
                        INNER JOIN re_block c ON a.block_id = c.id
                        INNER JOIN building_building d ON a.building_id = d.id
                        INNER JOIN re_floor e ON a.floor_id = e.id
                        INNER JOIN site_city f ON b.city_id = f.id
	                    INNER JOIN site_region g ON f.region_id = g.id
                    ) aa
                    INNER JOIN loan_line_rs_own b ON aa.id = b.loan_id
                    GROUP BY aa.contract_id, aa.id, aa.site_name, aa.block_name, aa.building_name, aa.floor_name, aa.city_name, aa.region_name
                ) contract_table
            LEFT JOIN ownership_handover_checklist handover_table ON contract_table.contract_id = handover_table.ownership_contract_id
            WHERE 1=1 
        """
        params = []
        if region:
            query_handover += " AND region_name = %s"
            params.append(region)
        if city:
            query_handover += " AND city_name = %s"
            params.append(city)
        if site:
            query_handover += " AND site_name = %s"
            params.append(site)
        if building:
            query_handover += " AND building_name = %s"
            params.append(building)
        if floor:
            query_handover += " AND floor_name = %s"
            params.append(floor)        
        query_handover += """ 
            GROUP BY contract_id, contract_code, total_residual, name, checklist_type, done
            ORDER BY contract_code
        )
        """

        self.env.cr.execute(query_handover, params)
        handover_list_count = self.env.cr.fetchone() or (0,0,0)

        handover_ready_count = handover_list_count[0]
        handovered_count = handover_list_count[1]
        handover_total_units_count = handover_list_count[2]
        
        if handover_total_units_count !=0 :
            handover_ready_percent = (handover_ready_count/handover_total_units_count)*100
            handovered_percent = (handovered_count/handover_total_units_count)*100
        else:
            handover_ready_percent = 0
            handovered_percent = 0

        # Installment #####################################################################

        # 3.1. For Remaining Amount vs Paid Amount ----------------------------------------
        query = """
            SELECT
                bb.number AS installment_number,                
                ROUND(COALESCE((SUM(bb.amount - bb.amount_residual) FILTER (WHERE bb.payment_state='paid'))::numeric, 0), 2) AS total_paid_amount,
                ROUND(COALESCE((SUM(bb.amount_residual) FILTER (WHERE bb.amount_residual > 0))::numeric, 0), 2) AS total_remaining_amount,
                ROUND(COALESCE((SUM(bb.amount_residual) FILTER (WHERE bb.amount_residual > 0 AND CURRENT_DATE > bb.date))::numeric, 0), 2) AS total_overdue_amount,
                ROUND(COALESCE((SUM(bb.amount) FILTER (WHERE 1=1))::numeric, 0), 2) AS total_installment_amount
            FROM (
                SELECT
                    a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) AS aa
            INNER JOIN loan_line_rs_own AS bb ON aa.id = bb.loan_id
            WHERE 1=1 
        """
        params = []
        if region:
            query += " AND aa.region_name = %s"
            params.append(region)
        if city:
            query += " AND aa.city_name = %s"
            params.append(city)
        if site:
            query += " AND aa.site_name = %s"
            params.append(site)
        if building:
            query += " AND aa.building_name = %s"
            params.append(building)
        if floor:
            query += " AND aa.floor_name = %s"
            params.append(floor)
        query += """ 
            GROUP BY bb.number
            ORDER BY bb.number ASC
        """        
        
        self.env.cr.execute(query,params)
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
        total = (total_paid+total_remaining)
        if total !=0 :
            total_paid_amount_percent = (total_paid/total)*100
            total_remaining_amount_percent = (total_remaining/total)*100
        else:
            total_paid_amount_percent = 0
            total_remaining_amount_percent = 0

        
        # 3.2. For To Be Collected vs Overdue Amount ----------------------------------------        
        query = """            
            SELECT
                number AS installment_number,
                ROUND(COALESCE((SUM(amount_residual) FILTER ( WHERE amount_residual > 0 ))::numeric, 0), 2) AS total_to_be_collected_amount,
                ROUND(COALESCE((SUM(amount_residual) FILTER ( WHERE amount_residual > 0 AND "date" < CURRENT_DATE ))::numeric, 0), 2) AS total_collectable_overdue_amount
            FROM
            (	SELECT
                    a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) contract_details
            INNER JOIN loan_line_rs_own b ON contract_details.id = b.loan_id
            WHERE 1=1             
        """
        params = []
        if region:
            query += " AND region_name = %s"
            params.append(region)
        if city:
            query += " AND city_name = %s"
            params.append(city)
        if site:
            query += " AND site_name = %s"
            params.append(site)
        if building:
            query += " AND building_name = %s"
            params.append(building)
        if floor:
            query += " AND floor_name = %s"
            params.append(floor)
        query += """ 
            GROUP BY number
            ORDER BY number ASC
        """   
        self.env.cr.execute(query,params)
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
        
        # Return all results ########################################################
        return {                                 
            "cancelled_contract_count": cancelled_contract_count,
            "cancelled_contract_percent": cancelled_contract_percent,

            "available_units_count": available_units_count,
            "available_units_percent": available_units_percent,

            "sold_units_count": sold_units_count,
            "sold_units_percent": sold_units_percent,
            
            "blocked_units_count": blocked_units_count,           
            "blocked_units_percent": blocked_units_percent,

            "handover_ready_units": handover_ready_count,
            "handover_ready_units_percent": handover_ready_percent,

            "handovered_units": handovered_count,
            "handovered_units_percent": handovered_percent,
           
            "installment_summary": installment_summary,

            "total_paid_amount": total_paid,
            "total_paid_amount_percent": total_paid_amount_percent,

            "total_remaining_amount": total_remaining,
            "total_remaining_amount_percent": total_remaining_amount_percent,

            "total_overdue_amount": total_overdue,
            "total_installment_amount": total_installment,

            "installment_tobe_collected": installment_tobe_collected,
            "total_to_be_collected_amount": total_collectable,
            "total_collectable_overdue_amount": total_collectable_overdue,
        }
        
        #############################################################


    @api.model
    def get_dashboard_data2(self, date_from=False, date_to=False, region=False, city=False, site=False, building=False, floor=False,):        
        
        # General Report #############################################################
        
        # 1.1. For Payment Request -----------------------------------------------------------------
        query = """
            SELECT
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=1) AS jan_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=2) AS feb_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=3) AS mar_count,

                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=4) AS apr_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=5) AS may_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=6) AS jun_count,

                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=7) AS jul_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=8) AS aug_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=9) AS sep_count,

                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=10) AS oct_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=11) AS nov_count,
                COUNT(*) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=12) AS dec_count
            FROM
            (   SELECT
                    a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) contract_details 
            INNER JOIN loan_line_rs_own c ON c.loan_id = contract_details.id
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        if region:
            query += " AND region_name = %s"
            params.append(region)
        if city:
            query += " AND city_name = %s"
            params.append(city)
        if site:
            query += " AND site_name = %s"
            params.append(site)
        if building:
            query += " AND building_name = %s"
            params.append(building)
        if floor:
            query += " AND floor_name = %s"
            params.append(floor)
        self.env.cr.execute(query, params)
        payment_request_letter = self.env.cr.dictfetchall()        
        
        
        # 1.2. For Paid Customers (count value) -----------------------------------------------------------------
        query = """
            SELECT
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=1) AS jan_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=2) AS feb_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=3) AS mar_count,

                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=4) AS apr_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=5) AS may_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=6) AS jun_count,

                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=7) AS jul_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=8) AS aug_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=9) AS sep_count,

                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=10) AS oct_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=11) AS nov_count,
                COUNT(*) FILTER (WHERE c.payment_state='paid' AND c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=12) AS dec_count
            FROM 
            (   SELECT
                    a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) contract_details 
            INNER JOIN loan_line_rs_own c ON c.loan_id = contract_details.id
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        if region:
            query += " AND region_name = %s"
            params.append(region)
        if city:
            query += " AND city_name = %s"
            params.append(city)
        if site:
            query += " AND site_name = %s"
            params.append(site)
        if building:
            query += " AND building_name = %s"
            params.append(building)
        if floor:
            query += " AND floor_name = %s"
            params.append(floor)
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
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=1),0) AS jan_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=2),0) AS feb_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=3),0) AS mar_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=4),0) AS apr_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=5),0) AS may_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=6),0) AS jun_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=7),0) AS jul_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=8),0) AS aug_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=9),0) AS sep_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=10),0) AS oct_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=11),0) AS nov_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND EXTRACT(MONTH FROM c.date)=12),0) AS dec_amount
            FROM 
            (   SELECT
                    a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) contract_details 
            INNER JOIN loan_line_rs_own c ON c.loan_id = contract_details.id
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        if region:
            query += " AND region_name = %s"
            params.append(region)
        if city:
            query += " AND city_name = %s"
            params.append(city)
        if site:
            query += " AND site_name = %s"
            params.append(site)
        if building:
            query += " AND building_name = %s"
            params.append(building)
        if floor:
            query += " AND floor_name = %s"
            params.append(floor)
        self.env.cr.execute(query, params)
        total_requested_amount = self.env.cr.dictfetchall()


        # 1.5. For Total Collected Amount (in Birr) -----------------------------------------------------------------
        query = """
            SELECT
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=1),0) AS jan_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=2),0) AS feb_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=3),0) AS mar_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=4),0) AS apr_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=5),0) AS may_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=6),0) AS jun_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=7),0) AS jul_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=8),0) AS aug_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=9),0) AS sep_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=10),0) AS oct_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=11),0) AS nov_amount,
                COALESCE(SUM(amount) FILTER (WHERE c.payment_request_letter='yes' AND c.payment_state='paid' AND EXTRACT(MONTH FROM c.date)=12),0) AS dec_amount
            FROM 
            (   SELECT
                    a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) contract_details 
            INNER JOIN loan_line_rs_own c ON c.loan_id = contract_details.id
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND date <= %s"
            params.append(date_to)
        if region:
            query += " AND region_name = %s"
            params.append(region)
        if city:
            query += " AND city_name = %s"
            params.append(city)
        if site:
            query += " AND site_name = %s"
            params.append(site)
        if building:
            query += " AND building_name = %s"
            params.append(building)
        if floor:
            query += " AND floor_name = %s"
            params.append(floor)
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
                b.id, b.name AS letter_level_name,
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
            FROM (
                SELECT
                    a.id, a.origin AS contract_id, a.name AS contract_ref, a.selling_price AS unit_selling_price, a.state AS contract_state,
                    b.name AS site_name, c.name AS block_name, d.name AS building_name, e.name AS floor_name,
                    f.id AS city_id, f.name AS city_name, g.id AS region_id, g.name AS region_name
                FROM ownership_contract a
                INNER JOIN re_site b ON a.site_id = b.id
                INNER JOIN re_block c ON a.block_id = c.id
                INNER JOIN building_building d ON a.building_id = d.id
                INNER JOIN re_floor e ON a.floor_id = e.id
                INNER JOIN site_city f ON b.city_id = f.id
	            INNER JOIN site_region g ON f.region_id = g.id
            ) contract_details
            INNER JOIN warning_letter a ON a.ownership_contract_id = contract_details.id 
            INNER JOIN warning_letter_level b ON a.letter_level_id = b.id
            WHERE 1=1            
        """
        params = []
        if date_from:
            query += " AND a.warning_letter_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND a.warning_letter_date <= %s"
            params.append(date_to)
        if region:
            query += " AND region_name = %s"
            params.append(region)
        if city:
            query += " AND city_name = %s"
            params.append(city)
        if site:
            query += " AND site_name = %s"
            params.append(site)
        if building:
            query += " AND building_name = %s"
            params.append(building)
        if floor:
            query += " AND floor_name = %s"
            params.append(floor)

        query += """ 
            GROUP BY b.id, b.name
            ORDER BY b.name
        """
        self.env.cr.execute(query, params)
        warning_letter_levels = self.env.cr.dictfetchall()
        
        # Return all results ###############################################################       
        return {
            "payment_request_letter": payment_request_letter,
            "paid_customers_count": paid_customers_count,
            "paid_customers_percentage": paid_customers_percentage,
            "total_requested_amount": total_requested_amount,
            "total_collected_amount": total_collected_amount,
            "remaining_amount_tobe_collected": remaining_amount_tobe_collected,
            "warning_letter_levels": warning_letter_levels,
        }
    
        #############################################################
        # _logger.info("remaining_amount_tobe_collected %s", remaining_amount_tobe_collected)