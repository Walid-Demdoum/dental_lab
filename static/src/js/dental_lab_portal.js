// dental_lab/static/src/js/dental_lab_portal.js
function initDentalLines() {
    var container = document.getElementById('dental-lines-container');
    var addBtn = document.getElementById('dental-add-line');
    if (!container || !addBtn) {
        return;
    }

    var nextIndex = container.querySelectorAll('.dental-line-row').length;

    function buildRow(index) {
        var row = document.createElement('div');
        row.className = 'row g-2 align-items-end dental-line-row border rounded p-2 mb-2';
        row.innerHTML =
            '<div class="col-md-2">' +
                '<label class="form-label">Teeth</label>' +
                '<input type="text" class="form-control" required="required" name="lines-' + index + '-teeth"/>' +
            '</div>' +
            '<div class="col-md-3">' +
                '<label class="form-label">Work Type</label>' +
                '<select class="form-select" required="required" name="lines-' + index + '-work_type">' +
                    '<option value="">-- Select --</option>' +
                    '<option value="zircon">Zircon</option>' +
                    '<option value="ccm">CCM</option>' +
                    '<option value="ceramic_metal">Metal-Ceramic</option>' +
                '</select>' +
            '</div>' +
            '<div class="col-md-3">' +
                '<label class="form-label">Description</label>' +
                '<input type="text" class="form-control" name="lines-' + index + '-description"/>' +
            '</div>' +
            '<div class="col-md-1">' +
                '<label class="form-label">Qty</label>' +
                '<input type="number" min="1" class="form-control" name="lines-' + index + '-quantity" value="1"/>' +
            '</div>' +
            '<div class="col-md-2 form-check pt-4">' +
                '<input type="checkbox" class="form-check-input" id="implant-' + index + '" name="lines-' + index + '-is_implant"/>' +
                '<label class="form-check-label" for="implant-' + index + '">Implant</label>' +
            '</div>' +
            '<div class="col-md-1">' +
                '<button type="button" class="btn btn-outline-danger btn-sm dental-remove-line"><i class="fa fa-trash"></i></button>' +
            '</div>';
        return row;
    }

    addBtn.addEventListener('click', function () {
        container.appendChild(buildRow(nextIndex));
        nextIndex += 1;
    });

    container.addEventListener('click', function (ev) {
        var removeBtn = ev.target.closest('.dental-remove-line');
        if (removeBtn) {
            var rows = container.querySelectorAll('.dental-line-row');
            if (rows.length > 1) {
                removeBtn.closest('.dental-line-row').remove();
            }
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDentalLines);
} else {
    initDentalLines();
}