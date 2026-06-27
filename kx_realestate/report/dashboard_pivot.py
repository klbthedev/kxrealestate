from odoo import models, fields, tools

class DashboardReport(models.Model):
    _name = "dashboard.report"
    _description = "Real Estate Dashboard Report"
    _auto = False
    _order = "month_order"
    _rec_name = "kpi_name"

    kpi_name = fields.Char(string="KPI")
    month_order = fields.Integer(string="Month Order")
    month = fields.Char(string="Month")
    value = fields.Float(string="Value")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW dashboard_report AS (

            WITH loan_data AS (

                SELECT
                    l.id,
                    l.amount,
                    l.date,
                    l.payment_state,
                    l.payment_request_letter,

                    CASE
                        WHEN to_char(l.date,'MM-DD') BETWEEN '09-11' AND '10-10' THEN 1
                        WHEN to_char(l.date,'MM-DD') BETWEEN '10-11' AND '11-09' THEN 2
                        WHEN to_char(l.date,'MM-DD') BETWEEN '11-10' AND '12-09' THEN 3
                        WHEN to_char(l.date,'MM-DD') >= '12-10'
                        OR to_char(l.date,'MM-DD') <= '01-08' THEN 4
                        WHEN to_char(l.date,'MM-DD') BETWEEN '01-09' AND '02-07' THEN 5
                        WHEN to_char(l.date,'MM-DD') BETWEEN '02-08' AND '03-09' THEN 6
                        WHEN to_char(l.date,'MM-DD') BETWEEN '03-10' AND '04-08' THEN 7
                        WHEN to_char(l.date,'MM-DD') BETWEEN '04-09' AND '05-08' THEN 8
                        WHEN to_char(l.date,'MM-DD') BETWEEN '05-09' AND '06-07' THEN 9
                        WHEN to_char(l.date,'MM-DD') BETWEEN '06-08' AND '07-07' THEN 10
                        WHEN to_char(l.date,'MM-DD') BETWEEN '07-08' AND '08-06' THEN 11
                        WHEN to_char(l.date,'MM-DD') BETWEEN '08-07' AND '09-05' THEN 12
                        ELSE 13
                    END AS month_order

                FROM loan_line_rs_own l
            ),

            months AS (
                SELECT 1 AS month_order UNION ALL
                SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
                SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL
                SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL
                SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13
            ),

            kpis AS (
                SELECT 'Customers Requested to Pay' AS kpi_name, 1 AS kpi_order
                UNION ALL SELECT 'Customers Paid (count)', 2
                UNION ALL SELECT 'Customers Paid (%)', 3
                UNION ALL SELECT 'Total Requested Amount', 4
                UNION ALL SELECT 'Total Collected Amount', 5
                UNION ALL SELECT 'Remaining Amount', 6
                UNION ALL SELECT 'Cancelled Contracts', 7
                UNION ALL SELECT 'Customer ready for Handover', 8
                UNION ALL SELECT 'Customer Handovered', 9
            ),

            base AS (
                SELECT k.kpi_name, m.month_order
                FROM kpis k
                CROSS JOIN months m
            )

            SELECT
                row_number() OVER () AS id,
                b.kpi_name,
                CASE b.month_order
                    WHEN 1 THEN '01. Meskerem (መስከረም)'
                    WHEN 2 THEN '02. Tikimt (ጥቅምት)'
                    WHEN 3 THEN '03. Hidar (ኅዳር)'
                    WHEN 4 THEN '04. Tahsas (ታኅሣሥ)'
                    WHEN 5 THEN '05. Tir (ጥር)'
                    WHEN 6 THEN '06. Yekatit (የካቲት)'
                    WHEN 7 THEN '07. Megabit (መጋቢት)'
                    WHEN 8 THEN '08. Miazia (ሚያዝያ)'
                    WHEN 9 THEN '09. Ginbot (ግንቦት)'
                    WHEN 10 THEN '10. Sene (ሰኔ)'
                    WHEN 11 THEN '11. Hamle (ሐምሌ)'
                    WHEN 12 THEN '12. Nehase (ነሐሴ)'
                    ELSE '13. Pagume (ጳጉሜ)'
                END AS month,
                            
                b.month_order,
                COALESCE(v.value,0) AS value

            FROM base b

            LEFT JOIN (

                -----------------------------------------------------------------
                -- KPI 1 Requested
                -----------------------------------------------------------------
                SELECT
                    'Customers Requested to Pay' AS kpi_name,
                    month_order,
                    COUNT(*)::numeric AS value
                FROM loan_data
                WHERE payment_request_letter='yes'
                GROUP BY month_order

                UNION ALL

                -----------------------------------------------------------------
                -- KPI 2 Paid count
                -----------------------------------------------------------------
                SELECT
                    'Customers Paid (count)',
                    month_order,
                    COUNT(*)::numeric
                FROM loan_data
                WHERE payment_state='paid'
                GROUP BY month_order

                UNION ALL

                -----------------------------------------------------------------
                -- KPI 3 Paid %
                -----------------------------------------------------------------
                SELECT
                    'Customers Paid (%)',
                    month_order,
                    CASE
                        WHEN COUNT(*) FILTER (WHERE payment_request_letter='yes') = 0 THEN 0
                        ELSE (
                            COUNT(*) FILTER (WHERE payment_state='paid')::numeric
                            / COUNT(*) FILTER (WHERE payment_request_letter='yes')
                        ) * 100
                    END
                FROM loan_data
                GROUP BY month_order

                -----------------------------------------------------------------
                UNION ALL

                -- KPI 4 Requested Amount
                -----------------------------------------------------------------
                SELECT
                    'Total Requested Amount',
                    month_order,
                    COALESCE(SUM(amount),0)
                FROM loan_data
                WHERE payment_request_letter='yes'
                GROUP BY month_order

                UNION ALL

                -----------------------------------------------------------------
                -- KPI 5 Collected Amount
                -----------------------------------------------------------------
                SELECT
                    'Total Collected Amount',
                    month_order,
                    COALESCE(SUM(amount),0)
                FROM loan_data
                WHERE payment_request_letter='yes'
                AND payment_state='paid'
                GROUP BY month_order

                UNION ALL

                -----------------------------------------------------------------
                -- KPI 6 Remaining Amount
                -----------------------------------------------------------------
                SELECT
                    'Remaining Amount',
                    month_order,
                    COALESCE(
                        SUM(CASE WHEN payment_request_letter='yes' THEN amount ELSE 0 END)
                        -
                        SUM(CASE WHEN payment_request_letter='yes' AND payment_state='paid' THEN amount ELSE 0 END),
                    0)
                FROM loan_data
                GROUP BY month_order

                UNION ALL

                -----------------------------------------------------------------
                -- KPI 7 Cancelled Contracts
                -----------------------------------------------------------------
                SELECT
                    'Cancelled Contracts',
                    CASE
                        WHEN to_char(date,'MM-DD') BETWEEN '09-11' AND '10-10' THEN 1
                        WHEN to_char(date,'MM-DD') BETWEEN '10-11' AND '11-09' THEN 2
                        WHEN to_char(date,'MM-DD') BETWEEN '11-10' AND '12-09' THEN 3
                        WHEN to_char(date,'MM-DD') >= '12-10'
                        OR to_char(date,'MM-DD') <= '01-08' THEN 4
                        WHEN to_char(date,'MM-DD') BETWEEN '01-09' AND '02-07' THEN 5
                        WHEN to_char(date,'MM-DD') BETWEEN '02-08' AND '03-09' THEN 6
                        WHEN to_char(date,'MM-DD') BETWEEN '03-10' AND '04-08' THEN 7
                        WHEN to_char(date,'MM-DD') BETWEEN '04-09' AND '05-08' THEN 8
                        WHEN to_char(date,'MM-DD') BETWEEN '05-09' AND '06-07' THEN 9
                        WHEN to_char(date,'MM-DD') BETWEEN '06-08' AND '07-07' THEN 10
                        WHEN to_char(date,'MM-DD') BETWEEN '07-08' AND '08-06' THEN 11
                        WHEN to_char(date,'MM-DD') BETWEEN '08-07' AND '09-05' THEN 12
                        ELSE 13
                    END,
                    COUNT(*)::numeric
                FROM ownership_contract
                WHERE state='cancel'
                GROUP BY 2

                UNION ALL

                -----------------------------------------------------------------
                -- KPI 8 Ready for Handover
                -----------------------------------------------------------------
                SELECT
                    'Customer ready for Handover',
                    CASE
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '09-11' AND '10-10' THEN 1
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '10-11' AND '11-09' THEN 2
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '11-10' AND '12-09' THEN 3
                        WHEN to_char(unit_status_id_date,'MM-DD') >= '12-10'
                        OR to_char(unit_status_id_date,'MM-DD') <= '01-08' THEN 4
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '01-09' AND '02-07' THEN 5
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '02-08' AND '03-09' THEN 6
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '03-10' AND '04-08' THEN 7
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '04-09' AND '05-08' THEN 8
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '05-09' AND '06-07' THEN 9
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '06-08' AND '07-07' THEN 10
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '07-08' AND '08-06' THEN 11
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '08-07' AND '09-05' THEN 12
                        ELSE 13
                    END,
                    COUNT(*)::numeric
                FROM re_unit_status
                WHERE unit_status_id = 0
                GROUP BY 2

                UNION ALL

                -----------------------------------------------------------------
                -- KPI 9 Handovered
                -----------------------------------------------------------------
                SELECT
                    'Customer Handovered',
                    CASE
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '09-11' AND '10-10' THEN 1
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '10-11' AND '11-09' THEN 2
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '11-10' AND '12-09' THEN 3
                        WHEN to_char(unit_status_id_date,'MM-DD') >= '12-10'
                        OR to_char(unit_status_id_date,'MM-DD') <= '01-08' THEN 4
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '01-09' AND '02-07' THEN 5
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '02-08' AND '03-09' THEN 6
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '03-10' AND '04-08' THEN 7
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '04-09' AND '05-08' THEN 8
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '05-09' AND '06-07' THEN 9
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '06-08' AND '07-07' THEN 10
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '07-08' AND '08-06' THEN 11
                        WHEN to_char(unit_status_id_date,'MM-DD') BETWEEN '08-07' AND '09-05' THEN 12
                        ELSE 13
                    END,
                    COUNT(*)::numeric
                FROM re_unit_status
                WHERE unit_status_id = 1
                GROUP BY 2

            ) v
            ON v.kpi_name = b.kpi_name
            AND v.month_order = b.month_order

        )
        """)

# class DashboardReport(models.Model):
#     _name = 'dashboard.report'
#     _description = 'Dashboard Report'
#     _auto = False
#     _rec_name = 'kpi_name'

#     kpi_name = fields.Char(string='KPI')
#     month = fields.Char(string='Month')
#     value = fields.Float(string='Value')
#     def init(self):
#         tools.drop_view_if_exists(self.env.cr, self._table)
#         self.env.cr.execute("""
#             CREATE OR REPLACE VIEW dashboard_report AS (

#                 /* Customers Requested to Pay */
#                 SELECT
#                     100000 + EXTRACT(MONTH FROM date)::integer AS id,
#                     'Customers Requested to Pay' AS kpi_name,
#                     TO_CHAR(date,'Mon') AS month,
#                     COUNT(*)::numeric AS value
#                 FROM loan_line_rs_own
#                 WHERE payment_request_letter = 'yes'
#                 GROUP BY EXTRACT(MONTH FROM date), TO_CHAR(date,'Mon')

#                 UNION ALL

#                 /* Customers Paid (count) */
#                 SELECT
#                     200000 + EXTRACT(MONTH FROM date)::integer AS id,
#                     'Customers Paid (count)' AS kpi_name,
#                     TO_CHAR(date,'Mon') AS month,
#                     COUNT(*)::numeric AS value
#                 FROM loan_line_rs_own
#                 WHERE payment_state = 'paid'
#                 GROUP BY EXTRACT(MONTH FROM date), TO_CHAR(date,'Mon')

#                 UNION ALL

#                 /* Customers Paid (%) */
#                 SELECT
#                     300000 + EXTRACT(MONTH FROM date)::integer AS id,
#                     'Customers Paid (%)' AS kpi_name,
#                     TO_CHAR(date,'Mon') AS month,
#                     CASE
#                         WHEN COUNT(*) FILTER (
#                             WHERE payment_request_letter='yes'
#                         ) = 0 THEN 0
#                         ELSE
#                             (
#                                 COUNT(*) FILTER (
#                                     WHERE payment_state='paid'
#                                 )::numeric
#                                 /
#                                 COUNT(*) FILTER (
#                                     WHERE payment_request_letter='yes'
#                                 )
#                             ) * 100
#                     END AS value
#                 FROM loan_line_rs_own
#                 GROUP BY EXTRACT(MONTH FROM date), TO_CHAR(date,'Mon')

#                 UNION ALL

#                 /* Total Requested Amount */
#                 SELECT
#                     400000 + EXTRACT(MONTH FROM date)::integer AS id,
#                     'Total Requested Amount' AS kpi_name,
#                     TO_CHAR(date,'Mon') AS month,
#                     COALESCE(SUM(amount),0) AS value
#                 FROM loan_line_rs_own
#                 WHERE payment_request_letter='yes'
#                 GROUP BY EXTRACT(MONTH FROM date), TO_CHAR(date,'Mon')

#                 UNION ALL

#                 /* Total Collected Amount */
#                 SELECT
#                     500000 + EXTRACT(MONTH FROM date)::integer AS id,
#                     'Total Collected Amount' AS kpi_name,
#                     TO_CHAR(date,'Mon') AS month,
#                     COALESCE(SUM(amount),0) AS value
#                 FROM loan_line_rs_own
#                 WHERE payment_request_letter='yes'
#                 AND payment_state='paid'
#                 GROUP BY EXTRACT(MONTH FROM date), TO_CHAR(date,'Mon')

#                 UNION ALL

#                 /* Remaining Amount */
#                 SELECT
#                     600000 + EXTRACT(MONTH FROM date)::integer AS id,
#                     'Remaining Amount to be Collected' AS kpi_name,
#                     TO_CHAR(date,'Mon') AS month,
#                     COALESCE(
#                         SUM(amount) FILTER (
#                             WHERE payment_request_letter='yes'
#                         )
#                         -
#                         SUM(amount) FILTER (
#                             WHERE payment_request_letter='yes'
#                             AND payment_state='paid'
#                         ),
#                     0) AS value
#                 FROM loan_line_rs_own
#                 GROUP BY EXTRACT(MONTH FROM date), TO_CHAR(date,'Mon')

#                 UNION ALL

#                 /* Cancelled Contracts */
#                 SELECT
#                     700000 + EXTRACT(MONTH FROM date)::integer AS id,
#                     'Cancelled Contracts' AS kpi_name,
#                     TO_CHAR(date,'Mon') AS month,
#                     COUNT(*)::numeric AS value
#                 FROM ownership_contract
#                 WHERE state='cancel'
#                 GROUP BY EXTRACT(MONTH FROM date), TO_CHAR(date,'Mon')

#                 UNION ALL

#                 /* Customer Ready for Handover */
#                 SELECT
#                     800000 + EXTRACT(MONTH FROM unit_status_id_date)::integer AS id,
#                     'Customer ready for Handover' AS kpi_name,
#                     TO_CHAR(unit_status_id_date,'Mon') AS month,
#                     COUNT(*)::numeric AS value
#                 FROM re_unit_status
#                 WHERE unit_status_id = 0
#                 GROUP BY
#                     EXTRACT(MONTH FROM unit_status_id_date),
#                     TO_CHAR(unit_status_id_date,'Mon')

#                 UNION ALL

#                 /* Customer Handovered */
#                 SELECT
#                     900000 + EXTRACT(MONTH FROM unit_status_id_date)::integer AS id,
#                     'Customer Handovered' AS kpi_name,
#                     TO_CHAR(unit_status_id_date,'Mon') AS month,
#                     COUNT(*)::numeric AS value
#                 FROM re_unit_status
#                 WHERE unit_status_id = 1
#                 GROUP BY
#                     EXTRACT(MONTH FROM unit_status_id_date),
#                     TO_CHAR(unit_status_id_date,'Mon')

#             )
#         """)