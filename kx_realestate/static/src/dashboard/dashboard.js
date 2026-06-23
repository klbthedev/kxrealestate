/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


export class Dashboard extends Component {

    setup() {

        this.orm = useService("orm");

        this.state = useState({

            date_from: null,
            date_to: null,

            requested_payment_count: 0,
            construction_count: 0,
            date_count: 0,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {

        const result = await this.orm.call(
            "kx.dashboard.service",
            "get_dashboard_data",
            [
                this.state.date_from,
                this.state.date_to,
            ]
        );

        Object.assign(this.state, result);
    }

    async applyFilter() {
        await this.loadDashboard();
    }
}

Dashboard.template = "kx_realestate.Dashboard";

registry.category("actions").add(
    "kx_dashboard",
    Dashboard
);