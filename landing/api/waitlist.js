/**
 * Vercel Serverless Function — /api/waitlist
 * Accepts POST { email } → validates → saves to Notion database
 */

const NOTION_API_KEY = process.env.NOTION_API_KEY;
const NOTION_VERSION = '2022-06-28';
const TEAM_HUB_PAGE_ID = '3215157f-7b56-8197-b73f-f0eb6fd0d129';

// Notion database ID — cached after first creation
// In production, store this in an env var: NOTION_WAITLIST_DB_ID
// We'll create it on first call if not set.
let cachedDbId = process.env.NOTION_WAITLIST_DB_ID || null;

/**
 * Simple email regex validation
 */
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).toLowerCase());
}

/**
 * Notion API helper
 */
async function notionRequest(path, method = 'GET', body = null) {
  const opts = {
    method,
    headers: {
      'Authorization': `Bearer ${NOTION_API_KEY}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`https://api.notion.com/v1${path}`, opts);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `Notion API error: ${res.status}`);
  }
  return data;
}

/**
 * Create (or retrieve) the waitlist database under Team Hub
 */
async function getOrCreateDatabase() {
  if (cachedDbId) return cachedDbId;

  // Search for an existing database with this title under Team Hub
  const search = await notionRequest('/search', 'POST', {
    query: 'Peak Overwatch Waitlist',
    filter: { value: 'database', property: 'object' },
    page_size: 5,
  });

  const existing = search.results?.find(r =>
    r.object === 'database' &&
    r.title?.[0]?.plain_text === 'Peak Overwatch Waitlist'
  );

  if (existing) {
    cachedDbId = existing.id;
    return cachedDbId;
  }

  // Create a new database
  const db = await notionRequest('/databases', 'POST', {
    parent: {
      type: 'page_id',
      page_id: TEAM_HUB_PAGE_ID,
    },
    title: [
      {
        type: 'text',
        text: { content: 'Peak Overwatch Waitlist' },
      },
    ],
    properties: {
      // Email is the title column
      Email: {
        title: {},
      },
      'Signed Up': {
        date: {},
      },
      Source: {
        select: {
          options: [
            { name: 'landing_page', color: 'red' },
            { name: 'referral', color: 'blue' },
            { name: 'organic', color: 'green' },
          ],
        },
      },
    },
  });

  cachedDbId = db.id;
  return cachedDbId;
}

/**
 * Add an email entry to the Notion waitlist database
 */
async function addToWaitlist(email) {
  const dbId = await getOrCreateDatabase();
  const now = new Date().toISOString().split('T')[0]; // YYYY-MM-DD

  await notionRequest('/pages', 'POST', {
    parent: { database_id: dbId },
    properties: {
      Email: {
        title: [{ text: { content: email } }],
      },
      'Signed Up': {
        date: { start: now },
      },
      Source: {
        select: { name: 'landing_page' },
      },
    },
  });
}

/**
 * Main handler
 */
module.exports = async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email } = req.body || {};

    if (!email) {
      return res.status(400).json({ error: 'Email is required' });
    }

    const trimmed = String(email).trim().toLowerCase();

    if (!isValidEmail(trimmed)) {
      return res.status(400).json({ error: 'Invalid email address' });
    }

    await addToWaitlist(trimmed);

    return res.status(200).json({ success: true });
  } catch (err) {
    console.error('[waitlist]', err);
    return res.status(500).json({ error: 'Failed to save email. Please try again.' });
  }
};
