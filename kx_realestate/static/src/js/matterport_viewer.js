/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class MatterportViewer extends Component {
    static template = "kx_realestate.MatterportViewer";

    setup() {
        this.url = this.props.action.params.url;
        this.name = this.props.action.params.name;
    }
}

registry.category("actions").add("matterport_viewer", MatterportViewer);