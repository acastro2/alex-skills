// Runs before first paint, so the page never flashes the wrong theme.
// Choice: "system" (default), "light" or "dark". data-theme always holds the resolved value.
(function () {
  var KEY = "harness-theme";
  var query = window.matchMedia("(prefers-color-scheme: dark)");
  function choice() {
    try {
      var v = localStorage.getItem(KEY);
      return v === "light" || v === "dark" ? v : "system";
    } catch (e) {
      return "system";
    }
  }
  function resolve() {
    var c = choice();
    return c === "system" ? (query.matches ? "dark" : "light") : c;
  }
  function apply() {
    var next = resolve();
    document.documentElement.setAttribute("data-theme", next);
    document.documentElement.setAttribute("data-theme-choice", choice());
    window.dispatchEvent(new CustomEvent("harness-theme", { detail: next }));
  }
  window.harnessTheme = {
    choice: choice,
    resolved: resolve,
    set: function (c) {
      try {
        if (c === "system") localStorage.removeItem(KEY);
        else localStorage.setItem(KEY, c);
      } catch (e) {}
      apply();
    },
  };
  query.addEventListener("change", apply);
  apply();
})();
