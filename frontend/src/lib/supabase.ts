import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://xjragvyzlailmtfwjfnm.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "sb_publishable_ShxAT_hZy_0hMbhdceiw0A_7zB8Xjmq";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
