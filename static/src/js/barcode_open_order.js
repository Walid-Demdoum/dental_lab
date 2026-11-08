/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const ORDER_BARCODE = /^DL\d{8}$/;

export const dentalBarcodeService = {
    dependencies: ["barcode", "orm", "action", "notification"],
    start(env, { barcode, orm, action, notification }) {
        barcode.bus.addEventListener("barcode_scanned", async (ev) => {
            const code = ev.detail.barcode;
            if (!ORDER_BARCODE.test(code)) {
                return; // not ours (inventory barcodes etc.)
            }
            const act = await orm.call("dental.lab.order", "action_open_from_barcode", [code]);
            if (act) {
                action.doAction(act);
            } else {
                notification.add(_t("No work order found for %s", code), { type: "warning" });
            }
        });
    },
};

registry.category("services").add("dental_lab_barcode", dentalBarcodeService);