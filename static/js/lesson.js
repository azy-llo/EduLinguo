/**
 * Урок: задания (включая writing, listening, reading_comp).
 */
(function () {
  "use strict";

  var GUEST_KEY = "ll_guest_progress_v1";
  var lessonFinalized = false;

  function readJson(id) {
    var el = document.getElementById(id);
    if (!el || !el.textContent) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function loadGuest() {
    try {
      var raw = sessionStorage.getItem(GUEST_KEY);
      if (!raw) return { xp: 0, done: {} };
      var o = JSON.parse(raw);
      return { xp: o.xp || 0, done: o.done && typeof o.done === "object" ? o.done : {} };
    } catch (e) {
      return { xp: 0, done: {} };
    }
  }

  function saveGuestDone(exerciseId, xpAdd) {
    var g = loadGuest();
    g.done[String(exerciseId)] = true;
    g.xp = (g.xp || 0) + xpAdd;
    sessionStorage.setItem(GUEST_KEY, JSON.stringify({ xp: g.xp, done: g.done }));
  }

  function scoreWritingClient(text, payload) {
    var words = text.match(/[A-Za-z']+/g) || [];
    var n = words.length;
    var minW = payload.min_words || 40;
    var score = 0;
    if (n >= minW) score += 45;
    else if (n >= Math.max(5, Math.floor(minW / 2))) score += 25;
    else score += 10;
    var lower = text.toLowerCase();
    var keys = payload.keywords || [];
    var hit = 0;
    for (var i = 0; i < keys.length; i++) {
      if (lower.indexOf(String(keys[i]).toLowerCase()) >= 0) hit++;
    }
    if (keys.length) score += Math.min(40, Math.floor((40 * hit) / keys.length));
    else score += 20;
    if (text.length > 400) score += 5;
    return Math.min(100, score);
  }

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i];
      a[i] = a[j];
      a[j] = t;
    }
    return a;
  }

  function kindLabel(kind) {
    var map = {
      words: "Слова",
      phrases: "Фразы",
      translate: "Перевод",
      reorder: "Сборка",
      reading_comp: "Чтение",
      listening: "Аудирование",
      writing: "Письмо",
    };
    return map[kind] || "Задание";
  }

  function finalizeLessonIfGuest() {
    var root = document.getElementById("lesson-root");
    if (!root || lessonFinalized) return;
    if (root.getAttribute("data-logged-in") === "true") return;
    var lid = parseInt(root.getAttribute("data-lesson-id") || "0", 10);
    if (!lid) return;
    fetch("/api/guest/lesson-complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lesson_id: lid }),
    })
      .then(function () {
        lessonFinalized = true;
      })
      .catch(function () {});
  }

  var root = document.getElementById("lesson-root");
  if (!root) return;

  var loggedIn = root.getAttribute("data-logged-in") === "true";
  var exercises = readJson("lesson-exercises-data") || [];
  var serverCompleted = readJson("lesson-completed-data") || [];
  var completedSet = {};
  var i;
  for (i = 0; i < serverCompleted.length; i++) {
    completedSet[String(serverCompleted[i])] = true;
  }

  var guest = loadGuest();
  if (!loggedIn) {
    Object.keys(guest.done).forEach(function (k) {
      if (guest.done[k]) completedSet[k] = true;
    });
  }

  var total = exercises.length;
  var step = 0;
  var bar = document.getElementById("lessonProgressBar");

  function updateBar() {
    if (!bar || total === 0) return;
    var doneCount = 0;
    for (i = 0; i < exercises.length; i++) {
      if (completedSet[String(exercises[i].id)]) doneCount++;
    }
    var pct = Math.round((doneCount / total) * 100);
    bar.style.width = pct + "%";
  }

  function markDone(id) {
    completedSet[String(id)] = true;
    updateBar();
  }

  function postComplete(exerciseId, cb) {
    fetch("/api/exercise/" + exerciseId + "/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok) cb(null, data);
        else cb(new Error("fail"));
      })
      .catch(function () {
        cb(new Error("network"));
      });
  }

  function postWriting(exerciseId, text, cb) {
    fetch("/api/exercise/" + exerciseId + "/writing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        cb(null, data);
      })
      .catch(function () {
        cb(new Error("network"));
      });
  }

  function speakWord(word, lang) {
    if (!window.speechSynthesis) return;
    var u = new SpeechSynthesisUtterance(word);
    u.lang = lang || "en-US";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  }

  function renderCurrent() {
    root.innerHTML = "";
    if (total === 0) {
      root.innerHTML = '<p class="muted">Задания для этого урока ещё готовятся.</p>';
      return;
    }
    if (step >= total) {
      finalizeLessonIfGuest();
      var wrap = document.createElement("div");
      wrap.className = "lesson-done card duo-card";
      var h = document.createElement("h2");
      h.textContent = "Урок пройден!";
      wrap.appendChild(h);
      var p = document.createElement("p");
      p.textContent = "Отличная работа. Выберите следующий урок в боковой панели.";
      wrap.appendChild(p);
      var back = document.querySelector(".lesson-top .eyebrow a");
      var a = document.createElement("a");
      a.className = "btn btn-primary";
      a.href = back ? back.getAttribute("href") : "/learn";
      a.textContent = "К уровню";
      wrap.appendChild(a);
      root.appendChild(wrap);
      return;
    }

    var ex = exercises[step];
    var idStr = String(ex.id);
    var already = !!completedSet[idStr];

    var card = document.createElement("div");
    card.className = "exercise-card card duo-card";
    card.setAttribute("data-ex-id", idStr);

    var head = document.createElement("div");
    head.className = "exercise-head";
    head.innerHTML =
      '<span class="exercise-kind">' +
      kindLabel(ex.kind) +
      "</span>" +
      '<span class="exercise-step">Задание ' +
      (step + 1) +
      " из " +
      total +
      "</span>";
    card.appendChild(head);

    var prompt = document.createElement("div");
    prompt.className = "exercise-prompt";
    prompt.textContent = ex.prompt;
    card.appendChild(prompt);

    var body = document.createElement("div");
    body.className = "exercise-body";
    card.appendChild(body);

    var feedback = document.createElement("div");
    feedback.className = "exercise-feedback";
    feedback.hidden = true;
    card.appendChild(feedback);

    var nav = document.createElement("div");
    nav.className = "exercise-nav";

    function showFeedback(ok, text) {
      feedback.hidden = false;
      feedback.className = "exercise-feedback " + (ok ? "is-ok" : "is-bad");
      feedback.textContent = text;
    }

    function goNext() {
      step++;
      renderCurrent();
    }

    function finishExercise() {
      if (already) {
        goNext();
        return;
      }
      function afterSave() {
        markDone(ex.id);
        showFeedback(true, "Готово! +10 XP");
        nav.innerHTML = "";
        var nextBtn = document.createElement("button");
        nextBtn.type = "button";
        nextBtn.className = "btn btn-primary";
        nextBtn.textContent = step + 1 >= total ? "Готово" : "Дальше";
        nextBtn.addEventListener("click", function () {
          if (step + 1 >= total && !loggedIn) finalizeLessonIfGuest();
          goNext();
        });
        nav.appendChild(nextBtn);
        if (step + 1 >= total && !loggedIn) finalizeLessonIfGuest();
      }

      if (loggedIn) {
        postComplete(ex.id, function (err) {
          if (err) {
            showFeedback(false, "Не удалось сохранить. Проверьте соединение.");
            return;
          }
          afterSave();
        });
      } else {
        saveGuestDone(ex.id, 10);
        afterSave();
      }
    }

    if (already) {
      showFeedback(true, "Уже выполнено ранее.");
      var skip = document.createElement("button");
      skip.type = "button";
      skip.className = "btn btn-primary";
      skip.textContent = "Дальше";
      skip.addEventListener("click", goNext);
      nav.appendChild(skip);
      card.appendChild(nav);
      root.appendChild(card);
      updateBar();
      return;
    }

    var p = ex.payload || {};

    if (
      ex.kind === "words" ||
      ex.kind === "phrases" ||
      ex.kind === "translate" ||
      ex.kind === "reading_comp"
    ) {
      var opts = p.options || [];
      var correct = p.correct_index;
      var grid = document.createElement("div");
      grid.className = "opt-grid";
      opts.forEach(function (label, idx) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "opt-btn";
        b.textContent = label;
        b.addEventListener("click", function () {
          if (b.disabled) return;
          var ok = idx === correct;
          Array.prototype.forEach.call(grid.querySelectorAll(".opt-btn"), function (x) {
            x.disabled = true;
          });
          if (ok) {
            b.classList.add("is-correct");
            finishExercise();
          } else {
            b.classList.add("is-wrong");
            showFeedback(false, "Попробуйте другой вариант.");
            setTimeout(function () {
              Array.prototype.forEach.call(grid.querySelectorAll(".opt-btn"), function (x) {
                x.disabled = false;
                x.classList.remove("is-wrong");
              });
              feedback.hidden = true;
            }, 900);
          }
        });
        grid.appendChild(b);
      });
      body.appendChild(grid);
    } else if (ex.kind === "reorder") {
      var tokens = (p.tokens || []).slice();
      var target = tokens.slice();
      var pool = shuffle(tokens);
      var answer = [];

      var area = document.createElement("div");
      area.className = "reorder-area";
      var poolEl = document.createElement("div");
      poolEl.className = "reorder-pool";
      var ansEl = document.createElement("div");
      ansEl.className = "reorder-answer";
      var hint = document.createElement("p");
      hint.className = "muted small";
      hint.textContent = "Нажимайте слова по порядку. Нажатие в ответе возвращает слово.";

      function renderPool() {
        poolEl.innerHTML = "";
        pool.forEach(function (tok, pi) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "token-btn";
          b.textContent = tok;
          b.addEventListener("click", function () {
            var ix = pool.indexOf(tok);
            if (ix < 0) return;
            var t = pool.splice(ix, 1)[0];
            answer.push(t);
            renderPool();
            renderAnswer();
          });
          poolEl.appendChild(b);
        });
      }

      function renderAnswer() {
        ansEl.innerHTML = "";
        answer.forEach(function (tok, ai) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "token-btn token-in-answer";
          b.textContent = tok;
          b.addEventListener("click", function () {
            var t = answer.splice(ai, 1)[0];
            pool.push(t);
            renderPool();
            renderAnswer();
          });
          ansEl.appendChild(b);
        });
      }

      area.appendChild(hint);
      area.appendChild(document.createElement("p")).textContent = "Соберите фразу:";
      area.appendChild(ansEl);
      area.appendChild(poolEl);

      var checkBtn = document.createElement("button");
      checkBtn.type = "button";
      checkBtn.className = "btn btn-primary";
      checkBtn.textContent = "Проверить";
      checkBtn.addEventListener("click", function () {
        var ok =
          answer.length === target.length &&
          answer.every(function (t, i) {
            return t === target[i];
          });
        if (ok) finishExercise();
        else showFeedback(false, "Порядок пока неверный.");
      });

      var clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "btn btn-ghost";
      clearBtn.textContent = "Сбросить";
      clearBtn.addEventListener("click", function () {
        pool = pool.concat(answer);
        answer = [];
        pool = shuffle(pool);
        renderPool();
        renderAnswer();
        feedback.hidden = true;
      });

      renderPool();
      renderAnswer();
      body.appendChild(area);
      var row = document.createElement("div");
      row.className = "reorder-actions";
      row.appendChild(clearBtn);
      row.appendChild(checkBtn);
      body.appendChild(row);
    } else if (ex.kind === "listening") {
      var w = (p.word || "hello").trim();
      var lang = p.language || "en-US";
      var play = document.createElement("button");
      play.type = "button";
      play.className = "btn btn-secondary";
      play.textContent = "Прослушать";
      play.addEventListener("click", function () {
        speakWord(w, lang);
      });
      var inp = document.createElement("input");
      inp.type = "text";
      inp.className = "listening-input";
      inp.placeholder = "Введите слово на английском";
      var checkL = document.createElement("button");
      checkL.type = "button";
      checkL.className = "btn btn-primary";
      checkL.textContent = "Проверить";
      checkL.addEventListener("click", function () {
        var v = (inp.value || "").trim().toLowerCase();
        if (v === w.toLowerCase()) finishExercise();
        else showFeedback(false, "Почти. Прослушайте ещё раз и проверьте написание.");
      });
      body.appendChild(play);
      body.appendChild(inp);
      body.appendChild(checkL);
    } else if (ex.kind === "writing") {
      var ta = document.createElement("textarea");
      ta.className = "writing-area";
      ta.rows = 8;
      ta.placeholder = "Напишите ответ на английском здесь…";
      var sub = document.createElement("button");
      sub.type = "button";
      sub.className = "btn btn-primary";
      sub.textContent = "Отправить на проверку";
      sub.addEventListener("click", function () {
        var text = ta.value || "";
        if (loggedIn) {
          postWriting(ex.id, text, function (err, data) {
            if (err || !data) {
              showFeedback(false, "Ошибка сети.");
              return;
            }
            if (data.passed) {
              markDone(ex.id);
              showFeedback(true, "Зачтено! Оценка: " + (data.score || 0) + "/100. +10 XP");
              nav.innerHTML = "";
              var nb = document.createElement("button");
              nb.type = "button";
              nb.className = "btn btn-primary";
              nb.textContent = step + 1 >= total ? "Готово" : "Дальше";
              nb.addEventListener("click", function () {
                if (step + 1 >= total && !loggedIn) finalizeLessonIfGuest();
                goNext();
              });
              nav.appendChild(nb);
              if (step + 1 >= total && !loggedIn) finalizeLessonIfGuest();
            } else {
              showFeedback(false, "Нужно развить ответ: длина и ключевые слова. Баллы: " + (data.score || 0) + "/100. Порог 50.");
            }
          });
        } else {
          var sc = scoreWritingClient(text, p);
          if (sc >= 50) {
            saveGuestDone(ex.id, 10);
            markDone(ex.id);
            showFeedback(true, "Зачтено локально: " + sc + "/100. +10 XP");
            nav.innerHTML = "";
            var nb2 = document.createElement("button");
            nb2.type = "button";
            nb2.className = "btn btn-primary";
            nb2.textContent = step + 1 >= total ? "Готово" : "Дальше";
            nb2.addEventListener("click", function () {
              if (step + 1 >= total) finalizeLessonIfGuest();
              goNext();
            });
            nav.appendChild(nb2);
            if (step + 1 >= total) finalizeLessonIfGuest();
          } else {
            showFeedback(false, "Добавьте объём и ключевые слова из задания. Сейчас: " + sc + "/100.");
          }
        }
      });
      body.appendChild(ta);
      body.appendChild(sub);
    }

    card.appendChild(nav);
    root.appendChild(card);
    updateBar();
  }

  renderCurrent();
})();
