import { useQuery } from "@tanstack/react-query";
import { auth } from "../api/client";

export function useAuthStatus() {
  return useQuery({
    queryKey: ["auth", "status"],
    queryFn: () => auth.status(),
    staleTime: 60_000,
  });
}
