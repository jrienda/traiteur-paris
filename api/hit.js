// Anonymous visit counter: stores only time (UTC, minute) + country. No IP, no cookie, no identifier.
// Appends one line to stats/YYYY-MM-DD.jsonl on the `stats` branch of the repo (GitHub Contents API).
// Needs Vercel env var GITHUB_TOKEN (fine-grained, this repo only, Contents: read & write).
const REPO = process.env.STATS_REPO || 'jrienda/traiteur-paris';
const BRANCH = 'stats';
const BOT = /bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|whatsapp|telegram/i;

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') return res.status(405).end();
  const ua = req.headers['user-agent'] || '';
  const token = process.env.GITHUB_TOKEN;
  if (!token || BOT.test(ua)) return res.status(204).end();
  const country = String(req.headers['x-vercel-ip-country'] || '??').slice(0, 2).toUpperCase();
  const now = new Date();
  const day = now.toISOString().slice(0, 10), t = now.toISOString().slice(11, 16);
  const line = JSON.stringify({ t, c: country }) + '\n';
  const url = `https://api.github.com/repos/${REPO}/contents/stats/${day}.jsonl`;
  const H = { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'User-Agent': 'traiteur-stats' };
  for (let i = 0; i < 4; i++) {
    const g = await fetch(`${url}?ref=${BRANCH}`, { headers: H });
    let sha, body = '';
    if (g.ok) { const j = await g.json(); sha = j.sha; body = Buffer.from(j.content, 'base64').toString('utf8'); }
    const p = await fetch(url, { method: 'PUT', headers: H, body: JSON.stringify({
      message: `visit ${day} ${t} ${country}`, branch: BRANCH, sha,
      content: Buffer.from(body + line, 'utf8').toString('base64') }) });
    if (p.ok) break;
    if (p.status !== 409 && p.status !== 422) break;   // sha race -> retry
  }
  return res.status(204).end();
};
