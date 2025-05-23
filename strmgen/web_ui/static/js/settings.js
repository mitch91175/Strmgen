const API_BASE = "/api/v1/settings";
const boolFields = [
  'skip_stream_check', 'only_updated_streams', 'update_stream_link',
  'clean_output_dir', 'process_movies_groups', 'process_tv_series_groups',
  'process_groups_24_7', 'tmdb_download_images', 'tmdb_create_not_found',
  'check_tmdb_thresholds', 'write_nfo', 'write_nfo_only_if_not_exists',
  'update_tv_series_nfo', 'opensubtitles_download', 'enable_scheduled_task'
];

const numberFields = [
  'last_modified_days', 'batch_size', 'batch_delay_seconds',
  'concurrent_requests', 'tmdb_rate_limit', 'minimum_year',
  'minimum_tmdb_rating', 'minimum_tmdb_votes',
  'minimum_tmdb_popularity', 'scheduled_hour', 'scheduled_minute'
];

const arrayFields = [
  'movies_groups_raw', 'tv_series_groups_raw',
  'groups_24_7_raw', 'remove_strings_raw'
];

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function showMessage(msg, success = true) {
  const box = document.createElement('div');
  box.textContent = msg;
  box.className = success ? 'msg-success' : 'msg-error';
  box.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; padding: 10px;
    background: ${success ? '#4CAF50' : '#f44336'}; color: white;
    text-align: center; z-index: 1000; font-weight: bold;
  `;
  document.body.prepend(box);
  setTimeout(() => box.remove(), 4000);
}

async function fetchSettingsFromApi() {
  const res = await fetch(API_BASE);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function populateForm(cfg) {
  [
    'api_base', 'token_url', 'access', 'refresh', 'username', 'password',
    'stream_base_url', 'output_root', 'movie_year_regex', 'tv_series_episode_regex',
    'tmdb_api_key', 'tmdb_language', 'tmdb_image_size',
    'opensubtitles_app_name', 'opensubtitles_api_key',
    'opensubtitles_username', 'opensubtitles_password',
    'emby_api_url', 'emby_api_key', 'emby_movie_library_id'
  ].forEach(id => setVal(id, cfg[id] ?? ''));

  numberFields.forEach(id => setVal(id, cfg[id]));

  arrayFields.forEach(id => {
    const val = (cfg[id.replace('_raw', '')] || []).join(',');
    setVal(id, val);
  });

  boolFields.forEach(name => {
    const cb = document.querySelector(`input[type="checkbox"][name="${name}"]`);
    if (cb) cb.checked = !!cfg[name];
  });
}

async function loadSettings() {
  try {
    if (!API_BASE) throw new Error('API base not found');
    const cached = sessionStorage.getItem('settings');
    const cfg = cached ? JSON.parse(cached) : await fetchSettingsFromApi();

    if (!cached) sessionStorage.setItem('settings', JSON.stringify(cfg));
    populateForm(cfg);
  } catch (err) {
    console.error('Failed to load settings:', err);
    showMessage('Could not load settings', false);
  }
}

function lazyLoadSettings() {
  if ('requestIdleCallback' in window) {
    requestIdleCallback(loadSettings);
  } else {
    setTimeout(loadSettings, 0);
  }
}

window.initSettingsPage = function () {
  const form = document.getElementById('settingsForm');
  const submitButton = form?.querySelector('button[type="submit"]');
  if (!form) return;

  lazyLoadSettings();

  // Rebind collapsible logic
  document.querySelectorAll('.collapsible-header').forEach(header => {
    header.addEventListener('click', () => {
      const group = header.closest('.settings-group');
      group?.classList.toggle('collapsed');
    });
  });

  // Rebind show/hide password
  document.querySelectorAll('.toggle-password').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.target);
      if (input) {
        const isHidden = input.type === 'password';
        input.type = isHidden ? 'text' : 'password';
        btn.textContent = isHidden ? 'Hide' : 'Show';
      }
    });
  });

  // Rebind submit handler
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const payload = {};

    boolFields.forEach(name => {
      const cb = form.querySelector(`input[type="checkbox"][name="${name}"]`);
      payload[name] = cb ? cb.checked : false;
    });

    const data = new FormData(form);
    for (let [key, value] of data.entries()) {
      if (boolFields.includes(key)) continue;

      if (arrayFields.includes(key)) {
        const realKey = key.replace('_raw', '');
        payload[realKey] = value.split(',').map(s => s.trim()).filter(Boolean);
      } else if (numberFields.includes(key)) {
        const number = Number(value);
        if (isNaN(number)) {
          showMessage(`Invalid number for ${key}`, false);
          return;
        }
        payload[key] = number;
      } else {
        payload[key] = value;
      }
    }

    try {
      if (submitButton) submitButton.disabled = true;

      const res = await fetch(API_BASE, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error(await res.text());
      sessionStorage.setItem('settings', JSON.stringify(payload));
      showMessage('Settings saved successfully');
    } catch (err) {
      console.error('Save failed:', err);
      showMessage('Failed to save settings', false);
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  }, { once: true }); // prevent reattaching
};

// Auto-init only on first load (full page load case)
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('settingsForm')) {
    window.initSettingsPage();
  }
});


async function syncGroupSelectors() {
  const movieInput = document.getElementById('movies_groups_raw');
  const tvInput = document.getElementById('tv_series_groups_raw');
  const process247Input = document.getElementById('groups_24_7_raw');
  const movieSelect = document.getElementById('movie_groups_select');
  const tvSelect = document.getElementById('tv_series_groups_select');
  const process247Select = document.getElementById('process_247_groups_select');

  try {
    const res = await fetch('/api/v1/streams/stream-groups');
    if (!res.ok) throw new Error('Failed to fetch stream groups');
    const groups = await res.json();

    // Clear existing options
    movieSelect.innerHTML = '';
    tvSelect.innerHTML = '';

    for (const g of groups) {
      const opt1 = new Option(g, g);
      const opt2 = new Option(g, g);
      const opt3 = new Option(g, g);
      movieSelect.appendChild(opt1);
      tvSelect.appendChild(opt2);
      process247Select.appendChild(opt3);
    }

    // Initialize Choices.js
    const movieChoices = new Choices(movieSelect, {
      removeItemButton: true,
      searchEnabled: true,
      placeholder: true,
      placeholderValue: 'Select movie groups'
    });

    let lastSelectedMovie = null;
    let lastSelectedTV = null;   
    let lastSelected247 = null;   

    // Add theme-aware class manually afterward
    movieChoices.containerOuter.element.classList.add('theme-aware');

    movieChoices.passedElement.element.addEventListener('change', () => {
      const selected = movieChoices.getValue(true);
      lastSelectedMovie = Array.isArray(selected)
        ? selected[selected.length - 1] || null
        : selected;

      setTimeout(() => {
        const container = movieChoices.dropdown.element;
        const item = Array.from(container.querySelectorAll('.choices__item--selectable'))
          .find(el => el.innerText.trim() === lastSelectedMovie);
        if (item) item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }, 50);
    });

    const tvChoices = new Choices(tvSelect, {
      removeItemButton: true,
      searchEnabled: true,
      placeholder: true,
      placeholderValue: 'Select TV groups'
    });
    tvChoices.containerOuter.element.classList.add('theme-aware');

    tvChoices.passedElement.element.addEventListener('change', () => {
      const selected = tvChoices.getValue(true);
      lastSelectedTV = Array.isArray(selected)
        ? selected[selected.length - 1] || null
        : selected;

      setTimeout(() => {
        const container = tvChoices.dropdown.element;
        const item = Array.from(container.querySelectorAll('.choices__item--selectable'))
          .find(el => el.innerText.trim() === lastSelectedTV);
        if (item) item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }, 50);
    });

    //24/7

    const process247Choices = new Choices(process247Select, {
      removeItemButton: true,
      searchEnabled: true,
      placeholder: true,
      placeholderValue: 'Select 24/7 groups'
    });
    process247Choices.containerOuter.element.classList.add('theme-aware');

    process247Choices.passedElement.element.addEventListener('change', () => {
      const selected = process247Choices.getValue(true);
      lastSelected247 = Array.isArray(selected)
        ? selected[selected.length - 1] || null
        : selected;

      setTimeout(() => {
        const container = process247Choices.dropdown.element;
        const item = Array.from(container.querySelectorAll('.choices__item--selectable'))
          .find(el => el.innerText.trim() === lastSelected247);
        if (item) item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }, 50);
    });    


    // Pre-select items from raw input
    const initChoices = (choicesInstance, input) => {
      const initial = input.value.split(',').map(s => s.trim()).filter(Boolean);
      choicesInstance.setChoiceByValue(initial);
      choicesInstance.passedElement.element.addEventListener('change', () => {
        const selected = Array.from(choicesInstance.passedElement.element.selectedOptions).map(o => o.value);
        input.value = selected.join(', ');
      });
    };

    initChoices(movieChoices, movieInput);
    initChoices(tvChoices, tvInput);
    initChoices(process247Choices, process247Input);


  } catch (err) {
    console.error('Error syncing group selectors:', err);
  }
}

// Initialize group selectors after DOM load and settings are loaded
document.addEventListener('DOMContentLoaded', async () => {
  if (!document.getElementById('settingsForm')) return;

  window.initSettingsPage();
  await syncGroupSelectors();

  // Rebind collapsibles AFTER dynamic elements are added
  document.querySelectorAll('.collapsible-header').forEach(header => {
    header.addEventListener('click', () => {
      const group = header.closest('.settings-group');
      if (group) group.classList.toggle('collapsed');
    });
  });
});