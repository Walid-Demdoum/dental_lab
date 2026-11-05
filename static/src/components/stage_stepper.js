/** @odoo-module **/
import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";

export class DentalStageStepperField extends Component {
    static template = "dental_lab.DentalStageStepperField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.rootRef = useRef("root");
        this.state = useState({ steps: [] });
        onWillStart(async () => {
            const { relation } = this.props.record.fields[this.props.name];
            const steps = await this.orm.searchRead(relation, [], ["display_name"]);
            this.state.steps = steps.map((s) => ({ id: s.id, label: s.display_name }));
        });
        // keep the current step visible when the stepper scrolls (narrow screens)
        useEffect(
            () => {
                const root = this.rootRef.el;
                const current = root && root.querySelector(".o_dental_step_current");
                if (current) {
                    root.scrollLeft = current.offsetLeft - (root.clientWidth - current.offsetWidth) / 2;
                }
            },
            () => [this.currentId, this.state.steps.length]
        );
    }

    get currentId() {
        const value = this.props.record.data[this.props.name];
        return value ? value[0] : false;
    }

    get currentIndex() {
        return this.state.steps.findIndex((s) => s.id === this.currentId);
    }

    async select(step) {
        if (this.props.readonly || step.id === this.currentId) {
            return;
        }
        await this.props.record.update({ [this.props.name]: [step.id, step.label] });
        await this.props.record.save();
    }
}

registry.category("fields").add("dental_stage_stepper", {
    component: DentalStageStepperField,
    displayName: _t("Dental Step Stepper"),
    supportedTypes: ["many2one"],
})