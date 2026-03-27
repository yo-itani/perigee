export interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "member";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UsersResponse {
  users: User[];
  total: number;
}

export interface CreateUserPayload {
  name: string;
  email: string;
  role: "admin" | "member";
}

export interface UpdateUserPayload {
  name: string;
  email: string;
  role: "admin" | "member";
}
