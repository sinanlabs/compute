// POST /api/auth/email/verify {token, code, return_to?, watch?} → 建会话，返回 {ok, return_to}
import { preflight } from "../../_lib.js";
import { redeem } from "../_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) { const b = await request.json().catch(() => ({})); return redeem(env, request, b); }
