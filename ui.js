const form = document.querySelector("form");
const error = document.querySelector("#error");
const status = document.querySelector("#status");
const submit = form.querySelector("button");
const metrics = document.querySelector("#metrics");
const table = document.querySelector("table");

function node(tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  return element;
}

function render(result) {
  metrics.replaceChildren(...result.metrics.map(([label, value]) => {
    const group = document.createElement("div");
    group.append(node("dt", label), node("dd", value));
    return group;
  }));
  const heading = table.tHead.rows[0];
  heading.replaceChildren(...result.columns.map(label => {
    const cell = node("th", label);
    cell.scope = "col";
    return cell;
  }));
  table.tBodies[0].replaceChildren(...result.rows.map(row => {
    const tr = document.createElement("tr");
    tr.append(...row.map(value => node("td", value)));
    return tr;
  }));
  status.textContent = result.note;
}

async function run() {
  submit.disabled = true;
  error.textContent = "";
  status.textContent = "Calculating…";
  try {
    const query = new URLSearchParams(new FormData(form));
    const response = await fetch(`/api/replay?${query}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    render(result);
  } catch (failure) {
    status.textContent = "";
    error.textContent = failure.message;
  } finally {
    submit.disabled = false;
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  run();
});
run();
