/** @odoo-module **/
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

            site: "",
            site_id: false,
            building: "",
            building_id: false,
            floor: "",
            floor_id: false,

            site2: "",
            site_id2: false,
            building2: "",
            building_id2: false,
            floor2: "",
            floor_id2: false,
        });
        onWillStart(
            async () => { 
                await this.loadDashboard(); 
                await this.loadDashboard2(); 
        });
        onMounted(() => { this.renderInstallmentChart(); });
    }
    
    // filter 1 setup ////////////////////////////////////////////////////////////////////////////////////
    getContext() {  return {}; }    
    getSiteDomain() {  return []; }    
    
    // domains for building and floor
    getBuildingDomain() {
        if (!this.state.site) { return [];  }
        return [ ["site_id", "=", this.state.site.id]  ];
    }    
    getBuildingDomain() {
        if (!this.state.site_id) { return []; }
        return [  ["site_id", "=", this.state.site_id] ];
    }    
    getFloorDomain() {
        if (!this.state.building) { return []; }
        return [ ["building_id", "=", this.state.building.id] ];
    }
    getFloorDomain() {
        if (!this.state.building_id) { return []; }
        return [ ["building_id", "=", this.state.building_id] ];
    }

    // get display name for selection from Search More option
    async getDisplayName(model, id) {
        const result = await this.orm.call( model, "name_get", [[id]]  );
        return result.length ? result[0][1] : "";
    }

    async resolveDisplayName(model, record) {
        if (record.display_name) { return record.display_name; }
        const result = await this.orm.call( model, "read", [[record.id], ["display_name"]] );
        return result.length ? result[0].display_name : "";
    }

    onSiteSelected(site) {
        this.state.site = site.display_name || site.name || "";
        this.state.site_id = site.id;
        this.state.building = "";
        this.state.building_id = false;
        this.state.floor = "";
        this.state.floor_id = false;
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
        this.state.building = "";
        this.state.building_id = false;
        this.state.floor = "";
        this.state.floor_id = false;
    }

    onBuildingSelected(building) {
        this.state.building = building;
        this.state.floor = null;
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
        this.state.floor = "";
        this.state.floor_id = false;
        console.log(building);
    }

    onFloorSelected(floor) {
        this.state.floor = floor;
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
        console.log(floor);
    }
    
    // for filer 1
    activeActions = { create: false, createEdit: false, write: false, };
    
    // filter 2 setup ////////////////////////////////////////////////////////////////////////////////////
    getContext2() {  return {}; }    
    getSiteDomain2() {  return []; }    
    
    // domains for building and floor
    getBuildingDomain2() {
        if (!this.state.site2) { return [];  }
        return [ ["site_id2", "=", this.state.site.id2]  ];
    }    
    getBuildingDomain2() {
        if (!this.state.site_id2) { return []; }
        return [  ["site_id2", "=", this.state.site_id2] ];
    }    
    getFloorDomain2() {
        if (!this.state.building2) { return []; }
        return [ ["building_id2", "=", this.state.building.id2] ];
    }
    getFloorDomain2() {
        if (!this.state.building_id2) { return []; }
        return [ ["building_id2", "=", this.state.building_id2] ];
    }

    // get display name for selection from Search More option
    async getDisplayName2(model, id) {
        const result = await this.orm.call( model, "name_get", [[id]]  );
        return result.length ? result[0][1] : "";
    }

    async resolveDisplayName2(model, record) {
        if (record.display_name) { return record.display_name; }
        const result = await this.orm.call( model, "read", [[record.id], ["display_name"]] );
        return result.length ? result[0].display_name : "";
    }

    onSiteSelected2(site2) {
        this.state.site2 = site2.display_name || site2.name || "";
        this.state.site_id2 = site2.id;
        this.state.building2 = "";
        this.state.building_id2 = false;
        this.state.floor2 = "";
        this.state.floor_id2 = false;
    }    
    async onSiteSelected2(records) {
        if (!records || !records.length) {
            this.state.site2 = "";
            this.state.site_id2 = false;
            return;
        }
        const site = records[0];
        this.state.site_id2 = site.id;
        this.state.site2 = await this.resolveDisplayName("re.site", site);
        this.state.building2 = "";
        this.state.building_id2 = false;
        this.state.floor2 = "";
        this.state.floor_id2 = false;
    }

    onBuildingSelected2(building) {
        this.state.building2 = building;
        this.state.floor2 = null;
    }
    async onBuildingSelected2(records) {
        if (!records || !records.length) {
            this.state.building2 = "";
            this.state.building_id2 = false;
            return;
        }
        const building = records[0];
        this.state.building_id2 = building.id;
        this.state.building2 = await this.resolveDisplayName("building.building", building);
        this.state.floor2 = "";
        this.state.floor_id2 = false;
    }

    onFloorSelected2(floor) {
        this.state.floor2 = floor;
    }    
    async onFloorSelected2(records) {
        if (!records || !records.length) {
            this.state.floor2 = "";
            this.state.floor_id2 = false;
            return;
        }
        const floor = records[0];
        this.state.floor_id2 = floor.id;
        this.state.floor2 = await this.resolveDisplayName("re.floor", floor);
    }
    
    // for filer 2
    activeActions2 = { create: false, createEdit: false, write: false, };

    //////////////////////////////////////////////////////////////////////////////////////////////////////

    // format number values  ////////////////////////////////////////////////////////////
    formatAmount(value) {
        return (value || 0).toLocaleString( undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2, });
    }

    // export to excel //////////////////////////////////////////////////////////////////
    async exportExcel() {
        const params = new URLSearchParams({
            date_from: this.state.date_from || "",
            date_to: this.state.date_to || "",
            site2: this.state.site2 || "",
            building2: this.state.building2 || "",
            floor2: this.state.floor2 || "",
        });

        window.open(`/kx_realestate/dashboard/export_excel?${params.toString()}`,"_blank");
    }

    // connect frontend to backend /////////////////////////////////////////////////////
    async loadDashboard() {
        const result = await this.orm.call( 
            "kx.dashboard.service", 
            "get_dashboard_data", 
            [ this.state.site, this.state.building, this.state.floor,]
        );
        Object.assign(this.state, result);
    }

    // connect frontend to backend for filter 2 /////////////////////////////////////////
    async loadDashboard2() {
        const result = await this.orm.call( 
            "kx.dashboard.service", 
            "get_dashboard_data2", 
            [ this.state.date_from, this.state.date_to, this.state.site2, this.state.building2, this.state.floor2,]
        );
        Object.assign(this.state, result);
    }
    
    // apply filter ////////////////////////////////////////////////////////////////////
    async applyFilter() {
        await this.loadDashboard();
        this.renderInstallmentChart();
    }

    // apply filter 2 //////////////////////////////////////////////////////////////////
    async applyFilter2() {
        await this.loadDashboard2();
        this.renderInstallmentChart();
    }

    // create charts ////////////////////////////////////////////////////////////////////
    renderInstallmentChart() {
        const installmentCanvas = this.installmentChartRef.el;
        const collectionCanvas = this.collectionChartRef.el;

        if (this.installmentChart)  { this.installmentChart.destroy();  }
        if (this.collectionChart)   { this.collectionChart.destroy();   }
        
        if (!installmentCanvas)     { return; }
        if (!collectionCanvas)      { return; }
        
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
                datasets: [ 
                    {   label: "Remaining Amount", 
                        data: remaining, 
                        backgroundColor: "#7A4E59",
                        borderColor: "#68414C",
                        borderWidth: 1,
                    }, 
                    {   label: "Collected Amount", 
                        data: paid,
                        backgroundColor: "#E6D8DC",
                        borderColor: "#68414C",
                        borderWidth: 1,
                    } 
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, }
        });

        // for collectionChart
        this.collectionChart = new Chart(collectionCanvas, { type: "bar",
            data: {
                labels: collectionLabel,
                datasets: [ 
                    {   label: "Collectable Amount", 
                        data: collectable, 
                        backgroundColor: "#7A4E59",
                        borderColor: "#68414C",
                        borderWidth: 1,
                    }, 
                    {   label: "Overdue Amount", 
                        data: overdue, 
                        backgroundColor: "#E6D8DC",
                        borderColor: "#68414C",
                        borderWidth: 1,
                    } ]
            },
            options: { responsive: true, maintainAspectRatio: false, }
        });
    }

}

Dashboard.template = "kx_realestate.Dashboard";
registry.category("actions").add( "kx_dashboard", Dashboard );