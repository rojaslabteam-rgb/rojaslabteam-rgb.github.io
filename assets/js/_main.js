/* ==========================================================================
   Various functions that we want to use within the template
   ========================================================================== */

// Determine the expected state of the theme toggle, which can be "dark", "light", or
// "system". Default is "system".
let determineThemeSetting = () => {
  let themeSetting = localStorage.getItem("theme");
  return (themeSetting != "dark" && themeSetting != "light" && themeSetting != "system") ? "system" : themeSetting;
};

// Determine the computed theme, which can be "dark" or "light". If the theme setting is
// "system", the computed theme is determined based on the user's system preference.
let determineComputedTheme = () => {
  let themeSetting = determineThemeSetting();
  if (themeSetting != "system") {
    return themeSetting;
  }
  return (userPref && userPref("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
};

// detect OS/browser preference
const browserPref = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

// Set the theme on page load or when explicitly called
let setTheme = (theme) => {
  const use_theme =
    theme ||
    localStorage.getItem("theme") ||
    $("html").attr("data-theme") ||
    browserPref;

  if (use_theme === "dark") {
    $("html").attr("data-theme", "dark");
    $("#theme-icon").removeClass("fa-sun").addClass("fa-moon");
  } else if (use_theme === "light") {
    $("html").removeAttr("data-theme");
    $("#theme-icon").removeClass("fa-moon").addClass("fa-sun");
  }
};

// Toggle the theme manually
var toggleTheme = () => {
  const current_theme = $("html").attr("data-theme");
  const new_theme = current_theme === "dark" ? "light" : "dark";
  localStorage.setItem("theme", new_theme);
  setTheme(new_theme);
};

/* ==========================================================================
   Plotly integration script so that Markdown codeblocks will be rendered
   ========================================================================== */

// Read the Plotly data from the code block, hide it, and render the chart as new node. This allows for the 
// JSON data to be retrieve when the theme is switched. The listener should only be added if the data is 
// actually present on the page.
import { plotlyDarkLayout, plotlyLightLayout } from './theme.js';
let plotlyElements = document.querySelectorAll("pre>code.language-plotly");
if (plotlyElements.length > 0) {
  document.addEventListener("readystatechange", () => {
    if (document.readyState === "complete") {
      plotlyElements.forEach((elem) => {
        // Parse the Plotly JSON data and hide it
        var jsonData = JSON.parse(elem.textContent);
        elem.parentElement.classList.add("hidden");

        // Add the Plotly node
        let chartElement = document.createElement("div");
        elem.parentElement.after(chartElement);

        // Set the theme for the plot and render it
        const theme = (determineComputedTheme() === "dark") ? plotlyDarkLayout : plotlyLightLayout;
        if (jsonData.layout) {
          jsonData.layout.template = (jsonData.layout.template) ? { ...theme, ...jsonData.layout.template } : theme;
        } else {
          jsonData.layout = { template: theme };
        }
        Plotly.react(chartElement, jsonData.data, jsonData.layout);
      });
    }
  });
}

/* ==========================================================================
   Actions that should occur when the page has been fully loaded
   ========================================================================== */

$(document).ready(function () {
  // SCSS SETTINGS - These should be the same as the settings in the relevant files 
  const scssLarge = 925;          // pixels, from /_sass/_themes.scss
  const scssMastheadHeight = 186; // pixels, Purdue header (gold bar + signature + main nav)

  // If the user hasn't chosen a theme, follow the OS preference
  setTheme();
  window.matchMedia('(prefers-color-scheme: dark)')
        .addEventListener("change", (e) => {
          if (!localStorage.getItem("theme")) {
            setTheme(e.matches ? "dark" : "light");
          }
        });

  // Enable the theme toggle
  $('#theme-toggle').on('click', toggleTheme);

  // Purdue header interactions
  const mobileBreakpoint = 992;
  const $purdueHeader = $('.purdue-header');
  const $quickLinksToggle = $('#purdue-quicklinks-toggle');
  const $quickLinksPanel = $('#purdue-quicklinks-panel');
  const $findInfoToggle = $('#purdue-findinfo-toggle');
  const $findInfoPanel = $('.purdue-header__goldBar__findInfoFor');
  const $searchToggle = $('#purdue-search-toggle');
  const $searchPanel = $('#purdue-search-dropdown');
  const $mainNavToggle = $('#purdue-mainnav-toggle');
  const $mainNavPanel = $('#purdue-mainnav-panel');

  const setExpanded = ($element, expanded) => {
    if ($element && $element.length) {
      $element.attr('aria-expanded', expanded ? 'true' : 'false');
    }
  };

  const closeUtilityMenus = () => {
    $findInfoPanel.removeClass('is-open');
    setExpanded($findInfoToggle, false);
    $searchPanel.removeClass('is-open');
    setExpanded($searchToggle, false);
  };

  if ($quickLinksToggle.length && $quickLinksPanel.length) {
    $quickLinksToggle.on('click', function (event) {
      event.preventDefault();
      const willOpen = !$quickLinksPanel.hasClass('is-open');
      $quickLinksPanel.toggleClass('is-open', willOpen);
      setExpanded($quickLinksToggle, willOpen);
    });
  }

  if ($findInfoToggle.length && $findInfoPanel.length) {
    $findInfoToggle.on('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      const willOpen = !$findInfoPanel.hasClass('is-open');
      $findInfoPanel.toggleClass('is-open', willOpen);
      setExpanded($findInfoToggle, willOpen);
    });
  }

  if ($searchToggle.length && $searchPanel.length) {
    $searchToggle.on('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      const willOpen = !$searchPanel.hasClass('is-open');
      $searchPanel.toggleClass('is-open', willOpen);
      setExpanded($searchToggle, willOpen);
      if (willOpen) {
        $('#purdue-search-input').trigger('focus');
      }
    });
  }

  if ($mainNavToggle.length && $mainNavPanel.length) {
    $mainNavToggle.on('click', function (event) {
      event.preventDefault();
      const willOpen = !$mainNavPanel.hasClass('is-open');
      $mainNavPanel.toggleClass('is-open', willOpen);
      setExpanded($mainNavToggle, willOpen);
    });
  }

  $(document).on('click', function (event) {
    if (!$purdueHeader.length || $(event.target).closest('.purdue-header').length) {
      return;
    }

    closeUtilityMenus();

    if ($(window).width() <= mobileBreakpoint) {
      $quickLinksPanel.removeClass('is-open');
      setExpanded($quickLinksToggle, false);
      $mainNavPanel.removeClass('is-open');
      setExpanded($mainNavToggle, false);
    }
  });

  $(window).on('resize', function () {
    if ($(window).width() > mobileBreakpoint) {
      $quickLinksPanel.removeClass('is-open');
      setExpanded($quickLinksToggle, false);
      $mainNavPanel.removeClass('is-open');
      setExpanded($mainNavToggle, false);
    }
    closeUtilityMenus();
  });

  // Enable the sticky footer
  var bumpIt = function () {
    $("body").css("padding-bottom", "0");
    $("body").css("margin-bottom", $(".page__footer").outerHeight(true));
  }
  $(window).resize(function () {
    didResize = true;
  });
  setInterval(function () {
    if (didResize) {
      didResize = false;
      bumpIt();
    }}, 250);
  var didResize = false;
  bumpIt();

  // FitVids init
  fitvids();

  // Follow menu drop down
  $(".author__urls-wrapper button").on("click", function () {
    $(".author__urls").fadeToggle("fast", function () { });
    $(".author__urls-wrapper button").toggleClass("open");
  });

  // Restore the follow menu if toggled on a window resize
  jQuery(window).on('resize', function () {
    if ($('.author__urls.social-icons').css('display') == 'none' && $(window).width() >= scssLarge) {
      $(".author__urls").css('display', 'block')
    }
  });

  // Init smooth scroll, this needs to be slightly more than then fixed masthead height
  $("a").smoothScroll({
    offset: -scssMastheadHeight,
    preventDefault: false,
  });

});
