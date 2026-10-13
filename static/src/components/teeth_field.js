/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";

const FDI_QUADRANTS = [
    { numbers: [18, 17, 16, 15, 14, 13, 12, 11], side: -1, upper: true },
    { numbers: [21, 22, 23, 24, 25, 26, 27, 28], side: 1, upper: true },
    { numbers: [48, 47, 46, 45, 44, 43, 42, 41], side: -1, upper: false },
    { numbers: [31, 32, 33, 34, 35, 36, 37, 38], side: 1, upper: false },
];

const TOOTH_W = 34;
const TOOTH_GAP = 6;
const TOOTH_H = 58;
const MIDLINE_GAP = 14;
const ARCH_AMPLITUDE = 20;
const CHART_HEIGHT = 300;
const GAP_Y = CHART_HEIGHT / 2;
const CHART_WIDTH = 2 * (8 * (TOOTH_W + TOOTH_GAP)) + MIDLINE_GAP + 40;

function parseTeeth(value) {
    return (value || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
}

function buildChart() {
    const teeth = [];
    const crownH = TOOTH_H * 0.55;
    for (const { numbers, side, upper } of FDI_QUADRANTS) {
        const maxDx = numbers.length;
        numbers.forEach((number, i) => {
            const dx = side < 0 ? maxDx - i : i + 1;
            const x =
                side < 0
                    ? CHART_WIDTH / 2 - MIDLINE_GAP / 2 - (dx - 1) * (TOOTH_W + TOOTH_GAP) - TOOTH_W
                    : CHART_WIDTH / 2 + MIDLINE_GAP / 2 + (dx - 1) * (TOOTH_W + TOOTH_GAP);
            const offset = ARCH_AMPLITUDE * Math.pow(dx / maxDx, 2);
            const y = upper ? GAP_Y - TOOTH_H - offset : GAP_Y + offset;
            const rootBaseY = TOOTH_H / 2;
            const rootTipY = upper ? 0 : TOOTH_H;
            teeth.push({
                key: String(number),
                x,
                y,
                crownY: upper ? TOOTH_H - crownH : 0,
                crownW: TOOTH_W - 4,
                crownH,
                rootPoints:
                    `${TOOTH_W * 0.32},${rootBaseY} ${TOOTH_W * 0.68},${rootBaseY} ` +
                    `${TOOTH_W * 0.5},${rootTipY}`,
                labelX: TOOTH_W / 2,
                labelY: upper ? -6 : TOOTH_H + 14,
            });
        });
    }
    return { teeth, width: CHART_WIDTH, height: CHART_HEIGHT };
}

const CHART = buildChart();

export class OdontogramDialog extends Component {
    static template = "dental_lab.OdontogramDialog";
    static components = { Dialog };
    static props = {
        selected: Array,
        onApply: Function,
        close: Function,
    };

    setup() {
        this.chart = CHART;
        this.state = useState({ selected: [...this.props.selected] });
    }

    get title() {
        return _t("Select Teeth (FDI)");
    }

    get selectedLabel() {
        return this.sortedSelection.length ? this.sortedSelection.join(", ") : _t("None");
    }

    get sortedSelection() {
        return [...this.state.selected].sort((a, b) => Number(a) - Number(b));
    }

    isSelected(key) {
        return this.state.selected.includes(key);
    }

    toggle(key) {
        const idx = this.state.selected.indexOf(key);
        if (idx === -1) {
            this.state.selected.push(key);
        } else {
            this.state.selected.splice(idx, 1);
        }
    }

    clear() {
        this.state.selected.length = 0;
    }

    apply() {
        this.props.onApply(this.sortedSelection);
        this.props.close();
    }
}

export class TeethField extends Component {
    static template = "dental_lab.TeethField";
    static props = { ...standardFieldProps };

    setup() {
        this.dialog = useService("dialog");
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    openOdontogram() {
        if (this.props.readonly) {
            return;
        }
        this.dialog.add(OdontogramDialog, {
            selected: parseTeeth(this.value),
            onApply: (teeth) =>
                this.props.record.update({ [this.props.name]: teeth.join(", ") }),
        });
    }
}

registry.category("fields").add("dental_teeth", {
    component: TeethField,
    displayName: _t("Dental Teeth (Odontogram)"),
    supportedTypes: ["char"],
});