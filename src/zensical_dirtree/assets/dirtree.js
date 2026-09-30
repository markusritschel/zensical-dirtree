/* zensical-dirtree: interactivity for the prebuilt [data-dirtree] markup.
 * Without this script the widget reads as a nested list of links followed by
 * every node's description; with it, one panel shows at a time. */
(() => {
  "use strict";
  if (window.__dirtreeLoaded) return; // never bind global listeners twice
  window.__dirtreeLoaded = true;

  const PREFIX = "dirtree-";
  const ITEM = '[role="treeitem"]';
  const controllers = new WeakMap();

  const isFolder = (li) => li.hasAttribute("aria-expanded");
  const isOpen = (li) => li.getAttribute("aria-expanded") === "true";
  const parentItem = (li) => li.parentElement.closest(ITEM);
  const children = (li) => [...li.querySelectorAll(`:scope > ul > ${ITEM}`)];
  const labelOf = (li) =>
    li.querySelector(":scope > .dirtree__row .dirtree__label").textContent;

  function isVisible(li) {
    for (let p = parentItem(li); p; p = parentItem(p)) if (!isOpen(p)) return false;
    return true;
  }

  function init(root) {
    if (controllers.has(root)) return;
    const tree = root.querySelector(".dirtree__tree");
    const items = [...tree.querySelectorAll(ITEM)];
    if (!items.length) return;
    const folders = items.filter(isFolder);
    const panels = [...root.querySelectorAll("[data-panel]")];
    const live = root.querySelector("[data-dirtree-live]");
    const toggleAll = root.querySelector("[data-dirtree-toggle-all]");
    let current = null;

    root.classList.add("dirtree--js");
    for (const li of items) {
      li.setAttribute("aria-selected", "false");
      li.tabIndex = -1;
      li.querySelector(":scope > .dirtree__row > .dirtree__link").tabIndex = -1;
    }

    // Roving tabindex: the selected item, or its nearest visible ancestor
    // when a collapse has hidden it, is the widget's single tab stop.
    function syncTabStop() {
      let stop = current;
      while (stop && !isVisible(stop)) stop = parentItem(stop);
      for (const li of items) li.tabIndex = li === stop ? 0 : -1;
    }

    function syncToggleAll() {
      if (!toggleAll) return;
      toggleAll.hidden = folders.length === 0;
      const action = folders.some((f) => !isOpen(f)) ? "expand" : "collapse";
      const label = action === "expand" ? "Expand all" : "Collapse all";
      toggleAll.dataset.action = action; // picks the icon
      toggleAll.setAttribute("aria-label", label);
      toggleAll.title = label; // hover tooltip
    }

    function setOpen(li, open) {
      if (!isFolder(li)) return;
      li.setAttribute("aria-expanded", String(open));
      syncToggleAll();
      syncTabStop();
    }

    function select(li, { focus = false, announce = true, hash = true } = {}) {
      if (current) current.setAttribute("aria-selected", "false");
      current = li;
      li.setAttribute("aria-selected", "true");
      for (let p = parentItem(li); p; p = parentItem(p)) setOpen(p, true);
      for (const panel of panels) panel.hidden = panel.dataset.panel !== li.dataset.node;
      syncTabStop();
      if (focus) li.focus();
      if (hash) history.replaceState(history.state, "", `#${PREFIX}${li.dataset.node}`);
      if (announce && live) live.textContent = `${labelOf(li)} selected`;
    }

    const byId = (id) => items.find((li) => li.dataset.node === id);

    tree.addEventListener("click", (event) => {
      const li = event.target.closest(ITEM);
      if (!li || !event.target.closest(".dirtree__row")) return;
      event.preventDefault();
      if (event.target.closest("[data-dirtree-arrow]")) {
        setOpen(li, !isOpen(li)); // toggle only; selection stays
        return;
      }
      select(li, { focus: true });
      setOpen(li, true);
    });

    tree.addEventListener("keydown", (event) => {
      const li = event.target.closest(ITEM);
      if (!li || event.altKey || event.ctrlKey || event.metaKey) return;
      const visible = items.filter(isVisible);
      const index = visible.indexOf(li);
      let next = null;
      switch (event.key) {
        case "ArrowDown": next = visible[index + 1]; break;
        case "ArrowUp": next = visible[index - 1]; break;
        case "Home": next = visible[0]; break;
        case "End": next = visible[visible.length - 1]; break;
        case "ArrowRight":
          if (isFolder(li) && !isOpen(li)) setOpen(li, true);
          else if (isFolder(li)) next = children(li)[0];
          break;
        case "ArrowLeft":
          if (isFolder(li) && isOpen(li)) setOpen(li, false);
          else next = parentItem(li);
          break;
        case "Enter":
        case " ":
          select(li);
          if (isFolder(li)) setOpen(li, !isOpen(li));
          break;
        default:
          return;
      }
      event.preventDefault();
      // Focus movement is announced by the screen reader itself.
      if (next) select(next, { focus: true, announce: false });
    });

    if (toggleAll) {
      toggleAll.addEventListener("click", () => {
        const open = folders.some((f) => !isOpen(f));
        for (const f of folders) f.setAttribute("aria-expanded", String(open));
        syncToggleAll();
        syncTabStop();
      });
    }

    // Breadcrumbs and "Contents" lists link to sibling panels. Instant
    // navigation rewrites hrefs to absolute URLs, so compare the parts.
    root.querySelector(".dirtree__panels").addEventListener("click", (event) => {
      const a = event.target.closest("a[href]");
      if (!a || a.pathname !== location.pathname) return;
      if (!a.hash.startsWith(`#${PREFIX}`)) return;
      const li = byId(decodeURIComponent(a.hash.slice(1 + PREFIX.length)));
      if (!li) return;
      event.preventDefault();
      select(li, { focus: true });
    });

    const controller = {
      select: (id, scroll) => {
        const li = byId(id);
        if (!li) return false;
        select(li, { hash: false });
        if (scroll) root.scrollIntoView({ block: "start" });
        return true;
      },
    };
    controllers.set(root, controller);
    syncToggleAll();
    if (!fromHash(location.hash)) {
      select(byId(root.dataset.selected) || items[0], { announce: false, hash: false });
    }
  }

  // Deep links: #dirtree-<id> selects that node in whichever widget holds it.
  function fromHash(hash) {
    if (!hash.startsWith(`#${PREFIX}`)) return false;
    const panel = document.getElementById(decodeURIComponent(hash.slice(1)));
    const root = panel && panel.closest("[data-dirtree]");
    const controller = root && controllers.get(root);
    return Boolean(controller && controller.select(panel.dataset.panel, true));
  }

  window.addEventListener("hashchange", () => fromHash(location.hash));

  const initAll = () => document.querySelectorAll("[data-dirtree]").forEach(init);
  if (typeof window.document$ !== "undefined") {
    window.document$.subscribe(initAll); // re-runs after instant navigation
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
