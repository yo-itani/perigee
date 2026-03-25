const DEV_USER_ID = "00000000-0000-0000-0000-000000000001";
const DEV_USER_NAME = "Dev User";

interface CurrentUser {
  userId: string;
  name: string;
}

export function useCurrentUser(): CurrentUser {
  return {
    userId: DEV_USER_ID,
    name: DEV_USER_NAME,
  };
}
