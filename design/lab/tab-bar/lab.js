// Lab page only: shows the tab bar and the menu as each role sees them,
// lights the tab of the page that is open, opens and closes the menu, and
// turns the sample Sounds switch. In the app the server sends each role
// only its own tabs and rows. Never used by the app.

const ROLES = {
  owner: { home: "Owner", menu: "Manage", name: "Ravi", role: "Owner account", menuPage: "cashbook" },
  office: { home: "Office", menu: "Manage", name: "Anil", role: "Office account", menuPage: "cashbook" },
  floor: { home: "Floor", menu: "Menu", name: "ab.floor", role: "Floor account", menuPage: "low-stock" },
};

const body = document.body;
const menu = document.getElementById("app-menu");
const menuTab = document.querySelector('[data-tab="menu"]');
const badge = document.querySelector("[data-badge]");

function text(key, value) {
  for (const element of document.querySelectorAll(`[data-lab-text="${key}"]`)) {
    element.textContent = value;
  }
}

function show() {
  const role = ROLES[body.dataset.role];
  for (const element of document.querySelectorAll("[data-for]")) {
    element.hidden = !element.dataset.for.split(" ").includes(body.dataset.role);
  }
  text("home", role.home);
  text("menu", role.menu);
  text("name", role.name);
  text("role", role.role);

  // Exactly one tab is lit (ROLE-28). A page from the menu lights Manage,
  // except Floor's stock pages, which light Inventory.
  for (const lit of document.querySelectorAll("[aria-current], [data-lit]")) {
    lit.removeAttribute("aria-current");
    delete lit.dataset.lit;
  }
  if (body.dataset.page === "home") {
    document.querySelector('[data-tab="home"]').setAttribute("aria-current", "page");
  } else {
    menu.querySelector(`[data-page="${role.menuPage}"]`).setAttribute("aria-current", "page");
    if (body.dataset.role === "floor") {
      document.querySelector('[data-tab="inventory"]').setAttribute("aria-current", "page");
    } else {
      menuTab.dataset.lit = "";
    }
  }
}

function showAlerts(count) {
  badge.hidden = count === 0;
  badge.querySelector("[data-badge-count]").textContent = count > 99 ? "99+" : String(count);
}

function choose(attribute, onChoose) {
  const buttons = document.querySelectorAll(`[${attribute}]`);
  for (const button of buttons) {
    button.addEventListener("click", () => {
      for (const other of buttons) {
        other.setAttribute("aria-pressed", String(other === button));
      }
      onChoose(button.getAttribute(attribute));
    });
  }
}

choose("data-lab-role", (role) => {
  body.dataset.role = role;
  show();
});
choose("data-lab-page", (page) => {
  body.dataset.page = page;
  show();
});
choose("data-lab-alerts", (count) => showAlerts(Number(count)));

// The menu: a modal dialog, so the keyboard stays in it and Escape closes
// it. A tap on the shaded page beside it closes it too (ROLE-33).
menuTab.addEventListener("click", () => {
  menu.showModal();
  menuTab.setAttribute("aria-expanded", "true");
});
menu.addEventListener("close", () => menuTab.setAttribute("aria-expanded", "false"));
menu.querySelector("[data-menu-close]").addEventListener("click", () => menu.close());
menu.addEventListener("click", (event) => {
  if (event.target === menu) {
    menu.close();
  }
});

// Sounds on or off, for this device (ROLE-34). The app keeps the choice
// in the browser, as sound.js reads it; the lab only turns the switch.
const sound = menu.querySelector("[data-lab-sound]");
sound.addEventListener("click", () => {
  const on = sound.getAttribute("aria-checked") !== "true";
  sound.setAttribute("aria-checked", String(on));
  sound.querySelector("[data-lab-sound-label]").textContent = on ? "Sounds on" : "Sounds off";
  const icon = sound.querySelector("[data-lab-sound-icon]");
  icon.setAttribute("href", icon.getAttribute("href").replace(/#.*/, on ? "#volume-2" : "#volume-x"));
});

// The sample links go nowhere in the lab.
for (const link of document.querySelectorAll('.tab-bar a, .menu a[href="#"]')) {
  link.addEventListener("click", (event) => event.preventDefault());
}

show();
showAlerts(3);
