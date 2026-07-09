/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * ContractLivePreview
 * --------------------
 * Standalone view widget (used as <widget name="contract_live_preview"/> in
 * the contract.contract form view) that renders a live, auto-updating
 * preview of the generated contract HTML. It calls the
 * `/contract_management/live_preview` RPC endpoint (backed by the
 * `contract.contract.get_live_preview_html` server method) every time the
 * user changes a variable value, without requiring a full page/form reload.
 */
export class ContractLivePreview extends Component {
    static template = "contract_management.ContractLivePreview";
    static props = { ...Component.props };

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            html: "",
            loading: false,
            error: "",
        });
        this._debounceTimer = null;

        onWillStart(() => this._refreshPreview());
        onWillUpdateProps(() => this._debouncedRefresh());
    }

    get recordId() {
        return this.props.record && this.props.record.resId;
    }

    get currentValues() {
        // Build {variable_code: raw_value} from the current (possibly
        // unsaved) variable_value_ids one2many editable rows.
        const values = {};
        const record = this.props.record;
        if (!record) {
            return values;
        }
        const lines = record.data.variable_value_ids &&
            record.data.variable_value_ids.records;
        if (!lines) {
            return values;
        }
        for (const line of lines) {
            const data = line.data;
            const variable = data.variable_id;
            if (!variable) {
                continue;
            }
            const code = Array.isArray(variable) ? null : variable.display_name;
            const dataType = data.data_type;
            let raw = null;
            switch (dataType) {
                case "integer":
                    raw = data.value_integer;
                    break;
                case "float":
                    raw = data.value_float;
                    break;
                case "date":
                    raw = data.value_date;
                    break;
                case "datetime":
                    raw = data.value_datetime;
                    break;
                case "boolean":
                    raw = data.value_boolean;
                    break;
                case "partner":
                case "company":
                case "employee":
                case "user":
                case "many2one":
                    raw = data.value_many2one_id;
                    break;
                default:
                    raw = data.value_char;
            }
            if (code) {
                values[code] = raw;
            }
        }
        return values;
    }

    _debouncedRefresh() {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => this._refreshPreview(), 400);
    }

    async _refreshPreview() {
        if (!this.recordId) {
            this.state.html = "<p class='text-muted'>Save the contract to enable the live preview.</p>";
            return;
        }
        this.state.loading = true;
        this.state.error = "";
        try {
            const result = await this.rpc("/contract_management/live_preview", {
                contract_id: this.recordId,
                values: this.currentValues,
            });
            if (result && result.error) {
                this.state.error = result.error;
            } else {
                this.state.html = (result && result.html) || "";
            }
        } catch (err) {
            this.state.error = err.message || String(err);
        } finally {
            this.state.loading = false;
        }
    }

    onRefreshClick() {
        this._refreshPreview();
    }
}

registry.category("view_widgets").add("contract_live_preview", {
    component: ContractLivePreview,
});
