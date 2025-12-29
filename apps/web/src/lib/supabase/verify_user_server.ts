import { Session, User } from "@supabase/supabase-js";
import { createClient } from "./server";

export async function verifyUserAuthenticated(): Promise<
  { user: User; session: Session } | undefined
> {
  const supabase = createClient();

  // 先用 getUser() 验证用户真实性（服务器端验证）
  // 这消除了"getSession() could be insecure"警告
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    return undefined;
  }

  // 用户已通过服务器验证，现在可以安全获取 session
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return undefined;
  }

  return { user, session };
}
