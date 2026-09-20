// dental_lab/static/src/js/dental_lab_portal.js
var FDI_QUADRANTS = {
    topLeft: [18, 17, 16, 15, 14, 13, 12, 11],
    topRight: [21, 22, 23, 24, 25, 26, 27, 28],
    bottomLeft: [48, 47, 46, 45, 44, 43, 42, 41],
    bottomRight: [31, 32, 33, 34, 35, 36, 37, 38],
};

var SVG_NS = 'http://www.w3.org/2000/svg';
var TOOTH_W = 34;
var TOOTH_GAP = 6;
var TOOTH_H = 58;
var MIDLINE_GAP = 14;
var ARCH_AMPLITUDE = 20;
var CHART_HEIGHT = 300;
var GAP_Y = CHART_HEIGHT / 2;
var CHART_WIDTH = 2 * (8 * (TOOTH_W + TOOTH_GAP)) + MIDLINE_GAP + 40;

var currentTeethInput = null;

function svgEl(tag, attrs) {
    var el = document.createElementNS(SVG_NS, tag);
    for (var key in attrs) {
        el.setAttribute(key, attrs[key]);
    }
    return el;
}

function buildToothShape(flip) {
    // flip = true  -> crown at bottom, root pointing up   (upper arch: crown faces the gap below it)
    // flip = false -> crown at top, root pointing down    (lower arch: crown faces the gap above it)
    var group = svgEl('g', { 'class': 'dental-tooth-shape' });
    var crownH = TOOTH_H * 0.55;
    var crownY = flip ? TOOTH_H - crownH : 0;
    var crown = svgEl('rect', {
        x: 2, y: crownY, width: TOOTH_W - 4, height: crownH, rx: 6, ry: 6,
    });
    var rootBaseY = TOOTH_H / 2;
    var rootTipY = flip ? 0 : TOOTH_H;
    var root = svgEl('polygon', {
        points: (TOOTH_W * 0.32) + ',' + rootBaseY + ' ' +
                (TOOTH_W * 0.68) + ',' + rootBaseY + ' ' +
                (TOOTH_W * 0.5) + ',' + rootTipY,
    });
    group.appendChild(root);
    group.appendChild(crown);
    return group;
}

function buildQuadrant(svg, numbers, sideSign, isUpper) {
    var maxDx = numbers.length;
    numbers.forEach(function (toothNumber, i) {
        var dx = sideSign < 0 ? (maxDx - i) : (i + 1);
        var slotX = sideSign < 0
            ? (CHART_WIDTH / 2) - (MIDLINE_GAP / 2) - (dx - 1) * (TOOTH_W + TOOTH_GAP) - TOOTH_W
            : (CHART_WIDTH / 2) + (MIDLINE_GAP / 2) + (dx - 1) * (TOOTH_W + TOOTH_GAP);
        var offset = ARCH_AMPLITUDE * Math.pow(dx / maxDx, 2);
        var topY = isUpper ? (GAP_Y - TOOTH_H - offset) : (GAP_Y + offset);

        var g = svgEl('g', {
            'class': 'dental-tooth',
            'data-tooth': String(toothNumber),
            transform: 'translate(' + slotX + ',' + topY + ')',
        });
        g.appendChild(buildToothShape(isUpper));

        var label = svgEl('text', {
            x: TOOTH_W / 2,
            y: isUpper ? -6 : TOOTH_H + 14,
            'text-anchor': 'middle',
            'class': 'dental-tooth-label',
        });
        label.textContent = String(toothNumber);
        g.appendChild(label);

        svg.appendChild(g);
    });
}

function buildOdontogram(chart) {
    if (chart.dataset.built) {
        return;
    }
    var svg = svgEl('svg', {
        viewBox: '0 0 ' + CHART_WIDTH + ' ' + CHART_HEIGHT,
        'class': 'dental-odontogram-svg',
    });

    var midline = svgEl('line', {
        x1: CHART_WIDTH / 2, y1: 10, x2: CHART_WIDTH / 2, y2: CHART_HEIGHT - 10,
        'class': 'dental-midline-guide',
    });
    svg.appendChild(midline);

    buildQuadrant(svg, FDI_QUADRANTS.topLeft, -1, true);
    buildQuadrant(svg, FDI_QUADRANTS.topRight, 1, true);
    buildQuadrant(svg, FDI_QUADRANTS.bottomLeft, -1, false);
    buildQuadrant(svg, FDI_QUADRANTS.bottomRight, 1, false);

    chart.appendChild(svg);
    chart.dataset.built = '1';
}

function getSelectedTeeth(chart) {
    return Array.prototype.slice.call(chart.querySelectorAll('.dental-tooth.active'))
        .map(function (g) { return g.dataset.tooth; });
}

function updateSelectedPreview(chart, preview) {
    var selected = getSelectedTeeth(chart);
    preview.textContent = selected.length ? selected.join(', ') : 'None';
}

function showOdontogramModal(modalEl) {
    modalEl.classList.add('show');
    modalEl.style.display = 'block';
    modalEl.removeAttribute('aria-hidden');
    document.body.classList.add('modal-open');

    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade show';
    backdrop.id = 'dental-odontogram-backdrop';
    backdrop.addEventListener('click', function () {
        hideOdontogramModal(modalEl);
    });
    document.body.appendChild(backdrop);
}

function hideOdontogramModal(modalEl) {
    modalEl.classList.remove('show');
    modalEl.style.display = 'none';
    modalEl.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');

    var backdrop = document.getElementById('dental-odontogram-backdrop');
    if (backdrop) {
        backdrop.remove();
    }
}

function openOdontogramModal(input) {
    var modalEl = document.getElementById('dental-odontogram-modal');
    var chart = document.getElementById('dental-odontogram-chart');
    var preview = document.getElementById('dental-odontogram-selected');
    if (!modalEl || !chart || !preview) {
        return;
    }

    buildOdontogram(chart);
    currentTeethInput = input;

    var current = (input.value || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    Array.prototype.slice.call(chart.querySelectorAll('.dental-tooth')).forEach(function (g) {
        g.classList.toggle('active', current.indexOf(g.dataset.tooth) !== -1);
    });
    updateSelectedPreview(chart, preview);

    showOdontogramModal(modalEl);
}

function initOdontogramModal() {
    var modalEl = document.getElementById('dental-odontogram-modal');
    var chart = document.getElementById('dental-odontogram-chart');
    var preview = document.getElementById('dental-odontogram-selected');
    var applyBtn = document.getElementById('dental-odontogram-apply');
    if (!modalEl || !chart || !applyBtn) {
        return;
    }

    chart.addEventListener('click', function (ev) {
        var tooth = ev.target.closest('.dental-tooth');
        if (!tooth) {
            return;
        }
        tooth.classList.toggle('active');
        updateSelectedPreview(chart, preview);
    });

    Array.prototype.slice.call(modalEl.querySelectorAll('.dental-odontogram-close')).forEach(function (btn) {
        btn.addEventListener('click', function () {
            hideOdontogramModal(modalEl);
        });
    });

    applyBtn.addEventListener('click', function () {
        if (currentTeethInput) {
            currentTeethInput.value = getSelectedTeeth(chart).join(', ');
            currentTeethInput.dispatchEvent(new Event('change'));
            syncRowQuantity(currentTeethInput.closest('.dental-line-row'));
        }
        hideOdontogramModal(modalEl);
    });

    document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape' && modalEl.classList.contains('show')) {
            hideOdontogramModal(modalEl);
        }
    });
}

function syncRowQuantity(row) {
    var teethInput = row.querySelector('.dental-teeth-input');
    var qtyInput = row.querySelector('.dental-quantity-input');
    if (!teethInput || !qtyInput) {
        return;
    }
    var teeth = (teethInput.value || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    qtyInput.value = teeth.length;
}

function initDentalLines() {
    var container = document.getElementById('dental-lines-container');
    var addBtn = document.getElementById('dental-add-line');
    if (!container || !addBtn) {
        return;
    }
    Array.prototype.slice.call(container.querySelectorAll('.dental-line-row')).forEach(syncRowQuantity);
    var nextIndex = container.querySelectorAll('.dental-line-row').length;

    function buildRow(index) {
        var row = document.createElement('div');
        row.className = 'row g-2 align-items-end dental-line-row border rounded p-2 mb-2';
        row.innerHTML =
            '<div class="col-md-2">' +
                '<label class="form-label">Teeth</label>' +
                '<input type="text" class="form-control dental-teeth-input" readonly="readonly" required="required" placeholder="Select..." name="lines-' + index + '-teeth"/>' +
                '<button type="button" class="btn btn-outline-secondary btn-sm w-100 mt-1 dental-select-teeth">Select</button>' +
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
                '<input type="number" min="1" class="form-control dental-quantity-input" readonly="readonly" name="lines-' + index + '-quantity" value="1"/>' +
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
        var selectBtn = ev.target.closest('.dental-select-teeth');
        if (selectBtn) {
            openOdontogramModal(selectBtn.closest('.dental-line-row').querySelector('.dental-teeth-input'));
            return;
        }
        var removeBtn = ev.target.closest('.dental-remove-line');
        if (removeBtn) {
            var rows = container.querySelectorAll('.dental-line-row');
            if (rows.length > 1) {
                removeBtn.closest('.dental-line-row').remove();
            }
        }
    });

    var form = container.closest('form');
    if (form) {
        form.addEventListener('submit', function (ev) {
            var inputs = form.querySelectorAll('.dental-teeth-input');
            var emptyInput = null;
            for (var i = 0; i < inputs.length; i++) {
                if (!inputs[i].value) {
                    emptyInput = inputs[i];
                    break;
                }
            }
            if (emptyInput) {
                ev.preventDefault();
                emptyInput.closest('.dental-line-row').scrollIntoView({ behavior: 'smooth', block: 'center' });
                window.alert('Please select teeth for every work line before submitting.');
            }
        });
    }
}

function initDentalLab() {
    initDentalLines();
    initOdontogramModal();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDentalLab);
} else {
    initDentalLab();
}