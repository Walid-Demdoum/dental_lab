/** @odoo-module **/
import { registry } from "@web/core/registry";
import {
    Many2ManyBinaryField,
    many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";

const VIEWABLE_RE = /\.(stl|obj)$/i;

export class Many2ManyBinary3DField extends Many2ManyBinaryField {
    static template = "dental_lab.Many2ManyBinary3DField";

    get viewableFiles() {
        return this.files.filter((file) => file.id && VIEWABLE_RE.test(file.name || ""));
    }

    open3D(file) {
        const url = `/dental_lab/static/viewer/viewer.html?id=${file.id}&name=${encodeURIComponent(file.name)}`;
        window.open(url, "_blank");
        // Popup window instead of a tab:
        // window.open(url, "dentalViewer", "width=1100,height=750,resizable=yes");
    }
}

registry.category("fields").add("many2many_binary_3d", {
    ...many2ManyBinaryField,
    component: Many2ManyBinary3DField,
});