// 百度站长平台验证文件（sinanlab.com 那一份）。用 Function 直接 200 返回，避开 Pages 对 .html 的 308 跳转。
export function onRequest() {
  return new Response("c6622763115f65b53d07cd9a36772f09", { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}
