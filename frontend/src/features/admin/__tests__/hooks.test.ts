import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "@/api/client";

// -- Mock setup ---------------------------------------------------------------

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();

vi.mock("@/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
      put: (...args: unknown[]) => mockPut(...args),
      delete: vi.fn(),
    },
  };
});

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    userId: "00000000-0000-0000-0000-000000000001",
    name: "Dev User",
    role: "admin",
  }),
}));

const TEST_USER_ID = "00000000-0000-0000-0000-000000000001";

beforeEach(() => {
  vi.clearAllMocks();
});

// -- useUsers -----------------------------------------------------------------

describe("useUsers", () => {
  it("fetches users on mount and returns data", async () => {
    const mockResponse = {
      users: [
        {
          id: "u1",
          name: "User 1",
          email: "u1@example.com",
          role: "admin",
          is_active: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      total: 1,
    };
    mockGet.mockResolvedValueOnce(mockResponse);

    const { useUsers } = await import("../hooks/useUsers");
    const { result } = renderHook(() => useUsers());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith(
      "/users?offset=0&limit=20",
      TEST_USER_ID,
    );
    expect(result.current.users).toEqual(mockResponse.users);
    expect(result.current.total).toBe(1);
    expect(result.current.error).toBeNull();
  });

  it("sets error when API call fails", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(403, "Forbidden", {}));

    const { useUsers } = await import("../hooks/useUsers");
    const { result } = renderHook(() => useUsers());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.users).toEqual([]);
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect(result.current.error?.status).toBe(403);
  });
});

// -- useCreateUser ------------------------------------------------------------

describe("useCreateUser", () => {
  it("calls API and returns user on success", async () => {
    const mockUser = {
      id: "u2",
      name: "New User",
      email: "new@example.com",
      role: "member",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockPost.mockResolvedValueOnce(mockUser);

    const { useCreateUser } = await import("../hooks/useCreateUser");
    const { result } = renderHook(() => useCreateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.createUser({
        name: "New User",
        email: "new@example.com",
        role: "member",
      });
    });

    expect(mockPost).toHaveBeenCalledWith("/users", TEST_USER_ID, {
      name: "New User",
      email: "new@example.com",
      role: "member",
    });
    expect(response).toEqual(mockUser);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on failure", async () => {
    mockPost.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useCreateUser } = await import("../hooks/useCreateUser");
    const { result } = renderHook(() => useCreateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.createUser({
        name: "Fail",
        email: "fail@example.com",
        role: "member",
      });
    });

    expect(response).toBeNull();
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect(result.current.error?.status).toBe(400);
  });
});

// -- useUpdateUser ------------------------------------------------------------

describe("useUpdateUser", () => {
  it("calls API and returns user on success", async () => {
    const mockUser = {
      id: "u1",
      name: "Updated",
      email: "u1@example.com",
      role: "admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    };
    mockPut.mockResolvedValueOnce(mockUser);

    const { useUpdateUser } = await import("../hooks/useUpdateUser");
    const { result } = renderHook(() => useUpdateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.updateUser("u1", {
        name: "Updated",
        email: "u1@example.com",
        role: "admin",
      });
    });

    expect(mockPut).toHaveBeenCalledWith("/users/u1", TEST_USER_ID, {
      name: "Updated",
      email: "u1@example.com",
      role: "admin",
    });
    expect(response).toEqual(mockUser);
    expect(result.current.error).toBeNull();
  });

  it("sets error and returns null on failure", async () => {
    mockPut.mockRejectedValueOnce(new ApiError(409, "Conflict", {}));

    const { useUpdateUser } = await import("../hooks/useUpdateUser");
    const { result } = renderHook(() => useUpdateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.updateUser("u1", {
        name: "Fail",
        email: "fail@example.com",
        role: "admin",
      });
    });

    expect(response).toBeNull();
    expect(result.current.error?.status).toBe(409);
  });
});

// -- useDeactivateUser --------------------------------------------------------

describe("useDeactivateUser", () => {
  it("calls API and returns user on success", async () => {
    const mockUser = {
      id: "u1",
      name: "User",
      email: "u1@example.com",
      role: "member",
      is_active: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    };
    mockPut.mockResolvedValueOnce(mockUser);

    const { useDeactivateUser } = await import("../hooks/useDeactivateUser");
    const { result } = renderHook(() => useDeactivateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.deactivateUser("u1");
    });

    expect(mockPut).toHaveBeenCalledWith("/users/u1/deactivate", TEST_USER_ID);
    expect(response).toEqual(mockUser);
  });

  it("sets error and returns null on failure", async () => {
    mockPut.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useDeactivateUser } = await import("../hooks/useDeactivateUser");
    const { result } = renderHook(() => useDeactivateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.deactivateUser("u1");
    });

    expect(response).toBeNull();
    expect(result.current.error?.status).toBe(400);
  });
});

// -- useActivateUser ----------------------------------------------------------

describe("useActivateUser", () => {
  it("calls API and returns user on success", async () => {
    const mockUser = {
      id: "u1",
      name: "User",
      email: "u1@example.com",
      role: "member",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    };
    mockPut.mockResolvedValueOnce(mockUser);

    const { useActivateUser } = await import("../hooks/useActivateUser");
    const { result } = renderHook(() => useActivateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.activateUser("u1");
    });

    expect(mockPut).toHaveBeenCalledWith("/users/u1/activate", TEST_USER_ID);
    expect(response).toEqual(mockUser);
  });

  it("sets error and returns null on failure", async () => {
    mockPut.mockRejectedValueOnce(new ApiError(400, "Bad Request", {}));

    const { useActivateUser } = await import("../hooks/useActivateUser");
    const { result } = renderHook(() => useActivateUser());

    let response: unknown;
    await act(async () => {
      response = await result.current.activateUser("u1");
    });

    expect(response).toBeNull();
    expect(result.current.error?.status).toBe(400);
  });
});
