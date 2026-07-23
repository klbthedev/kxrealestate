/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class Dashboard extends Component {
    
    static components = {   Many2XAutocomplete,  };
    
    setup() 
    {   this.orm = useService("orm");
        this.installmentChartRef = useRef("installmentChart");
        this.collectionChartRef = useRef("collectionChart");
        this.action = useService("action"); // for card click

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

            region: "",
            region_id: false,
            city: "",
            city_id: false,
            site: "",
            site_id: false,
            building: "",
            building_id: false,
            floor: "",
            floor_id: false,

            region2: "",
            region_id2: false,
            city2: "",
            city_id2: false,
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

        onMounted(
            () => { 
                this.renderInstallmentChart(); 
        });
    }
    

    /******************************************************************************/
    /* Methods for Card click event  */
    /******************************************************************************/

    async openAvailableProperties() {   
        
        const domain = [ ["is_property", "=", true], ["state", "=", "free"], ];

        if (this.state.region_id)      {  domain.push(["site_id.region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)        {  domain.push(["site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)        {  domain.push(["site_id", "=", this.state.site_id]);  }
        if (this.state.building_id)    {  domain.push(["building_id", "=", this.state.building_id]);  }
        if (this.state.floor_id)       {  domain.push(["floor_id", "=",  this.state.floor_id]);   }

        // if (this.state.date_from) {  domain.push(["date", ">=", this.state.date_from]); }
        // if (this.state.date_to) {   domain.push(["date", "<=", this.state.date_to]);    }

        // console.log(JSON.stringify(domain, null, 4));

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.template",
            views: [  [false, "list"], [false, "form"], ],
            domain: domain,
        });
    }

    async openSoldProperties() {   
        
        const domain = [ ["is_property", "=", true], ["state", "=", "sold"], ];

        if (this.state.region_id)      {  domain.push(["site_id.region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)        {  domain.push(["site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)        {  domain.push(["site_id", "=", this.state.site_id]);  }
        if (this.state.building_id)    {  domain.push(["building_id", "=", this.state.building_id]);  }
        if (this.state.floor_id)       {  domain.push(["floor_id", "=",  this.state.floor_id]);   }

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.template",
            views: [  [false, "list"], [false, "form"], ],
            domain: domain,
        }); 
    }

    async openReservedProperties() {   
        
        const domain = [ ["is_property", "=", true], ["state", "=", "reserved"], ];

        if (this.state.region_id)      {  domain.push(["site_id.region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)        {  domain.push(["site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)        {  domain.push(["site_id", "=", this.state.site_id]);  }
        if (this.state.building_id)    {  domain.push(["building_id", "=", this.state.building_id]);  }
        if (this.state.floor_id)       {  domain.push(["floor_id", "=",  this.state.floor_id]);   }

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.template",
            views: [  [false, "list"], [false, "form"], ],
            domain: domain,
        });
    }

    async openCanelledContracts() {   
        
        const domain = [ ["state", "=", "cancel"], ];

        // if (this.state.region_id)      {  domain.push(["site_id.region_id", "=", this.state.region_id]);  }
        // if (this.state.city_id)        {  domain.push(["site_id.city_id", "=", this.state.city_id]);  }
        // if (this.state.site_id)        {  domain.push(["site_id", "=", this.state.site_id]);  }
        // if (this.state.building_id)    {  domain.push(["building_id", "=", this.state.building_id]);  }
        // if (this.state.floor_id)       {  domain.push(["floor_id", "=",  this.state.floor_id]);   }

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ownership.contract",
            views: [  [false, "list"], [false, "form"], ],
            domain: domain,
        });
    }

    async openHandoverReadyProperties() {   
        
        const domain = [ ["done", "=", false], ];
        
        if (this.state.region_id)      {  domain.push(["ownership_contract_id.site_id.site_region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)        {  domain.push(["ownership_contract_id.site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)        {  domain.push(["ownership_contract_id.site_id.id", "=", this.state.site_id]);  }
        if (this.state.building_id)    {  domain.push(["ownership_contract_id.building_id", "=", this.state.building_id]);  }
        if (this.state.floor_id)       {  domain.push(["ownership_contract_id.floor_id", "=",  this.state.floor_id]);   }
        
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Properties Ready for Handover",
            res_model: "ownership.handover.checklist",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            domain: domain,
        });
    }

    async openHandoveredPropertyUnits() {   
        
        const domain = [ ["done", "=", true], ];
        
        if (this.state.region_id)      {  domain.push(["ownership_contract_id.site_id.site_region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)        {  domain.push(["ownership_contract_id.site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)        {  domain.push(["ownership_contract_id.site_id.id", "=", this.state.site_id]);  }
        if (this.state.building_id)    {  domain.push(["ownership_contract_id.building_id", "=", this.state.building_id]);  }
        if (this.state.floor_id)       {  domain.push(["ownership_contract_id.floor_id", "=",  this.state.floor_id]);   }
        
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Handovered Property Units",
            res_model: "ownership.handover.checklist",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            domain: domain,
        });
    }

    async openTotalCollectedAmount() {   
        
        const domain = [ ["paid", ">", "0"], ];

        if (this.state.region_id)      {  domain.push(["site_id.region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)        {  domain.push(["site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)        {  domain.push(["site_id", "=", this.state.site_id]);  }
        if (this.state.building_id)    {  domain.push(["building_id", "=", this.state.building_id]);  }
        if (this.state.floor_id)       {  domain.push(["floor_id", "=",  this.state.floor_id]);   }

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ownership.contract",
            views: [  [false, "list"], [false, "form"], ],
            domain: domain,
        });
    }

    async openTotalRemainingAmount() {

        const domain = [ ["balance", ">", "0"], ];

        if (this.state.region_id)      {  domain.push(["site_id.region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)        {  domain.push(["site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)        {  domain.push(["site_id", "=", this.state.site_id]);  }
        if (this.state.building_id)    {  domain.push(["building_id", "=", this.state.building_id]);  }
        if (this.state.floor_id)       {  domain.push(["floor_id", "=",  this.state.floor_id]);   }

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ownership.contract",
            views: [  [false, "list"], [false, "form"], ],
            domain: domain,
        });
    }


    /******************************************************************************/
    /* Filter 1 Setup   */
    /******************************************************************************/
    
    getContext() {  
        return {}; 
    }
    
    getRegionDomain() {  
        return []; 
    }

    getCityDomain() {
        const domain = [];
        if (this.state.region_id)   {   domain.push(["region_id", "=", this.state.region_id]); }
        return domain;
    }

    getSiteDomain() {
        const domain = [];
        if (this.state.region_id)   {   domain.push(["city_id.region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)     {   domain.push(["city_id", "=", this.state.city_id]);  }
        return domain;
    }

    getBuildingDomain() {
        const domain = [];
        if (this.state.region_id)   {   domain.push(["site_id.city_id.region_id", "=", this.state.region_id]);  }
        if (this.state.city_id)     {   domain.push(["site_id.city_id", "=", this.state.city_id]);  }
        if (this.state.site_id)     {   domain.push(["site_id", "=", this.state.site_id]);  }
        return domain;
    }

    getFloorDomain() {
        const domain = [];
        if (this.state.region_id)   {   domain.push(["building_id.site_id.city_id.region_id", "=", this.state.region_id,]); }
        if (this.state.city_id)     {   domain.push(["building_id.site_id.city_id", "=", this.state.city_id,]); }
        if (this.state.site_id)     {   domain.push(["building_id.site_id", "=", this.state.site_id,]); }
        if (this.state.building_id) {   domain.push(["building_id", "=", this.state.building_id,]); }
        return domain;
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

    async onRegionSelected(records) {
        if (!records || !records.length) {
            this.state.region = "";
            this.state.region_id = false;
            return;
        }
        const region = records[0];
        this.state.region_id = region.id;
        this.state.region = await this.resolveDisplayName("site.region", region);
        this.state.city = "";
        this.state.city_id = false;
        this.state.site = "";
        this.state.site_id = false;
        this.state.building = "";
        this.state.building_id = false;
        this.state.floor = "";
        this.state.floor_id = false;
    }
    
    async onCitySelected(records) {
        if (!records || !records.length) {
            this.state.city = "";
            this.state.city_id = false;
            return;
        }
        const city = records[0];
        this.state.city_id = city.id;
        this.state.city = await this.resolveDisplayName("site.city", city);
        this.state.site = "";
        this.state.site_id = false;
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
    
    // for filer 1
    activeActions = { create: false, createEdit: false, write: false, };
    

    /******************************************************************************/
    /* Filter 2 Setup   */
    /******************************************************************************/
    
    getContext2() {  
        return {}; 
    }
    
    getRegionDomain2() {  
        return []; 
    }

    getCityDomain2() {
        const domain = [];
        if (this.state.region_id2)   {   domain.push(["region_id", "=", this.state.region_id2]); }
        return domain;
    }

    getSiteDomain2() {
        const domain = [];
        if (this.state.region_id2)   {   domain.push(["city_id.region_id", "=", this.state.region_id2]);  }
        if (this.state.city_id2)     {   domain.push(["city_id", "=", this.state.city_id2]);  }
        return domain;
    }

    getBuildingDomain2() {
        const domain = [];
        if (this.state.region_id2)   {   domain.push(["site_id.city_id.region_id", "=", this.state.region_id2]);  }
        if (this.state.city_id2)     {   domain.push(["site_id.city_id", "=", this.state.city_id2]);  }
        if (this.state.site_id2)     {   domain.push(["site_id", "=", this.state.site_id2]);  }
        return domain;
    }

    getFloorDomain2() {
        const domain = [];
        if (this.state.region_id2)   {   domain.push(["building_id.site_id.city_id.region_id", "=", this.state.region_id2,]); }
        if (this.state.city_id2)     {   domain.push(["building_id.site_id.city_id", "=", this.state.city_id2,]); }
        if (this.state.site_id2)     {   domain.push(["building_id.site_id", "=", this.state.site_id2,]); }
        if (this.state.building_id2) {   domain.push(["building_id", "=", this.state.building_id2,]); }
        return domain;
    }

    async getDisplayName2(model, id) { // for Search More option of drop-down list
        const result = await this.orm.call( model, "name_get", [[id]]  );
        return result.length ? result[0][1] : "";
    }

    async resolveDisplayName2(model, record) {
        if (record.display_name) { return record.display_name; }
        const result = await this.orm.call( model, "read", [[record.id], ["display_name"]] );
        return result.length ? result[0].display_name : "";
    }

    async onRegionSelected2(records) {
        if (!records || !records.length) {
            this.state.region2 = "";
            this.state.region_id2 = false;
            return;
        }
        const region = records[0];
        this.state.region_id2 = region.id;
        this.state.region2 = await this.resolveDisplayName("site.region", region);
        this.state.city2 = "";
        this.state.city_id2 = false;
        this.state.site2 = "";
        this.state.site_id2 = false;
        this.state.building2 = "";
        this.state.building_id2 = false;
        this.state.floor2 = "";
        this.state.floor_id2 = false;
    }
    
    async onCitySelected2(records) {
        if (!records || !records.length) {
            this.state.city2 = "";
            this.state.city_id2 = false;
            return;
        }
        const city = records[0];
        this.state.city_id2 = city.id;
        this.state.city2 = await this.resolveDisplayName("site.city", city);
        this.state.site2 = "";
        this.state.site_id2 = false;
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
    
    
    /******************************************************************************/
    /* Function to format numerical values   */
    /******************************************************************************/

    formatAmount(value) {
        return (value || 0).toLocaleString( undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2, });
    }

    
    /******************************************************************************/
    /* Export dashboard to excel file */
    /******************************************************************************/
    
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

    /******************************************************************************/
    /* Connect Filter 1 frontend to backend */
    /******************************************************************************/
    
    async loadDashboard() {
        const result = await this.orm.call( 
            "kx.dashboard.service", 
            "get_dashboard_data", 
            [ this.state.region, this.state.city, this.state.site, this.state.building, this.state.floor,]
        );
        Object.assign(this.state, result);
    }

    /******************************************************************************/
    /* Connect Filter 2 frontend to backend */
    /******************************************************************************/
    
    async loadDashboard2() {
        const result = await this.orm.call( 
            "kx.dashboard.service", 
            "get_dashboard_data2", 
            [ this.state.date_from, this.state.date_to, this.state.region2, this.state.city2, 
                this.state.site2, this.state.building2, this.state.floor2,]
        );
        Object.assign(this.state, result);
    }
    
    /* Apply Filter 1 ***************************************************************/
    async applyFilter() {
        await this.loadDashboard();
        this.renderInstallmentChart();
    }

    /* Apply Filter 2 ***************************************************************/
    async applyFilter2() {
        await this.loadDashboard2();
        //this.renderInstallmentChart();
    }


    /******************************************************************************/
    /* Create Chart */
    /******************************************************************************/

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