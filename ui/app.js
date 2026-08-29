/**
 * MedAssist clinical console.
 *
 * Each agent takes different inputs, so the form is generated from a spec
 * rather than hand-written per agent: adding an agent is one entry here.
 */
(function () {
  'use strict';

  var config = {
    apiUrl: window.MEDASSIST_API_URL || '',
    environment: window.MEDASSIST_ENV || 'dev'
  };

  var AGENTS = {
    triage: {
      title: 'Triage',
      blurb: 'Assess urgency and surface red flags from a presenting complaint.',
      fields: [
        { name: 'complaint', label: 'Presenting complaint', type: 'textarea', required: true },
        { name: 'vitals', label: 'Vitals (JSON, optional)', type: 'textarea', json: true }
      ],
      example: {
        complaint: '58-year-old male, crushing substernal chest pain for 40 minutes, radiating to left arm, diaphoretic',
        vitals: '{"BP": "158/96", "HR": 112, "SpO2": "94% RA"}'
      }
    },
    historian: {
      title: 'Historian',
      blurb: 'Summarise prior chart history relevant to the current presentation.',
      fields: [
        { name: 'presentation', label: 'Current presentation', type: 'textarea', required: true },
        { name: 'chart_excerpts', label: 'Prior records (one per line)', type: 'textarea', lines: true }
      ],
      example: {
        presentation: 'Recurrent exertional chest pain',
        chart_excerpts: '2024: MI, stented LAD. On aspirin and atorvastatin.\n2025: HbA1c 7.8. Metformin started.'
      }
    },
    scribe: {
      title: 'Scribe',
      blurb: 'Draft a SOAP visit note from an encounter transcript.',
      fields: [
        { name: 'transcript', label: 'Encounter transcript', type: 'textarea', required: true }
      ],
      example: {
        transcript: 'Follow-up visit. BP 128/80. Reports good adherence, no side effects. Continue current medications, recheck in 3 months.'
      }
    },
    priorauth: {
      title: 'Prior Authorisation',
      blurb: 'Draft a payer justification grounded in the clinical record.',
      fields: [
        { name: 'service', label: 'Requested service', type: 'input', required: true },
        { name: 'clinical_record', label: 'Clinical record', type: 'textarea', required: true }
      ],
      example: {
        service: 'MRI lumbar spine without contrast',
        clinical_record: '6 weeks of low back pain, failed physiotherapy and NSAIDs, new left foot drop on examination.'
      }
    },
    assist: {
      title: 'Auto-route',
      blurb: 'The orchestrator picks the right specialist and runs it.',
      fields: [
        { name: 'request', label: 'Request', type: 'textarea', required: true },
        { name: 'transcript', label: 'Supporting detail (optional)', type: 'textarea' }
      ],
      example: {
        request: 'Draft a visit note from this encounter',
        transcript: 'Patient reports 3 days of productive cough, low-grade fever 38.1C, no chest pain. Lungs: scattered rhonchi. Started amoxicillin today, review in 1 week.'
      }
    }
  };

  var current = 'triage';

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s).replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    });
  }

  function toast(msg, kind) {
    var t = $('toast');
    t.textContent = msg;
    t.className = 'toast show ' + (kind || 'error');
    setTimeout(function () { t.className = 'toast'; }, 3500);
  }

  function renderForm() {
    var spec = AGENTS[current];
    var html = '<div class="agent-head"><h2>' + spec.title + '</h2><p>' + spec.blurb + '</p></div>';

    spec.fields.forEach(function (f) {
      var req = f.required ? ' <span class="req">required</span>' : '';
      var el = f.type === 'input'
        ? '<input id="f-' + f.name + '" type="text">'
        : '<textarea id="f-' + f.name + '" rows="' + (f.lines ? 5 : 4) + '"></textarea>';
      html += '<label for="f-' + f.name + '">' + f.label + req + '</label>' + el;
    });

    $('fields').innerHTML = html;

    $('examples').innerHTML = '<button type="button" class="example-btn" id="load-example">Load example case</button>';
    $('load-example').addEventListener('click', function () {
      Object.keys(spec.example).forEach(function (k) {
        var el = $('f-' + k);
        if (el) el.value = spec.example[k];
      });
    });
  }

  function collect() {
    var spec = AGENTS[current];
    var body = {};

    for (var i = 0; i < spec.fields.length; i++) {
      var f = spec.fields[i];
      var el = $('f-' + f.name);
      if (!el) continue;

      var raw = el.value.trim();
      if (!raw) {
        if (f.required) throw new Error(f.label + ' is required');
        continue;
      }

      if (f.json) {
        try {
          body[f.name] = JSON.parse(raw);
        } catch (e) {
          throw new Error(f.label + ' must be valid JSON');
        }
      } else if (f.lines) {
        body[f.name] = raw.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
      } else {
        body[f.name] = raw;
      }
    }
    return body;
  }

  // Render the agent's JSON as readable sections rather than a code dump,
  // while keeping the raw payload available for inspection.
  var TEXT_KEYS = ['rationale', 'recommended_next_step', 'routing_reason',
                   'subjective', 'objective', 'assessment', 'plan',
                   'requested_service', 'draft_letter'];

  var LIST_KEYS = ['red_flags', 'missing_information', 'relevant_history',
                   'active_medications', 'allergies', 'prior_episodes', 'gaps',
                   'clarifications_needed', 'medical_necessity',
                   'supporting_evidence', 'missing_documentation'];

  function renderResult(data, ms) {
    var result = (data && data.result) || data || {};
    var payload = result.output || result;
    var html = '<div class="result-meta">' + ms + ' ms</div>';

    if (payload.acuity) {
      var cls = String(payload.acuity).replace(/_/g, '-');
      html += '<div class="acuity acuity-' + cls + '">' +
              esc(String(payload.acuity).replace(/_/g, ' ')) + '</div>';
    }
    if (result.routed_to) {
      html += '<div class="routed">routed to <strong>' + esc(result.routed_to) + '</strong></div>';
    }

    TEXT_KEYS.forEach(function (key) {
      if (typeof payload[key] === 'string' && payload[key]) {
        html += '<section><h4>' + key.replace(/_/g, ' ') + '</h4><p>' + esc(payload[key]) + '</p></section>';
      }
    });

    LIST_KEYS.forEach(function (key) {
      var v = payload[key];
      if (Array.isArray(v) && v.length) {
        html += '<section><h4>' + key.replace(/_/g, ' ') + '</h4><ul>';
        v.forEach(function (x) {
          html += '<li>' + esc(typeof x === 'string' ? x : JSON.stringify(x)) + '</li>';
        });
        html += '</ul></section>';
      }
    });

    if (payload.disclaimer) {
      html += '<div class="disclaimer">' + esc(payload.disclaimer) + '</div>';
    }

    html += '<details class="raw"><summary>Raw response</summary><pre>' +
            esc(JSON.stringify(data, null, 2)) + '</pre></details>';

    $('output').innerHTML = html;
  }

  function submit(ev) {
    ev.preventDefault();

    if (!config.apiUrl) {
      toast('API URL not configured');
      return;
    }

    var body;
    try {
      body = collect();
    } catch (e) {
      toast(e.message);
      return;
    }

    var btn = $('run-btn');
    btn.disabled = true;
    btn.textContent = 'Running...';
    var started = performance.now();

    fetch(config.apiUrl + '/v1/' + current, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (r) {
        var ms = Math.round(performance.now() - started);
        if (!r.ok) throw new Error(r.data.message || ('HTTP ' + r.status));
        $('latency').textContent = ms + ' ms';
        renderResult(r.data, ms);
      })
      .catch(function (e) {
        toast(e.message);
        $('output').innerHTML = '<div class="empty"><h3>Request failed</h3><p>' +
                                esc(e.message) + '</p></div>';
      })
      .then(function () {
        btn.disabled = false;
        btn.textContent = 'Run';
      });
  }

  var buttons = document.querySelectorAll('.agent-btn');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', function (ev) {
      for (var j = 0; j < buttons.length; j++) buttons[j].classList.remove('active');
      ev.currentTarget.classList.add('active');
      current = ev.currentTarget.getAttribute('data-agent');
      renderForm();
      $('output').innerHTML = '<div class="empty"><h3>' + AGENTS[current].title +
        '</h3><p>' + AGENTS[current].blurb + '</p></div>';
    });
  }

  $('agent-form').addEventListener('submit', submit);
  $('env-badge').textContent = config.environment;
  renderForm();
})();
