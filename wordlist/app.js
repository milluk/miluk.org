import { wordlist } from './data.js';

// State
let currentMode = 'english';
let currentFilter = 'all';
let searchQuery = '';
let activeLetters = new Set();
let entryIdMap = new Map(); // Maps word index to unique ID
let observer = null; // IntersectionObserver for hash updates

// Helper: Clean text for display (fix diacritics)
function cleanForDisplay(str) {
    if (!str) return '';
    // Replace unreleased glottal stop ʔ̚ (U+0294 + U+031A) with plain ʔ (U+0294)
    return str.replace(/ʔ̚/g, 'ʔ');
}

// Helper: Clean text for sorting (strip glottal stops and zero-width chars)
function cleanForSort(str) {
    if (!str) return '';
    // Strip leading whitespace and zero-width characters
    str = str.replace(/^[\s\u200B\uFEFF\u00A0]+/, '');
    // Strip glottal stop for sorting purposes
    str = str.replace(/ʔ/g, '');
    // Map æ (ash) to e for sorting (not a)
    str = str.replace(/æ/g, 'e');
    str = str.replace(/Æ/g, 'E');
    return str;
}

// Helper: Get first letter for alphabetical grouping
function getFirstLetter(str) {
    const cleaned = cleanForSort(str);
    if (!cleaned) return '';
    return cleaned.charAt(0).toUpperCase();
}

// Helper: Generate URL-safe ID from headword
function headwordToId(headword) {
    return headword
        .toLowerCase()
        .trim()
        .replace(/\s+/g, '-')
        .replace(/[^a-z0-9\-]/g, '');
}

// Build ID map with deduplication
function buildIdMap(words) {
    entryIdMap.clear();
    const idCounts = new Map();

    // First pass: count occurrences of each base ID
    words.forEach(word => {
        const baseId = headwordToId(word.headword);
        idCounts.set(baseId, (idCounts.get(baseId) || 0) + 1);
    });

    // Second pass: assign unique IDs
    const idAssigned = new Map();
    words.forEach((word, index) => {
        const baseId = headwordToId(word.headword);
        const count = idCounts.get(baseId);

        if (count === 1) {
            // Unique headword, use as-is
            entryIdMap.set(index, baseId);
        } else {
            // Duplicate headword, assign suffix
            const assignedCount = idAssigned.get(baseId) || 0;
            if (assignedCount === 0) {
                // First occurrence: no suffix
                entryIdMap.set(index, baseId);
            } else {
                // Subsequent occurrences: add suffix
                entryIdMap.set(index, `${baseId}-${assignedCount}`);
            }
            idAssigned.set(baseId, assignedCount + 1);
        }
    });
}

// Get entry ID for a word at given index
function getEntryId(index) {
    return entryIdMap.get(index) || '';
}

// DOM elements
const wordlistEl = document.getElementById('wordlist');
const searchEl = document.getElementById('search');
const alphaIndexEl = document.getElementById('alphaIndex');
const entryCountEl = document.getElementById('entryCount');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupModeTabs();
    setupFilters();
    setupSearch();
    render();
    handleInitialHash();
});

// Handle initial URL hash on page load
function handleInitialHash() {
    const hash = window.location.hash.slice(1);
    if (hash) {
        setTimeout(() => {
            scrollToEntry(hash);
        }, 100);
    }
}

// Scroll to entry by ID and expand it
function scrollToEntry(id) {
    const entry = document.getElementById(id);
    if (entry) {
        entry.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Expand all expandable sections in this entry
        entry.querySelectorAll('.expand-toggle').forEach(toggle => {
            toggle.classList.add('open');
            toggle.nextElementSibling.classList.add('open');
        });
        // Briefly highlight the entry
        entry.classList.add('highlighted');
        setTimeout(() => entry.classList.remove('highlighted'), 2000);
    }
}

// Setup IntersectionObserver to update hash on scroll
function setupScrollObserver() {
    // Disconnect previous observer if exists
    if (observer) {
        observer.disconnect();
    }

    const cards = document.querySelectorAll('.word-card[id]');
    if (cards.length === 0) return;

    let isUserScrolling = true;
    let scrollTimeout;

    observer = new IntersectionObserver((entries) => {
        if (!isUserScrolling) return;

        // Find the most visible entry
        let mostVisible = null;
        let maxRatio = 0;

        entries.forEach(entry => {
            if (entry.isIntersecting && entry.intersectionRatio > maxRatio) {
                maxRatio = entry.intersectionRatio;
                mostVisible = entry.target;
            }
        });

        if (mostVisible && mostVisible.id) {
            // Update URL hash without triggering scroll
            const newHash = '#' + mostVisible.id;
            if (window.location.hash !== newHash) {
                history.replaceState(null, '', newHash);
            }
        }
    }, {
        root: null,
        rootMargin: '-20% 0px -60% 0px',
        threshold: [0, 0.25, 0.5, 0.75, 1]
    });

    cards.forEach(card => observer.observe(card));
}

// Copy entry URL to clipboard
function copyEntryUrl(id, btn) {
    const url = window.location.origin + window.location.pathname + '#' + id;
    navigator.clipboard.writeText(url).then(() => {
        // Show feedback
        const originalText = btn.textContent;
        btn.textContent = '✓';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('copied');
        }, 1500);
    }).catch(() => {
        // Fallback: select the URL
        prompt('Copy this URL:', url);
    });
}

// Expose to global scope for onclick
window.copyEntryUrl = copyEntryUrl;

// Setup mode tabs
function setupModeTabs() {
    document.querySelectorAll('.mode-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentMode = tab.dataset.mode;
            render();
        });
    });
}

// Setup filter buttons
function setupFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            render();
        });
    });
}

// Setup search
function setupSearch() {
    searchEl.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        render();
    });
}

// Get Miluk form for sorting/display
function getMilukForm(word) {
    const table = word.pronunciation_table || {};
    if (table.lolly && table.lolly.americanist) {
        // Extract first bracketed form or first word
        const am = table.lolly.americanist;
        const match = am.match(/\[([^\]]+)\]/);
        return match ? match[1] : am.split(',')[0].trim();
    }
    if (table.annie && table.annie.jacobs) {
        return table.annie.jacobs.split('\n')[0].split('(')[0].trim();
    }
    return '';
}

// Check if word has LHM data
function hasLHM(word) {
    return word.pronunciation_table?.lolly != null;
}

// Check if word has AMP data
function hasAMP(word) {
    return word.pronunciation_table?.annie != null;
}

// Filter words
function filterWords() {
    let filtered = [...wordlist];

    // Apply speaker filter
    if (currentFilter === 'with-amp') {
        filtered = filtered.filter(w => hasAMP(w));
    } else if (currentFilter === 'lhm-only') {
        filtered = filtered.filter(w => hasLHM(w) && !hasAMP(w));
    }

    // Apply search
    if (searchQuery) {
        filtered = filtered.filter(w => {
            const headword = w.headword.toLowerCase();
            const miluk = getMilukForm(w).toLowerCase();
            const variants = (w.pronunciation_variants || []).join(' ').toLowerCase();
            return headword.includes(searchQuery) ||
                   miluk.includes(searchQuery) ||
                   variants.includes(searchQuery);
        });
    }

    // Sort (using cleaned strings for proper alphabetical order)
    if (currentMode === 'english') {
        filtered.sort((a, b) => cleanForSort(a.headword).localeCompare(cleanForSort(b.headword)));
    } else {
        filtered.sort((a, b) => cleanForSort(getMilukForm(a)).localeCompare(cleanForSort(getMilukForm(b))));
    }

    return filtered;
}

// Build alphabet index
function buildAlphaIndex(words) {
    activeLetters.clear();

    words.forEach(w => {
        const sortKey = currentMode === 'english'
            ? w.headword
            : getMilukForm(w);
        const key = getFirstLetter(sortKey);
        if (/[A-ZƔɢQq]/i.test(key)) {
            activeLetters.add(key.toUpperCase());
        }
    });

    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    alphaIndexEl.innerHTML = alphabet.map(letter => {
        const isActive = activeLetters.has(letter);
        return `<button class="alpha-btn ${isActive ? '' : 'disabled'}"
                        data-letter="${letter}"
                        ${isActive ? '' : 'disabled'}>${letter}</button>`;
    }).join('');

    // Add click handlers
    alphaIndexEl.querySelectorAll('.alpha-btn:not(.disabled)').forEach(btn => {
        btn.addEventListener('click', () => {
            const letter = btn.dataset.letter;
            const target = document.querySelector(`[data-letter-section="${letter}"]`);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// Render pronunciation table
function renderPronunciationTable(word) {
    const table = word.pronunciation_table || {};
    const lolly = table.lolly;
    const annie = table.annie;

    if (!lolly && !annie) return '';

    const hasLollyData = lolly !== null;
    const hasAnnieData = annie !== null;

    let html = '<div class="pronunciation-table-section"><table class="pronunciation-table">';

    // Header row
    html += '<thead><tr>';
    if (hasLollyData) {
        html += '<th colspan="2" class="speaker-header">Lolly Metcalf\'s Miluk</th>';
    }
    if (hasAnnieData) {
        html += '<th colspan="2" class="speaker-header">Annie Miner Peterson\'s Miluk</th>';
    }
    html += '</tr><tr>';
    if (hasLollyData) {
        html += '<th>Americanist</th><th>IPA</th>';
    }
    if (hasAnnieData) {
        html += '<th>Jacobs</th><th>Am. & IPA</th>';
    }
    html += '</tr></thead>';

    // Data row
    html += '<tbody><tr>';
    if (hasLollyData) {
        html += `<td>${escapeHtml(lolly.americanist || '')}</td>`;
        html += `<td>${escapeHtml(lolly.ipa || '')}</td>`;
    }
    if (hasAnnieData) {
        html += `<td>${escapeHtml(annie.jacobs || '')}</td>`;
        html += `<td>${escapeHtml(annie.americanist_ipa || '')}</td>`;
    }
    html += '</tr></tbody></table></div>';

    return html;
}

// Extract clean SoundCloud embed URL
function cleanSoundCloudUrl(url) {
    // Handle Google redirect wrapper
    if (url.includes('google.com/url')) {
        const match = url.match(/url=([^&]+)/);
        if (match) {
            url = decodeURIComponent(match[1]);
        }
    }

    // If it's already an embed URL, use it directly
    if (url.includes('w.soundcloud.com/player')) {
        // Update color to gold
        return url.replace(/color=[^&]+/, 'color=C9952A');
    }

    // If it's an API URL, wrap it
    if (url.includes('api.soundcloud.com')) {
        return `https://w.soundcloud.com/player/?url=${encodeURIComponent(url)}&color=C9952A&auto_play=false&hide_related=true&show_comments=false&show_user=false&show_reposts=false&show_teaser=false`;
    }

    return url;
}

// Render audio embeds
function renderAudio(word) {
    const urls = word.soundcloud_urls || [];
    if (urls.length === 0) return '';

    const hasMultiple = urls.length >= 2;

    return '<div class="audio-section">' +
        urls.map((url, index) => {
            const embedUrl = cleanSoundCloudUrl(url);
            let label = '';
            if (hasMultiple) {
                label = index === 0
                    ? '<div class="audio-label">Laura Hodgkiss Metcalf Recording</div>'
                    : '<div class="audio-label">Contemporary Recording</div>';
            }
            return `<div class="audio-embed">
                ${label}
                <iframe src="${escapeHtml(embedUrl)}" height="166" allow="autoplay"></iframe>
            </div>`;
        }).join('') +
    '</div>';
}

// Render a single card
function renderCard(word, index) {
    const milukForm = getMilukForm(word);
    const isAmpOnly = !hasLHM(word) && hasAMP(word);
    const table = word.pronunciation_table || {};
    const instant = table.instant_phonetic_englishization || '';
    const notes = word.linguistics_notes || '';
    const entryId = getEntryId(index);

    let html = `<article class="word-card ${isAmpOnly ? 'amp-only' : ''}" id="${entryId}" data-headword="${escapeHtml(word.headword)}">`;

    // Header - different layout for each mode
    html += '<header class="card-header">';
    if (currentMode === 'miluk') {
        // Miluk mode: Miluk form primary, English secondary
        if (milukForm) {
            html += `<h2 class="headword miluk-primary">${escapeHtml(milukForm)}</h2>`;
        }
        html += `<div class="english-form">${escapeHtml(word.headword)}</div>`;
    } else {
        // English mode: English primary, Miluk secondary
        html += `<h2 class="headword">${escapeHtml(word.headword)}</h2>`;
        if (milukForm) {
            html += `<div class="miluk-form">${escapeHtml(milukForm)}</div>`;
        }
    }
    // Anchor link button
    html += `<button class="entry-anchor" onclick="copyEntryUrl('${entryId}', this)" title="Copy link to this entry">¶</button>`;
    if (isAmpOnly) {
        html += '<div class="amp-only-label">Jacobs texts only — no Lolly recording</div>';
    }
    html += '</header>';

    // Audio
    html += renderAudio(word);

    // Pronunciation table
    html += renderPronunciationTable(word);

    // Instant Phonetic (expandable)
    if (instant) {
        html += `<div class="expandable">
            <button class="expand-toggle" onclick="toggleExpand(this)">
                How to say it <span class="arrow">▾</span>
            </button>
            <div class="expand-content">
                <p>${escapeHtml(instant)}</p>
            </div>
        </div>`;
    }

    // Linguistics notes (expandable)
    if (notes) {
        const paragraphs = notes.split('\n\n').filter(p => p.trim());
        html += `<div class="expandable">
            <button class="expand-toggle" onclick="toggleExpand(this)">
                Scholar's notes <span class="arrow">▾</span>
            </button>
            <div class="expand-content">
                ${paragraphs.map(p => `<p>${escapeHtml(p)}</p>`).join('')}
            </div>
        </div>`;
    }

    html += '</article>';
    return html;
}

// Main render function
function render() {
    const filtered = filterWords();

    // Build ID map for filtered words
    buildIdMap(filtered);
    buildAlphaIndex(filtered);

    // Update entry count
    entryCountEl.textContent = `Showing ${filtered.length} of ${wordlist.length} entries`;

    if (filtered.length === 0) {
        wordlistEl.innerHTML = '<div class="no-results">No entries found</div>';
        return;
    }

    let html = '';
    let currentLetter = '';

    filtered.forEach((word, index) => {
        const sortKey = currentMode === 'english'
            ? word.headword
            : getMilukForm(word);
        let letter = getFirstLetter(sortKey);

        // For Miluk mode, group special characters under '#'
        if (currentMode === 'miluk' && !/[A-Z]/i.test(letter)) {
            letter = '#';
        }

        // Add letter divider
        if (letter !== currentLetter) {
            currentLetter = letter;
            const displayLetter = letter === '#' ? 'Other' : letter;
            html += `<div class="letter-divider" data-letter-section="${letter}">${displayLetter}</div>`;
        }

        html += renderCard(word, index);
    });

    wordlistEl.innerHTML = html;

    // Setup scroll observer after rendering
    setupScrollObserver();
}

// Toggle expandable sections
window.toggleExpand = function(btn) {
    btn.classList.toggle('open');
    const content = btn.nextElementSibling;
    content.classList.toggle('open');
};

// Escape HTML and clean for display
function escapeHtml(str) {
    if (!str) return '';
    return cleanForDisplay(String(str))
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\n/g, '<br>');
}
