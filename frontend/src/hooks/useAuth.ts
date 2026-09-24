import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api, { clearToken, getToken, setToken } from "@/lib/api";
import type { User } from "@/lib/types";

export const useAuth = () => {
  const queryClient = useQueryClient();

  const loginMutation = useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const formData = new URLSearchParams();
      formData.append("username", credentials.email);
      formData.append("password", credentials.password);

      const { data } = await api.post("/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      return data as { access_token: string };
    },
    onSuccess: (data) => {
      setToken(data.access_token);
      queryClient.invalidateQueries({ queryKey: ["user"] });
    },
  });

  // Registration signs the user in directly: re-entering credentials typed
  // seconds ago is a step with no benefit.
  const registerMutation = useMutation({
    mutationFn: async (user: { name: string; email: string; password: string }) => {
      const { data } = await api.post("/register", user);
      return data as { user: User; access_token: string };
    },
    onSuccess: (data) => {
      if (data.access_token) setToken(data.access_token);
      queryClient.setQueryData(["user"], data.user);
      queryClient.invalidateQueries({ queryKey: ["user"] });
    },
  });

  const userQuery = useQuery<User | null>({
    queryKey: ["user"],
    queryFn: async () => {
      if (!getToken()) return null;
      try {
        const { data } = await api.get("/users/me");
        return data as User;
      } catch {
        clearToken();
        return null;
      }
    },
    retry: false,
  });

  const logout = () => {
    clearToken();
    queryClient.clear();
    queryClient.setQueryData(["user"], null);
  };

  return {
    login: loginMutation,
    register: registerMutation,
    user: userQuery.data ?? null,
    isLoading: userQuery.isLoading,
    logout,
  };
};
