// 百度站长平台验证文件（robo.sinanlab.com 那一份）。用 Function 直接 200 返回，避开 Pages 对 .html 的 308 跳转。
export function onRequest() {
  return new Response("a49e479c75602fcca1c64581d6e5fbf1", { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}
