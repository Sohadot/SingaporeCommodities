(() => {
  "use strict";

  const doc = document;
  const root = doc.documentElement;
  const body = doc.body;

  const selectors = {
    navToggle: ".nav-toggle",
    mainNav: ".main-nav",
    navLinks: ".main-nav .nav-link",
    toolAnalyzeButton: "#tool-analyze-button",
    toolCommodity: "#tool-commodity",
    toolFunction: "#tool-function",
    toolResult: "#tool-result"
  };

  const state = {
    navOpen: false
  };

  const qs = (selector, scope = doc) => scope.querySelector(selector);
  const qsa = (selector, scope = doc) => Array.from(scope.querySelectorAll(selector));

  const navToggle = qs(selectors.navToggle);
  const mainNav = qs(selectors.mainNav);

  function closeNav() {
    if (!navToggle || !mainNav) return;
    navToggle.setAttribute("aria-expanded", "false");
    mainNav.classList.remove("is-open");
    state.navOpen = false;
    body.classList.remove("nav-open");
  }

  function openNav() {
    if (!navToggle || !mainNav) return;
    navToggle.setAttribute("aria-expanded", "true");
    mainNav.classList.add("is-open");
    state.navOpen = true;
    body.classList.add("nav-open");
  }

  function toggleNav() {
    if (state.navOpen) {
      closeNav();
    } else {
      openNav();
    }
  }

  function bindNavigation() {
    if (!navToggle || !mainNav) return;

    navToggle.addEventListener("click", toggleNav);

    doc.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.navOpen) {
        closeNav();
      }
    });

    doc.addEventListener("click", (event) => {
      if (!state.navOpen) return;
      const target = event.target;
      if (!(target instanceof Node)) return;

      const clickedInsideNav = mainNav.contains(target);
      const clickedToggle = navToggle.contains(target);

      if (!clickedInsideNav && !clickedToggle) {
        closeNav();
      }
    });

    qsa(selectors.navLinks, mainNav).forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 920) {
          closeNav();
        }
      });
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 920 && state.navOpen) {
        closeNav();
      }
    });
  }

  function secureExternalLinks() {
    qsa('a[href^="http"]').forEach((link) => {
      try {
        const url = new URL(link.href, window.location.origin);
        if (url.hostname !== window.location.hostname) {
          const currentRel = (link.getAttribute("rel") || "").trim();
          const relTokens = new Set(
            currentRel ? currentRel.split(/\s+/).filter(Boolean) : []
          );
          relTokens.add("noopener");
          relTokens.add("noreferrer");
          link.setAttribute("rel", Array.from(relTokens).join(" "));
          link.setAttribute("target", "_blank");
        }
      } catch (_) {
        // Ignore malformed URLs
      }
    });
  }

  function markCurrentPageContext() {
    root.classList.add("js-ready");

    const path = window.location.pathname.replace(/\/+$/, "") || "/";
    body.dataset.path = path;
  }

  function buildToolMessage(commodity, fn) {
    const commodityMap = {
      lng: "LNG",
      oil: "oil",
      bunkering: "bunkering fuel",
      metals: "metals",
      agriculture: "agriculture"
    };

    const functionMap = {
      routing: "routing logic",
      coordination: "coordination capacity",
      stabilization: "stabilization function",
      "strategic-relevance": "strategic relevance"
    };

    const commodityLabel = commodityMap[commodity] || commodity;
    const functionLabel = functionMap[fn] || fn;

    return [
      `Interpretive output: ${commodityLabel} through the lens of ${functionLabel}.`,
      "",
      "Read this not as a standalone commodity event, but as part of a wider system where Singapore may operate as:",
      "• a routing decision layer",
      "• a coordination interface",
      "• a maritime-commercial stabilizer",
      "• or a node translating movement into organized market relevance.",
      "",
      "The next production iteration can connect this interface to dynamic data surfaces, route intelligence, and structured market signals."
    ].join("\n");
  }

  function bindToolInterface() {
    const analyzeButton = qs(selectors.toolAnalyzeButton);
    const commoditySelect = qs(selectors.toolCommodity);
    const functionSelect = qs(selectors.toolFunction);
    const resultBox = qs(selectors.toolResult);

    if (!analyzeButton || !commoditySelect || !functionSelect || !resultBox) {
      return;
    }

    const renderToolResult = () => {
      const commodity = commoditySelect.value;
      const fn = functionSelect.value;
      resultBox.textContent = buildToolMessage(commodity, fn);
    };

    analyzeButton.addEventListener("click", renderToolResult);
    commoditySelect.addEventListener("change", renderToolResult);
    functionSelect.addEventListener("change", renderToolResult);
  }

  function bindInPageAnchors() {
    qsa('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", (event) => {
        const href = anchor.getAttribute("href");
        if (!href || href === "#") return;

        const target = qs(href);
        if (!target) return;

        event.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  function init() {
    markCurrentPageContext();
    bindNavigation();
    secureExternalLinks();
    bindToolInterface();
    bindInPageAnchors();
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
