import { preflight } from "../../_lib.js";
import { redeem } from "../_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) { const b = await request.json().catch(() => ({})); return redeem(env, request, b); }
