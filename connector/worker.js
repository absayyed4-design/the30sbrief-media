// Facebook Page MCP server for Cloudflare Workers (free plan)
// Secrets to set in Cloudflare: ACCESS_KEY, TOKEN_30SBRIEF, TOKEN_OVERTHINKER, TOKEN_HEYPUNE, TOKEN_ONTHISDAY
// Connector URL for Claude: https://<your-worker>.workers.dev/mcp/<ACCESS_KEY>

function loadPages(env) {
  const pages = {
    "the30sbrief": { id: "1413354608527260", token: env.TOKEN_30SBRIEF },
    "certifiedoverthinker": { id: "1222360100960819", token: env.TOKEN_OVERTHINKER },
    "heypune": { id: "517710101428239", token: env.TOKEN_HEYPUNE },
    "onthisdayusa": { id: "1351686401369959", token: env.TOKEN_ONTHISDAY },
  };
  for (const k of Object.keys(pages)) if (!pages[k].token) delete pages[k];
  return pages;
}

const VERSION = "v26.0";
const GRAPH = `https://graph.facebook.com/${VERSION}`;

const page = { page: { type: "string", description: "Page key from list_pages" } };
const when = { schedule_time: { type: "integer", description: "Unix seconds, 10 min to 30 days ahead. Omit to publish now." } };

const TOOLS = [
  { name: "list_pages", description: "List the Facebook pages this connector manages.",
    inputSchema: { type: "object", properties: {} } },

  { name: "post_text", description: "Publish or schedule a text/link post on a page.",
    inputSchema: { type: "object", properties: { ...page, message: { type: "string" }, link: { type: "string" }, ...when }, required: ["page", "message"] } },

  { name: "post_photo", description: "Publish or schedule a photo from a public image URL, with caption.",
    inputSchema: { type: "object", properties: { ...page, image_url: { type: "string" }, caption: { type: "string" }, ...when }, required: ["page", "image_url"] } },

  { name: "post_video", description: "Publish or schedule a normal (non-Reel) video from a public video URL.",
    inputSchema: { type: "object", properties: { ...page, video_url: { type: "string" }, title: { type: "string" }, description: { type: "string" }, ...when }, required: ["page", "video_url"] } },

  { name: "post_reel", description: "Publish or schedule a Reel from a public MP4 URL (vertical 9:16, 3-90 sec).",
    inputSchema: { type: "object", properties: { ...page, video_url: { type: "string" }, description: { type: "string" }, ...when }, required: ["page", "video_url"] } },

  { name: "set_reel_thumbnail", description: "Set a custom cover image (public image URL, 9:16 JPG/PNG) on a Reel or video by its video_id.",
    inputSchema: { type: "object", properties: { ...page, video_id: { type: "string" }, image_url: { type: "string" } }, required: ["page", "video_id", "image_url"] } },

  { name: "video_status", description: "Check upload/processing/publishing status of a Reel or video by video_id.",
    inputSchema: { type: "object", properties: { ...page, video_id: { type: "string" } }, required: ["page", "video_id"] } },

  { name: "list_posts", description: "List recent published posts on a page.",
    inputSchema: { type: "object", properties: { ...page, limit: { type: "integer" } }, required: ["page"] } },

  { name: "list_scheduled", description: "List scheduled (not yet published) posts on a page.",
    inputSchema: { type: "object", properties: { ...page }, required: ["page"] } },

  { name: "publish_scheduled_now", description: "Publish a scheduled post immediately.",
    inputSchema: { type: "object", properties: { ...page, post_id: { type: "string" } }, required: ["page", "post_id"] } },

  { name: "edit_post", description: "Edit the text of an existing post.",
    inputSchema: { type: "object", properties: { ...page, post_id: { type: "string" }, message: { type: "string" } }, required: ["page", "post_id", "message"] } },

  { name: "delete_post", description: "Delete a post, photo or video from the page. Permanent.",
    inputSchema: { type: "object", properties: { ...page, post_id: { type: "string" } }, required: ["page", "post_id"] } },

  { name: "list_comments", description: "List comments on a post (newest first).",
    inputSchema: { type: "object", properties: { ...page, post_id: { type: "string" }, limit: { type: "integer" } }, required: ["page", "post_id"] } },

  { name: "reply_comment", description: "Reply to a comment as the page.",
    inputSchema: { type: "object", properties: { ...page, comment_id: { type: "string" }, message: { type: "string" } }, required: ["page", "comment_id", "message"] } },

  { name: "comment_on_post", description: "Add a top-level comment on a post as the page.",
    inputSchema: { type: "object", properties: { ...page, post_id: { type: "string" }, message: { type: "string" } }, required: ["page", "post_id", "message"] } },

  { name: "hide_comment", description: "Hide or unhide a comment.",
    inputSchema: { type: "object", properties: { ...page, comment_id: { type: "string" }, hidden: { type: "boolean" } }, required: ["page", "comment_id", "hidden"] } },

  { name: "delete_comment", description: "Delete a comment. Permanent.",
    inputSchema: { type: "object", properties: { ...page, comment_id: { type: "string" } }, required: ["page", "comment_id"] } },

  { name: "post_insights", description: "Get reach/engagement numbers for a post.",
    inputSchema: { type: "object", properties: { ...page, post_id: { type: "string" } }, required: ["page", "post_id"] } },
];

async function graph(path, token, params = {}, method = "POST") {
  const url = new URL(GRAPH + path);
  const body = new URLSearchParams({ ...params, access_token: token });
  let res;
  if (method === "GET" || method === "DELETE") {
    body.forEach((v, k) => url.searchParams.set(k, v));
    res = await fetch(url, { method });
  } else {
    res = await fetch(url, { method: "POST", body });
  }
  const data = await res.json();
  if (data.error) throw new Error(data.error.message);
  return data;
}

function sched(params, t) {
  if (t) {
    params.published = "false";
    params.scheduled_publish_time = String(t);
  }
  return params;
}

async function runTool(name, a, pages) {
  if (name === "list_pages") return Object.keys(pages);
  const p = pages[a.page];
  if (!p) throw new Error("Unknown page. Available: " + Object.keys(pages).join(", "));
  const t = p.token;

  switch (name) {
    case "post_text": {
      const params = { message: a.message };
      if (a.link) params.link = a.link;
      return graph(`/${p.id}/feed`, t, sched(params, a.schedule_time));
    }
    case "post_photo": {
      const params = { url: a.image_url };
      if (a.caption) params.caption = a.caption;
      return graph(`/${p.id}/photos`, t, sched(params, a.schedule_time));
    }
    case "post_video": {
      const params = { file_url: a.video_url };
      if (a.title) params.title = a.title;
      if (a.description) params.description = a.description;
      return graph(`/${p.id}/videos`, t, sched(params, a.schedule_time));
    }
    case "post_reel": {
      const start = await graph(`/${p.id}/video_reels`, t, { upload_phase: "start" });
      const up = await fetch(`https://rupload.facebook.com/video-upload/${VERSION}/${start.video_id}`, {
        method: "POST",
        headers: { Authorization: `OAuth ${t}`, file_url: a.video_url },
      });
      const upData = await up.json();
      if (!upData.success) throw new Error("Upload failed: " + JSON.stringify(upData));
      const finish = {
        upload_phase: "finish",
        video_id: start.video_id,
        video_state: a.schedule_time ? "SCHEDULED" : "PUBLISHED",
      };
      if (a.description) finish.description = a.description;
      if (a.schedule_time) finish.scheduled_publish_time = String(a.schedule_time);
      const done = await graph(`/${p.id}/video_reels`, t, finish);
      return { video_id: start.video_id, ...done };
    }
    case "set_reel_thumbnail": {
      const img = await fetch(a.image_url);
      if (!img.ok) throw new Error("Could not download image: HTTP " + img.status);
      const form = new FormData();
      form.append("source", new Blob([await img.arrayBuffer()], { type: img.headers.get("content-type") || "image/jpeg" }), "cover.jpg");
      form.append("is_preferred", "true");
      form.append("access_token", t);
      const res = await fetch(`${GRAPH}/${a.video_id}/thumbnails`, { method: "POST", body: form });
      const data = await res.json();
      if (data.error) throw new Error(data.error.message);
      return data;
    }
    case "video_status":
      return graph(`/${a.video_id}`, t, { fields: "status,permalink_url,published,created_time" }, "GET");
    case "list_posts":
      return graph(`/${p.id}/posts`, t, {
        fields: "id,message,created_time,permalink_url,comments.summary(true).limit(0),reactions.summary(true).limit(0)",
        limit: String(a.limit || 10),
      }, "GET");
    case "list_scheduled":
      return graph(`/${p.id}/scheduled_posts`, t, { fields: "id,message,scheduled_publish_time" }, "GET");
    case "publish_scheduled_now":
      return graph(`/${a.post_id}`, t, { is_published: "true" });
    case "edit_post":
      return graph(`/${a.post_id}`, t, { message: a.message });
    case "delete_post":
      return graph(`/${a.post_id}`, t, {}, "DELETE");
    case "list_comments":
      return graph(`/${a.post_id}/comments`, t, {
        fields: "id,from,message,created_time,comment_count,is_hidden",
        order: "reverse_chronological",
        limit: String(a.limit || 25),
      }, "GET");
    case "reply_comment":
      return graph(`/${a.comment_id}/comments`, t, { message: a.message });
    case "comment_on_post":
      return graph(`/${a.post_id}/comments`, t, { message: a.message });
    case "hide_comment":
      return graph(`/${a.comment_id}`, t, { is_hidden: String(a.hidden) });
    case "delete_comment":
      return graph(`/${a.comment_id}`, t, {}, "DELETE");
    case "post_insights":
      return graph(`/${a.post_id}/insights`, t, {
        metric: "post_impressions_unique,post_clicks,post_reactions_by_type_total",
      }, "GET");
    default:
      throw new Error("Unknown tool: " + name);
  }
}

// Never let a page token leave the worker, whatever Facebook puts in a response.
function scrub(text, pages) {
  let s = String(text);
  for (const p of Object.values(pages)) if (p.token) s = s.split(p.token).join("[redacted]");
  return s.replace(/access_token=[^&"\s]+/g, "access_token=[redacted]");
}

function rpc(id, result) {
  return Response.json({ jsonrpc: "2.0", id, result });
}

const PRIVACY_HTML = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Privacy Policy - ABD Page Publisher</title>
<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;line-height:1.6;color:#222}</style></head><body>
<h1>Privacy Policy</h1><p><b>App:</b> ABD Page Publisher<br><b>Owner:</b> Abdullah Sayyed, Pune, India<br><b>Contact:</b> absayyed4@gmail.com</p>
<p>ABD Page Publisher is a private tool used only by its owner to publish and manage content on Facebook Pages that the owner administers (The 30s Brief, On This Day USA, Certified Overthinker, Hey Pune).</p>
<h2>What data we use</h2><p>The app uses Page access tokens granted by the Page owner to publish posts, Reels and photos, read post insights and manage comments on those Pages. It does not collect, store or sell personal data of Facebook users.</p>
<h2>Data storage</h2><p>Access tokens are stored encrypted as server secrets and are never shared. No user data is kept after a request is completed.</p>
<h2>Data deletion</h2><p>Because the app stores no personal user data, there is nothing to delete. To request removal of any information or to ask a question, email absayyed4@gmail.com and we will respond within 30 days. You can also remove the app at any time in Facebook Settings, Business Integrations.</p>
<p>Last updated: October 2026</p></body></html>`;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/privacy" || url.pathname === "/data-deletion")
      return new Response(PRIVACY_HTML, { headers: { "content-type": "text/html; charset=utf-8" } });
    if (url.pathname !== `/mcp/${env.ACCESS_KEY}`) return new Response("Not found", { status: 404 });
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });

    const msg = await request.json();
    if (msg.id === undefined) return new Response(null, { status: 202 }); // notifications

    const pages = loadPages(env);

    switch (msg.method) {
      case "initialize":
        return rpc(msg.id, {
          protocolVersion: msg.params?.protocolVersion || "2025-06-18",
          capabilities: { tools: {} },
          serverInfo: { name: "facebook-pages", version: "1.1.0" },
        });
      case "ping":
        return rpc(msg.id, {});
      case "tools/list":
        return rpc(msg.id, { tools: TOOLS });
      case "tools/call":
        try {
          const out = await runTool(msg.params.name, msg.params.arguments || {}, pages);
          if (out && typeof out === "object") delete out.paging; // paging links carry the access token
          return rpc(msg.id, { content: [{ type: "text", text: scrub(JSON.stringify(out), pages) }] });
        } catch (e) {
          return rpc(msg.id, { content: [{ type: "text", text: "Error: " + scrub(e.message, pages) }], isError: true });
        }
      default:
        return Response.json({ jsonrpc: "2.0", id: msg.id, error: { code: -32601, message: "Method not found" } });
    }
  },
};
