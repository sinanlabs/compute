// 百度站长平台验证文件。Pages 会把静态 .html 308 到无后缀地址，百度的校验器不跟随跳转，所以用 Function 直接 200 返回。
export function onRequest() {
  return new Response("04c1e8a60f06cc85ac333a9dc3f7e849", { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}
