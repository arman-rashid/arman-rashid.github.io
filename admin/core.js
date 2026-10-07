/* Site Studio core — parsing and rebuilding index.html. Pure functions, no DOM. */
(function (root) {
  const DATA_OPEN = /<script[^>]*id="site-data"[^>]*>/;
  const NEWS_HEAD = 'const news = [';

  // Find the index of the bracket that closes the one at `start`, skipping string contents.
  function matchBracket(src, start) {
    let depth = 0, q = null;
    for (let i = start; i < src.length; i++) {
      const c = src[i];
      if (q) {
        if (c === '\\') { i++; continue; }
        if (c === q) q = null;
        continue;
      }
      if (c === '"' || c === "'" || c === '`') { q = c; continue; }
      if (c === '[') depth++;
      else if (c === ']') { depth--; if (depth === 0) return i; }
    }
    return -1;
  }

  function parseIndex(html) {
    const m = DATA_OPEN.exec(html);
    if (!m) throw new Error('No <script id="site-data"> block found in index.html');
    const dStart = m.index + m[0].length;
    const dEnd = html.indexOf('</script>', dStart);
    if (dEnd < 0) throw new Error('site-data block is not closed');
    const data = JSON.parse(html.slice(dStart, dEnd));

    const nHead = html.indexOf(NEWS_HEAD);
    if (nHead < 0) throw new Error('No "const news = [" array found in index.html');
    const aStart = nHead + NEWS_HEAD.length - 1;
    const aEnd = matchBracket(html, aStart);
    if (aEnd < 0) throw new Error('news array is not closed');
    // eslint-disable-next-line no-new-func
    const news = Function('"use strict"; return (' + html.slice(aStart, aEnd + 1) + ');')();
    if (!Array.isArray(news)) throw new Error('news is not an array');

    return { data, news };
  }

  const q1 = (s) => "'" + String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n') + "'";
  const lit = (v) => v === null || v === undefined ? 'null' : typeof v === 'number' || typeof v === 'boolean' ? String(v) : q1(v);

  function serializeNews(news) {
    const rows = news.map((n) => {
      const a = n.slice();
      while (a.length > 5 && (a[a.length - 1] === undefined || a[a.length - 1] === null || a[a.length - 1] === '')) a.pop();
      return '    [' + a.map(lit).join(', ') + ']';
    });
    return '[\n' + rows.join(',\n') + '\n  ]';
  }

  function buildIndex(html, model) {
    const m = DATA_OPEN.exec(html);
    const dStart = m.index + m[0].length;
    const dEnd = html.indexOf('</script>', dStart);
    let out = html.slice(0, dStart) + '\n' + JSON.stringify(model.data, null, 1) + '\n' + html.slice(dEnd);

    const nHead = out.indexOf(NEWS_HEAD);
    const aStart = nHead + NEWS_HEAD.length - 1;
    const aEnd = matchBracket(out, aStart);
    out = out.slice(0, aStart) + serializeNews(model.news) + out.slice(aEnd + 1);
    return out;
  }

  // Crossref → publication record in the site's own format
  function initials(given) {
    return String(given || '').split(/[\s-]+/).filter(Boolean).map((w) => w[0].toUpperCase()).join('');
  }
  function fromCrossref(msg, me) {
    me = me || { family: 'Rashid', short: 'U. Rashid', given: /^u/i };
    const strip = (s) => String(s || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
    const authors = (msg.author || []).map((a) => {
      if (a.family && a.family.toLowerCase() === me.family.toLowerCase() && me.given.test(a.given || '')) return me.short;
      return [a.family, initials(a.given)].filter(Boolean).join(' ') || a.name || '';
    }).join(', ');
    const dp = (msg.published || msg.issued || msg['published-print'] || msg['published-online'] || {})['date-parts'];
    const y = dp && dp[0] && dp[0][0];
    const jName = strip((msg['short-container-title'] || [])[0] || (msg['container-title'] || [])[0]);
    const page = (msg.page || msg['article-number'] || '').replace(/-/g, '–');
    const j = [jName + (y ? ' ' + y : ''), msg.volume, msg.issue, page].filter(Boolean).join(', ');
    const full = strip((msg['container-title'] || [])[0]).toLowerCase();
    const k = /journal of the american chemical society|j\. ?am\. ?chem/.test(full + ' ' + jName.toLowerCase()) ? 'jacs'
      : /angew/.test(full + ' ' + jName.toLowerCase()) ? 'angew' : 'other';
    const first = (msg.author || [])[0];
    const f = first && first.family && first.family.toLowerCase() === me.family.toLowerCase() ? 1 : undefined;
    return { y, t: strip((msg.title || [])[0]), a: authors, j, k, f, doi: msg.DOI };
  }

  const api = { parseIndex, buildIndex, serializeNews, matchBracket, fromCrossref };
  if (typeof module !== 'undefined') module.exports = api; else root.Core = api;
})(this);
