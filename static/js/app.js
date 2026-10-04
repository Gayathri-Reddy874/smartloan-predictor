(function () {
  "use strict";

  var printBtn = document.getElementById("print-btn");
  if (printBtn) printBtn.addEventListener("click", function () { window.print(); });

  var form = document.getElementById("loan-form");
  if (!form) return;

  var rate = parseFloat(form.dataset.rate) || 9;
  var el = {
    income: form.elements.income, co: form.elements.co_app_income,
    loan: form.elements.loan_amount, term: form.elements.loan_amount_term,
    emi: document.getElementById("emi-value"), sub: document.getElementById("emi-sub"),
    meter: document.getElementById("meter"), marker: document.getElementById("marker"),
    label: document.getElementById("meter-label")
  };

  function inr(n) { return "₹" + Math.round(n).toLocaleString("en-IN"); }

  // Same reducing-balance formula as scoring.monthly_emi in Python.
  function emi(p, annualPct, months) {
    var r = annualPct / 1200;
    if (r === 0) return p / months;
    var g = Math.pow(1 + r, months);
    return p * r * g / (g - 1);
  }

  function band(share) {
    if (share <= 0.30) return "Comfortable";
    if (share <= 0.40) return "Within the usual lender limit";
    if (share <= 0.50) return "Stretched: likely to need manual review";
    return "Above what most lenders accept";
  }

  function update() {
    var loan = parseFloat(el.loan.value), term = parseInt(el.term.value, 10);
    var income = (parseFloat(el.income.value) || 0) + (parseFloat(el.co.value) || 0);

    if (!(loan > 0) || !(term >= 6)) {
      el.emi.textContent = "–";
      el.sub.textContent = "Fill in income, loan amount and term to see your EMI.";
      el.meter.hidden = true; el.label.hidden = true;
      return;
    }
    var monthly = emi(loan, rate, term);
    el.emi.textContent = inr(monthly);

    if (!(income > 0)) {
      el.sub.textContent = "a month. Add your income to see how it compares.";
      el.meter.hidden = true; el.label.hidden = true;
      return;
    }
    var share = monthly / income;
    el.sub.textContent = "a month, which is " + Math.round(share * 100) + "% of household income.";
    el.meter.hidden = false; el.label.hidden = false;
    el.marker.style.left = "calc(" + Math.min(share / 0.8, 1) * 100 + "% - 2px)";
    el.label.textContent = band(share);
  }

  ["income", "co", "loan", "term"].forEach(function (k) { el[k].addEventListener("input", update); });
  update();
})();
