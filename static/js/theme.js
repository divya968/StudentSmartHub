/* Student Smart Hub — shared front-end helpers:
   dark mode, toasts, confetti, sidebar, shortcuts, PWA, animations. */
(function () {
    var root = document.documentElement;

    // ---- Dark / light mode (remembers choice) ----
    var saved = null;
    try { saved = localStorage.getItem("ssh-theme"); } catch (e) {}
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.setAttribute("data-theme", saved || (prefersDark ? "dark" : "light"));

    // ---- PWA: manifest + theme colour (service worker registered on load) ----
    function addHead(tag, attrs) {
        var el = document.createElement(tag);
        Object.keys(attrs).forEach(function (k) { el.setAttribute(k, attrs[k]); });
        document.head.appendChild(el);
    }
    addHead("link", { rel: "manifest", href: "/manifest.json" });
    addHead("meta", { name: "theme-color", content: "#7c3aed" });
    addHead("link", { rel: "apple-touch-icon", href: "/static/img/icon-192.png" });

    // ---- Public helpers ----
    var SSH = window.SSH = {};

    SSH.csrf = function () {
        var el = document.querySelector("input[name=csrfmiddlewaretoken]");
        if (el) return el.value;
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : "";
    };

    SSH.post = function (url, data) {
        return fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": SSH.csrf(), "X-Requested-With": "fetch" },
            body: JSON.stringify(data || {})
        }).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (j) { j._status = r.status; j._ok = r.ok; return j; });
        });
    };

    SSH.toast = function (msg, level) {
        var box = document.getElementById("toasts");
        if (!box) { box = document.createElement("div"); box.id = "toasts"; document.body.appendChild(box); }
        level = (level || "info").replace("debug", "info");
        var t = document.createElement("div");
        t.className = "toast " + level;
        t.textContent = msg;
        function close() { t.classList.add("out"); setTimeout(function () { t.remove(); }, 320); }
        t.addEventListener("click", close);
        box.appendChild(t);
        setTimeout(close, 5200);
        if (level === "success" && /complet|goal|streak|level|badge|congrat|great|welcome|saved|🎉/i.test(msg)) SSH.confetti();
    };

    SSH.confetti = function () {
        if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
        var c = document.getElementById("confetti");
        if (!c) { c = document.createElement("canvas"); c.id = "confetti"; document.body.appendChild(c); }
        var ctx = c.getContext("2d");
        c.width = window.innerWidth; c.height = window.innerHeight;
        var colors = ["#7c3aed", "#ec4899", "#06b6d4", "#f59e0b", "#10b981", "#4f46e5"];
        var parts = [];
        for (var i = 0; i < 130; i++) {
            parts.push({
                x: c.width / 2 + (Math.random() - .5) * 200, y: c.height * .35,
                vx: (Math.random() - .5) * 15, vy: Math.random() * -13 - 3,
                s: Math.random() * 8 + 4, r: Math.random() * 6, vr: (Math.random() - .5) * .4,
                c: colors[(Math.random() * colors.length) | 0]
            });
        }
        var frames = 0;
        (function tick() {
            ctx.clearRect(0, 0, c.width, c.height);
            parts.forEach(function (p) {
                p.vy += .35; p.x += p.vx; p.y += p.vy; p.r += p.vr;
                ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r);
                ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); ctx.restore();
            });
            if (++frames < 130) requestAnimationFrame(tick); else c.remove();
        })();
    };

    document.addEventListener("DOMContentLoaded", function () {
        // ---- Theme toggle button ----
        var btn = document.createElement("button");
        btn.className = "theme-toggle no-print";
        btn.type = "button";
        btn.setAttribute("aria-label", "Toggle dark mode");
        function paint() { btn.textContent = root.getAttribute("data-theme") === "dark" ? "☀️" : "🌙"; }
        paint();
        btn.addEventListener("click", function () {
            var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
            root.setAttribute("data-theme", next);
            try { localStorage.setItem("ssh-theme", next); } catch (e) {}
            paint();
            document.dispatchEvent(new CustomEvent("ssh-theme-change"));
        });
        document.body.appendChild(btn);

        // ---- Django messages -> toasts ----
        document.querySelectorAll(".ssh-flash").forEach(function (el) {
            SSH.toast(el.textContent.trim(), el.getAttribute("data-level"));
            el.remove();
        });
        document.querySelectorAll(".messages, .message, .alert-success, .alert-info, .alert-danger").forEach(function (el) {
            if (el.closest("#toasts") || el.classList.contains("toast")) return;
            var txt = el.textContent.trim();
            if (!txt) return;
            var level = el.classList.contains("alert-danger") || /error|invalid/i.test(el.className) ? "error" : "success";
            SSH.toast(txt, level);
            el.style.display = "none";
        });

        // ---- Sidebar (mobile) ----
        var side = document.getElementById("sidebar"), toggle = document.getElementById("sideToggle"),
            backdrop = document.getElementById("sideBackdrop");
        function setSide(open) {
            if (!side) return;
            side.classList.toggle("open", open);
            if (backdrop) backdrop.classList.toggle("show", open);
        }
        if (toggle) toggle.addEventListener("click", function () { setSide(!side.classList.contains("open")); });
        if (backdrop) backdrop.addEventListener("click", function () { setSide(false); });
        var active = document.querySelector(".side-link.active");
        if (active && active.scrollIntoView) active.scrollIntoView({ block: "nearest" });

        // ---- Keyboard shortcut: Ctrl/Cmd+K focuses search ----
        document.addEventListener("keydown", function (e) {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                var s = document.getElementById("globalSearch");
                if (s) { e.preventDefault(); setSide(true); s.focus(); }
            }
        });

        // ---- Count-up for stat numbers ----
        document.querySelectorAll("[data-count]").forEach(function (el) {
            var target = parseFloat(el.getAttribute("data-count")) || 0;
            var start = null, dur = 900;
            function step(ts) {
                if (!start) start = ts;
                var p = Math.min((ts - start) / dur, 1);
                el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
                if (p < 1) requestAnimationFrame(step);
            }
            requestAnimationFrame(step);
        });

        // ---- Progress bars animate from 0 ----
        document.querySelectorAll(".progress-fill, .fill, .progress-bar, .xp-bar > i").forEach(function (bar) {
            var w = bar.style.width;
            if (!w) return;
            bar.style.width = "0%";
            setTimeout(function () { bar.style.width = w; }, 150);
        });

        // ---- Scroll reveal on cards ----
        var items = document.querySelectorAll(".card, .stat, .task, .stat-card, .module-card, .streak-card, .formbox, .panel, .kpi");
        if ("IntersectionObserver" in window) {
            var io = new IntersectionObserver(function (entries) {
                entries.forEach(function (e) {
                    if (e.isIntersecting) {
                        var t = e.target;
                        t.classList.add("show");
                        io.unobserve(t);
                        setTimeout(function () { t.classList.remove("reveal", "show"); t.style.transitionDelay = ""; }, 1000);
                    }
                });
            }, { threshold: 0.05 });
            items.forEach(function (el, i) {
                el.classList.add("reveal");
                el.style.transitionDelay = Math.min(i % 6, 5) * 60 + "ms";
                io.observe(el);
            });
        }
    });

    // ---- Service worker (installable app + offline page) ----
    window.addEventListener("load", function () {
        if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
            navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
        }
    });
})();
