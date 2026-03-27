const DEV_USER_ID = "00000000-0000-0000-0000-000000000001";
const DEV_USER_NAME = "Dev User";
const DEV_USER_ROLE = "admin";

interface CurrentUser {
  userId: string;
  name: string;
  role: "admin" | "member";
}

export function useCurrentUser(): CurrentUser {
  return {
    userId: DEV_USER_ID,
    name: DEV_USER_NAME,
    role: DEV_USER_ROLE,
  };
}
