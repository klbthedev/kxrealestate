/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class Dashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.installmentChartRef = useRef("installmentChart");
        this.collectionChartRef = useRef("collectionChart");

        this.chart = null;
        this.installmentChart = null;
        this.collectionChart = null;
        
        this.state = useState({
            date_from: null,
            date_to: null,
            total_paid: 0,
            total_remaining: 0,
            total_overdue: 0,
            installment_summary: [],
            installment_tobe_collected: [],
        });
        onWillStart(async () => { await this.loadDashboard(); });
        onMounted(() => { this.renderInstallmentChart(); });
    }

    formatAmount(value) {
        return (value || 0).toLocaleString( undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2, });
    }

    async loadDashboard() {
        const result = await this.orm.call( "kx.dashboard.service", "get_dashboard_data", [ this.state.date_from, this.state.date_to, ]);
        Object.assign(this.state, result);
    }

    renderInstallmentChart() {
        const installmentCanvas = this.installmentChartRef.el;
        const collectionCanvas = this.collectionChartRef.el;

        if (this.installmentChart) { this.installmentChart.destroy(); }
        if (this.collectionChart) { this.collectionChart.destroy(); }
        
        if (!installmentCanvas) { return; }
        if (!collectionCanvas) { return; }
        
        // for installmentChart
        const installmentLabel = this.state.installment_summary.map( row => row.installment_number );
        const remaining = this.state.installment_summary.map( row => Number(row.total_remaining_amount || 0) );
        const paid = this.state.installment_summary.map( row => Number(row.total_paid_amount || 0) );

        // for collectionChart
        const collectionLabel = this.state.installment_tobe_collected.map( row => row.installment_number );
        const collectable = this.state.installment_tobe_collected.map( row => Number(row.total_to_be_collected_amount || 0) );
        const overdue = this.state.installment_tobe_collected.map( row => Number(row.total_collectable_overdue_amount || 0) );

        if (this.installmentChart) { this.installmentChart.destroy(); }

        // for installmentChart
        this.installmentChart = new Chart(installmentCanvas, { type: "bar",
            data: {
                labels: installmentLabel,
                datasets: [ { label: "Remaining Amount", data: remaining, }, { label: "Paid Amount", data: paid, } ]
            },
            options: { responsive: true, maintainAspectRatio: false, }
        });

        // for collectionChart
        this.collectionChart = new Chart(collectionCanvas, { type: "bar",
            data: {
                labels: collectionLabel,
                datasets: [ { label: "Collectable Amount", data: collectable, }, { label: "Overdue Amount", data: overdue, } ]
            },
            options: { responsive: true, maintainAspectRatio: false, }
        });
    }

    async applyFilter() {
        await this.loadDashboard();
        this.renderInstallmentChart();
    }
}

Dashboard.template = "kx_realestate.Dashboard";
registry.category("actions").add( "kx_dashboard", Dashboard );