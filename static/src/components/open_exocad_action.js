/** @odoo-module **/
import { registry } from "@web/core/registry";

function openExocadAction(env, action) {
    const url = action.params && action.params.url;
    if (!url) {
        return;
    }
    // Hand the custom-protocol link to the browser; the form stays open.
    const link = document.createElement("a");
    link.href = url;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    link.remove();
}

registry.category("actions").add("dental_lab.open_exocad", openExocadAction);