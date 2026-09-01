/* Local-only Dictionary Repair Desk. Served dynamically by repair_desk.py. */
(function () {
  'use strict';

  var cfg = window.DICTIONARY_REPAIR_DESK_CONFIG || {};
  if (!cfg.token || ['127.0.0.1', 'localhost', '::1'].indexOf(location.hostname) < 0) return;

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c];
    });
  }

  function changedMarkup(before, after, tag) {
    if (before === after) return esc(before);
    var start = 0;
    while (start < before.length && start < after.length && before[start] === after[start]) start++;
    var endBefore = before.length;
    var endAfter = after.length;
    while (endBefore > start && endAfter > start &&
           before[endBefore - 1] === after[endAfter - 1]) {
      endBefore--; endAfter--;
    }
    return esc(before.slice(0, start)) + '<' + tag + '>' +
      esc((tag === 'del' ? before.slice(start, endBefore) : after.slice(start, endAfter)) || '∅') +
      '</' + tag + '>' + esc(before.slice(endBefore));
  }

  function request(path, options) {
    options = options || {};
    options.headers = Object.assign({'X-Repair-Desk-Token': cfg.token}, options.headers || {});
    return fetch(path, options).then(function (response) {
      return response.json().then(function (payload) {
        if (!response.ok) throw new Error(payload.error || ('Request failed: ' + response.status));
        return payload;
      });
    });
  }

  var style = document.createElement('style');
  style.textContent = [
    '.repair-queue{font:600 .7rem system-ui,sans-serif;color:#e8d4a8;background:#211a0d;border:1px solid #6c511d;border-radius:.35rem;padding:.25rem .5rem;cursor:pointer}',
    '.repair-queue:hover,.repair-queue:focus-visible{color:#0a0a0a;background:#c9952a;outline:none}',
    '.line .repair-queue{grid-column:2;justify-self:start;margin:.25rem 0 .1rem}',
    '.formlist li .repair-queue{margin:.25rem .3rem .25rem 0;white-space:nowrap}',
    '.repair-dialog{width:min(900px,calc(100vw - 2rem));max-height:calc(100vh - 2rem);overflow:auto;color:#f2efe9;background:#101010;border:1px solid #6c511d;border-radius:.7rem;padding:0;box-shadow:0 1.5rem 5rem #000}',
    '.repair-dialog::backdrop{background:rgba(0,0,0,.75)}',
    '.repair-head,.repair-body{padding:1rem 1.2rem}.repair-head{display:flex;justify-content:space-between;gap:1rem;border-bottom:1px solid #262626}',
    '.repair-head h2{margin:0;font-size:.85rem}.repair-close{background:none;color:#9a948a;border:0;font-size:1.5rem;cursor:pointer}',
    '.repair-meta{font: .8rem system-ui,sans-serif;color:#9a948a}.repair-related{font:.78rem system-ui,sans-serif;color:#9a948a;margin:.45rem 0 1rem}',
    '.repair-diff{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:.8rem 0}.repair-card{background:#171717;border:1px solid #262626;border-radius:.45rem;padding:.7rem;min-width:0}',
    '.repair-card h3{font:.7rem system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;color:#c9952a;margin:0 0 .35rem}',
    '.repair-card code,.repair-card .mk{display:block;overflow-wrap:anywhere;white-space:pre-wrap}.repair-card del{background:#51262b;color:#ffd7db}.repair-card ins{background:#23412a;color:#d8ffe0;text-decoration:none}',
    '.repair-field{display:block;font:.75rem system-ui,sans-serif;color:#9a948a;margin:.75rem 0 .2rem}.repair-dialog textarea,.repair-dialog input{width:100%;color:#f2efe9;background:#141414;border:1px solid #3a3a3a;border-radius:.4rem;padding:.55rem;font:inherit}',
    '.repair-dialog textarea{min-height:4.5rem;resize:vertical}.repair-actions{display:flex;align-items:center;gap:.7rem;margin-top:1rem;flex-wrap:wrap}',
    '.repair-create{font:600 .8rem system-ui,sans-serif;color:#0a0a0a;background:#c9952a;border:0;border-radius:.4rem;padding:.55rem .8rem;cursor:pointer}.repair-create:disabled{opacity:.45;cursor:not-allowed}',
    '.repair-status{font:.78rem system-ui,sans-serif;color:#9a948a}.repair-status.error{color:#e0a8a8}.repair-status a{color:#e8d4a8}',
    '@media(max-width:650px){.repair-diff{grid-template-columns:1fr}}'
  ].join('');
  document.head.appendChild(style);

  var dialog = document.createElement('dialog');
  dialog.className = 'repair-dialog';
  dialog.innerHTML = '<div class="repair-head"><h2>Dictionary Repair Desk</h2>' +
    '<button class="repair-close" type="button" aria-label="Close">×</button></div>' +
    '<div class="repair-body"><p class="repair-meta"></p><p class="repair-related"></p>' +
    '<div class="repair-diff"><section class="repair-card repair-before"><h3>Before — current source</h3>' +
    '<code></code><span class="mk"></span></section><section class="repair-card repair-after">' +
    '<h3>After — proposed correction</h3><code></code><span class="mk"></span></section></div>' +
    '<label class="repair-field" for="repair-ascii">Proposed miluk_ascii</label>' +
    '<textarea id="repair-ascii" spellcheck="false"></textarea>' +
    '<label class="repair-field" for="repair-summary">Summary</label>' +
    '<input id="repair-summary" type="text" maxlength="300">' +
    '<label class="repair-field" for="repair-notes">Reviewer notes (optional)</label>' +
    '<textarea id="repair-notes" maxlength="8000"></textarea>' +
    '<div class="repair-actions"><button type="button" class="repair-create">Create GitHub Issue</button>' +
    '<span class="repair-status" role="status" aria-live="polite"></span></div></div>';
  document.body.appendChild(dialog);

  var currentContext = null;
  var currentRequest = null;
  var currentRendered = '';
  var previewSequence = 0;
  var asciiInput = dialog.querySelector('#repair-ascii');
  var summaryInput = dialog.querySelector('#repair-summary');
  var notesInput = dialog.querySelector('#repair-notes');
  var createButton = dialog.querySelector('.repair-create');
  var status = dialog.querySelector('.repair-status');

  dialog.querySelector('.repair-close').addEventListener('click', function () { dialog.close(); });

  function updateDiff() {
    if (!currentContext) return;
    var beforeAscii = currentContext.current.miluk_ascii;
    var afterAscii = asciiInput.value;
    var beforeMiluk = currentContext.current.miluk;
    var afterMiluk = currentRendered;
    dialog.querySelector('.repair-before code').innerHTML = changedMarkup(beforeAscii, afterAscii, 'del');
    dialog.querySelector('.repair-after code').innerHTML = changedMarkup(beforeAscii, afterAscii, 'ins');
    dialog.querySelector('.repair-before .mk').innerHTML = changedMarkup(beforeMiluk, afterMiluk, 'del');
    dialog.querySelector('.repair-after .mk').innerHTML = changedMarkup(beforeMiluk, afterMiluk, 'ins');
    createButton.disabled = !afterAscii.trim() || afterAscii.trim() === beforeAscii;
  }

  function preview() {
    var sequence = ++previewSequence;
    return request('/__repair/preview', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(Object.assign({}, currentRequest, {proposed_ascii: asciiInput.value}))
    }).then(function (payload) {
      if (sequence !== previewSequence) return;
      currentRendered = payload.miluk;
      updateDiff();
    }).catch(function (error) {
      status.textContent = error.message; status.className = 'repair-status error';
    });
  }

  var previewTimer = null;
  asciiInput.addEventListener('input', function () {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(preview, 180);
  });

  function openDesk(source) {
    previewSequence++;
    currentContext = null;
    currentRequest = source;
    createButton.disabled = true;
    status.textContent = 'Loading source context…'; status.className = 'repair-status';
    var query = new URLSearchParams(source).toString();
    request('/__repair/context?' + query).then(function (context) {
      currentContext = context;
      currentRendered = context.proposed.miluk;
      dialog.querySelector('.repair-meta').textContent = context.story.title + ' · ' +
        context.story.story_id + ' · line ' + context.story.line;
      dialog.querySelector('.repair-related').textContent = context.related_dictionary.length ?
        'Related: ' + context.related_dictionary.map(function (entry) {
          var text = entry.entry_id + ' · ' + entry.headword;
          if (entry.selected_form) text += ' · source form ' + entry.selected_form.form;
          return text;
        }).join('; ') : 'No related dictionary entry is currently linked.';
      asciiInput.value = context.proposed.miluk_ascii;
      summaryInput.value = context.proposed.summary;
      notesInput.value = '';
      status.textContent = 'Review the before/after diff. No issue exists yet.';
      status.className = 'repair-status';
      updateDiff();
      if (!dialog.open) dialog.showModal();
    }).catch(function (error) {
      status.textContent = error.message; status.className = 'repair-status error';
      if (!dialog.open) dialog.showModal();
    });
  }

  createButton.addEventListener('click', function () {
    if (!currentContext || createButton.disabled) return;
    createButton.disabled = true;
    status.textContent = 'Creating GitHub Issue through the local gh CLI…';
    status.className = 'repair-status';
    request('/__repair/issues', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(Object.assign({}, currentRequest, {
        proposed_ascii: asciiInput.value,
        summary: summaryInput.value,
        notes: notesInput.value
      }))
    }).then(function (payload) {
      status.innerHTML = 'Issue created: <a target="_blank" rel="noopener" href="' +
        esc(payload.issue_url) + '">' + esc(payload.issue_url) + '</a>';
    }).catch(function (error) {
      createButton.disabled = false;
      status.textContent = error.message; status.className = 'repair-status error';
    });
  });

  var storyMatch = location.pathname.match(/\/dictionary\/stories\/([^/]+)\.html$/);
  if (storyMatch) {
    document.querySelectorAll('#story .line').forEach(function (line) {
      var number = Number(line.id.slice(1));
      var button = document.createElement('button');
      button.type = 'button'; button.className = 'repair-queue'; button.textContent = 'Queue correction';
      button.addEventListener('click', function () {
        openDesk({story_id: storyMatch[1], line: number});
      });
      line.appendChild(button);
    });
  }

  var entryMatch = location.pathname.match(/\/dictionary\/words\/([^/]+)\.html$/);
  if (entryMatch) {
    var formItems = Array.prototype.slice.call(document.querySelectorAll('.formlist > li'));
    formItems.forEach(function (item, formIndex) {
      var link = item.querySelector('a.formlink');
      if (!link) return;
      var target = new URL(link.href);
      var sourceMatch = target.pathname.match(/\/dictionary\/stories\/([^/]+)\.html$/);
      var lineMatch = target.hash.match(/^#l(\d+)$/);
      if (!sourceMatch || !lineMatch) return;
      var button = document.createElement('button');
      button.type = 'button'; button.className = 'repair-queue'; button.textContent = 'Queue correction';
      button.addEventListener('click', function () {
        openDesk({story_id: sourceMatch[1], line: Number(lineMatch[1]),
                  entry_id: entryMatch[1], form_index: formIndex});
      });
      item.appendChild(button);
    });
  }
})();
