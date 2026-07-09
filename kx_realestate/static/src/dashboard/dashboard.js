import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class Dashboard extends Component {
    static components = {
        Many2XAutocomplete,
    };

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

            // Filter 1 State Attributes
            country: "",
            country_id: false,
            state_record: "",
            state_id: false,
            site: "",
            site_id: false,
            building: "",
            building_id: false,
            floor: "",
            floor_id: false,

            // Filter 2 State Attributes
            site2: "",
            site_id2: false,
            building2: "",
            building_id2: false,
            floor2: "",
            floor_id2: false,
        });

        onWillStart(async () => { 
            await this.loadDashboard(); 
            await this.loadDashboard2(); 
        });

        onMounted(() => { this.renderInstallmentChart(); });
    }
    
    // Filter 1 Setup Engine /////////////////////////////////////////////////////////////////////////////
    getContext() { return {}; }    
    getCountryDomain() { return []; }

    getStateDomain() {
        if (!this.state.country_id) { return []; }
        return [["country_id", "=", this.state.country_id]];
    }

    getSiteDomain() {  
        let domain = [];
        if (this.state.country_id) { domain.push(["country_id", "=", this.state.country_id]); }
        if (this.state.state_id) { domain.push(["state_id", "=", this.state.state_id]); }
        return domain; 
    }    
    
    getBuildingDomain() {
        if (!this.state.site_id) { return []; }
        return [["site_id", "=", this.state.site_id]];
    }    

    getFloorDomain() {
        if (!this.state.building_id) { return []; }
        return [["building_id", "=", this.state.building_id]];
    }

    // Record Name Resolution Helpers ////////////////////////////////////////////////////////////////////
    async resolveDisplayName(model, record) {
        if (record.display_name) { return record.display_name; }
        const result = await this.orm.call(model, "read", [[record.id], ["display_name"]]);
        return result.length ? result[0].display_name : "";
    }

    // Auto-complete Events Handlers (Filter Set 1) /////////////////////////////////////////////////////
    async onCountrySelected(records) {
        if (!records || !records.length) {
            this.state.country = "";
            this.state.country_id = false;
        } else {
            const country = records[0];
            this.state.country_id = country.id;
            this.state.country = await this.resolveDisplayName("res.country", country);
        }
        // Cascading Clearances
        this.state.state_record = ""; this.state.state_id = false;
        this.state.site = ""; this.state.site_id = false;
        this.state.building = ""; this.state.building_id = false;
        this.state.floor = ""; this.state.floor_id = false;
    }

    async onStateSelected(records) {
        if (!records || !records.length) {
            this.state.state_record = "";
            this.state.state_id = false;
        } else {
            const stateRec = records[0];
            this.state.state_id = stateRec.id;
            this.state.state_record = await this.resolveDisplayName("res.country_state", stateRec);
        }
        this.state.site = ""; this.state.site_id = false;
        this.state.building = ""; this.state.building_id = false;
        this.state.floor = ""; this.state.floor_id = false;
    }

    async onSiteSelected(records) {
        if (!records || !records.length) {
            this.state.site = "";
            this.state.site_id = false;
            return;
        }
        const site = records[0];
        this.state.site_id = site.id;
        this.state.site = await this.resolveDisplayName("re.site", site);
        this.state.building = ""; this.state.building_id = false;
        this.state.floor = ""; this.state.floor_id = false;
    }

    async onBuildingSelected(records) {
        if (!records || !records.length) {
            this.state.building = "";
            this.state.building_id = false;
            return;
        }
        const building = records[0];
        this.state.building_id = building.id;
        this.state.building = await this.resolveDisplayName("building.building", building);
        this.state.floor = ""; this.state.floor_id = false;
    }

    async onFloorSelected(records) {
        if (!records || !records.length) {
            this.state.floor = "";
            this.state.floor_id = false;
            return;
        }
        const floor = records[0];
        this.state.floor_id = floor.id;
        this.state.floor = await this.resolveDisplayName("re.floor", floor);
    }
    
    activeActions = { create: false, createEdit: false, write: false };
    
    // Filter 2 Setup (Preserved Intact) /////////////////////////////////////////////////////////////////
    getContext2() { return {}; }    
    getSiteDomain2() { return []; }    
    
    getBuildingDomain2() {
        if (!this.state.site_id2) { return []; }
        return [["site_id", "=", this.state.site_id2]];
    }    
    getFloorDomain2() {
        if (!this.state.building_id2) { return []; }
        return [["building_id", "=", this.state.building_id2]];
    }

    async onSiteSelected2(records) {
        if (!records || !records.length) {
            this.state.site2 = ""; this.state.site_id2 = false;
            return;
        }
        const site = records[0];
        this.state.site_id2 = site.id;
        this.state.site2 = await this.resolveDisplayName("re.site", site);
        this.state.building2 = ""; this.state.building_id2 = false;
        this.state.floor2 = ""; this.state.floor_id2 = false;
    }

    async onBuildingSelected2(records) {
        if (!records || !records.length) {
            this.state.building2 = ""; this.state.building_id2 = false;
            return;
        }
        const building = records[0];
        this.state.building_id2 = building.id;
        this.state.building2 = await this.resolveDisplayName("building.building", building);
        this.state.floor2 = ""; this.state.floor_id2 = false;
    }

    async onFloorSelected2(records) {
        if (!records || !records.length) {
            this.state.floor2 = ""; this.state.floor_id2 = false;
            return;
        }
        const floor = records[0];
        this.state.floor_id2 = floor.id;
        this.state.floor2 = await this.resolveDisplayName("re.floor", floor);
    }
    
    activeActions2 = { create: false, createEdit: false, write: false };

    formatAmount(value) {
        return (value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    async exportExcel() {
        const params = new URLSearchParams({
            date_from: this.state.date_from || "",
            date_to: this.state.date_to || "",
            country: this.state.country2 || "",
            state: this.state.state2 || "",
            city: this.state.city2 || "",

            site: this.state.site2 || "",
            building: this.state.building2 || "",
            floor: this.state.floor2 || "",
        });
        window.open(`/kx_realestate/dashboard/export_excel?${params.toString()}`, "_blank");
    }

    // Connect Front-end Context to Backend Server RPC Methods //////////////////////////////////////////
    async loadDashboard() {
        // Must align directly with: (country, state, city, site, building, floor)
        const result = await this.orm.call( 
            "kx.dashboard.service", 
            "get_dashboard_data", 
            [ 
                this.state.country_id, 
                this.state.state_id, 
                "", // City is a fallback empty string for now as it lacks an absolute model id
                this.state.site_id, 
                this.state.building_id, 
                this.state.floor_id
            ]
        );
        Object.assign(this.state, result);
    }

    async loadDashboard2() {
        const _getCleanId = (fieldValue) => {
            if (Array.isArray(fieldValue) && fieldValue.length > 0) {
                return fieldValue[0];
            }
            return fieldValue || false;
        };
        const params = {
            date_from: this.state.date_from || false,
            date_to: this.state.date_to || false,
            // country: _getCleanId(this.state.country_id2),
            // state: _getCleanId(this.state.state_id2),
            // city: Array.isArray(this.state.city2) ? this.state.city2[1] : (this.state.city2 || false),
            country: false, 
            state: false,
            city: false,
            site: _getCleanId(this.state.site_id2),
            building: _getCleanId(this.state.building_id2),
            floor: _getCleanId(this.state.floor_id2),
        };
        const result = await this.orm.call(
            "kx.dashboard.service",
            "get_dashboard_data2",
            [],
            params
        );
        Object.assign(this.state, result);
    }

    async applyFilter() {
        await this.loadDashboard();
        this.renderInstallmentChart();
    }

    async applyFilter2() {
        await this.loadDashboard2();
        this.renderInstallmentChart();
    }

    // Chart Render Logics (Preserved Intact) ///////////////////////////////////////////////////////////
    renderInstallmentChart() {
        const installmentCanvas = this.installmentChartRef.el;
        const collectionCanvas = this.collectionChartRef.el;

        if (this.installmentChart)  { this.installmentChart.destroy(); }
        if (this.collectionChart)   { this.collectionChart.destroy(); }
        
        if (!installmentCanvas || !collectionCanvas) { return; }
        
        const installmentLabel = this.state.installment_summary.map(row => row.installment_number);
        const remaining = this.state.installment_summary.map(row => Number(row.total_remaining_amount || 0));
        const paid = this.state.installment_summary.map(row => Number(row.total_paid_amount || 0));

        const collectionLabel = this.state.installment_tobe_collected.map(row => row.installment_number);
        const collectable = this.state.installment_tobe_collected.map(row => Number(row.total_to_be_collected_amount || 0));
        const overdue = this.state.installment_tobe_collected.map(row => Number(row.total_collectable_overdue_amount || 0));

        this.installmentChart = new Chart(installmentCanvas, { 
            type: "bar",
            data: {
                labels: installmentLabel,
                datasets: [ 
                    { label: "Remaining Amount", data: remaining, backgroundColor: "#7A4E59", borderColor: "#68414C", borderWidth: 1 }, 
                    { label: "Collected Amount", data: paid, backgroundColor: "#E6D8DC", borderColor: "#68414C", borderWidth: 1 } 
                ]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        this.collectionChart = new Chart(collectionCanvas, { 
            type: "bar",
            data: {
                labels: collectionLabel,
                datasets: [ 
                    { label: "Collectable Amount", data: collectable, backgroundColor: "#7A4E59", borderColor: "#68414C", borderWidth: 1 }, 
                    { label: "Overdue Amount", data: overdue, backgroundColor: "#E6D8DC", borderColor: "#68414C", borderWidth: 1 } 
                ]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
}

Dashboard.template = "kx_realestate.Dashboard";
registry.category("actions").add("kx_dashboard", Dashboard);