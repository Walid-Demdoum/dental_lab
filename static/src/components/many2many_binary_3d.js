/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import {
    Many2ManyBinaryField,
    many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";

const VIEWABLE_RE = /\.(stl|obj)$/i;

export class Viewer3DDialog extends Component {
    static template = "dental_lab.Viewer3DDialog";
    static components = { Dialog };
    static props = ["title", "url", "close?"];
}

export class Many2ManyBinary3DField extends Many2ManyBinaryField {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    isViewable3D(file) {
        return Boolean(file.id) && VIEWABLE_RE.test(file.name || "");
    }

    open3D(file) {
        this.dialogService.add(Viewer3DDialog, {
            title: `3D - ${file.name}`,
            url: `/dental_lab/static/viewer/viewer.html?id=${file.id}&name=${encodeURIComponent(file.name)}`,
        });
    }
}

registry.category("fields").add("many2many_binary_3d", {
    ...many2ManyBinaryField,
    component: Many2ManyBinary3DField,
});